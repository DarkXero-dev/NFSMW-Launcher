import pytest

gi = pytest.importorskip("gi")
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

if not Gtk.init_check():
    pytest.skip("no display available", allow_module_level=True)
Adw.init()

from nfsmw_launcher import launcher_window
from nfsmw_launcher.config import load_config


@pytest.fixture
def window(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setattr(launcher_window, "tray_available", lambda: True)
    win = launcher_window.LauncherWindow(Adw.Application(application_id="org.nfsmw.ReduxLauncherCloseTest"))
    win._tray = type("FakeTray", (), {"shown": 0, "hidden": 0,
                                      "show": lambda s: (setattr(s, "shown", s.shown + 1), True)[1],
                                      "hide": lambda s: setattr(s, "hidden", s.hidden + 1)})()
    win.present()
    return win


def test_remembered_tray_choice_hides_the_window_without_asking(window):
    window._config.close_action = "tray"
    assert window._on_close_request(window) is True
    assert not window.get_visible()
    assert window._tray.shown == 1


def test_remembered_quit_choice_lets_the_window_close(window):
    window._config.close_action = "quit"
    assert window._on_close_request(window) is False


def test_without_a_tray_a_remembered_tray_choice_explains_instead_of_hiding(window, monkeypatch):
    monkeypatch.setattr(launcher_window, "tray_available", lambda: False)
    window._config.close_action = "tray"
    assert window._on_close_request(window) is True
    assert window.get_visible()
    assert window._tray.shown == 0


def images(widget, icon_name):
    found = []
    child = widget.get_first_child()
    while child:
        if isinstance(child, Gtk.Image) and child.get_icon_name() == icon_name:
            found.append(child)
        found.extend(images(child, icon_name))
        child = child.get_next_sibling()
    return found


def labels_and_checks(widget):
    found = []
    child = widget.get_first_child()
    while child:
        if isinstance(child, Gtk.Label):
            found.append(child.get_label())
        if isinstance(child, Gtk.CheckButton):
            found.append(child.get_label())
        found.extend(labels_and_checks(child))
        child = child.get_next_sibling()
    return found


def test_close_dialog_with_a_tray_enables_minimize_and_has_no_info_icon(window):
    dialog = window._ask_close()
    assert dialog.tray_button.get_sensitive()
    assert not images(dialog.get_content(), "dialog-information-symbolic")


def test_close_dialog_without_a_tray_disables_minimize_and_shows_the_info_icon(window, monkeypatch):
    monkeypatch.setattr(launcher_window, "tray_available", lambda: False)
    dialog = window._ask_close()
    assert not dialog.tray_button.get_sensitive()
    assert dialog.quit_button.get_sensitive()
    assert images(dialog.get_content(), "dialog-information-symbolic")


def test_close_dialog_buttons_sit_side_by_side_with_remember_checkbox_bottom_right(window):
    dialog = window._ask_close()
    row = dialog.quit_button.get_parent()
    assert dialog.cancel_button.get_parent() is row and dialog.tray_button.get_parent() is row
    assert row.get_orientation() == Gtk.Orientation.HORIZONTAL
    texts = labels_and_checks(dialog.get_content())
    assert "Do you want to save setting?" not in texts
    assert dialog.remember.get_label() == "Remember setting"
    assert dialog.remember.get_halign() == Gtk.Align.END
    assert row.get_next_sibling() is dialog.remember


def test_clicking_a_close_dialog_button_reports_the_choice_and_remember_state(window):
    choices = []
    dialog = window._ask_close()
    dialog._on_choice = lambda choice, remember: choices.append((choice, remember))
    dialog.remember.set_active(True)
    dialog.quit_button.emit("clicked")
    assert choices == [("quit", True)]


def test_launcher_settings_show_an_info_icon_only_when_no_tray_exists(monkeypatch):
    from nfsmw_launcher import prefs_window
    from nfsmw_launcher.config import Config

    monkeypatch.setattr(prefs_window, "tray_available", lambda: False)
    assert images(prefs_window.PreferencesWindow(None, Config()).get_content(), "dialog-information-symbolic")
    monkeypatch.setattr(prefs_window, "tray_available", lambda: True)
    assert not images(prefs_window.PreferencesWindow(None, Config()).get_content(), "dialog-information-symbolic")


def test_close_setting_in_launcher_settings_is_saved(monkeypatch):
    from nfsmw_launcher import prefs_window
    from nfsmw_launcher.config import Config

    monkeypatch.setattr(prefs_window, "tray_available", lambda: True)
    win = prefs_window.PreferencesWindow(None, Config(close_action="ask"))
    saved = []
    win.connect("saved", lambda _w, config: saved.append(config))
    win._close_row.set_selected(2)
    win._on_save(None)
    assert saved[0].close_action == "tray"


def test_ask_mode_blocks_the_close_and_shows_a_dialog(window):
    window._config.close_action = "ask"
    assert window._on_close_request(window) is True
    assert window.get_visible()


def test_choosing_tray_with_remember_saves_the_setting_and_hides(window):
    window._config.close_action = "ask"
    window._on_close_choice("tray", remember=True)
    assert load_config().close_action == "tray"
    assert not window.get_visible()


def test_choosing_without_remember_does_not_save(window):
    window._config.close_action = "ask"
    window._on_close_choice("tray", remember=False)
    assert load_config().close_action == "ask"


def test_cancel_keeps_the_window_open_and_saves_nothing(window):
    window._on_close_choice("cancel", remember=True)
    assert window.get_visible()
    assert load_config().close_action == "ask"


def test_showing_the_window_again_removes_the_tray_icon(window):
    window._config.close_action = "tray"
    window._on_close_request(window)
    window._show_from_tray()
    assert window.get_visible()
    assert window._tray.hidden == 1


def make_game(tmp_path):
    (tmp_path / "speed.exe").write_bytes(b"MZ")
    (tmp_path / "scripts").mkdir()
    return tmp_path


def test_tray_launch_starts_the_game_and_keeps_the_launcher_running(window, tmp_path, monkeypatch):
    window._config.game_dir = str(make_game(tmp_path))
    window._config.runner = "custom"
    window._config.custom_command = "true"
    started, quit_calls = [], []
    monkeypatch.setattr(launcher_window, "start", lambda launch: started.append(launch.argv))
    monkeypatch.setattr(window, "_quit", lambda: quit_calls.append(1))
    window._launch_from_tray()
    assert started == [["true"]]
    assert quit_calls == []


def test_tray_launch_with_a_broken_setup_shows_the_window_instead(window, monkeypatch):
    window._config.game_dir = ""
    started = []
    monkeypatch.setattr(launcher_window, "start", lambda launch: started.append(launch))
    monkeypatch.setattr(window, "_open_preferences", lambda: None)
    window.set_visible(False)
    window._launch_from_tray()
    assert started == []
    assert window.get_visible()


def test_tray_settings_shows_the_window_and_opens_redux_settings(window, tmp_path, monkeypatch):
    window._config.game_dir = str(make_game(tmp_path))
    opened = []

    class Recorder:
        def __init__(self, parent, scripts_dir):
            opened.append(scripts_dir)

        def connect(self, *args):
            pass

        def present(self):
            pass

    monkeypatch.setattr(launcher_window, "ReduxSettingsWindow", Recorder)
    window.set_visible(False)
    window._settings_from_tray()
    assert window.get_visible()
    assert window._tray.hidden == 1
    assert opened == [tmp_path / "scripts"]
