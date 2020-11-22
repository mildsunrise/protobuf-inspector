# protobuf-inspector

Simple program that can parse [Google Protobuf][] encoded blobs
(version 2 or 3) without knowing their accompanying definition.
It will print a nice, colored representation of their contents. Example:

![Main screenshot](https://i.imgur.com/Vw403MI.png)

As you can see, the field names are obviously lost, together with
some high-level details such as:

 - whether a varint uses [zig-zag encoding][] or not (will assume no zig-zag by default)
 - whether a 32-bit/64-bit value is an integer or float (both shown by default)
 - signedness (auto-detect by default)

But protobuf-inspector is able to correctly guess the message structure
most of the time. When it finds embedded binary data on a field, it'll
first try to parse it as a message. If that fails, it'll display the data
as a string or hexdump. It can make mistakes, especially with small chunks.

It shows the fields just in the order they are encoded in the
wire, so it can be useful for those wanting to get familiar with
the [wire format][] or parser developers, in addition to reverse-engineering.

## Usage

You can install with pip:

    pip install protobuf-inspector

This installs the `protobuf_inspector` command. Run it, feeding the protobuf blob
on stdin:

    protobuf_inspector < my-protobuf-blob

After reading the first (blind) analysis of the blob, you typically start defining
some of the fields so protobuf-inspector can better parse your blobs, until you get
to a point where you have a full protobuf definition and the parser no longer has
to guess anything.

[Read about defining fields here.](CONFIG.md)

## Parsing errors

If a parsing error is found, parsing will stop *within that field*, but
will go on unaffected at the outside of the hierarchy. The stack trace will
be printed where the field contents would go, along with a hexdump indicating where
parsing was stopped in that chunk, if applicable.

So, if you specified a `uint32` and a larger varint is found, you'd get something like:

![Error on invalid varint](https://i.imgur.com/DWG9MGX.png)

If you specified that some field contained an embedded message, but invalid data was
found there, you'd get:

![Error on invalid message](https://i.imgur.com/URaWqXz.png)

Please note that `main.py` will exit with non-zero status if one or more parsing
errors occurred.

## Tricks

There are some tricks you can use to save time when approaching a blob:

 1. If you are positive that a varint does *not* use zig-zag encoding, but are still
    not sure of the signedness, leave it as `varint`. If it does use zig-zag encoding,
    use `sint64` unless you are sure it's 32-bit and not 64-bit.

 2. If a chunk is wrongly being recognized as a `packed chunk` or an embedded message,
    or if you see something weird with the parsed message and want to see the raw bytes,
    specify a type of `bytes`. Conversely, if for some reason it's not being detected
    as an embedded message and it should, force it to `message` to see the reason.

 3. If you want to extract a chunk's raw data to a file to analyze it better, specify a
    type of `dump` and protobuf-inspector will create `dump.0`, `dump.1`,
    etc. every time it finds a matching blob.

 4. protobuf-inspector parses the blob as a message of type `root`, but that's just a
    default. If you have lots of message types defined, you can pass a type name as
    optional argument, and protobuf-inspector will use that instead of `root`:
    
        protobuf_inspector request < my-protobuf-blob

## Programmatic access

Simple example:

~~~ python
from protobuf_inspector.types import StandardParser

parser = StandardParser()
with open('my-blob', 'rb') as fh:
   output = parser.parse_message(fh, "message")
print(output)
~~~

This project was not initially designed for use as a library, though,
and its API might change. For a more complex example,
see `protobuf_inspector/__main__.py`.



[Google Protobuf]: https://developers.google.com/protocol-buffers
[Wire format]: https://developers.google.com/protocol-buffers/docs/encoding
[Zig-zag encoding]: https://developers.google.com/protocol-buffers/docs/encoding#signed-integers
