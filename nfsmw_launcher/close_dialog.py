import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gtk

from .tray import TRAY_HELP


class CloseDialog(Adw.Window):
    def __init__(self, parent: Gtk.Window | None, tray_ok: bool, on_choice):
        super().__init__(transient_for=parent, modal=True, resizable=False, title="Close the launcher?", width_request=560)
        self._on_choice = on_choice

        heading = Gtk.Label(label="Close the launcher?", css_classes=["title-3"])
        body = Gtk.Label(
            label="Quit completely, or keep it running in the system tray.", css_classes=["dim-label"]
        )

        self.cancel_button = Gtk.Button(label="Cancel")
        self.quit_button = Gtk.Button(label="Quit")
        self.tray_button = Gtk.Button(label="Minimize to Tray", sensitive=tray_ok)
        (self.tray_button if tray_ok else self.quit_button).add_css_class("gold")
        buttons = Gtk.Box(spacing=10, homogeneous=True, halign=Gtk.Align.CENTER, margin_top=6)
        for choice, button in (
            ("cancel", self.cancel_button),
            ("quit", self.quit_button),
            ("tray", self.tray_button),
        ):
            button.add_css_class("pill")
            button.connect("clicked", lambda _b, picked=choice: self._choose(picked))
            buttons.append(button)

        self.remember = Gtk.CheckButton(label="Remember setting", halign=Gtk.Align.END, margin_top=8)

        content = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12,
            margin_top=8,
            margin_bottom=22,
            margin_start=28,
            margin_end=28,
        )
        content.append(heading)
        content.append(body)
        if not tray_ok:
            note = Gtk.Box(spacing=10, halign=Gtk.Align.CENTER, margin_top=4)
            note.append(Gtk.Image(icon_name="dialog-information-symbolic", valign=Gtk.Align.START))
            note.append(Gtk.Label(label=TRAY_HELP, wrap=True, xalign=0, max_width_chars=60, css_classes=["dim-label"]))
            content.append(note)
        content.append(buttons)
        content.append(self.remember)

        view = Adw.ToolbarView(content=content)
        view.add_top_bar(Adw.HeaderBar(css_classes=["flat"], title_widget=Gtk.Box()))
        self.set_content(view)

        keys = Gtk.EventControllerKey()
        keys.connect("key-pressed", self._on_key)
        self.add_controller(keys)

    def _on_key(self, _controller, keyval, _keycode, _state):
        if keyval == Gdk.KEY_Escape:
            self.close()
            return True
        return False

    def _choose(self, choice: str):
        self._on_choice(choice, self.remember.get_active())
        self.close()
