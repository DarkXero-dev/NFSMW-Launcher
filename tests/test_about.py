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


def test_launcher_shows_compatible_distro_logos_in_the_bottom_right_corner(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    from nfsmw_launcher.launcher_window import LOGOS, LauncherWindow
    from nfsmw_launcher.settings_window import ASSETS

    assert [name for name, _ in LOGOS] == ["Arch Linux", "XeroLinux", "CachyOS", "EndeavourOS"]
    assert all((ASSETS / "logos" / file).is_file() for _, file in LOGOS)

    window = LauncherWindow(Adw.Application(application_id="org.nfsmw.ReduxLauncherTest2"))

    def find(widget, css):
        child = widget.get_first_child()
        while child:
            if css in child.get_css_classes():
                return child
            hit = find(child, css)
            if hit:
                return hit
            child = child.get_next_sibling()

    logos = find(window.get_content(), "distro-logos")
    tooltips = []
    image = logos.get_first_child()
    while image:
        tooltips.append(image.get_tooltip_text())
        image = image.get_next_sibling()
    assert tooltips == ["Arch Linux", "XeroLinux", "CachyOS", "EndeavourOS"]

    compatible = logos.get_parent()
    label = compatible.get_first_child()
    assert label.get_label() == "Compatible with:"
    assert label.get_next_sibling() is logos

    assert (compatible.get_halign(), compatible.get_valign()) == (Gtk.Align.END, Gtk.Align.END)
    buttons = find(window.get_content(), "launch-buttons")
    assert compatible.get_parent() is not buttons.get_parent()


def find_css(widget, css):
    child = widget.get_first_child()
    while child:
        if css in child.get_css_classes():
            return child
        hit = find_css(child, css)
        if hit:
            return hit
        child = child.get_next_sibling()


def test_about_explains_what_redux_means_in_a_rounded_card():
    content = AboutWindow(None, "1.0.9").get_content()
    card = find_css(content, "redux-card")
    assert "card" in card.get_css_classes()
    texts = labels(card)
    assert texts[0] == "What is Redux?"
    assert any("community-made overhaul mod" in t and "2005 PC version" in t for t in texts)
    assert any("pre-configured compilation pack" in t and "high-definition texture upgrades" in t for t in texts)
    assert any("look and play like a modern video game remaster" in t for t in texts)


def test_about_card_sits_beside_the_logo_column_so_the_window_stays_short():
    content = AboutWindow(None, "1.0.9").get_content()
    card = find_css(content, "redux-card")
    assert card.get_parent().get_orientation() == Gtk.Orientation.HORIZONTAL


def test_logo_column_and_redux_card_end_up_exactly_the_same_height():
    from gi.repository import GLib

    window = AboutWindow(None, "1.0.9")
    window.present()
    context = GLib.MainContext.default()
    for _ in range(60):
        context.iteration(False)
    content = window.get_content()
    identity = find_css(content, "about-identity")
    card = find_css(content, "redux-card")
    assert identity.get_valign() == Gtk.Align.FILL and card.get_valign() == Gtk.Align.FILL
    assert identity.get_height() == card.get_height() > 0
    assert identity.measure(Gtk.Orientation.VERTICAL, 280)[1] <= identity.get_height()
