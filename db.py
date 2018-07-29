import os
import sqlite3

stat_types = {
    'DIRECTORY': (1, 'directory'),
    'CHAR': (2, 'character special device file'),
    'BLOCK': (3, 'block special device file'),
    'REGULAR': (4, 'regular file'),
    'FIFO': (5, 'FIFO (named pipe)'),
    'SYMLINK': (6, 'symbolic link'),
    'BROKEN_SYMLINK': (7, 'broken symbolic link'),
    'SOCKET': (8, 'socket'),
    'UNKNOWN': (9, 'unknown'),
    'ERROR': (10, 'unknown error')
}


db_dir = os.path.expanduser('~/.local/share/fileorganize')
if not os.path.exists(db_dir):
    os.makedirs(db_dir)
db_path = db_dir + os.sep + 'fileorganize.db'
conn = sqlite3.connect(db_path)
cur = conn.cursor()


def init_database():
    """Initializes the database, if needed

    Creates a new database and tables if they don't already exist, otherwise does nothing.
    """

    # Create tables if they don't exist already
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='file_inode_stats'")
    if not cur.fetchone():
        cur.execute('CREATE TABLE file_inode_stats (id NUMERIC , type TEXT)')
        cur.execute("INSERT INTO 'file_inode_stats' VALUES (?, ?)", (stat_types['DIRECTORY'][0], stat_types['DIRECTORY'][1]))
        cur.execute("INSERT INTO 'file_inode_stats' VALUES (?, ?)", (stat_types['CHAR'][0], stat_types['CHAR'][1]))
        cur.execute("INSERT INTO 'file_inode_stats' VALUES (?, ?)", (stat_types['BLOCK'][0], stat_types['BLOCK'][1]))
        cur.execute("INSERT INTO 'file_inode_stats' VALUES (?, ?)", (stat_types['REGULAR'][0], stat_types['REGULAR'][1]))
        cur.execute("INSERT INTO 'file_inode_stats' VALUES (?, ?)", (stat_types['FIFO'][0], stat_types['FIFO'][1]))
        cur.execute("INSERT INTO 'file_inode_stats' VALUES (?, ?)", (stat_types['SYMLINK'][0], stat_types['SYMLINK'][1]))
        cur.execute("INSERT INTO 'file_inode_stats' VALUES (?, ?)", (stat_types['BROKEN_SYMLINK'][0], stat_types['BROKEN_SYMLINK'][1]))
        cur.execute("INSERT INTO 'file_inode_stats' VALUES (?, ?)", (stat_types['SOCKET'][0], stat_types['SOCKET'][1]))
        cur.execute("INSERT INTO 'file_inode_stats' VALUES (?, ?)",(stat_types['ERROR'][0], stat_types['ERROR'][1]))

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='file_metadata'")
    if not cur.fetchone():
        cur.execute('CREATE TABLE file_metadata (file_name TEXT PRIMARY KEY, extension TEXT, size INTEGER, mime_type TEXT, mime_detail TEXT, stat_type INTEGER)')

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='hashes'")
    if not cur.fetchone():
        cur.execute('CREATE TABLE hashes (file_name TEXT PRIMARY KEY, md5_sum TEXT)')
        cur.execute('CREATE INDEX hashes_md5sums ON hashes (md5_sum)')


def upsert_file_metadata(file_name, stat_type=None, size=None, extension=None, mime_type=None, mime_detail=None):
    """Upserts records into the file_metadata table

    :type  file_name: String
    :param file_name: The path of the file
    :type  stat_type:  int
    :param stat_type: The ID from the stat_types dict representing the type of file as reported by stat
    :type  size:  int
    :param size: The size of the file
    :type  extension:  String
    :param extension: The file extension. Duplicate data from file_name, but kept here for performance
    :type  mime_type:  String
    :param mime_type: The file's mime-type. Simplified version, ex: text/plain
    :type  mime_detail:  String
    :param mime_detail: The detailed mime-type data. Example, XML 1.0 document, ASCII text
    """
    if stat_type:
        cur.execute(
            'INSERT OR REPLACE INTO file_metadata (file_name, stat_type) VALUES (?, ?)',
            (file_name, stat_type[0]))
    if size:
        cur.execute(
            'INSERT OR REPLACE INTO file_metadata (file_name, size) VALUES (?, ?)',
            (file_name, size))
    if extension:
        cur.execute(
            'INSERT OR REPLACE INTO file_metadata (file_name, extension) VALUES (?, ?)',
            (file_name, extension))
    if mime_type:
        cur.execute(
            'INSERT OR REPLACE INTO file_metadata (file_name, mime_type) VALUES (?, ?)',
            (file_name, mime_type))
    if mime_detail:
        cur.execute(
            'INSERT OR REPLACE INTO file_metadata (file_name, mime_detail) VALUES (?, ?)',
            (file_name, mime_detail))


def upsert_md5_hash(path, md5_sum):
    cur.execute('INSERT OR REPLACE INTO hashes (file_name, md5_sum) VALUES (?, ?)', (path, md5_sum))


def commit():
    conn.commit()