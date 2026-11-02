#!/bin/sh
# remove only the test run's own entries from the host trash (Wine's Recycle Bin), identified by their original path
T=$HOME/.local/share/Trash
for i in "$T"/info/*.trashinfo; do
  [ -f "$i" ] || continue
  if grep -q "^Path=.*exsl_" "$i"; then n=$(basename "$i" .trashinfo); rm -rf "$T/files/$n" "$i"; fi
done
