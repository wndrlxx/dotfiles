"""Read Ellie's Chromium cache without opening or locking its LevelDB database.

Only plain V8 values used by Firestore documents are supported. Unknown formats
fail closed. Records stay in memory and are never logged or written to disk.
"""

import struct
from pathlib import Path


class FormatError(ValueError):
    pass


class Reader:
    def __init__(self, data):
        self.data = data
        self.pos = 0

    def take(self, size):
        if size < 0 or self.pos + size > len(self.data):
            raise FormatError("Truncated data")
        result = self.data[self.pos:self.pos + size]
        self.pos += size
        return result

    def uint(self):
        result = 0
        for shift in range(0, 70, 7):
            byte = self.take(1)[0]
            result |= (byte & 127) << shift
            if byte < 128:
                return result
        raise FormatError("Invalid varint")

    def blob(self):
        return self.take(self.uint())


def log_records(data):
    """Read complete LevelDB log records; ignore an in-flight trailing record."""
    pending = None
    for offset in range(0, len(data), 32768):
        block = Reader(data[offset:offset + 32768])
        while len(block.data) - block.pos >= 7:
            checksum, size, kind = struct.unpack("<IHB", block.take(7))
            if not checksum and not size and not kind:
                break
            if size > len(block.data) - block.pos:
                break
            payload = block.take(size)
            if kind == 1:
                pending = None
                yield payload
            elif kind == 2:
                pending = bytearray(payload)
            elif kind == 3 and pending is not None:
                pending.extend(payload)
            elif kind == 4 and pending is not None:
                pending.extend(payload)
                yield bytes(pending)
                pending = None
            else:
                pending = None


def live_files(directory):
    """Replay VersionEdits so compacted, obsolete tables cannot revive old data."""
    current = (directory / "CURRENT").read_text().strip()
    if not current.startswith("MANIFEST-") or "/" in current:
        raise FormatError("Invalid manifest")
    tables = {}
    log_number = previous_log = 0
    for record in log_records((directory / current).read_bytes()):
        reader = Reader(record)
        while reader.pos < len(record):
            tag = reader.uint()
            if tag == 1:
                reader.blob()  # comparator
            elif tag == 2:
                log_number = reader.uint()
            elif tag in (3, 4):
                reader.uint()  # next file / last sequence
            elif tag == 5:
                reader.uint()
                reader.blob()  # compaction pointer
            elif tag == 6:
                reader.uint()
                tables.pop(reader.uint(), None)
            elif tag == 7:
                level, number, size = reader.uint(), reader.uint(), reader.uint()
                reader.blob()
                reader.blob()
                tables[number] = (level, size)
            elif tag == 9:
                previous_log = reader.uint()
            else:
                raise FormatError("Unsupported manifest entry")
    result = []
    for number in tables:
        candidates = [directory / f"{number:06d}{suffix}" for suffix in (".ldb", ".sst")]
        result.append(next((p for p in candidates if p.exists()), candidates[0]))
    # A new WAL may have opened before its manifest edit is flushed.
    for path in directory.glob("*.log"):
        if path.stem.isdigit() and (int(path.stem) >= log_number or int(path.stem) == previous_log):
            result.append(path)
    return sorted(result)


def snappy(data):
    reader = Reader(data)
    expected = reader.uint()
    if expected > 64 * 1024 * 1024:
        raise FormatError("Oversized Snappy block")
    result = bytearray()
    while reader.pos < len(data):
        tag = reader.take(1)[0]
        kind = tag & 3
        if kind == 0:
            length = tag >> 2
            if length >= 60:
                length = int.from_bytes(reader.take(length - 59), "little")
            result.extend(reader.take(length + 1))
        else:
            if kind == 1:
                length = 4 + ((tag >> 2) & 7)
                distance = ((tag & 224) << 3) | reader.take(1)[0]
            else:
                length = 1 + (tag >> 2)
                distance = int.from_bytes(reader.take(2 if kind == 2 else 4), "little")
            if distance <= 0 or distance > len(result):
                raise FormatError("Invalid Snappy reference")
            for _ in range(length):
                result.append(result[-distance])
        if len(result) > expected:
            raise FormatError("Invalid Snappy length")
    if len(result) != expected:
        raise FormatError("Truncated Snappy block")
    return bytes(result)


def block_entries(data):
    if len(data) < 4:
        raise FormatError("Invalid table block")
    restarts = struct.unpack_from("<I", data, len(data) - 4)[0]
    end = len(data) - 4 * (restarts + 1)
    if end < 0:
        raise FormatError("Invalid restart table")
    reader, key = Reader(data[:end]), b""
    while reader.pos < end:
        shared, remaining, value_size = reader.uint(), reader.uint(), reader.uint()
        if shared > len(key):
            raise FormatError("Invalid shared key")
        key = key[:shared] + reader.take(remaining)
        yield key, reader.take(value_size)


def table_entries(data):
    if len(data) < 48 or data[-8:] != bytes.fromhex("57fb808b247547db"):
        raise FormatError("Unsupported LevelDB table")
    footer = Reader(data[-48:-8])
    footer.uint()
    footer.uint()  # metaindex handle
    index_offset, index_size = footer.uint(), footer.uint()

    def block(offset, size):
        if offset + size + 5 > len(data):
            raise FormatError("Truncated table")
        payload, compression = data[offset:offset + size], data[offset + size]
        if compression == 1:
            return snappy(payload)
        if compression == 0:
            return payload
        raise FormatError("Unsupported table compression")

    for _, handle in block_entries(block(index_offset, index_size)):
        reader = Reader(handle)
        yield from block_entries(block(reader.uint(), reader.uint()))


def database_entries(directory):
    """Return latest live values by user key, including WAL tombstones."""
    entries = {}

    def save(key, sequence, value):
        if key not in entries or entries[key][0] <= sequence:
            entries[key] = (sequence, value)

    for path in live_files(directory):
        data = path.read_bytes()
        if path.suffix != ".log":
            for key, value in table_entries(data):
                if len(key) < 8:
                    raise FormatError("Invalid internal key")
                trailer = int.from_bytes(key[-8:], "little")
                kind = trailer & 255
                if kind not in (0, 1):
                    raise FormatError("Unsupported table value")
                save(key[:-8], trailer >> 8, value if kind else None)
        else:
            for record in log_records(data):
                if len(record) < 12:
                    raise FormatError("Invalid write batch")
                sequence, count = struct.unpack_from("<QI", record)
                reader = Reader(record[12:])
                for i in range(count):
                    kind = reader.take(1)[0]
                    key = reader.blob()
                    if kind not in (0, 1):
                        raise FormatError("Unsupported write operation")
                    save(key, sequence + i, reader.blob() if kind else None)
    return [(sequence, value) for sequence, value in entries.values() if value is not None]


class V8Reader(Reader):
    """Subset of Chromium's structured clone format for Firestore JSON records."""
    def __init__(self, data):
        super().__init__(data)
        self.objects = []

    def value(self, depth=0):
        if depth > 80:
            raise FormatError("V8 nesting limit")
        tag = self.take(1)
        while tag == b"\x00":
            tag = self.take(1)  # alignment padding
        if tag == b"\xff":
            if self.uint() not in (15, 16):
                raise FormatError("Unsupported V8 version")
            return self.value(depth + 1)
        if tag in (b'"', b"S", b"c"):
            enc = {b'"': "latin1", b"S": "utf-8", b"c": "utf-16-le"}[tag]
            return self.blob().decode(enc)
        if tag in (b"0", b"_", b"-"):
            return None
        if tag in (b"T", b"F"):
            return tag == b"T"
        if tag in (b"I", b"U"):
            number = self.uint()
            return (number >> 1) ^ -(number & 1) if tag == b"I" else number
        if tag == b"N":
            return struct.unpack("<d", self.take(8))[0]
        if tag == b"^":
            return self.objects[self.uint()]
        if tag == b"o":
            result = {}
            self.objects.append(result)
            count = 0
            while self.data[self.pos:self.pos + 1] != b"{":
                key = self.value(depth + 1)
                result[key] = self.value(depth + 1)
                count += 1
            self.take(1)
            if self.uint() != count:
                raise FormatError("V8 property count mismatch")
            return result
        if tag in (b"A", b"a"):
            size = self.uint()
            if size > 100000:
                raise FormatError("V8 array limit")
            result = [None] * size
            self.objects.append(result)
            if tag == b"A":
                for i in range(size):
                    result[i] = self.value(depth + 1)
            end = b"$" if tag == b"A" else b"@"
            count = 0
            while self.data[self.pos:self.pos + 1] != end:
                key, value = self.value(depth + 1), self.value(depth + 1)
                if not isinstance(key, int) or not 0 <= key < size:
                    raise FormatError("Unsupported V8 array property")
                result[key] = value
                count += 1
            self.take(1)
            if self.uint() != count or self.uint() != size:
                raise FormatError("V8 array count mismatch")
            return result
        raise FormatError("Unsupported V8 value")


def firestore_records(directory):
    for sequence, value in database_entries(Path(directory)):
        if not any(key in value[:512] for key in (b"prefixPath", b"overlayMutation", b"fbase_key")):
            continue
        # Blink adds its own version/trailer envelope before the V8 payload.
        # The payload starts within the first 32 bytes of the IndexedDB value.
        for offset in range(min(32, len(value) - 2)):
            if value[offset:offset + 3] in (b"\xff\x10o", b"\xff\x0fo"):
                yield sequence, V8Reader(value[offset:]).value()
                break
