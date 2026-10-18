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


class AboutWindow(Adw.Window):
    def __init__(self, parent: Gtk.Window | None, version: str):
        super().__init__(transient_for=parent, modal=True, title="About", resizable=False)

        logo = Gtk.Picture.new_for_filename(str(ASSETS / "darkxero.png"))
        logo.set_content_fit(Gtk.ContentFit.CONTAIN)
        logo.set_can_shrink(True)
        logo_frame = Adw.Clamp(maximum_size=160, tightening_threshold=160, child=logo)

        name = Gtk.Label(label="DarkXero", halign=Gtk.Align.CENTER, css_classes=["title-1"])
        build = "dev build" if version == "dev" else version
        caption = Gtk.Label(
            label=f"NFSMW Launcher {build}", halign=Gtk.Align.CENTER, css_classes=["dim-label"]
        )

        links = Gtk.Box(spacing=12, homogeneous=True, margin_top=14)
        for title, uri in LINKS:
            icon = _icon_for(title)
            icon.set_pixel_size(20)
            content = Gtk.Box(spacing=8, halign=Gtk.Align.CENTER)
            content.append(icon)
            content.append(Gtk.Label(label=title))
            button = Gtk.Button(child=content, css_classes=["pill"])
            button.connect("clicked", lambda _b, target=uri: Gtk.UriLauncher.new(target).launch(self, None, None))
            links.append(button)

        body = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=10,
            margin_top=24,
            margin_bottom=28,
            margin_start=32,
            margin_end=32,
            width_request=380,
        )
        for widget in (logo_frame, name, caption):
            body.append(widget)
        body.append(links)

        view = Adw.ToolbarView(content=body)
        view.add_top_bar(Adw.HeaderBar())
        self.set_content(view)
