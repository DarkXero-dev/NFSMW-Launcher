import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

work = Path(tempfile.mkdtemp())
game = work / "game"
(game / "scripts").mkdir(parents=True)
(game / "speed.exe").write_bytes(b"MZ")
for ini in (root / "tests" / "fixtures").glob("*.ini"):
    shutil.copy(ini, game / "scripts")
os.environ["XDG_CONFIG_HOME"] = str(work / "config")

from gi.repository import GLib

import main
from nfsmw_launcher.config import Config, save_config
from nfsmw_launcher.launcher_window import LauncherWindow
from nfsmw_launcher.prefs_window import PreferencesWindow
from nfsmw_launcher.settings_window import ReduxSettingsWindow

save_config(Config(game_dir=str(game), runner="custom", custom_command="true"))
out = Path(sys.argv[1])


class Probe(main.LauncherApp):
    def do_activate(self):
        window = LauncherWindow(self)
        window.present()
        PreferencesWindow(window, window._config).present()
        ReduxSettingsWindow(window, game / "scripts").present()
        GLib.timeout_add(3000, self.finish)

    def finish(self):
        libs = {
            m.group(1)
            for m in re.finditer(r"\s(/\S+\.so[\d.]*)\s*$", Path("/proc/self/maps").read_text(), re.M)
        }
        out.write_text("\n".join(sorted(libs)) + "\n")
        self.quit()


Probe().run([])
shutil.rmtree(work, ignore_errors=True)
