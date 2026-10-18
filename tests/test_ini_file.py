from pathlib import Path

import pytest

from nfsmw_launcher.ini_file import IniFile

FIXTURES = Path(__file__).parent / "fixtures"


def test_parses_semicolon_inline_comment():
    ini = IniFile("[MAIN]\r\nResX = 2560      ; Horizontal resolution.\r\n")
    entry = ini.entries[0]
    assert (entry.section, entry.key, entry.value) == ("MAIN", "ResX", "2560")
    assert entry.comment == "Horizontal resolution."


def test_parses_double_slash_inline_comment():
    ini = IniFile("[Menu]\nShowOnline = 1    // Shows Online option. (0 = False, 1 = True)\n")
    entry = ini.entries[0]
    assert entry.value == "1"
    assert entry.comment == "Shows Online option. (0 = False, 1 = True)"


def test_value_followed_by_parenthesised_note_without_comment_marker():
    ini = IniFile("[Hotkeys]\nToggleVisualTreatment = 86 (Default = 86 = V)\n")
    entry = ini.entries[0]
    assert entry.value == "86"
    assert entry.comment == "(Default = 86 = V)"


def test_preceding_comment_lines_become_description():
    text = "[MAIN]\n; Enables contrails\n; second line\nContrails = 1\n"
    assert IniFile(text).entries[0].comment == "Enables contrails second line"


def test_section_header_comment_and_blank_lines_ignored():
    ini = IniFile("[Hotkeys] // see vk table\n\nHeadlights = 72 // H key\n")
    assert [(e.section, e.key) for e in ini.entries] == [("Hotkeys", "Headlights")]


def test_get_returns_value():
    ini = IniFile("[A]\nx = 1\n[B]\nx = 2\n")
    assert ini.get("A", "x") == "1"
    assert ini.get("B", "x") == "2"


def test_set_changes_only_target_line_and_keeps_comment_alignment():
    text = "[MAIN]\r\nResX = 2560                 ; Horizontal.\r\nResY = 1440                 ; Vertical.\r\n"
    ini = IniFile(text)
    ini.set("MAIN", "ResX", "800")
    out = ini.dumps()
    assert out == "[MAIN]\r\nResX = 800                  ; Horizontal.\r\nResY = 1440                 ; Vertical.\r\n"


def test_set_longer_value_keeps_at_least_one_space_before_comment():
    ini = IniFile("[A]\nkey = 1   // note\n")
    ini.set("A", "key", "123456")
    assert ini.dumps() == "[A]\nkey = 123456 // note\n"


def test_set_on_line_without_trailing_comment_has_no_padding():
    ini = IniFile("[A]\nkey = SAVE\n")
    ini.set("A", "key", "0")
    assert ini.dumps() == "[A]\nkey = 0\n"


def test_set_unknown_key_raises():
    with pytest.raises(KeyError):
        IniFile("[A]\nx = 1\n").set("A", "nope", "2")


def test_set_preserves_missing_trailing_newline():
    ini = IniFile("[A]\nx = 1 ; c")
    ini.set("A", "x", "0")
    assert ini.dumps() == "[A]\nx = 0 ; c"


@pytest.mark.parametrize("path", sorted(FIXTURES.glob("*.ini")), ids=lambda p: p.name)
def test_roundtrip_without_changes_is_byte_identical(path):
    raw = path.read_bytes()
    assert IniFile.load(path).dumps().encode("utf-8", "surrogateescape") == raw


@pytest.mark.parametrize("path", sorted(FIXTURES.glob("*.ini")), ids=lambda p: p.name)
def test_setting_every_value_to_itself_is_byte_identical(path):
    ini = IniFile.load(path)
    for entry in ini.entries:
        ini.set(entry.section, entry.key, entry.value)
    assert ini.dumps().encode("utf-8", "surrogateescape") == path.read_bytes()


def test_save_writes_backup_once(tmp_path):
    target = tmp_path / "a.ini"
    target.write_text("[A]\nx = 1\n", newline="")
    ini = IniFile.load(target)
    ini.set("A", "x", "2")
    ini.save(target)
    ini.set("A", "x", "3")
    ini.save(target)
    assert target.read_text() == "[A]\nx = 3\n"
    assert (tmp_path / "a.ini.redux-launcher.bak").read_text() == "[A]\nx = 1\n"
