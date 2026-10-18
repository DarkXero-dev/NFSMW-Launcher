import pytest

gi = pytest.importorskip("gi")
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

if not Gtk.init_check():
    pytest.skip("no display available", allow_module_level=True)
Adw.init()

from nfsmw_launcher.about_window import LINKS, AboutWindow


def labels(widget):
    found = []
    child = widget.get_first_child()
    while child:
        if isinstance(child, Gtk.Label):
            found.append(child.get_label())
        found.extend(labels(child))
        child = child.get_next_sibling()
    return found


def test_links_point_at_the_authors_github_and_site():
    assert LINKS == [
        ("GitHub", "https://github.com/DarkXero-dev"),
        ("Site", "https://techxero.com"),
    ]


def buttons(widget):
    found = []
    child = widget.get_first_child()
    while child:
        if isinstance(child, Gtk.Button):
            found.append(child)
        found.extend(buttons(child))
        child = child.get_next_sibling()
    return found


def test_links_are_side_by_side_buttons_without_visible_urls():
    content = AboutWindow(None, "1.0.9").get_content()
    link_buttons = [b for b in buttons(content) if labels(b)]
    assert [labels(b)[0] for b in link_buttons] == ["GitHub", "Site"]
    row = link_buttons[0].get_parent()
    assert link_buttons[1].get_parent() is row
    assert row.get_orientation() == Gtk.Orientation.HORIZONTAL
    assert not any("http" in line for line in labels(content))


def test_about_window_shows_name_and_version():
    text = labels(AboutWindow(None, "1.0.9").get_content())
    assert "DarkXero" in text
    assert any("1.0.9" in line for line in text)


def test_buttons_open_their_own_urls(monkeypatch):
    opened = []

    class Recorder:
        def __init__(self, uri):
            self.uri = uri

        def launch(self, parent, cancellable, callback):
            opened.append(self.uri)

    monkeypatch.setattr(Gtk.UriLauncher, "new", Recorder)
    content = AboutWindow(None, "1.0.9").get_content()
    for button in [b for b in buttons(content) if labels(b)]:
        button.emit("clicked")
    assert opened == [uri for _, uri in LINKS]


def test_update_button_is_hidden_until_an_update_is_found(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    from nfsmw_launcher.launcher_window import LauncherWindow
    from nfsmw_launcher.updater import Update

    window = LauncherWindow(Adw.Application(application_id="org.nfsmw.ReduxLauncherTest"))
    assert not window._update_button.get_visible()
    window._on_update_found(Update("1.0.99", "https://example.test/x", None))
    assert window._update_button.get_visible()
    assert "1.0.99" in window._update_button.get_tooltip_text()
