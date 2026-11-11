#!/bin/sh
# Per-user install (no sudo): ~/.local
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
PREFIX="${PREFIX:-$HOME/.local}"
if ! /usr/bin/python3 -c "import gi; gi.require_version('Gtk', '3.0'); from gi.repository import Gtk" 2>/dev/null; then
  echo "GTK 3 for Python is missing. Install it with:"
  echo "  sudo apt install python3-gi gir1.2-gtk-3.0 librsvg2-common"
  exit 1
fi
mkdir -p "$PREFIX/lib/wt-planner" "$PREFIX/bin" "$PREFIX/share/applications" \
         "$PREFIX/share/mime/packages" "$PREFIX/share/icons/hicolor/scalable/apps"
rm -rf "$PREFIX/lib/wt-planner/wt_planner"
cp -r "$HERE/wt_planner" "$PREFIX/lib/wt-planner/"
find "$PREFIX/lib/wt-planner" -name __pycache__ -prune -exec rm -rf {} +
install -m 755 "$HERE/packaging/wt-planner" "$PREFIX/bin/wt-planner"
install -m 644 "$HERE/packaging/wt-planner.desktop" "$PREFIX/share/applications/wt-planner.desktop"
install -m 644 "$HERE/packaging/wt-planner-mime.xml" "$PREFIX/share/mime/packages/wt-planner.xml"
install -m 644 "$HERE/packaging/wt-planner.svg" "$PREFIX/share/icons/hicolor/scalable/apps/wt-planner.svg"
command -v update-mime-database >/dev/null && update-mime-database "$PREFIX/share/mime" || true
command -v update-desktop-database >/dev/null && update-desktop-database "$PREFIX/share/applications" || true
command -v gtk-update-icon-cache >/dev/null && gtk-update-icon-cache -q -t "$PREFIX/share/icons/hicolor" || true
echo "Installed. Start 'Technical Officials Scheduler' from the app grid, or run: wt-planner"
case ":$PATH:" in *":$PREFIX/bin:"*) ;; *) echo "(Add $PREFIX/bin to PATH to use the terminal command.)";; esac
