from sys import stdin, argv
from os.path import ismount, exists, join
from runpy import run_path
from .types import StandardParser

def main():
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
            assert(type not in parser.types)
            parser.types[type] = value
    if "native_types" in config:
        for type, value in config["native_types"].items():
            parser.native_types[type] = value

    # Make sure root type is defined and not compactable
    if root_type not in parser.types: parser.types[root_type] = {}
    parser.types[root_type]["compact"] = False

    # PARSE!
    print(parser.safe_call(parser.match_handler("message"), stdin.buffer, root_type) + "\n")
    return 1 if len(parser.errors_produced) else 0

if __name__ == "__main__":
    exit(main())
