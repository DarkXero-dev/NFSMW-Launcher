import struct
import sys
from pathlib import Path

SECTION = b".upd_info"
_ELF_HEADER = struct.Struct("<HHIQQQIHHHHHH")
_SECTION_HEADER = struct.Struct("<IIQQQQIIQQ")


def _find_section(data: bytes) -> tuple[int, int]:
    if data[:4] != b"\x7fELF" or data[4] != 2:
        raise ValueError("not a 64-bit ELF file")
    (_type, _machine, _version, _entry, _phoff, section_table, _flags, _ehsize,
     _phentsize, _phnum, entry_size, count, names_index) = _ELF_HEADER.unpack_from(data, 16)
    sections = [
        _SECTION_HEADER.unpack_from(data, section_table + i * entry_size) for i in range(count)
    ]
    names_offset = sections[names_index][4]
    for name, _kind, _flags, _addr, offset, size, *_rest in sections:
        label = data[names_offset + name : data.index(b"\0", names_offset + name)]
        if label == SECTION:
            return offset, size
    raise ValueError(f"{SECTION.decode()} section not found")


def embed(path: Path, info: str) -> None:
    path = Path(path)
    data = bytearray(path.read_bytes())
    offset, size = _find_section(bytes(data))
    encoded = info.encode()
    if len(encoded) > size:
        raise ValueError(f"update information is {len(encoded)} bytes, section holds {size}")
    data[offset : offset + size] = encoded.ljust(size, b"\0")
    path.write_bytes(data)


if __name__ == "__main__":
    embed(Path(sys.argv[1]), sys.argv[2])
