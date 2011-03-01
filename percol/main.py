#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import locale

from optparse import OptionParser

from percol import Percol

def get_ttyname():
    for f in sys.stdin, sys.stdout, sys.stderr:
        if f.isatty():
            return os.ttyname(f.fileno())
    return None

def reconnect_descriptors(tty):
    target = {}

    stdios = (("stdin", "r"), ("stdout", "w"), ("stderr", "w"))

    tty_desc = tty.fileno()

    for name, mode in stdios:
        f = getattr(sys, name)

        if f.isatty():
            # f is TTY
            target[name] = f
        else:
            # f is other process's output / input or a file

            # save descriptor connected with other process
            std_desc = f.fileno()
            other_desc = os.dup(std_desc)

            # set std descriptor. std_desc become invalid.
            os.dup2(tty_desc, std_desc)

            # set file object connected to other_desc to corresponding one of sys.{stdin, stdout, stderr}
            try:
                target[name] = os.fdopen(other_desc, mode)
            except OSError:
                # maybe mode specification is invalid or /dev/null is specified (?)
                target[name] = None
                print("Failed to open {0}".format(other_desc))

    return target

def set_locale():
    locale.setlocale(locale.LC_ALL, '')
    code = locale.getpreferredencoding()
    return code

def setup_options(parser):
    parser.add_option("--tty", dest = "tty", help = "path to the TTY (usually, $TTY)", metavar = "TTY")
    return 

if __name__ == "__main__":
    parser = OptionParser(usage = "Usage: %prog [options] [FILE]")
    setup_options(parser)
    options, args = parser.parse_args()

    def exit_program(msg=None):
        if not msg is None:
            print("\n" + msg + "\n")
        parser.print_help()
        exit(1)

    ttyname = options.tty or get_ttyname()
    if not ttyname:
        exit_program("""Error: No tty name is given and failed to guess (maybe stderr is redirecred)""")

    code = set_locale()

    with open(ttyname, "r+w") as tty:
        if not tty.isatty():
            exit_program("Error: {0} is not a tty file".format(ttyname))

        filename = args[0] if len(args) > 0 else None

        collection = None
        if filename:
            with open(filename, "r") as f:
                collection = f.read().split("\n")

        with Percol(descriptors = reconnect_descriptors(tty), collection = collection) as percol:
            percol.loop()
