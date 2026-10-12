#!/bin/sh
# Builds NextUp.app into ~/Applications and (re)starts it.
set -e
HERE="$(dirname "$0")"
APP="$HOME/Applications/NextUp.app"
mkdir -p "$APP/Contents/MacOS"
swiftc -O -o "$APP/Contents/MacOS/NextUp" "$HERE/NextUp.swift"
cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleIdentifier</key><string>local.nextup</string>
<key>CFBundleName</key><string>NextUp</string>
<key>CFBundleExecutable</key><string>NextUp</string>
<key>CFBundlePackageType</key><string>APPL</string>
<key>LSUIElement</key><true/>
<key>NSCalendarsFullAccessUsageDescription</key><string>NextUp shows your next meeting in the menu bar.</string>
</dict></plist>
PLIST
codesign -s - -f "$APP" >/dev/null 2>&1 || true
pkill -x NextUp || true
open "$APP"
