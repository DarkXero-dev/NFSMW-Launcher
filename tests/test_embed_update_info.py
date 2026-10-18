import importlib.util
import struct
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "embed_update_info", Path(__file__).parent.parent / "packaging" / "embed_update_info.py"
)
embed_update_info = importlib.util.module_from_spec(spec)
spec.loader.exec_module(embed_update_info)


def fake_elf(section_size=64):
    names = b"\0.upd_info\0.shstrtab\0"
    payload_offset = 64
    payload = b"\0" * section_size
    names_offset = payload_offset + section_size
    headers_offset = names_offset + len(names)

    def header(name, kind, offset, size):
        return struct.pack("<IIQQQQIIQQ", name, kind, 0, 0, offset, size, 0, 0, 1, 0)

    sections = (
        header(0, 0, 0, 0)
        + header(1, 1, payload_offset, section_size)
        + header(11, 3, names_offset, len(names))
    )
    ident = b"\x7fELF" + bytes([2, 1, 1]) + b"\0" * 9
    elf_header = ident + struct.pack("<HHIQQQIHHHHHH", 3, 62, 1, 0, 0, headers_offset, 0, 64, 0, 0, 64, 3, 2)
    return elf_header + b"\0" * (payload_offset - len(elf_header)) + payload + names + sections, payload_offset


def test_embed_writes_info_into_the_update_section_and_pads_with_nulls(tmp_path):
    data, offset = fake_elf(64)
    path = tmp_path / "runtime"
    path.write_bytes(data)
    embed_update_info.embed(path, "gh-releases-zsync|me|repo|latest|App.AppImage.zsync")
    result = path.read_bytes()
    info = b"gh-releases-zsync|me|repo|latest|App.AppImage.zsync"
    assert result[offset : offset + 64] == info + b"\0" * (64 - len(info))
    assert len(result) == len(data)
    assert result[:offset] == data[:offset]
    assert result[offset + 64 :] == data[offset + 64 :]


def test_embed_rejects_info_longer_than_the_section(tmp_path):
    data, _ = fake_elf(8)
    path = tmp_path / "runtime"
    path.write_bytes(data)
    with pytest.raises(ValueError):
        embed_update_info.embed(path, "x" * 9)


def test_embed_fails_clearly_when_section_is_missing(tmp_path):
    path = tmp_path / "not-elf"
    path.write_bytes(b"hello")
    with pytest.raises(ValueError):
        embed_update_info.embed(path, "x")
