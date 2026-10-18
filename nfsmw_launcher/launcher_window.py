import os
import subprocess
import threading
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk

from .about_window import AboutWindow
from .config import Config, load_config, save_config
from .prefs_window import PreferencesWindow
from .runners import build_launch, find_game_dir, host_env, start, validate
from .settings_window import ASSETS, ReduxSettingsWindow
from .updater import Update, check_for_update, download, install, relaunch_argv, update_check_enabled
from .version import REPO, VERSION


class LauncherWindow(Adw.ApplicationWindow):
    def __init__(self, application: Adw.Application):
        super().__init__(application=application, title="Most Wanted Redux", default_width=960, default_height=540, resizable=False)
        self._config = load_config()
        self._autodetect_game_dir()
        self._toasts = Adw.ToastOverlay()
        self._update: Update | None = None
        self._build_ui()
        if validate(self._config):
            GLib.idle_add(self._open_preferences)
        if update_check_enabled(os.environ, VERSION, REPO):
            threading.Thread(target=self._check_for_update, daemon=True).start()

    def _autodetect_game_dir(self):
        if self._config.game_dir:
            return
        candidates = [Path(__file__).resolve().parent.parent.parent]
        if os.environ.get("APPIMAGE"):
            candidates.insert(0, Path(os.environ["APPIMAGE"]).resolve().parent)
        found = find_game_dir(candidates)
        if found:
            self._config.game_dir = str(found)
            save_config(self._config)

    def _build_ui(self):
        art = Gtk.Picture.new_for_filename(str(ASSETS / "launcher.jpg"))
        art.set_content_fit(Gtk.ContentFit.COVER)
        art.set_can_shrink(True)

        cog = Gtk.Button(icon_name="emblem-system-symbolic", tooltip_text="Launcher settings")
        cog.connect("clicked", lambda *_: self._open_preferences())
        header = Adw.HeaderBar(
            css_classes=["art-header"], title_widget=Gtk.Box(), valign=Gtk.Align.START
        )
        header.pack_end(cog)
        about = Gtk.Button(icon_name="help-about-symbolic", tooltip_text="About")
        about.connect("clicked", lambda *_: AboutWindow(self, VERSION).present())
        header.pack_end(about)
        self._update_button = Gtk.Button(label="UPDATE & RELAUNCH", css_classes=["gold"], visible=False)
        self._update_button.connect("clicked", self._on_update_clicked)
        header.pack_end(self._update_button)

        launch = Gtk.Button(label="LAUNCH GAME", css_classes=["gold"])
        launch.connect("clicked", self._on_launch)
        settings = Gtk.Button(label="REDUX SETTINGS", css_classes=["settings-button"])
        settings.connect("clicked", self._on_redux_settings)
        bar = Gtk.Box(
            spacing=16, halign=Gtk.Align.FILL, valign=Gtk.Align.END, css_classes=["launch-bar"]
        )
        bar.append(Gtk.Box(hexpand=True))
        bar.append(launch)
        bar.append(settings)
        bar.append(Gtk.Box(hexpand=True))

        overlay = Gtk.Overlay(child=art)
        overlay.add_overlay(bar)
        overlay.add_overlay(header)
        self._toasts.set_child(overlay)
        self.set_content(self._toasts)

    def _check_for_update(self):
        update = check_for_update(REPO, VERSION)
        if update:
            GLib.idle_add(self._on_update_found, update)

    def _on_update_found(self, update: Update):
        self._update = update
        self._update_button.set_tooltip_text(f"Version {VERSION} to {update.version}")
        self._update_button.set_visible(True)
        return False

    def _on_update_clicked(self, button: Gtk.Button):
        button.set_sensitive(False)
        button.set_label("DOWNLOADING...")
        threading.Thread(target=self._run_update, daemon=True).start()

    def _run_update(self):
        target = Path(os.environ["APPIMAGE"])
        partial = target.with_name(target.name + ".update")
        try:
            download(self._update.url, partial, self._update.sha256, self._show_progress)
            install(partial, target)
        except (OSError, ValueError) as error:
            GLib.idle_add(self._update_failed, str(error))
            return
        GLib.idle_add(self._relaunch, target)

    def _show_progress(self, done: int, total: int):
        label = f"DOWNLOADING {done * 100 // total}%" if total else "DOWNLOADING..."
        GLib.idle_add(self._update_button.set_label, label)

    def _update_failed(self, reason: str):
        self._toast(f"Update failed: {reason}")
        self._update_button.set_label("UPDATE & RELAUNCH")
        self._update_button.set_sensitive(True)
        return False

    def _relaunch(self, target: Path):
        subprocess.Popen(
            relaunch_argv(os.getpid(), str(target)),
            env=host_env(os.environ),
            start_new_session=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.get_application().quit()
        return False

    def _toast(self, message: str):
        self._toasts.add_toast(Adw.Toast(title=message))

    def _open_preferences(self):
        window = PreferencesWindow(self, self._config)
        window.connect("saved", self._on_preferences_saved)
        window.present()
        return False

    def _on_preferences_saved(self, _window, config: Config):
        self._config = config
        save_config(config)
        self._toast("Launcher settings saved")

    def _on_launch(self, _button):
        problems = validate(self._config)
        if problems:
            self._toast(problems[0])
            self._open_preferences()
            return
        try:
            start(build_launch(self._config))
        except OSError as error:
            self._toast(f"Could not start the game: {error}")
            return
        self._toast("Launching...")
        GLib.timeout_add_seconds(2, self.close)

    def _on_redux_settings(self, _button):
        scripts_dir = Path(self._config.game_dir) / "scripts"
        if not self._config.game_dir or not scripts_dir.is_dir():
            self._toast("Set the game folder first (cog, top right)")
            return
        window = ReduxSettingsWindow(self, scripts_dir)
        window.connect("saved", lambda _w, count: self._toast(f"Saved {count} change(s)" if count else "No changes"))
        window.present()
