"""Where Zotero keeps things on this machine, and the settings the scripts share.

Used by scan_and_identify.py and verify_and_move.py. Everything here only reads
the user's Zotero files; the one thing it deletes is a scratch copy of the database
that a script made itself (remove_db_copy).

Zotero's data directory is found, in order, from:
  1. the ZOTERO_DATA_DIR environment variable;
  2. Zotero's own setting (extensions.zotero.dataDir in the profile's prefs.js),
     when the profile says to use it;
  3. ~/Zotero, Zotero's default.

ZOTERO_IMPORT_CLEARED_ROOTS (folders separated by os.pathsep) names the folders
that verify_and_move.py may clear, and where a PDF held by Zotero does not count
as the user's own copy. The default is ~/Downloads and ~/Desktop.
"""
import os, re, subprocess, sys

HOME = os.path.expanduser("~")

# Zotero keeps one folder per profile under these, each holding a prefs.js.
# macOS is the system this was written and tested on; the Linux path is Zotero's
# documented location and is untested here.
PROFILE_ROOTS = (os.path.join(HOME, "Library/Application Support/Zotero/Profiles"),
                 os.path.join(HOME, ".zotero/zotero"))


def _prefs_files():
    for root in PROFILE_ROOTS:
        for prof in (sorted(os.listdir(root)) if os.path.isdir(root) else []):
            p = os.path.join(root, prof, "prefs.js")
            if os.path.isfile(p):
                yield p


def _pref(name):
    """The value of extensions.zotero.<name> in the first profile that sets it, as text."""
    pat = re.compile(r'user_pref\("extensions\.zotero\.' + re.escape(name)
                     + r'",\s*(?:"([^"]*)"|(true|false))\s*\)')
    for p in _prefs_files():
        try:
            with open(p, encoding="utf-8", errors="replace") as f:
                m = pat.search(f.read())
        except OSError:
            continue
        if m:
            return m.group(1) if m.group(1) is not None else m.group(2)
    return None


def data_dir():
    """Zotero's data directory, which holds zotero.sqlite and storage/."""
    d = os.environ.get("ZOTERO_DATA_DIR")
    if not d and _pref("useDataDir") == "true":
        d = _pref("dataDir")
    d = os.path.abspath(os.path.expanduser(d or os.path.join(HOME, "Zotero")))
    if not os.path.isfile(os.path.join(d, "zotero.sqlite")):
        sys.exit(f"No zotero.sqlite in {d}. Set ZOTERO_DATA_DIR to your Zotero data directory "
                 "(Zotero > Settings > Advanced > Files and Folders shows where it is).")
    return d


def base_attachment_path():
    """The base directory for linked attachments (Zotero's Linked Attachment Base Directory)."""
    return _pref("baseAttachmentPath") or ""


def cleared_roots():
    env = os.environ.get("ZOTERO_IMPORT_CLEARED_ROOTS")
    roots = env.split(os.pathsep) if env else [os.path.join(HOME, "Downloads"),
                                              os.path.join(HOME, "Desktop")]
    return tuple(os.path.abspath(os.path.expanduser(r)) for r in roots if r.strip())


def remove_db_copy(path):
    """Delete a scratch copy of the database made by snapshot_db, with its -wal, -shm
    and -journal files. The copy holds the whole library, so the scripts remove it
    when they finish, including when they stop on an error. Never call it on the
    live database: it is only given the path of a copy the caller created."""
    for sfx in ("", "-wal", "-shm", "-journal"):
        try:
            os.remove(path + sfx)
        except OSError:
            pass


def zotero_running():
    """Is the Zotero application open? A plain `ps | grep zotero` also matches folder names."""
    for args in (["pgrep", "-f", "Zotero.app/Contents/MacOS/zotero"],   # macOS
                 ["pgrep", "-x", "zotero-bin"]):                        # Linux, untested
        try:
            if subprocess.run(args, capture_output=True).returncode == 0:
                return True
        except OSError:
            pass
    return False


if __name__ == "__main__":
    # python3 zotero_env.py running   ->  says whether Zotero is open; exit code 0 if it is
    if sys.argv[1:] == ["running"]:
        up = zotero_running()
        print("Zotero is running" if up else "Zotero is not running")
        sys.exit(0 if up else 1)
    sys.exit("usage: zotero_env.py running")
