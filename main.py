#!/usr/bin/env python3
import sys
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gtk

from nfsmw_launcher.launcher_window import LauncherWindow

STYLE = Path(__file__).resolve().parent / "assets" / "style.css"


class LauncherApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="org.nfsmw.ReduxLauncher")

    def do_startup(self):
        Adw.Application.do_startup(self)
        Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        provider = Gtk.CssProvider()
        provider.load_from_path(str(STYLE))
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def do_activate(self):
        window = self.props.active_window or LauncherWindow(self)
        window.present()


if __name__ == "__main__":
    sys.exit(LauncherApp().run(sys.argv))
