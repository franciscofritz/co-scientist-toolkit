#!/bin/bash
# Licence-check hooks. A cheap pre-filter so Python starts only when the call could matter.
# Usage (from settings.json): hook.sh <event>   events: see license_check.py
event="$1"
input=$(cat)
here="$(dirname "$0")"
# true when the file being read sits within three levels of a license.json
near_license_json() {
  local f d
  command -v jq >/dev/null 2>&1 || return 0  # without jq, let the Python check decide
  f=$(printf '%s' "$input" | jq -r '.tool_input.file_path // empty' 2>/dev/null)
  [ -n "$f" ] || return 1
  d=$(dirname "$f")
  [ -f "$d/license.json" ] || [ -f "$(dirname "$d")/license.json" ] \
    || [ -f "$(dirname "$(dirname "$d")")/license.json" ]
}
# true when a Grep could touch a PDF or material covered by a license.json: the path (or the
# working directory when the call has none) is a PDF, a file or folder within three levels of a
# license.json, or a folder with a license.json in a subfolder
grep_could_matter() {
  local p cwd d g
  command -v jq >/dev/null 2>&1 || return 0  # without jq, let the Python check decide
  p=$(printf '%s' "$input" | jq -r '.tool_input.path // empty' 2>/dev/null)
  cwd=$(printf '%s' "$input" | jq -r '.cwd // empty' 2>/dev/null)
  [ -n "$cwd" ] || cwd=$(pwd)
  [ -n "$p" ] || p="$cwd"
  case "$p" in /*) ;; *) p="$cwd/$p" ;; esac
  case "$p" in *.[pP][dD][fF]) return 0 ;; esac
  if [ -d "$p" ]; then
    d=$(cd "$p" 2>/dev/null && pwd -P) || return 0
    for g in "$d" "$(dirname "$d")" "$(dirname "$(dirname "$d")")"; do
      [ -f "$g/license.json" ] && return 0
    done
    for g in "$d"/*/license.json; do
      [ -f "$g" ] && return 0
    done
    return 1
  fi
  [ -e "$p" ] || return 1
  d=$(cd "$(dirname "$p")" 2>/dev/null && pwd -P) || return 0
  for g in "$d" "$(dirname "$d")" "$(dirname "$(dirname "$d")")"; do
    [ -f "$g/license.json" ] && return 0
  done
  return 1
}
case "$event" in
  pre-read|post-read)
    case "$input" in *.[pP][dD][fF]\"*) ;; *) near_license_json || exit 0 ;; esac ;;
  pre-grep)
    grep_could_matter || exit 0 ;;
  pre-bash)
    # PDFs, and the Markdown, figures and tables extracted from them
    case "$input" in *.[pP][dD][fF]*|*.md*|*fulltext*|*figures*|*tables*) ;; *) exit 0 ;; esac ;;
  post-bash)
    case "$input" in *.[pP][dD][fF]*) ;; *) exit 0 ;; esac ;;
esac
printf '%s' "$input" | python3 "$here/license_check.py" hook "$event"
exit 0
