from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, GObject, Gtk

from .fields import make_field
from .ini_file import IniFile
from .layout import TwoColumnPage
from .schema import FILES, TABS, build_options

ASSETS = Path(__file__).resolve().parent.parent / "assets"

_TAB_ICONS = {
    "Display": "video-display-symbolic",
    "Graphics": "applications-graphics-symbolic",
    "Gameplay": "input-gaming-symbolic",
    "Menus": "view-list-symbolic",
    "Hotkeys": "input-keyboard-symbolic",
    "Advanced": "emblem-system-symbolic",
}


def _banner() -> Gtk.Widget:
    picture = Gtk.Picture.new_for_filename(str(ASSETS / "settings-banner.png"))
    picture.set_content_fit(Gtk.ContentFit.COVER)
    picture.set_can_shrink(True)
    picture.set_size_request(-1, 96)

    title = Gtk.Label(label="REDUX SETTINGS", xalign=0, css_classes=["banner-title"])
    subtitle = Gtk.Label(
        label="MOST WANTED REDUX  ·  GAME TWEAKS", xalign=0, css_classes=["banner-subtitle"]
    )
    text = Gtk.Box(
        orientation=Gtk.Orientation.VERTICAL,
        spacing=2,
        halign=Gtk.Align.START,
        valign=Gtk.Align.CENTER,
        margin_start=28,
    )
    text.append(title)
    text.append(subtitle)

    overlay = Gtk.Overlay(child=picture, css_classes=["banner"])
    overlay.add_overlay(text)
    return overlay


class ReduxSettingsWindow(Adw.Window):
    __gsignals__ = {"saved": (GObject.SignalFlags.RUN_FIRST, None, (int,))}

    def __init__(self, parent: Gtk.Window, scripts_dir: Path):
        super().__init__(
            transient_for=parent, modal=True, title="Redux Settings", default_width=1240, default_height=640
        )
        self._scripts_dir = scripts_dir
        self._files: list[tuple[Path, IniFile]] = []
        self._fields = []
        self._groups: list[tuple[Adw.PreferencesGroup, list]] = []
        self._pages: list[tuple[Adw.ViewStackPage, list]] = []
        self._discard_confirmed = False

        self._toasts = Adw.ToastOverlay()
        self._stack = Adw.ViewStack(vexpand=True)
        self._load()
        self._build_ui()
        self.connect("close-request", self._on_close_request)

    def _load(self):
        grouped: dict[str, dict[str, list]] = {tab: {} for tab in TABS}

        for name in FILES:
            path = self._scripts_dir / name
            if not path.is_file():
                continue
            ini = IniFile.load(path)
            self._files.append((path, ini))
            options = build_options(ini, name)
            height = next((o for o in options if o.kind == "resolution_height"), None)
            partner = height and (height, ini.get(height.section, height.key))
            for option in options:
                if option.kind == "resolution_height":
                    continue
                field = make_field(option, ini.get(option.section, option.key), partner)
                self._fields.append(field)
                grouped[option.tab].setdefault(option.group, []).append(field)

        for tab in TABS:
            if not grouped[tab]:
                continue
            page = TwoColumnPage()
            tab_fields = []
            for title, members in grouped[tab].items():
                group = Adw.PreferencesGroup(title=title)
                for field in members:
                    group.add(field.row)
                page.add(group, sum(1 + len(f.option.description) // 60 for f in members))
                self._groups.append((group, members))
                tab_fields.extend(members)
            stack_page = self._stack.add_titled_with_icon(page, tab.lower(), tab, _TAB_ICONS[tab])
            self._pages.append((stack_page, tab_fields))

    def _build_ui(self):
        switcher = Adw.ViewSwitcher(stack=self._stack, policy=Adw.ViewSwitcherPolicy.WIDE)
        search_entry = Gtk.SearchEntry(placeholder_text="Search every setting", hexpand=True)
        search_entry.connect("search-changed", self._on_search)
        search_bar = Gtk.SearchBar(child=search_entry)
        search_bar.connect_entry(search_entry)
        toggle = Gtk.ToggleButton(icon_name="system-search-symbolic", tooltip_text="Search")
        toggle.bind_property(
            "active", search_bar, "search-mode-enabled", GObject.BindingFlags.BIDIRECTIONAL
        )

        GLib.idle_add(switcher.grab_focus)
        header = Adw.HeaderBar(title_widget=switcher)
        header.pack_start(toggle)

        restore = Gtk.Button(label="Restore Defaults", tooltip_text="Reset every option that lists a default")
        restore.connect("clicked", self._on_restore_clicked)
        cancel = Gtk.Button(label="Cancel")
        cancel.connect("clicked", lambda *_: self.close())
        save = Gtk.Button(label="Save", css_classes=["gold"])
        save.connect("clicked", self._on_save)
        actions = Gtk.ActionBar()
        actions.pack_start(restore)
        actions.pack_end(save)
        actions.pack_end(cancel)

        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        body.append(_banner())
        if self._fields:
            body.append(self._stack)
        else:
            body.append(
                Adw.StatusPage(
                    icon_name="document-open-symbolic",
                    title="No settings files found",
                    description=f"Looked in {self._scripts_dir}",
                    vexpand=True,
                )
            )
            save.set_sensitive(False)
            restore.set_sensitive(False)
            toggle.set_sensitive(False)

        view = Adw.ToolbarView(content=body)
        view.add_top_bar(header)
        view.add_top_bar(search_bar)
        view.add_bottom_bar(actions)
        self._toasts.set_child(view)
        self.set_content(self._toasts)

    def _on_search(self, entry: Gtk.SearchEntry):
        query = entry.get_text().strip().lower()
        for field in self._fields:
            field.row.set_visible(not query or field.matches(query))
        for group, fields in self._groups:
            group.set_visible(any(f.row.get_visible() for f in fields))
        for page, fields in self._pages:
            page.set_visible(any(f.row.get_visible() for f in fields))

    def _on_restore_clicked(self, _button):
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading="Restore defaults?",
            body="Every option that lists a default value is reset. Nothing is written until you press Save.",
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("restore", "Restore")
        dialog.set_response_appearance("restore", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.connect("response", self._on_restore_response)
        dialog.present()

    def _on_restore_response(self, _dialog, response):
        if response == "restore":
            for field in self._fields:
                field.restore_default()

    def _on_save(self, _button):
        changed = [f for f in self._fields if f.changed()]
        try:
            for path, ini in self._files:
                touched = False
                for field in changed:
                    for option, value in field.entries():
                        if option.file == path.name:
                            ini.set(option.section, option.key, value)
                            touched = True
                if touched:
                    ini.save(path)
        except OSError as error:
            self._toasts.add_toast(Adw.Toast(title=f"Could not save: {error}"))
            return
        self._discard_confirmed = True
        self.emit("saved", len(changed))
        self.close()

    def _on_close_request(self, _window):
        if self._discard_confirmed or not any(f.changed() for f in self._fields):
            return False
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading="Discard changes?",
            body="You have unsaved changes.",
        )
        dialog.add_response("keep", "Keep Editing")
        dialog.add_response("discard", "Discard")
        dialog.set_response_appearance("discard", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.connect("response", self._on_discard_response)
        dialog.present()
        return True

    def _on_discard_response(self, _dialog, response):
        if response == "discard":
            self._discard_confirmed = True
            self.close()
