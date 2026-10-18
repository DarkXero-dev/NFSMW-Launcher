import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, Gtk

from .settings_window import ASSETS

LINKS = [
    ("GitHub", "https://github.com/DarkXero-dev"),
    ("Site", "https://techxero.com"),
]


def _icon_for(title: str) -> Gtk.Image:
    if title == "GitHub":
        icon = Gio.FileIcon.new(Gio.File.new_for_path(str(ASSETS / "github.png")))
        return Gtk.Image.new_from_gicon(icon)
    return Gtk.Image.new_from_icon_name("web-browser-symbolic")


REDUX_TITLE = "What is Redux?"
REDUX_INTRO = (
    "<b>Need for Speed: Most Wanted Redux</b> is a massive, community-made overhaul mod "
    "for the classic 2005 PC version of the game."
)
REDUX_DETAIL = (
    "Instead of being a single modification, it is a pre-configured compilation pack that "
    "combines dozens of the best community mods, scripts and high-definition texture "
    "upgrades into one unified package."
)
REDUX_PURPOSE = "Its main purpose is to make the 2005 classic look and play like a modern video game remaster."


def _redux_card() -> Gtk.Box:
    card = Gtk.Box(
        orientation=Gtk.Orientation.VERTICAL,
        spacing=8,
        valign=Gtk.Align.FILL,
        width_request=400,
        css_classes=["card", "redux-card"],
    )
    card.append(Gtk.Label(label=REDUX_TITLE, xalign=0, css_classes=["redux-card-title"]))
    for text, css in ((REDUX_INTRO, "redux-card-text"), (REDUX_DETAIL, "redux-card-text"), (REDUX_PURPOSE, "redux-purpose")):
        card.append(Gtk.Label(label=text, use_markup=True, wrap=True, xalign=0, max_width_chars=52, css_classes=[css]))
    return card


class AboutWindow(Adw.Window):
    def __init__(self, parent: Gtk.Window | None, version: str):
        super().__init__(transient_for=parent, modal=True, title="About", resizable=False)

        logo = Gtk.Picture.new_for_filename(str(ASSETS / "darkxero.png"))
        logo.set_content_fit(Gtk.ContentFit.CONTAIN)
        logo.set_can_shrink(True)
        logo_frame = Adw.Clamp(maximum_size=104, tightening_threshold=104, child=logo)

        name = Gtk.Label(label="DarkXero", halign=Gtk.Align.CENTER, css_classes=["title-1"])
        build = "dev build" if version == "dev" else version
        caption = Gtk.Label(
            label=f"NFSMW Launcher {build}", halign=Gtk.Align.CENTER, css_classes=["dim-label"]
        )

        links = Gtk.Box(spacing=12, homogeneous=True, vexpand=True, valign=Gtk.Align.END)
        for title, uri in LINKS:
            icon = _icon_for(title)
            icon.set_pixel_size(20)
            content = Gtk.Box(spacing=8, halign=Gtk.Align.CENTER)
            content.append(icon)
            content.append(Gtk.Label(label=title))
            button = Gtk.Button(child=content, css_classes=["pill"])
            button.connect("clicked", lambda _b, target=uri: Gtk.UriLauncher.new(target).launch(self, None, None))
            links.append(button)

        identity = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=6,
            valign=Gtk.Align.FILL,
            width_request=280,
            css_classes=["about-identity"],
        )
        for widget in (logo_frame, name, caption):
            identity.append(widget)
        identity.append(links)

        body = Gtk.Box(spacing=28, margin_top=22, margin_bottom=28, margin_start=30, margin_end=30)
        body.append(identity)
        body.append(_redux_card())

        view = Adw.ToolbarView(content=body)
        view.add_top_bar(Adw.HeaderBar())
        self.set_content(view)
