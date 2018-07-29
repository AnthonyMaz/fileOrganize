import hashlib
import io
import os
import magic
from blessings import Terminal
from progressive.bar import Bar
from stat import S_ISCHR, S_ISBLK, S_ISFIFO, S_ISLNK, S_ISDIR, S_ISREG, S_ISSOCK
from progressive.tree import Value, BarDescriptor, ProgressTree
from db import upsert_file_metadata, stat_types, upsert_md5_hash, init_database, commit

try:
    RUNNING_IN_PYCHARM = os.environ['RUNNING_IN_PYCHARM']
except KeyError:
    RUNNING_IN_PYCHARM = False


init_database()


def analyze(src, length=io.DEFAULT_BUFFER_SIZE):
    md5 = hashlib.md5()
    src = os.path.abspath(src)
    try:
        mode = os.stat(src).st_mode

        if S_ISREG(mode):
            upsert_file_metadata(src, stat_types['REGULAR'],
                                 size=os.path.getsize(src),
                                 extension=os.path.splitext(src)[1])
        elif S_ISDIR(mode):
            upsert_file_metadata(src, stat_types['DIRECTORY'])
        elif S_ISCHR(mode):
            upsert_file_metadata(src, stat_types['CHAR'])
        elif S_ISBLK(mode):
            upsert_file_metadata(src, stat_types['BLOCK'])
        elif S_ISFIFO(mode):
            upsert_file_metadata(src, stat_types['FIFO'])
        elif S_ISLNK(mode):
            upsert_file_metadata(src, stat_types['SYMLINK'])
        elif S_ISSOCK(mode):
            upsert_file_metadata(src, stat_types['SOCKET'])
        else:
            upsert_file_metadata(src, stat_types['UNKNOWN'])
    except FileNotFoundError:
        mode = os.stat(src, follow_symlinks=False).st_mode
        if S_ISLNK(mode):
            upsert_file_metadata(src, stat_types['BROKEN_SYMLINK'])

    # Just return the MD5 hash of an empty string for non-regular files
    if not S_ISREG(mode):
        return md5

    try:
        upsert_file_metadata(src, mime_type=(magic.from_file(src, mime=True)), mime_detail=magic.from_file(src))
        with io.open(src, mode="rb") as fd:
            for chunk in iter(lambda: fd.read(length), b''):
                md5.update(chunk)
    except OSError:
        upsert_file_metadata(src, stat_types['ERROR'])
        pass
    return md5


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
            upsert_md5_hash(directory_name, file_hash)
            dirs_analyzed += 1
            leaf_values[0].value = dirs_analyzed

        for file_name in files:
            file_name = os.path.join(root, file_name)
            file_hash = analyze(file_name).hexdigest()
            upsert_md5_hash(file_name, file_hash)
            files_analyzed += 1
            leaf_values[1].value = files_analyzed
            if not RUNNING_IN_PYCHARM:
                n.cursor.restore()
                try:
                    n.draw(test_d, BarDescriptor(bd_defaults))
                except TypeError:
                    print("Looks like you're running in pycharm. Progressive doesn't work in its terminal.")
                    print("Disable progressive by setting the environment variable RUNNING_IN_PYCHARM=1")
                    quit()


commit()
