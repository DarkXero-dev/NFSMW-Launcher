import re
import shutil
from pathlib import Path

import pytest

gi = pytest.importorskip("gi")
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

if not Gtk.init_check():
    pytest.skip("no display available", allow_module_level=True)
Adw.init()

from nfsmw_launcher.fields import ChoiceField, HotkeyField, NumberField, ResolutionField, SwitchField, TextField
from nfsmw_launcher.ini_file import IniFile
from nfsmw_launcher.schema import FILES, RESOLUTIONS
from nfsmw_launcher.settings_window import ReduxSettingsWindow

FIXTURES = Path(__file__).parent / "fixtures"


def alternative(field):
    current = field.current()
    option = field.option
    if isinstance(field, SwitchField):
        return "0" if current == "1" else "1"
    if isinstance(field, ResolutionField):
        return next(f"{w}x{h}" for w, h, _ in RESOLUTIONS if f"{w}x{h}" != current)
    if isinstance(field, ChoiceField):
        values = field.values
        return values[(values.index(current) + 1) % len(values)]
    if isinstance(field, NumberField):
        step = 10 ** -option.digits if option.kind == "float" else 1
        value = float(current) + step * 3
        if value > option.maximum:
            value = float(current) - step * 3
        return f"{value:.{option.digits}f}" if option.kind == "float" else str(int(value))
    if isinstance(field, HotkeyField):
        return "66" if current == "65" else "65"
    if isinstance(field, TextField):
        return current + "x"
    raise AssertionError(f"unhandled field {field}")


def normalised(line):
    return re.sub(r"\s+", " ", line.strip())


def written_pairs(field):
    return {(o.section, o.key): v for o, v in field.entries()}


@pytest.fixture
def scripts(tmp_path):
    for ini in FIXTURES.glob("*.ini"):
        shutil.copy(ini, tmp_path / ini.name)
    return tmp_path


@pytest.mark.parametrize("name", list(FILES))
def test_every_option_written_exactly_and_nothing_else_changes(scripts, name):
    window = ReduxSettingsWindow(None, scripts)
    fields = [f for f in window._fields if f.option.file == name]
    assert fields, name

    expected = {}
    for field in fields:
        field.set(alternative(field))
        assert field.changed(), f"{field.option.key} did not register a change"
        expected.update(written_pairs(field))

    window._on_save(None)

    original = IniFile.load(FIXTURES / name)
    saved = IniFile.load(scripts / name)
    assert len(saved.entries) == len(original.entries)
    assert (scripts / name).read_bytes().count(b"\r\n") == (FIXTURES / name).read_bytes().count(b"\r\n")

    for before, after in zip(original.entries, saved.entries):
        assert (before.section, before.key, before.comment) == (after.section, after.key, after.comment)
        want = expected.get((before.section, before.key), before.value)
        assert after.value == want, f"{before.section}/{before.key}: wrote {after.value!r}, expected {want!r}"

    old_lines = (FIXTURES / name).read_text(newline="").splitlines(keepends=True)
    new_lines = (scripts / name).read_text(newline="").splitlines(keepends=True)
    assert len(old_lines) == len(new_lines)
    entry_lines = {e.line_index for e in original.entries}
    for index, (old, new) in enumerate(zip(old_lines, new_lines)):
        if index not in entry_lines:
            assert old == new, f"non-setting line {index} changed"
        else:
            old_entry = next(e for e in original.entries if e.line_index == index)
            new_entry = next(e for e in saved.entries if e.line_index == index)
            restored = new.replace(new_entry.value, old_entry.value, 1)
            assert normalised(restored) == normalised(old), f"line {index}: {old!r} -> {new!r}"


@pytest.mark.parametrize("name", list(FILES))
def test_written_values_keep_the_original_format(scripts, name):
    window = ReduxSettingsWindow(None, scripts)
    original = IniFile.load(FIXTURES / name)
    for field in [f for f in window._fields if f.option.file == name]:
        field.set(alternative(field))
        for option, value in field.entries():
            before = original.get(option.section, option.key)
            if option.kind == "switch":
                assert value in ("0", "1")
            elif option.kind in ("int", "hotkey", "resolution", "resolution_height"):
                assert re.fullmatch(r"-?\d+", value), f"{option.key}: {value!r}"
            elif option.kind == "float":
                assert re.fullmatch(r"-?\d+\.\d+", value), f"{option.key}: {value!r}"
            elif option.kind == "choice":
                assert value.lower() in [v.lower() for v, _ in option.choices] or value == before
            assert value.strip() == value and value


@pytest.mark.parametrize("name", list(FILES))
def test_changing_then_restoring_values_reproduces_the_original_bytes(scripts, name):
    window = ReduxSettingsWindow(None, scripts)
    fields = [f for f in window._fields if f.option.file == name]
    originals = {id(f): f.current() for f in fields}
    for field in fields:
        field.set(alternative(field))
    window._on_save(None)

    second = ReduxSettingsWindow(None, scripts)
    for field in [f for f in second._fields if f.option.file == name]:
        match = next(f for f in fields if f.option.key == field.option.key and f.option.section == field.option.section)
        field.set(originals[id(match)])
    second._on_save(None)

    restored = IniFile.load(scripts / name)
    original = IniFile.load(FIXTURES / name)
    assert len(restored.entries) == len(original.entries)
    for after, before in zip(restored.entries, original.entries):
        assert (after.section, after.key) == (before.section, before.key)
        if re.fullmatch(r"-?\d*\.?\d+", before.value) and re.fullmatch(r"-?\d*\.?\d+", after.value):
            assert float(after.value) == pytest.approx(float(before.value)), before.key
        else:
            assert after.value == before.value, f"{before.section}/{before.key}"


def test_untouched_options_never_rewrite_the_file(scripts):
    window = ReduxSettingsWindow(None, scripts)
    window._on_save(None)
    for ini in FIXTURES.glob("*.ini"):
        assert (scripts / ini.name).read_bytes() == ini.read_bytes()
    assert not list(scripts.glob("*.bak"))


@pytest.mark.parametrize("name", list(FILES))
def test_gui_opens_showing_exactly_what_the_ini_holds(scripts, name):
    window = ReduxSettingsWindow(None, scripts)
    original = IniFile.load(FIXTURES / name)
    for field in [f for f in window._fields if f.option.file == name]:
        for option, shown in field.entries():
            held = original.get(option.section, option.key)
            if re.fullmatch(r"-?\d*\.?\d+", held) and re.fullmatch(r"-?\d*\.?\d+", shown):
                assert float(shown) == pytest.approx(float(held)), f"{option.key} shows {shown}, ini has {held}"
            else:
                assert shown.lower() == held.lower(), f"{option.key} shows {shown}, ini has {held}"
        assert not field.changed()
