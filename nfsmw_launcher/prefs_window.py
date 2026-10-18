import threading
from dataclasses import replace

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, GObject, Gtk

from .config import CLOSE_ACTIONS, DEFAULT_ENV, Config
from .layout import TwoColumnPage
from .tray import TRAY_HELP, tray_available
from .runners import GAME_EXE, find_bottles_cli, find_game_exe, list_bottles

RUNNERS = [
    ("bottles", "Bottles"),
    ("wine", "Wine"),
    ("umu", "Proton (umu-run)"),
    ("custom", "Custom command"),
]


class PreferencesWindow(Adw.Window):
    __gsignals__ = {"saved": (GObject.SignalFlags.RUN_FIRST, None, (object,))}

    def __init__(self, parent: Gtk.Window, config: Config):
        super().__init__(
            transient_for=parent, modal=True, title="Launcher Settings", default_width=960, default_height=470
        )
        self._config = config
        self._game_dir = config.game_dir
        self._bottles: list[str] = []
        self._build_ui()
        self._refresh_game_status()
        self._sync_runner_groups()
        self._load_bottles()

    def _entry(self, title: str, text: str, folder_picker: bool = False) -> Adw.EntryRow:
        row = Adw.EntryRow(title=title)
        row.set_text(text)
        if folder_picker:
            button = Gtk.Button(
                icon_name="folder-open-symbolic", valign=Gtk.Align.CENTER, css_classes=["flat"],
                tooltip_text="Choose folder",
            )
            button.connect("clicked", lambda *_: self._choose_folder(row.set_text))
            row.add_suffix(button)
        return row

    def _choose_folder(self, apply):
        dialog = Gtk.FileDialog(title="Choose a folder")

        def done(source, result):
            try:
                folder = source.select_folder_finish(result)
            except GLib.Error:
                return
            apply(folder.get_path())

        dialog.select_folder(self, None, done)

    def _build_ui(self):
        config = self._config
        page = TwoColumnPage()

        game = Adw.PreferencesGroup(title="Game")
        self._game_row = Adw.ActionRow(title="Game folder")
        choose = Gtk.Button(label="Choose...", valign=Gtk.Align.CENTER)
        choose.connect("clicked", lambda *_: self._choose_folder(self._set_game_dir))
        self._game_row.add_suffix(choose)
        game.add(self._game_row)
        page.add(game, column=0)

        run = Adw.PreferencesGroup(title="How to run the game")
        self._runner_row = Adw.ComboRow(
            title="Run with", model=Gtk.StringList.new([label for _, label in RUNNERS])
        )
        self._runner_row.set_selected(
            next((i for i, (key, _) in enumerate(RUNNERS) if key == config.runner), 0)
        )
        self._runner_row.connect("notify::selected", lambda *_: self._sync_runner_groups())
        run.add(self._runner_row)
        page.add(run, column=0)

        self._bottles_group = Adw.PreferencesGroup(title="Bottles")
        self._bottle_row = Adw.ComboRow(title="Bottle", model=Gtk.StringList.new([]))
        self._bottles_group.add(self._bottle_row)
        page.add(self._bottles_group, column=0)

        self._wine_group = Adw.PreferencesGroup(
            title="Wine", description="Leave the binary empty to use wine from your PATH."
        )
        self._wine_binary = self._entry("Wine binary", config.wine_binary)
        self._wine_prefix = self._entry("Wine prefix folder", config.wine_prefix, folder_picker=True)
        self._wine_group.add(self._wine_binary)
        self._wine_group.add(self._wine_prefix)
        page.add(self._wine_group, column=0)

        self._umu_group = Adw.PreferencesGroup(
            title="Proton (umu-run)",
            description="Needs umu-launcher installed. Leave Proton empty for umu's default.",
        )
        self._umu_proton = self._entry("Proton version or folder (for example GE-Proton)", config.umu_proton)
        self._umu_prefix = self._entry("Prefix folder", config.umu_prefix, folder_picker=True)
        self._umu_group.add(self._umu_proton)
        self._umu_group.add(self._umu_prefix)
        page.add(self._umu_group, column=0)

        self._custom_group = Adw.PreferencesGroup(
            title="Custom command",
            description="{exe} is replaced with the path to speed.exe and {dir} with the game folder.",
        )
        self._custom_command = self._entry("Command", config.custom_command)
        self._custom_group.add(self._custom_command)
        page.add(self._custom_group, column=0)

        closing = Adw.PreferencesGroup(title="Closing the launcher")
        self._close_row = Adw.ComboRow(
            title="When closing the window",
            model=Gtk.StringList.new(["Ask every time", "Quit", "Minimize to tray"]),
        )
        self._close_row.set_selected(CLOSE_ACTIONS.index(config.close_action))
        if not tray_available():
            note = Gtk.Image(icon_name="dialog-information-symbolic", valign=Gtk.Align.CENTER)
            note.set_tooltip_text(TRAY_HELP)
            self._close_row.add_suffix(note)
        closing.add(self._close_row)
        page.add(closing, column=1)

        env = Adw.PreferencesGroup(
            title="Environment variables",
            description="One KEY=VALUE per line. The default makes Wine load the Redux mod loader.",
        )
        reset = Gtk.Button(label="Reset", valign=Gtk.Align.CENTER, css_classes=["flat"])
        reset.connect("clicked", lambda *_: self._env_buffer.set_text(DEFAULT_ENV))
        env.set_header_suffix(reset)
        self._env_buffer = Gtk.TextBuffer(text=config.env)
        view = Gtk.TextView(
            buffer=self._env_buffer, monospace=True, top_margin=8, bottom_margin=8,
            left_margin=10, right_margin=10, wrap_mode=Gtk.WrapMode.WORD_CHAR,
        )
        frame = Gtk.ScrolledWindow(child=view, min_content_height=170, css_classes=["card"])
        env.add(frame)
        page.add(env, column=1)

        cancel = Gtk.Button(label="Cancel")
        cancel.connect("clicked", lambda *_: self.close())
        save = Gtk.Button(label="Save", css_classes=["gold"])
        save.connect("clicked", self._on_save)
        header = Adw.HeaderBar(show_end_title_buttons=False, show_start_title_buttons=False)
        header.pack_start(cancel)
        header.pack_end(save)
        toolbar = Adw.ToolbarView(content=page)
        toolbar.add_top_bar(header)
        self.set_content(toolbar)

    def _set_game_dir(self, path: str):
        self._game_dir = path
        self._refresh_game_status()

    def _refresh_game_status(self):
        if not self._game_dir:
            self._game_row.set_subtitle("Not set")
        elif find_game_exe(self._game_dir) is None:
            folder = GLib.markup_escape_text(self._game_dir)
            self._game_row.set_subtitle(f"{folder}\n{GAME_EXE} not found in this folder")
        else:
            self._game_row.set_subtitle(GLib.markup_escape_text(self._game_dir))

    def _selected_runner(self) -> str:
        return RUNNERS[self._runner_row.get_selected()][0]

    def _sync_runner_groups(self):
        runner = self._selected_runner()
        self._bottles_group.set_visible(runner == "bottles")
        self._wine_group.set_visible(runner == "wine")
        self._umu_group.set_visible(runner == "umu")
        self._custom_group.set_visible(runner == "custom")

    def _load_bottles(self):
        def work():
            cli = find_bottles_cli()
            names = list_bottles(cli) if cli else []
            GLib.idle_add(self._set_bottles, names, cli is not None)

        threading.Thread(target=work, daemon=True).start()

    def _set_bottles(self, names: list[str], bottles_found: bool):
        saved = self._config.bottles_bottle
        if saved and saved not in names:
            names = [*names, saved]
        self._bottles = names
        self._bottle_row.set_model(Gtk.StringList.new(names))
        if saved in names:
            self._bottle_row.set_selected(names.index(saved))
        self._bottle_row.set_subtitle("" if bottles_found else "Bottles was not found on this system")

    def _on_save(self, _button):
        bottle = ""
        if self._bottles and self._bottle_row.get_selected() < len(self._bottles):
            bottle = self._bottles[self._bottle_row.get_selected()]
        start, end = self._env_buffer.get_bounds()
        config = replace(
            self._config,
            game_dir=self._game_dir,
            runner=self._selected_runner(),
            bottles_bottle=bottle,
            wine_binary=self._wine_binary.get_text().strip(),
            wine_prefix=self._wine_prefix.get_text().strip(),
            umu_proton=self._umu_proton.get_text().strip(),
            umu_prefix=self._umu_prefix.get_text().strip(),
            custom_command=self._custom_command.get_text().strip(),
            env=self._env_buffer.get_text(start, end, False),
            close_action=CLOSE_ACTIONS[self._close_row.get_selected()],
        )
        self.emit("saved", config)
        self.close()
