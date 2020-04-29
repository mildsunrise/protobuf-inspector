from .core import read_varint, read_identifier, read_value
from .parser import Parser, fg0, fg1, fg2, fg3, fg4, fg5, fg6, fg7, fg8, fg9, dim, bold
from struct import unpack
from io import BytesIO

# Code that implements and registers the usual native types (high
# level parsing and formatting) into the barebones Parser.

class StandardParser(Parser):

    def __init__(self):
        super(StandardParser, self).__init__()

        self.types["message"] = {}

        self.message_compact_max_lines = 4
        self.packed_compact_max_lines = 20

        self.dump_prefix = "dump."
        self.dump_index = 0

        self.wire_types_not_matching = False
        self.groups_observed = False

        types_to_register = {
            0: ["varint", "sint32", "sint64", "int32", "int64", "uint32", "uint64", "enum", "bool"],
            1: ["64bit", "sfixed64", "fixed64", "double"],
            2: ["chunk", "bytes", "string", "message", "packed", "dump"],
            5: ["32bit", "sfixed32", "fixed32", "float"],
        }
        for wire_type, types in types_to_register.items():
            for type in types:
                self.native_types[type] = (getattr(self, "parse_"+type), wire_type)


    # This is the function that handles any non-native type.

    def get_message_field_entry(self, gtype, key):
        type = None; field = None
        try:
            field_entry = self.types[gtype][key]
            if not isinstance(field_entry, tuple): field_entry = (field_entry,)
            type = field_entry[0]
            field = field_entry[1]
        except KeyError: pass
        except IndexError: pass
        return (type, field)

    def parse_message(self, file, gtype, endgroup=None):
        if gtype not in self.types and gtype != self.default_handler:
            raise Exception("Unknown message type %s" % gtype)

        lines = []
        keys_types = {}
        while True:
            key, wire_type = read_identifier(file)
            if key is None: break

            x = read_value(file, wire_type)
            assert(not (x is None))

            if wire_type == 4:
                if not endgroup: raise Exception("Unexpected end group")
                endgroup[0] = key
                break

            if key in keys_types and keys_types[key] != wire_type:
                self.wire_types_not_matching = True
            keys_types[key] = wire_type

            type, field = self.get_message_field_entry(gtype, key)
            if wire_type == 3:
                if type is None: type = "message"
                end = [None]
                x = self.parse_message(file, type, end)
                x = "group (end %s) " % fg4(str(end[0])) + x
                self.groups_observed = True
            else:
                if type is None: type = self.default_handlers[wire_type]
                x = self.safe_call(lambda x: self.match_handler(type, wire_type)(x, type), x)

            if field is None: field = "<%s>" % type
            lines.append("%s %s = %s" % (fg4(str(key)), field, x))

        if key is None and endgroup: raise Exception("Group was not ended")
        if len(lines) <= self.message_compact_max_lines and self.to_display_compactly(gtype, lines):
            return "%s(%s)" % (gtype, ", ".join(lines))
        if not len(lines): lines = ["empty"]
        return "%s:\n%s" % (gtype, self.indent("\n".join(lines)))


    # Functions for generic types (default for wire types)

    def parse_varint(self, x, type):
        result = [x]
        if (1 << 64) - 20000 <= x < (1 << 64):
            # Would be small and negative if interpreted as int32 / int64
            result.insert(0, x - (1 << 64))

        s = fg3("%d" % result[0])
        if len(result) >= 2: s += " (%d)" % result[1]
        return s

    def is_probable_string(self, string):
        controlchars = 0; alnum = 0; total = len(string)
        for c in string:
            c = ord(c)
            if c < 0x20 or c == 0x7F: controlchars += 1
            if (ord("A") <= c <= ord("Z")) or (ord("a") <= c <= ord("z")) or (ord("0") <= c <= ord("9")): alnum += 1

        if controlchars / float(total) > 0.1: return False
        if alnum / float(total) < 0.5: return False
        return True

    def parse_chunk(self, file, type):
        chunk = file.read()
        if not chunk: return "empty chunk"

        # Attempt to decode message
        try:
            return self.parse_message(BytesIO(chunk), "message")
        except Exception:
            pass

        # Attempt to decode packed repeated chunks
        try:
            if len(chunk) >= 5:
                return self.parse_packed(BytesIO(chunk), "packed chunk")
        except Exception:
            pass

        # Attempt to decode as UTF-8
        try:
            if self.is_probable_string(chunk.decode("utf-8")):
                return self.parse_string(BytesIO(chunk), "string")
        except UnicodeError:
            pass

        # Fall back to hexdump
        return self.parse_bytes(BytesIO(chunk), "bytes")

    def parse_32bit(self, x, type):
        signed = unpack("<i", x)[0]
        unsigned = unpack("<I", x)[0]
        floating = unpack("<f", x)[0]
        return "0x%08X / %d / %#g" % (unsigned, signed, floating)

    def parse_64bit(self, x, type):
        signed = unpack("<q", x)[0]
        unsigned = unpack("<Q", x)[0]
        floating = unpack("<d", x)[0]
        return "0x%016X / %d / %#.8g" % (unsigned, signed, floating)


    # Functions for protobuf types

    def parse_sint32(self, x, type):
        assert(0 <= x < (1 << 32))
        return fg3(str(zigzag(x)))

    def parse_sint64(self, x, type):
        assert(0 <= x < (1 << 64))
        return fg3(str(zigzag(x)))

    def parse_int32(self, x, type):
        assert(0 <= x < (1 << 64))
        if x >= (1 << 63): x -= (1 << 64)
        assert(-(1 << 31) <= x < (1 << 31))
        return fg3(str(x))

    def parse_int64(self, x, type):
        assert(0 <= x < (1 << 64))
        if x >= (1 << 63): x -= (1 << 64)
        return fg3(str(x))

    def parse_uint32(self, x, type):
        assert(0 <= x < (1 << 32))
        return fg3(str(x))

    def parse_uint64(self, x, type):
        assert(0 <= x < (1 << 64))
        return fg3(str(x))

    def parse_bool(self, x, type):
        assert(0 <= x < (1 << 1))
        return fg3(str(bool(x)))

    def parse_string(self, file, type):
        string = file.read().decode("utf-8")
        return fg2('"%s"' % (repr(string)[1:-1]))

    def parse_bytes(self, file, type):
        hex_dump, offset = self.hex_dump(file)
        return "%s (%d)\n%s" % (type, offset, self.indent(hex_dump))

    def parse_packed(self, file, gtype):
        assert(gtype.startswith("packed "))
        type = gtype[7:]
        handler, wire_type = self.match_native_type(type)

        lines = []
        while True:
            x = read_value(file, wire_type)
            if x is None: break
            lines.append(self.safe_call(handler, x, type))

        if len(lines) <= self.packed_compact_max_lines and self.to_display_compactly(gtype, lines):
            return "[%s]" % (", ".join(lines))
        return "packed:\n%s" % (self.indent("\n".join(lines)))

    def parse_fixed32(self, x, type):
        return fg3("%d" % unpack("<i", x)[0])

    def parse_sfixed32(self, x, type):
        return fg3("%d" % unpack("<I", x)[0])

    def parse_float(self, x, type):
        return fg3("%#g" % unpack("<f", x)[0])

    def parse_fixed64(self, x, type):
        return fg3("%d" % unpack("<q", x)[0])

    def parse_sfixed64(self, x, type):
        return fg3("%d" % unpack("<Q", x)[0])

    def parse_double(self, x, type):
        return fg3("%#.8g" % unpack("<d", x)[0])

    def parse_enum(self, x, type):
        if type not in self.types:
            raise Exception("Enum type '%s' not defined" % type)
        type_entry = self.types[type]
        if x not in type_entry:
            raise Exception("Unknown value %d for '%s'" % (x, type))
        return fg6(type_entry[x])


    # Other convenience types

    def parse_dump(self, file, type):
        chunk = file.read()
        filename = self.dump_prefix + str(self.dump_index)
        file = open(filename, "w")
        file.write(chunk)
        file.close()
        self.dump_index += 1
        return "%d bytes written to %s" % (len(chunk), filename)


def zigzag(x):
    negative = x & 1
    x = x >> 1
    return -(x+1) if negative else x
