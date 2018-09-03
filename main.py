#!/usr/bin/env python2

from sys import stdin, stderr, argv
from os.path import ismount, exists, join
from runpy import run_path
from lib.types import StandardParser
import lib.types

# Parse arguments
root_type = "root"
if len(argv) >= 2: root_type = argv[1]

# Load the config
config = {}
directory = "."
while not ismount(directory):
    filename = join(directory, "protobuf_config.py")
    if exists(filename):
        config = run_path(filename)
        break
    directory = join(directory, "..")

# Create and initialize parser with config
parser = StandardParser()
if "types" in config:
    for type, value in config["types"].items():
        type = unicode(type)
        assert(type not in parser.types)
        parser.types[type] = value
if "native_types" in config:
    for type, value in config["native_types"].items():
        parser.native_types[unicode(type)] = value

# Make sure root type is defined and not compactable
if root_type not in parser.types: parser.types[root_type] = {}
parser.types[root_type]["compact"] = False

# PARSE!
print parser.safe_call(parser.match_handler("message"), stdin, root_type) + "\n"

# print veredict
if parser.errors_produced:
    stderr.write(lib.types.fg1("* %d errors seen.\n" % len(parser.errors_produced)))
if parser.wire_types_not_matching:
    stderr.write(lib.types.fg3("* Warning: different wire types were associated with the same key.\n  This should never happen in a Protobuf blob.\n"))
if parser.groups_observed and not parser.errors_produced:
    stderr.write(lib.types.fg4("* This blob uses groups.\n  Groups are deprecated and only used in old Protobuf 2 apps, in whose case you should not see packed values. Support for groups hasn't been as tested and you may run into trouble.\n"))

exit(1 if len(parser.errors_produced) else 0)
