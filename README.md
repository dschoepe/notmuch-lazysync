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

To use this tool to synchronize notmuch tags, run `notmuch-lazysync replay`
after new incoming mail has been sorted. Moreover, instruct your notmuch
frontend to record tag changes. When the user tags mails matching a query `Q`
with tag `+t`, run `notmuch-lazysync record -- notmuch tag +t -- Q`. For example,
in the Emacs frontend, this can be achieved using `notmuch-after-tag-hook`:

    (add-hook 'notmuch-after-tag-hook
    	  (lambda ()
    	    (apply 'start-process "notmuch-lazysync" nil
                                  "notmuch-lazysync" "record" "--"
                                  "notmuch" "tag" (append tag-changes (list "--" query)))))

In addition, tag changes performed using the `notmuch` binary directly
can be logged by putting the following script with the name `notmuch`
in a directory that occurs before `/usr/bin` in `$PATH`:

    #!/bin/sh
    if [[ "$1" == "tag" ]]; then
        # note that comm truncates the name after 15 characters
        if [[ $(ps -p $PPID -o comm=) != "notmuch-lazysyn" ]]; then
            notmuch-lazysync record -v -- notmuch "$@"
        fi
    fi
    # perform the original command
    /usr/bin/notmuch "$@"
