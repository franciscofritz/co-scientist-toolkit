"""Settings for the meeting tools, read from a small JSON file.

The file is ~/.config/meeting/config.json, or the file named by the MEETING_CONFIG
environment variable. Every key is optional; a missing key keeps the default below.
Paths may start with ~.
"""
import json
import os
import sys

CONFIG_PATH = os.path.expanduser(os.environ.get("MEETING_CONFIG", "~/.config/meeting/config.json"))

DEFAULTS = {
    # label for your own voice on the microphone track; empty means "Me"
    "your_name": "",
    # where recordings, sidecars, transcripts and logs go
    "recordings_dir": "~/Recordings/Meetings",
    # whisper.cpp models
    "whisper_model": "~/models/whisper/ggml-large-v3.bin",
    "vad_model": "~/models/whisper/ggml-silero-v6.2.0.bin",
    # what OBS records as the remote side: null means all system audio (Desktop Audio);
    # a bundle identifier such as "com.apple.Safari" means that application's audio only
    "remote_app": None,
    # the application brought to the front after `meeting start` has to open OBS, so
    # the call window gets focus back; an empty string skips this
    "focus_app": "",
    # days after a transcript passes its checks before its audio goes to the Bin;
    # 0 keeps audio for ever (`meeting prune` can still be run by hand)
    "retain_days": 30,
}


def load():
    cfg = dict(DEFAULTS)
    try:
        with open(CONFIG_PATH) as f:
            user = json.load(f)
    except FileNotFoundError:
        user = {}
    except ValueError as e:
        sys.exit(f"{CONFIG_PATH} is not valid JSON: {e}")
    unknown = sorted(set(user) - set(DEFAULTS))
    if unknown:
        print(f"warning: unknown key(s) in {CONFIG_PATH}: {', '.join(unknown)}", file=sys.stderr)
    cfg.update({k: v for k, v in user.items() if k in DEFAULTS})
    for k in ("recordings_dir", "whisper_model", "vad_model"):
        cfg[k] = os.path.expanduser(cfg[k])
    return cfg
