#!/usr/bin/python3
# coding: utf8

import argparse
from datetime import datetime, timezone
import os
import sqlite3
import sys
import re

DEFAULT_HISTORY = '.bash_history'
DEFAULT_DB = '.hisql.db'
SCHEMA_VERSION = 1


def schema_version(c):
    return c.execute("PRAGMA user_version").fetchone()[0]


def cmd_add(c, args):
    c.execute("INSERT INTO history (cmd) VALUES (?)", args.cmd)


def cmd_clear(c, args):
    c.execute("DELETE FROM history")


def cmd_init(c, args):
    version = schema_version()
    if version == 0:
        # In this case, it's either uninitialised or at first version
        # if the table exists, we assume the latter
        r = c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='history'")
        if len(r.fetchall()) == 0:
            version = -1

    c.execute("""CREATE TABLE IF NOT EXISTS history (
                    ts INTEGER(4) DEFAULT (strftime('%s', 'now', 'localtime')),
                    cmd TEXT NOT NULL,
                    UNIQUE (cmd) ON CONFLICT REPLACE)"""
              )


def cmd_list(c, args):
    r = c.execute("SELECT datetime(ts, 'unixepoch'), cmd FROM history ORDER BY ts ASC")
    for x in r.fetchall():
        if args.time:
            print("{} {}".format(x[0] or 0, x[1]))
        else:
            print(x[1])


def cmd_load(c, args):
    file = sys.stdin if args.file == "-" else open(args.file, 'w+')
    if args.file != "-" and not os.path.isfile(args.file):
        print("Could find history [{}]".format(args.file))
        return
    lines = file.read().split('\n')
    ts = None
    records = []
    ts_regex = re.compile('^#\d+')
    now = int(datetime.now().replace(tzinfo=timezone.utc).timestamp())
    for line in filter(lambda x: x != "", lines):
        if ts_regex.match(line):
            ts = int(line[1:])
        else:
            ts = now if ts is None and args.now else ts
            records.append((ts, line))
            ts = None
    records.sort(key=lambda x: x[0] or -1)
    if args.clear:
        c.execute("DELETE FROM history")
    c.executemany("INSERT INTO history (ts, cmd) VALUES (?, ?)", records)


def cmd_save(c, args):
    f = sys.stdout if args.file == "-" else open(args.file, 'w+')
    with f:
        r = c.execute("SELECT ts, cmd FROM history ORDER BY ts ASC")
        for x in r.fetchall():
            if args.no_time or x[0] is None:
                f.write("{}\n".format(x[1]))
            else:
                f.write("#{}\n{}\n".format(x[0], x[1]))


def cmd_sql(c, args):
    r = c.execute(args.sql[0])
    for x in r.fetchall():
        print('|'.join(map(str, x)))


def main():
    parser = argparse.ArgumentParser(description='Store your shell history in sqlite')
    subparsers = parser.add_subparsers()

    add_p = subparsers.add_parser('add')
    add_p.set_defaults(func=cmd_add)
    add_p.add_argument("cmd", nargs=1)

    clear_p = subparsers.add_parser('clear')
    clear_p.set_defaults(func=cmd_clear)

    init_p = subparsers.add_parser('init')
    init_p.set_defaults(func=cmd_init)

    list_p = subparsers.add_parser('list')
    list_p.set_defaults(func=cmd_list)
    list_p.add_argument("-t", "--time", action='store_true')

    load_p = subparsers.add_parser('load')
    load_p.set_defaults(func=cmd_load)
    load_p.add_argument("-c", "--clear", action='store_true', help="Clear history before importing")
    load_p.add_argument("-n", "--now", action='store_true', help="Uses 'now' for null timestamps")
    load_p.add_argument("file", nargs='?', default='-')

    save_p = subparsers.add_parser('save')
    save_p.set_defaults(func=cmd_save)
    save_p.add_argument("-T", "--no-time", action='store_true')
    save_p.add_argument("file", nargs='?', default='-')

    sql_p = subparsers.add_parser('sql')
    sql_p.set_defaults(func=cmd_sql)
    sql_p.add_argument("sql", nargs=1)

    args = parser.parse_args()

    try:
        f = args.func
    except AttributeError:
        parser.print_usage()
        sys.exit(-1)

    c = sqlite3.connect(os.path.join(os.getenv("HOME"), DEFAULT_DB))
    try:
        f(c, args)
    except BrokenPipeError:
        pass
    except sqlite3.OperationalError:
        sys.exit(-2)
    c.commit()
    c.close()


if __name__ == '__main__':
    main()
