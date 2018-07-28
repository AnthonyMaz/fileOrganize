import hashlib
import io
import os
import sqlite3

from progressbar import Bar, Percentage, ProgressBar


def md5sum(src, length=io.DEFAULT_BUFFER_SIZE):
    calculated = 0
    size = os.path.getsize(src)
    md5 = hashlib.md5()
    print(os.path.basename(src))
    if size > 10000000:
        pbar = ProgressBar(widgets=[Percentage(), Bar()], maxval=size).start()
        pbar.start()
        with io.open(src, mode="rb") as fd:
            for chunk in iter(lambda: fd.read(length), b''):
                md5.update(chunk)
                calculated += len(chunk)
                pbar.update(calculated)
        print('')
    else:
        with io.open(src, mode="rb") as fd:
            for chunk in iter(lambda: fd.read(length), b''):
                md5.update(chunk)
    return md5


conn = sqlite3.connect('example.db')
cur = conn.cursor()

# Create the hashes table if it doesn't exist already
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='hashes'")
if not cur.fetchone():
    cur.execute('CREATE TABLE hashes (file_name TEXT PRIMARY KEY, md5_sum TEXT)')
    cur.execute('CREATE INDEX hashes_md5sums ON hashes (md5_sum)')

rootDir = '.'
rootDir = os.path.abspath(rootDir)

print('Collecting MD5 sums for files in %s' % rootDir)

for dirName, subdirList, fileList in os.walk(rootDir):
    for fname in fileList:
        file_name = dirName + os.sep + fname
        hash = md5sum(file_name).hexdigest()
        cur.execute('INSERT OR REPLACE INTO hashes (file_name, md5_sum) VALUES (?, ?)', (file_name, hash))
conn.commit()
