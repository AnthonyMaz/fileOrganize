fileOrganize
============

## Setup
```
git clone git@github.com:AnthonyMaz/fileOrganize.git
cd fileOrganize
git checkout python
virtualenv venv
source venv/bin/activate
make
```

## Running it
```
python fileorganize.py
```
It'll create a SQLite3 database in the current directory, and populate
it with filenames and their corresponding hashes.

See the results with something like
```sql
sqlite3 example.db 'select top 25 * from hashes'
```
or
```sql
sqlite3 example.db 'select * from hashes limit 25'
```


Files > 10,000,000 bytes will show a progress indicator as their
hash is being calculated.

## Next steps

Try to organize a mess of files.

* Need to define what "organize" means
  * Media?
  * Archives?
  * Documents?
* How do we classify a file
* Once classified, what do we do with it?
  * Move it to a new directory?
  * Rename it?
  * Store metadata in a database somewhere?

Right now, we can focus on just de-duplicating files

Features
--------

Organize by file type
* Image
* Video
* Audio
* Document
* Archive

Report
* Organize by MIME type
  * Consolidate multiple MIME types into one category
* File sizes
* Extension
* File Name

Identify duplicates
* Generates a file's hash and looks for duplicates

Hide files
* Prepends file with a dot and symlinks to it from a "hide" directory
with the original name

Move files
* Stores metadata about where files were originally located, and moves
them using symlinks. When

Need to identify all files upfront, including dotfiles and checksums
since that's how we'll be hiding files during orginization

Libraries
---------
[progressbar][https://github.com/niltonvolpato/python-progressbar]