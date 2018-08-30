# Configuration tutorial

## Basic field info

If you're positive about the type of some fields in your message, you can tell
that to protobuf-inspector to help it parse your message better. To do this, create
a `protobuf_config.py` file in the current directory or any parent one, with the
following in it:

~~~ python
types = {
  "root": {
  },
}
~~~

Let's say we start working with this blob:

    $ ./main.py < my-blob
    root:
        1 <varint> = 1469046243471
        2 <chunk> = "kotlin46"
        7 <chunk> = bytes (5)
            0000   00 01 03 04 07                                                           .....
        8 <chunk> = empty chunk
        9 <varint> = 250
        10 <32bit> = 0x43480000 / 1128792064 / 200.000
        14 <chunk> = message:
            1 <chunk> = "POKECOIN"
        14 <chunk> = message:
            1 <chunk> = "STARDUST"
            2 <varint> = 100

After further analysis of many similar blobs we have deduced that, in our `root` message:

 - field 1 is an `uint32` timestamp
 - field 2 is a username `string` (i.e. force parsing as a string, rather than guessing what the chunk is)
 - field 7 is a packed `varint` array (we don't know their exact type or function yet)
 - field 10 certainly looks like a `float` rather than an integer

Our `protobuf_config.py` would turn into:

~~~ python
types = {
  "root": {
    1: ("uint32"),
    2: ("string"),
    7: ("packed varint"),
    10: ("float"),
  },
}
~~~

We can also put names to some of these fields. This has no effect in parsing, it's just
to get more readable output.

~~~ python
types = {
  "root": {
    1: ("uint32", "timestamp"),
    2: ("string", "username"),
    7: ("packed varint"),
    10: ("float"),
  },
}
~~~

After this, we get:

    $ ./main.py < my-blob
    root:
        1 timestamp = 1469046243471
        2 username = "kotlin46"
        7 <packed varint> = [0, 1, 3, 4, 7]
        8 <chunk> = empty chunk
        9 <varint> = 250
        10 <float> = 200.000
        14 <chunk> = message:
            1 <chunk> = "POKECOIN"
        14 <chunk> = message:
            1 <chunk> = "STARDUST"
            2 <varint> = 100

Here's the list of native types supported:

Wire type | Type | Description
----------|------|------------
0 | `varint` | Generic varint, try to guess signedness.
0 | `uint32`, `uint64` | Unsigned varints.
0 | `int32`, `int64` | Signed varints.
0 | `sint32`, `sint64` | Zig-zag encoded varints.
0 | `bool` | Boolean.
0 | `enum <name>` | Enum type `<name>` (see later).
1 | `64bit` | Generic 64-bit (8 byte) value.
1 | `sfixed64`, `fixed64` | 64-bit integer, signed / unsigned.
1 | `double` | Double precision IEEE float
2 | `chunk` | Length-delimited blob, try to guess contents.
2 | `bytes` | Blob of binary data, presented as hexdump.
2 | `string` | Blob with UTF-8 encoded string.
2 | `packed <T>` | Blob with packed repeated field `<T>`.
2 | `dump` | *(convenience)* Dump the blob raw data to file.
2 | `message` | Blob contains a message of unknown type.
3; 4 | - | Group start / end. These are deprecated, and handled transparently by the parser. These wire types are never searched for handlers.
5 | `32bit` | Generic 32-bit (4 byte) value.
5 | `sfixed32`, `fixed32` | 32-bit integer, signed / unsigned.
5 | `float` | Single precision IEEE float


## Message types

Staying with our example blob, suppose we notice that field 14 is a series
of messages, each of which describes a possible item to buy. We will specify
type `item`, and define it:

~~~ python
types = {
  "root": {
    1: ("uint32", "timestamp"),
    2: ("string", "username"),
    7: ("packed varint"),
    10: ("float"),
    14: ("item", "available_items"),
  },
  "item": {
  },
}
~~~

Because `item` isn't any of the native types, protobuf-inspector will assume it's
a new message type. Now let's label the fields of each item: field 1 is the name,
field 2 seems the price.

~~~ python
types = {
  "root": {
    1: ("uint32", "timestamp"),
    2: ("string", "username"),
    7: ("packed varint"),
    10: ("float"),
    14: ("item", "available_items"),
  },
  "item": {
    1: ("string", "name"),
    2: ("varint", "price"),
  },
}
~~~

Parsing now gets us a lovely:

    $ ./main.py < my-blob
    root:
        1 timestamp = 1469046243471
        2 username = "kotlin46"
        7 <packed varint> = [0, 1, 3, 4, 7]
        8 <chunk> = empty chunk
        9 <varint> = 250
        10 <float> = 200.000
        14 available_items = item(1 name = "POKECOIN")
        14 available_items = item(1 name = "STARDUST", 2 price = 100)


## Enum types

Varints can represent enum types. To parse them, define an enum type like so:

~~~ python
types = {
  "root": {
    # ...
  },

  "enum request_type": {
    1: "CONNECT",
    2: "DISCONNECT",
    3: "JOIN",
    4: "LEAVE",
    5: "TALK",
  },
}
~~~

Enum types are defined just like message types, but instead of mapping fields to
their types, it maps enum values to their identifiers. To use the enum type you
just defined, specify `enum request_type` at a varint field.


## Custom native types

It can be useful to define your own native types, such as your own version of `dump`,
or a special version of `float` that presents the number in percentage form.

For an example, let's continue with our blob:

    $ ./main.py < my-blob
    root:
        1 timestamp = 1469046243471
        2 username = "kotlin46"
        7 <packed varint> = [0, 1, 3, 4, 7]
        8 <chunk> = empty chunk
        9 <varint> = 250
        10 <float> = 200.000
        14 available_items = item(1 name = "POKECOIN")
        14 available_items = item(1 name = "STARDUST", 2 price = 100)

We see that field 1 is a timestamp, in the form of milliseconds since the epoch,
so let's register a `milliseconds_timestamp` native type to parse it:

~~~ python
types = {
  "root": {
    1: ("uint32", "timestamp"),
    2: ("string", "username"),
    7: ("packed varint"),
    10: ("float"),
    14: ("item", "available_items"),
  },
  "item": {
    1: ("string", "name"),
    2: ("varint", "price"),
  },
}

def parse_milliseconds_timestamp(x, type):
  from time import ctime
  return ctime(x / 1000.0)

native_types = {
  "milliseconds_timestamp": (parse_milliseconds_timestamp, 0),
}
~~~

Notice the `0` at the end. Because our native type parses varints,
it has to be wire type 0 just like the `varint` type.

After we have registered the native type, we can simply use it
in place of `uint32`:

~~~ python
types = {
  "root": {
    1: ("milliseconds_timestamp", "timestamp"),
    2: ("string", "username"),
    7: ("packed varint"),
    10: ("float"),
    14: ("item", "available_items"),
  },
  "item": {
    1: ("string", "name"),
    2: ("varint", "price"),
  },
}

def parse_milliseconds_timestamp(x, type):
  from time import ctime
  return ctime(x / 1000.0)

native_types = {
  "milliseconds_timestamp": (parse_milliseconds_timestamp, 0),
}
~~~

This gets us:

    $ ./main.py < my-blob
    root:
        1 timestamp = Wed Jul 20 22:24:03 2016
        2 username = "kotlin46"
        7 <packed varint> = [0, 1, 3, 4, 7]
        8 <chunk> = empty chunk
        9 <varint> = 250
        10 <float> = 200.000
        14 available_items = item(1 name = "POKECOIN")
        14 available_items = item(1 name = "STARDUST", 2 price = 100)
