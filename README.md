# notmuch-lazysync -- tool for synchronzing notmuch tags

This is a simple tool for synchronizing tag information for the
[notmuch](http://notmuchmail.org/) mail client between machines by
using a normal file synchronizer such as
[seafile](https://www.seafile.com/en/home/) or
[dropbox](https://www.dropbox.com/). Notmuch tags are synchronized by
logging tag commands performed on one machine and executing them again
on all other machines.

## Installation

To install `notmuch-lazysync`, make sure
[python 3](https://www.python.org/) and
[setuptools](https://pypi.python.org/pypi/setuptools) are installed.
For installation in your home directory (`~/.local/bin` by default),
run `python setup.py install --user`. For a global installation, run
`python setup.py install` as root.

## Usage

The configuration file `~/.notmuch-lazysync.cfg` specifies the
location of the database used for tag information. This file needs to
be synchronized between your machines using external tools like
dropbox. For example, the following configuration stores the database
in the user's dropbox folder:

    [lazysync]
    # location of database file (needs to be synchronized by external tools)
    db_file = ~/Dropbox/notmuch-lazysync.db
    # total number of hosts to be synchronized (optional, only for database cleanup)
    num_hosts = 3

The `num_hosts` option specifies the total number of machines to be
synchronized. This option is only needed to remove old entries from
the database.

To use this tool to synchronize notmuch tags, run `notmuch-lazysync
replay` after new incoming mail has been sorted. Moreover, tag
modifications need to be logged. If your frontend does this by calling
the notmuch binary, put the `notmuch` script included with this tool
somewhere in your `$PATH` such that it occurs before the real
`notmuch` binary. Note that this script depends on the python library
`psutil`.


For frontends using notmuch bindings directly, tag operations need to
be logged through hook functionality in the frontend.
