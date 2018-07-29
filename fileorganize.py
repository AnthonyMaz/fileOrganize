import hashlib
import io
import os
import sqlite3

import magic
from blessings import Terminal
from progressive.bar import Bar
from stat import S_ISCHR, S_ISBLK, S_ISFIFO, S_ISLNK, S_ISDIR, S_ISREG, S_ISSOCK

from progressive.tree import Value, BarDescriptor, ProgressTree

try:
    RUNNING_IN_PYCHARM = os.environ['RUNNING_IN_PYCHARM']
except KeyError:
    RUNNING_IN_PYCHARM = False


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


def analyze(src, length=io.DEFAULT_BUFFER_SIZE):
    md5 = hashlib.md5()
    src = os.path.abspath(src)
    try:
        mode = os.stat(src).st_mode
        if S_ISDIR(mode):
            cur.execute('INSERT OR REPLACE INTO file_metadata (file_name, stat_type) VALUES (?, ?)',
                        (src, DIRECTORY[0]))
        elif S_ISCHR(mode):
            cur.execute('INSERT OR REPLACE INTO file_metadata (file_name, stat_type) VALUES (?, ?)',
                        (src, CHAR[0]))
        elif S_ISBLK(mode):
            cur.execute('INSERT OR REPLACE INTO file_metadata (file_name, stat_type) VALUES (?, ?)',
                        (src, BLOCK[0]))
        elif S_ISREG(mode):
            cur.execute('INSERT OR REPLACE INTO file_metadata (file_name, size, stat_type) VALUES (?, ?, ?)',
                        (src, os.path.getsize(src), REGULAR[0]))
        elif S_ISFIFO(mode):
            cur.execute('INSERT OR REPLACE INTO file_metadata (file_name, stat_type) VALUES (?, ?)',
                        (src, FIFO[0]))
        elif S_ISLNK(mode):
            cur.execute('INSERT OR REPLACE INTO file_metadata (file_name, size, stat_type) VALUES (?, ?)',
                        (src, os.path.getsize(src), SYMLINK[0]))
        elif S_ISSOCK(mode):
            cur.execute('INSERT OR REPLACE INTO file_metadata (file_name, stat_type) VALUES (?, ?)',
                        (src, SOCKET[0]))
        else:
            cur.execute('INSERT OR REPLACE INTO file_metadata (file_name, stat_type) VALUES (?, ?)',
                (src, None, UNKNOWN[0]))
    except FileNotFoundError:
        mode = os.stat(src, follow_symlinks=False).st_mode
        if S_ISLNK(mode):
            cur.execute('INSERT OR REPLACE INTO file_metadata (file_name, stat_type) VALUES (?, ?)',
                (src, BROKEN_SYMLINK[0]))

    if not S_ISREG(mode):
        return md5

    try:
        cur.execute('UPDATE file_metadata SET mime_type = ?, mime_detail = ? WHERE file_name = ?',
                    (magic.from_file(src, mime=True), magic.from_file(src), src))
        with io.open(src, mode="rb") as fd:
            for chunk in iter(lambda: fd.read(length), b''):
                md5.update(chunk)
    except OSError:
        cur.execute('UPDATE file_metadata set stat_type = ? WHERE file_name = ?',
                    (ERROR[0], src))
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
    cur.execute('CREATE TABLE file_metadata (file_name TEXT PRIMARY KEY, size INTEGER, mime_type TEXT, mime_detail TEXT, stat_type INTEGER)')


# Create the hashes table if it doesn't exist already
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='hashes'")
if not cur.fetchone():
    cur.execute('CREATE TABLE hashes (file_name TEXT PRIMARY KEY, md5_sum TEXT)')
    cur.execute('CREATE INDEX hashes_md5sums ON hashes (md5_sum)')


scan_dir = os.path.abspath('.')
print('Finding files to process in %s' % scan_dir)

exclude = {'dev', 'run', 'sys', 'proc', 'btrfs', 'tmp'}


dir_count = 0
dirs_analyzed = 0
file_count = 0
files_analyzed = 0

for root, dirs, files in os.walk(scan_dir, followlinks=False, topdown=True):
    dirs[:] = [d for d in dirs if d not in exclude]
    dir_count += len(dirs)
    file_count += len(files)

leaf_values = [Value(0) for i in range(2)]
bd_directories = dict(type=Bar, kwargs=dict(max_value=dir_count, width='50%'))
bd_files = dict(type=Bar, kwargs=dict(max_value=file_count, width='50%'))
bd_defaults = dict(type=Bar, kwargs=dict(max_value=100, width='50%', num_rep='percentage'))


test_d = {
    'Analyze files in %s' % scan_dir: {
        "Directories": BarDescriptor(value=leaf_values[0], **bd_directories),
        "Files": BarDescriptor(value=leaf_values[1], **bd_files)
    }
}

t = Terminal()
n = ProgressTree(term=t)
n.make_room(test_d)


def are_we_done():
    return files_analyzed == file_count

while not are_we_done():
    for root, dirs, files in os.walk(scan_dir, followlinks=False, topdown=True):
        dirs[:] = [d for d in dirs if d not in exclude]
        for directory_name in dirs:
            directory_name = os.path.join(root, directory_name)
            file_hash = analyze(directory_name).hexdigest()
            cur.execute('INSERT OR REPLACE INTO hashes (file_name, md5_sum) VALUES (?, ?)', (directory_name, file_hash))
            dirs_analyzed += 1
            leaf_values[0].value = dirs_analyzed


        for file_name in files:
            file_name = os.path.join(root, file_name)
            file_hash = analyze(file_name).hexdigest()
            cur.execute('INSERT OR REPLACE INTO hashes (file_name, md5_sum) VALUES (?, ?)', (file_name, file_hash))
            files_analyzed += 1
            leaf_values[1].value = files_analyzed
            if not RUNNING_IN_PYCHARM:
                n.cursor.restore()
                n.draw(test_d, BarDescriptor(bd_defaults))

conn.commit()
