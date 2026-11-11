#!/bin/sh
PREFIX="${PREFIX:-$HOME/.local}"
rm -rf "$PREFIX/lib/wt-planner" "$PREFIX/bin/wt-planner" "$PREFIX/share/applications/wt-planner.desktop" \
       "$PREFIX/share/mime/packages/wt-planner.xml" "$PREFIX/share/icons/hicolor/scalable/apps/wt-planner.svg"
command -v update-mime-database >/dev/null && update-mime-database "$PREFIX/share/mime" || true
command -v update-desktop-database >/dev/null && update-desktop-database "$PREFIX/share/applications" || true
echo "Removed. Your saved events stay in ~/.local/share/wt-planner/events"
