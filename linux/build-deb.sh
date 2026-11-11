#!/bin/sh
# Builds dist/wt-planner_<version>_all.deb  (install: sudo apt install ./dist/wt-planner_*.deb)
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
VER="$(/usr/bin/env python3 -c "import sys; sys.path.insert(0, '$HERE'); from wt_planner.reference import APP_VERSION; print(APP_VERSION)")"
ROOT="$HERE/build/deb"
rm -rf "$ROOT"
mkdir -p "$ROOT/DEBIAN" "$ROOT/usr/lib/wt-planner" "$ROOT/usr/bin" "$ROOT/usr/share/applications" \
         "$ROOT/usr/share/mime/packages" "$ROOT/usr/share/icons/hicolor/scalable/apps" "$ROOT/usr/share/doc/wt-planner"
cp -r "$HERE/wt_planner" "$ROOT/usr/lib/wt-planner/"
find "$ROOT" -name __pycache__ -prune -exec rm -rf {} +
install -m 755 "$HERE/packaging/wt-planner" "$ROOT/usr/bin/wt-planner"
install -m 644 "$HERE/packaging/wt-planner.desktop" "$ROOT/usr/share/applications/"
install -m 644 "$HERE/packaging/wt-planner-mime.xml" "$ROOT/usr/share/mime/packages/wt-planner.xml"
install -m 644 "$HERE/packaging/wt-planner.svg" "$ROOT/usr/share/icons/hicolor/scalable/apps/"
install -m 644 "$HERE/README.md" "$ROOT/usr/share/doc/wt-planner/README.md"
printf 'Technical Officials Scheduler\nLicense: MIT\n' > "$ROOT/usr/share/doc/wt-planner/copyright"
SIZE="$(du -sk "$ROOT/usr" | cut -f1)"
cat > "$ROOT/DEBIAN/control" <<CTRL
Package: wt-planner
Version: $VER
Section: misc
Priority: optional
Architecture: all
Installed-Size: $SIZE
Depends: python3 (>= 3.8), python3-gi, gir1.2-gtk-3.0, librsvg2-common
Recommends: libreoffice-calc
Maintainer: Technical Officials Scheduler <maintainer@localhost>
Description: Technical Officials planner for World Triathlon races
 Plans primary and secondary Technical Official positions for one or more
 races (formats from the World Triathlon Competition Rules), checks time
 clashes using the duties in the TO Checklist, and shows a Gantt chart,
 race timeline and radio count. Exports Excel, ODS, JSON, iCalendar and SVG.
CTRL
find "$ROOT" -type d -exec chmod 755 {} +
find "$ROOT/usr/lib" -type f -exec chmod 644 {} +
mkdir -p "$HERE/dist"
dpkg-deb --root-owner-group --build "$ROOT" "$HERE/dist/wt-planner_${VER}_all.deb"
echo "Built dist/wt-planner_${VER}_all.deb"
