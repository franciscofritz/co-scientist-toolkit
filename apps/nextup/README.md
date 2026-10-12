# NextUp

A Mac menu bar app that shows your next meeting: its start time and a short title, switching to
a countdown in the last 15 minutes. The menu lists the day's meetings, steps through other days,
and gives each meeting Join, Record and Join-and-record buttons. Record runs the `meeting`
command from `tools/meeting` in this repository.

It reads your calendars through macOS Calendar (EventKit), on the Mac itself. Add your Google,
Microsoft or other accounts to the Calendar app, and NextUp sees them without being given access
to any online account. It makes no network requests; Join opens the meeting link in your browser.

## Build

Needs macOS 14 or later and the Xcode command line tools (`xcode-select --install`). Recording
also needs the `meeting` command, which needs macOS 15.

    ./build.sh

This compiles `NextUp.swift` into `~/Applications/NextUp.app`, signs it locally and starts it.
macOS asks once for access to your calendars.

## Settings

Settings are in `~/.config/nextup/config.json`. Every key is optional. Invalid settings use the defaults.

| Key | Default | Meaning |
|---|---|---|
| `excludeCalendars` | `[]` | Calendar titles to ignore |
| `excludeTitles` | `[]` | Event titles to ignore (exact match) |
| `browserPath` | `null` | App that opens join links; `null` is your default browser |
| `maxTitleLength` | `20` | Characters of title in the menu bar |
| `countdownMinutes` | `15` | Minutes before the start at which the countdown begins |
| `meetingPath` | `null` | Path to the `meeting` command. With `null`, NextUp looks in `~/.local/bin`, `/opt/homebrew/bin` and `/usr/local/bin` |

Recording other people needs their agreement; see `tools/meeting/README.md`.
