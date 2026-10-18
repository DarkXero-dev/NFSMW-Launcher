#!/usr/bin/env bash
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
target="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
mkdir -p "$target"

cat > "$target/nfsmw-redux-launcher.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Most Wanted Redux Launcher
Comment=Launch NFS Most Wanted Redux and edit its settings
Exec=python3 "$here/main.py"
Path=$here
Icon=$here/assets/launcher.jpg
Categories=Game;
Terminal=false
StartupWMClass=org.nfsmw.ReduxLauncher
EOF

echo "Installed $target/nfsmw-redux-launcher.desktop"
