#!/usr/bin/env python
# notmuch-lazysync
# Copyright (C) 2015 Daniel Schoepe
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import sqlite3
import os.path
import os
import sys
from argparse import ArgumentParser
from configparser import ConfigParser
from subprocess import call, check_output
from socket import gethostname
from tempfile import NamedTemporaryFile
from datetime import datetime

TAGPREFIX = "notmuch tag"
maildir_tags = frozenset(["unread", "draft", "replied",
                          "flagged", "passed"])
config = None

def info(s):
    print(s, file=sys.stderr)

def debug(s):
    if args.verbose:
        print(s, file=sys.stderr)

def die(s):
    info(s)
    sys.exit(1)

def load_config(args):
    global config
    config_parser = ConfigParser(allow_no_value = True)
    cfg_loc = os.path.expanduser(args.cfg_file)
    if os.path.isfile(cfg_loc):
        config_parser.read(cfg_loc)
    else:
        info("No config file found, creating default config")
        config_parser.add_section('lazysync')
        config_parser.set('lazysync', '# Location of database file (needs to be synchronized by external tools)')
        config_parser.set('lazysync', 'db_file', "~/.notmuch-lazysync.db")
        config_parser.set('lazysync', '# Total number of hosts to be synchronized (optional, only for database cleanup)')
        config_parser.set('lazysync', 'num_hosts', '')
        with open(cfg_loc, 'w') as cfg_handle:
            config_parser.write(cfg_handle)
    config = config_parser['lazysync']
    if 'db_file' not in config:
        die("No database file specified in configuration")

def setup_tables():
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS commands
        (id INTEGER PRIMARY KEY, cmd TEXT, time TEXT);''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS seen
        (id INTEGER PRIMARY KEY, host TEXT,
         cmdid INTEGER REFERENCES commands(id) ON DELETE CASCADE);''')

def gethost():
    # allow overriding hostname for testing
    if 'HOST' in os.environ:
        return os.environ['HOST']
    else:
        return gethostname()

def record(args):
    cmd = " ".join(args.cmd_list)
    debug("Recording: %s" % cmd)
    # Ignore tags handled by maildir synchronization
    record_maildir = check_output(["notmuch", "config", "get",
                                   "maildir.synchronize_flags"]) == b'false\n'
    if cmd.startswith(TAGPREFIX) and not record_maildir:
        tags = parse_tags(cmd[len(TAGPREFIX):])[0]
        debug("Parsed tags: %s: %s" % (cmd[len(TAGPREFIX):], tags))
        if frozenset(map(lambda x: x[1:], tags)).issubset(maildir_tags):
            debug("Ignoring maildir-only tag command: %s" % cmd)
            return
    cursor.execute('''
        INSERT INTO commands (cmd, time)
        VALUES (?, DATETIME('now'));''', [cmd])
    markseen(cursor.lastrowid)

def parse_tags(tagstr):
    tags = []
    qry = []
    tags_parsed = False
    for x in tagstr.strip().split(" "):
        if not tags_parsed:
            if x == "--":
                tags_parsed = True
            elif (x.startswith("+") or x.startswith("-")):
                tags.append(x)
            else:
                tags_parsed = True
                qry.append(x)
        else:
            qry.append(x)
    return (tags, " ".join(qry))


def markseen(row_id):
    cursor.execute("INSERT INTO seen (host, cmdid) VALUES (?, ?)",
                   [gethost(), row_id])

def replay(args):
    tmpfile = NamedTemporaryFile(mode='w', delete=False)
    query_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    host = gethost()
    cursor.execute('''
      SELECT c.id, c.cmd
      FROM commands c
      WHERE NOT EXISTS
        (SELECT s.id FROM seen s
         WHERE s.cmdid = c.id AND s.host = ?)
      ORDER BY c.time ASC''', [host])
    for row in cursor.fetchall():
        debug("Replaying command {0} (id: {1!s})".format(row[1], row[0]))
        cmd = row[1]
        if cmd.startswith(TAGPREFIX):
            debug("Logging tag command for batch execution: " + row[1][len(TAGPREFIX):])
            tmpfile.write(row[1][len(TAGPREFIX):].strip() + "\n")
        else:
            # Not a tag command:
            debug("Executing {0} (id: {1!s})".format(cmd, row[0]))
            ret = call(cmd, shell=True)
            if ret == 0:
                markseen(row[0])
            else:
                info("Command failed: %s" % row[1])
    tmpfile.file.close()
    ret = call(["notmuch", "tag", "--input=" + tmpfile.name])
    os.remove(tmpfile.name)
    if ret == 0:
        cursor.execute('''
        INSERT INTO seen (host, cmdid)
        SELECT ?, c.id FROM commands c
         WHERE
           c.time <= ? AND
           c.cmd LIKE 'notmuch tag%' AND
           NOT EXISTS
            (SELECT s.id FROM seen s
             WHERE s.cmdid = c.id AND s.host = ?);''', [host, query_time, host])
    else:
        info("Failed to execute tag operations")
    if config.get('num_hosts', '') != '' and not args.no_gc:
        gc()

def gc():
    cursor.execute('''
        DELETE FROM commands
        WHERE EXISTS
            (SELECT cnt FROM
                      (SELECT s.id, s.cmdid, count(DISTINCT host) AS cnt
                       FROM seen s WHERE s.cmdid = commands.id)
             WHERE cnt >= ?)''', [int(config['num_hosts'])])
    debug("Garbage collection: removed %s entries" % cursor.rowcount)

def show(args):
    c2 = db.cursor()
    cursor.execute('''
        SELECT c.id, c.cmd, c.time
        FROM commands c;''')
    cnt = 0
    for row in cursor.fetchall():
        print(row)
        hosts = []
        for hostrow in c2.execute('''
        SELECT host FROM seen WHERE cmdid = ?''', [row[0]]):
            hosts.append(hostrow[0])
        print("Seen by: %s" % ", ".join(hosts))
        cnt += 1
    print("%i commands in total." % cnt)

def main():
    parser = ArgumentParser(prog='notmuch-lazysync')
    subparsers = parser.add_subparsers(dest='subparser')
    parser_rec = subparsers.add_parser('record', help='record command')
    parser_rec.add_argument('cmd_list', metavar='CMD', type=str, nargs='+',
                            help='Command to record')
    parser_rec.set_defaults(func=record)
    parser_replay = subparsers.add_parser('replay',
                                          help='replay unseen commands')
    parser_replay.add_argument('--no-gc', default=False, action='store_true',
                               dest='no_gc', help='don\'t remove commands seen'\
                               'by all hosts (mainly useful for debugging).')
    parser_replay.set_defaults(func=replay)
    parser_show = subparsers.add_parser('show', help='show contents of database')
    parser_show.set_defaults(func=show)
    for p in [parser_rec, parser_replay, parser_show]:
        p.add_argument('-v', '--verbose', dest='verbose',
                       action='store_true', default=False,
                       help="enable verbose output")
        p.add_argument('-c', '--config', dest='cfg_file', action='store',
                       default="~/.notmuch-lazysync.cfg",
                       help="use alternate config file location")
    global args
    args = parser.parse_args()
    if args.subparser is None:
        info("No mode given.")
        parser.print_help()
        sys.exit(1)
    load_config(args)
    global db
    db = sqlite3.connect(os.path.expanduser(config['db_file']))
    db.execute('pragma foreign_keys=ON')
    global cursor
    cursor = db.cursor()
    try:
        setup_tables()
        args.func(args)
    finally:
        db.commit()
        db.close()

if __name__ == "__main__":
    main()
