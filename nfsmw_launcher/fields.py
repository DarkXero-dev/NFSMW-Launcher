import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, GLib, Gtk

from dataclasses import replace

from .hotkeys import vk_from_key_name, vk_name
from .schema import RESOLUTIONS, Option, resolution_label


class Field:
    def __init__(self, option: Option, value: str):
        self.option = option
        self.row = self._build(value)
        self.initial = self.current()

    def _build(self, value: str) -> Adw.PreferencesRow:
        raise NotImplementedError

    def current(self) -> str:
        raise NotImplementedError

    def set(self, value: str) -> None:
        raise NotImplementedError

    def entries(self) -> list[tuple[Option, str]]:
        return [(self.option, self.current())]

    def changed(self) -> bool:
        return self.current() != self.initial

    def restore_default(self) -> None:
        if self.option.default is not None:
            self.set(self.option.default)

    def matches(self, query: str) -> bool:
        haystack = f"{self.option.label} {self.option.key} {self.option.description} {self.option.group}"
        return query in haystack.lower()

    def _title(self) -> str:
        return GLib.markup_escape_text(self.option.label)

    def _subtitle(self) -> str:
        return GLib.markup_escape_text(self.option.description)


class SwitchField(Field):
    def _build(self, value):
        row = Adw.SwitchRow(title=self._title(), subtitle=self._subtitle())
        row.set_active(value == "1")
        return row

    def current(self):
        return "1" if self.row.get_active() else "0"

    def set(self, value):
        self.row.set_active(value == "1")


class ChoiceField(Field):
    def _build(self, value):
        self.values = [v for v, _ in self.option.choices]
        labels = [label for _, label in self.option.choices]
        if self._index(value) < 0:
            self.values.append(value)
            labels.append(f"{value} (custom)")
        row = Adw.ComboRow(
            title=self._title(), subtitle=self._subtitle(), model=Gtk.StringList.new(labels)
        )
        row.set_selected(self._index(value))
        return row

    def _index(self, value):
        lowered = [v.lower() for v in self.values]
        return lowered.index(value.lower()) if value.lower() in lowered else -1

    def current(self):
        return self.values[self.row.get_selected()]

    def set(self, value):
        index = self._index(value)
        if index >= 0:
            self.row.set_selected(index)


class ResolutionField(ChoiceField):
    def __init__(self, option: Option, width: str, partner: tuple[Option, str]):
        self.height_option, height = partner
        sizes = [(w, h) for w, h, _ in RESOLUTIONS]
        if (int(width), int(height)) not in sizes:
            sizes.append((int(width), int(height)))
        choices = [(f"{w}x{h}", resolution_label(w, h)) for w, h in sizes]
        super().__init__(replace(option, choices=choices), f"{int(width)}x{int(height)}")

    def entries(self):
        width, height = self.current().split("x")
        return [(self.option, width), (self.height_option, height)]

    def matches(self, query):
        return super().matches(query) or query in "resolution width height resx resy"


class NumberField(Field):
    def _build(self, value):
        option = self.option
        is_float = option.kind == "float"
        step = 10 ** -option.digits if is_float else 1
        adjustment = Gtk.Adjustment(
            value=float(value),
            lower=option.minimum,
            upper=option.maximum,
            step_increment=step,
            page_increment=step * 10,
        )
        return Adw.SpinRow(
            title=self._title(),
            subtitle=self._subtitle(),
            adjustment=adjustment,
            digits=option.digits if is_float else 0,
        )

    def current(self):
        number = self.row.get_value()
        if self.option.kind == "float":
            return f"{number:.{self.option.digits}f}"
        return str(int(round(number)))

    def set(self, value):
        self.row.set_value(float(value))


class TextField(Field):
    def _build(self, value):
        row = Adw.EntryRow(title=self._title())
        row.set_text(value)
        row.set_tooltip_text(self.option.description)
        return row

    def current(self):
        return self.row.get_text()

    def set(self, value):
        self.row.set_text(value)


class HotkeyField(Field):
    def _build(self, value):
        self._code = int(value)
        self._capturing = False
        self.button = Gtk.Button(valign=Gtk.Align.CENTER, css_classes=["hotkey-button"])
        self.button.connect("clicked", self._start_capture)
        keys = Gtk.EventControllerKey(propagation_phase=Gtk.PropagationPhase.CAPTURE)
        keys.connect("key-pressed", self._on_key)
        self.button.add_controller(keys)
        focus = Gtk.EventControllerFocus()
        focus.connect("leave", lambda *_: self._stop_capture())
        self.button.add_controller(focus)
        row = Adw.ActionRow(title=self._title(), subtitle=self._subtitle())
        row.add_suffix(self.button)
        self._refresh()
        return row

    def _refresh(self):
        self.button.set_label("Press a key..." if self._capturing else vk_name(self._code))

    def _start_capture(self, _button):
        self._capturing = True
        self._refresh()
        self.button.grab_focus()

    def _stop_capture(self):
        if self._capturing:
            self._capturing = False
            self._refresh()

    def _on_key(self, _controller, keyval, _keycode, _state):
        if not self._capturing:
            return False
        name = Gdk.keyval_name(keyval)
        code = vk_from_key_name(name) if name else None
        if name != "Escape" and code is not None:
            self._code = code
        self._stop_capture()
        return True

    def current(self):
        return str(self._code)

    def set(self, value):
        self._code = int(value)
        self._refresh()


_KIND_TO_FIELD = {
    "switch": SwitchField,
    "choice": ChoiceField,
    "int": NumberField,
    "float": NumberField,
    "text": TextField,
    "hotkey": HotkeyField,
}


def make_field(option: Option, value: str, partner: tuple[Option, str] | None = None) -> Field:
    if option.kind == "resolution":
        return ResolutionField(option, value, partner)
    return _KIND_TO_FIELD[option.kind](option, value)
