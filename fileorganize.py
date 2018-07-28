import hashlib
import io
import os
import sqlite3
from progressbar import Bar, Percentage, ProgressBar
from stat import S_ISCHR, S_ISBLK, S_ISFIFO, S_ISLNK, S_ISDIR, S_ISREG, S_ISSOCK

DIRECTORY = (1, 'directory')
CHAR = (2, 'character special device file')
BLOCK = (3, 'block special device file')
REGULAR = (4, 'regular file')
FIFO = (5, 'FIFO (named pipe)')
SYMLINK = (6, 'symbolic link')
BROKEN_SYMLINK = (7, 'broken symbolic link')
SOCKET = (8, 'socket')
UNKNOWN = (9, 'unknown')
ERROR = (10, 'unknown error')


def md5sum(src, length=io.DEFAULT_BUFFER_SIZE):
    calculated = 0
    md5 = hashlib.md5()
    src = os.path.abspath(src)
    try:
        mode = os.stat(src).st_mode
        if S_ISDIR(mode):
            cur.execute('INSERT OR REPLACE INTO file_metadata (file_name, size, type) VALUES (?, ?, ?)',
                        (src, None, DIRECTORY[0]))
        elif S_ISCHR(mode):
            cur.execute('INSERT OR REPLACE INTO file_metadata (file_name, size, type) VALUES (?, ?, ?)',
                        (src, None, CHAR[0]))
        elif S_ISBLK(mode):
            cur.execute('INSERT OR REPLACE INTO file_metadata (file_name, size, type) VALUES (?, ?, ?)',
                        (src, None, BLOCK[0]))
        elif S_ISREG(mode):
            cur.execute('INSERT OR REPLACE INTO file_metadata (file_name, size, type) VALUES (?, ?, ?)',
                        (src, os.path.getsize(src), REGULAR[0]))
        elif S_ISFIFO(mode):
            cur.execute('INSERT OR REPLACE INTO file_metadata (file_name, size, type) VALUES (?, ?, ?)',
                        (src, None, FIFO[0]))
        elif S_ISLNK(mode):
            cur.execute('INSERT OR REPLACE INTO file_metadata (file_name, size, type) VALUES (?, ?, ?)',
                        (src, os.path.getsize(src), SYMLINK[0]))
        elif S_ISSOCK(mode):
            cur.execute('INSERT OR REPLACE INTO file_metadata (file_name, size, type) VALUES (?, ?, ?)',
                        (src, None, SOCKET[0]))
        else:
            cur.execute('INSERT OR REPLACE INTO file_metadata (file_name, size, type) VALUES (?, ?, ?)',
                (src, None, UNKNOWN[0]))
    except FileNotFoundError:
        mode = os.stat(src, follow_symlinks=False).st_mode
        if S_ISLNK(mode):
            cur.execute('INSERT OR REPLACE INTO file_metadata (file_name, size, type) VALUES (?, ?, ?)',
                (src, None, BROKEN_SYMLINK[0]))

    if not S_ISREG(mode):
        return md5
    else:
        size = os.path.getsize(src)

    if size > 10 * 1024 * 1024:
        print(src)
        pbar = ProgressBar(widgets=[Percentage(), Bar()], maxval=size).start()
        pbar.start()
        with io.open(src, mode="rb") as fd:
            for chunk in iter(lambda: fd.read(length), b''):
                md5.update(chunk)
                calculated += len(chunk)
                pbar.update(calculated)
        print('')
    else:
        try:
            with io.open(src, mode="rb") as fd:
                for chunk in iter(lambda: fd.read(length), b''):
                    md5.update(chunk)
        except OSError:
            pass
    return md5


db_dir = os.path.expanduser('~/.local/share/fileorganize')
if not os.path.exists(db_dir):
    os.makedirs(db_dir)
db_path = db_dir + os.sep + 'fileorganize.db'
conn = sqlite3.connect(db_path)
cur = conn.cursor()


# Create tables if they don't exist already
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='file_inode_stats'")
if not cur.fetchone():
    cur.execute('CREATE TABLE file_inode_stats (id NUMERIC , type TEXT)')
    cur.execute("INSERT INTO 'file_inode_stats' VALUES (?, ?)", (DIRECTORY[0], DIRECTORY[1]))
    cur.execute("INSERT INTO 'file_inode_stats' VALUES (?, ?)", (CHAR[0], CHAR[1]))
    cur.execute("INSERT INTO 'file_inode_stats' VALUES (?, ?)", (BLOCK[0], BLOCK[1]))
    cur.execute("INSERT INTO 'file_inode_stats' VALUES (?, ?)", (REGULAR[0], REGULAR[1]))
    cur.execute("INSERT INTO 'file_inode_stats' VALUES (?, ?)", (FIFO[0], FIFO[1]))
    cur.execute("INSERT INTO 'file_inode_stats' VALUES (?, ?)", (SYMLINK[0], SYMLINK[1]))
    cur.execute("INSERT INTO 'file_inode_stats' VALUES (?, ?)", (BROKEN_SYMLINK[0], BROKEN_SYMLINK[1]))
    cur.execute("INSERT INTO 'file_inode_stats' VALUES (?, ?)", (SOCKET[0], SOCKET[1]))
    cur.execute("INSERT INTO 'file_inode_stats' VALUES (?, ?)", (ERROR[0], ERROR[1]))


cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='file_metadata'")
if not cur.fetchone():
    cur.execute('CREATE TABLE file_metadata (file_name TEXT PRIMARY KEY, size INTEGER, type INTEGER)')
    cur.execute('CREATE INDEX file_metadata_file_name ON file_metadata(file_name)')


# Create the hashes table if it doesn't exist already
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='hashes'")
if not cur.fetchone():
    cur.execute('CREATE TABLE hashes (file_name TEXT PRIMARY KEY, md5_sum TEXT)')
    cur.execute('CREATE INDEX hashes_md5sums ON hashes (md5_sum)')


scan_dir = os.path.abspath('.')
print('Collecting MD5 sums for files in %s' % scan_dir)

exclude = {'dev', 'run', 'sys', 'proc', 'btrfs', 'tmp'}

for root, dirs, files in os.walk(scan_dir, followlinks=False, topdown=True):
    dirs[:] = [d for d in dirs if d not in exclude]
    for directory_name in dirs:
        directory_name = os.path.join(root, directory_name)
        file_hash = md5sum(directory_name).hexdigest()
        cur.execute('INSERT OR REPLACE INTO hashes (file_name, md5_sum) VALUES (?, ?)', (directory_name, file_hash))
    for file_name in files:
        file_name = os.path.join(root, file_name)
        file_hash = md5sum(file_name).hexdigest()
        cur.execute('INSERT OR REPLACE INTO hashes (file_name, md5_sum) VALUES (?, ?)', (file_name, file_hash))


conn.commit()
