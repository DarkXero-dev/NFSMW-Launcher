#!/usr/bin/env bash
# Usage: build-appimage.sh [output-path]   (default: NFSMW-Launcher.AppImage in the project folder)
# Builds a single-file AppImage from the host's Python, GTK4 and libadwaita.
# The result only runs on distros whose glibc is at least as new as this machine's.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root="$(dirname "$here")"
build="$root/build"
appdir="$build/AppDir"
output="$(realpath -m "${1:-$root/NFSMW-Launcher.AppImage}")"
runtime_url="https://github.com/AppImage/type2-runtime/releases/download/20251108/runtime-x86_64"
runtime_sha256="2fca8b443c92510f1483a883f60061ad09b46b978b2631c807cd873a47ec260d"
app_share="$appdir/usr/share/nfsmw-redux-launcher"
trap 'rm -rf "$build"' EXIT

pyver="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
stdlib="$(python3 -c 'import sysconfig; print(sysconfig.get_paths()["stdlib"])')"
gi_dir="$(python3 -c 'import gi, os; print(os.path.dirname(gi.__file__))')"

host_lib='^(ld-linux.*|libc\.so.*|libm\.so.*|libdl\.so.*|libpthread\.so.*|librt\.so.*|libutil\.so.*|libresolv\.so.*|libnss_.*|libnsl.*|libanl.*|libGL.*|libEGL.*|libOpenGL.*|libGLES.*|libGLX.*|libGLdispatch.*|libvulkan.*|libdrm.*|libgbm.*|libnvidia.*|libcuda.*|libLLVM.*|libwayland-egl.*|libudev.*|libsystemd.*|libVkLayer.*|libxcb-dri.*|libgallium.*|libglapi.*)$'

bundle_lib() {
    local path="$1" soname name
    [[ -f "$path" ]] || return 0
    [[ "$path" == "$stdlib"/* || "$path" == "$gi_dir"/* || "$path" == /usr/lib/dri/* ]] && return 0
    soname="$(readelf -d "$path" 2>/dev/null | sed -n 's/.*(SONAME).*\[\(.*\)\]/\1/p')"
    name="${soname:-$(basename "$path")}"
    [[ "$name" =~ $host_lib ]] && return 0
    [[ -e "$appdir/usr/lib/$name" ]] || install -D -m 755 "$path" "$appdir/usr/lib/$name"
}

rm -rf "$build"
mkdir -p "$appdir/usr/bin" "$appdir/usr/lib/gio/modules" "$app_share"

echo "Python runtime"
install -m 755 "$(readlink -f "$(command -v python3)")" "$appdir/usr/bin/python3"
mkdir -p "$appdir/usr/lib/python$pyver"
tar -C "$stdlib" \
    --exclude=site-packages --exclude=test --exclude=tests --exclude=idlelib \
    --exclude=tkinter --exclude=turtledemo --exclude=ensurepip --exclude=__pycache__ \
    -cf - . | tar -C "$appdir/usr/lib/python$pyver" -xf -
mkdir -p "$appdir/usr/lib/python$pyver/site-packages"
cp -a "$gi_dir" "$appdir/usr/lib/python$pyver/site-packages/gi"
find "$appdir/usr/lib/python$pyver" -name __pycache__ -type d -prune -exec rm -rf {} +
rm -f "$appdir"/usr/lib/python"$pyver"/lib-dynload/{_tkinter,_curses,_curses_panel,readline,_gdbm,_dbm,_sqlite3}.*

echo "Application files"
cp -a "$root/main.py" "$root/nfsmw_launcher" "$app_share/"
[[ -f "$root/VERSION" ]] && cp "$root/VERSION" "$app_share/"
repo="${GITHUB_REPOSITORY:-DarkXero-dev/NFSMW-Launcher}"
echo "$repo" > "$app_share/REPO"
mkdir -p "$app_share/assets"
cp -a "$root/assets/launcher.jpg" "$root/assets/darkxero.png" "$root/assets/github.png" "$root/assets/settings-banner.png" "$root/assets/style.css" "$root/assets/logos" "$app_share/assets/"
find "$app_share" -name __pycache__ -type d -prune -exec rm -rf {} +

echo "Shared libraries (probing a live run for dlopen'd ones)"
python3 "$here/probe_libs.py" "$build/loaded-libs.txt"
{
    cat "$build/loaded-libs.txt"
    for module in "$appdir"/usr/lib/python"$pyver"/lib-dynload/*.so "$appdir"/usr/lib/python"$pyver"/site-packages/gi/_gi*.so "$appdir/usr/bin/python3"; do
        ldd "$module" | awk '/=> \//{print $3}'
    done
} | sort -u | while read -r lib; do bundle_lib "$lib"; done

echo "GObject typelibs, schemas, icons"
mkdir -p "$appdir/usr/lib/girepository-1.0" "$appdir/usr/share/glib-2.0/schemas" "$appdir/usr/share/icons"
cp -a /usr/lib/girepository-1.0/*.typelib "$appdir/usr/lib/girepository-1.0/"
cp -a /usr/share/glib-2.0/schemas/org.gtk.* /usr/share/glib-2.0/schemas/org.gnome.desktop.* \
    "$appdir/usr/share/glib-2.0/schemas/" 2>/dev/null || true
glib-compile-schemas "$appdir/usr/share/glib-2.0/schemas"
cp -a /usr/share/icons/Adwaita "$appdir/usr/share/icons/"

echo "Launcher entry points"
cat > "$appdir/AppRun" <<'APPRUN'
#!/bin/sh
APPDIR="$(dirname "$(readlink -f "$0")")"
for var in LD_LIBRARY_PATH PATH XDG_DATA_DIRS GI_TYPELIB_PATH GSETTINGS_SCHEMA_DIR GIO_MODULE_DIR; do
    eval "export NFSMW_ORIG_$var=\"\${$var-}\""
done
export LD_LIBRARY_PATH="$APPDIR/usr/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export PATH="$APPDIR/usr/bin:$PATH"
export XDG_DATA_DIRS="$APPDIR/usr/share:${XDG_DATA_DIRS:-/usr/local/share:/usr/share}"
export GI_TYPELIB_PATH="$APPDIR/usr/lib/girepository-1.0"
export GSETTINGS_SCHEMA_DIR="$APPDIR/usr/share/glib-2.0/schemas"
export GIO_MODULE_DIR="$APPDIR/usr/lib/gio/modules"
exec "$APPDIR/usr/bin/python3" -sEB "$APPDIR/usr/share/nfsmw-redux-launcher/main.py" "$@"
APPRUN
chmod +x "$appdir/AppRun"

cat > "$appdir/nfsmw-redux-launcher.desktop" <<'DESKTOP'
[Desktop Entry]
Type=Application
Name=Most Wanted Redux Launcher
Comment=Launch NFS Most Wanted Redux and edit its settings
Exec=AppRun
Icon=nfsmw-redux-launcher
Categories=Game;
Terminal=false
StartupWMClass=org.nfsmw.ReduxLauncher
DESKTOP

python3 - "$root/assets/launcher.jpg" "$appdir/nfsmw-redux-launcher.png" <<'PY'
import sys
import gi

gi.require_version("GdkPixbuf", "2.0")
from gi.repository import GdkPixbuf

source = GdkPixbuf.Pixbuf.new_from_file(sys.argv[1])
side = source.get_height()
source.new_subpixbuf(0, 0, side, side).scale_simple(256, 256, GdkPixbuf.InterpType.BILINEAR).savev(
    sys.argv[2], "png", [], []
)
PY
ln -s nfsmw-redux-launcher.png "$appdir/.DirIcon"

echo "Bytecode"
LD_LIBRARY_PATH="$appdir/usr/lib" "$appdir/usr/bin/python3" -sE -m compileall -q "$appdir/usr/lib/python$pyver" "$app_share"

echo "Bundle self-check"
LD_LIBRARY_PATH="$appdir/usr/lib" "$appdir/usr/bin/python3" -sE -c 'import ssl, hashlib, urllib.request; ssl.create_default_context()'

echo "Packaging"
runtime="$build/runtime-x86_64"
[[ -f "$runtime" ]] || curl -sSL -o "$runtime" "$runtime_url"
echo "$runtime_sha256  $runtime" | sha256sum -c --quiet
update_info="gh-releases-zsync|${repo%/*}|${repo#*/}|latest|$(basename "$output").zsync"
cp "$runtime" "$build/runtime-with-update-info"
python3 "$here/embed_update_info.py" "$build/runtime-with-update-info" "$update_info"
mksquashfs "$appdir" "$build/app.squashfs" -root-owned -noappend -comp zstd -Xcompression-level 19 \
    -all-time 0 -mkfs-time 0 -quiet
cat "$build/runtime-with-update-info" "$build/app.squashfs" > "$output.tmp"
chmod +x "$output.tmp"
mv -f "$output.tmp" "$output"
echo "Built $output ($(du -h "$output" | cut -f1))"
