"""Connect to OBS over WebSocket and report what the meeting setup needs.

Reads the password from OBS's own WebSocket settings and never prints it.
"""
import json
import os
import sys

import obsws_python as obs

PW_FILE = os.path.expanduser("~/.config/obs-websocket/password")
OBS_WS_CONFIG = os.path.expanduser(
    "~/Library/Application Support/obs-studio/plugin_config/obs-websocket/config.json")


def load_password():
    """OBS's own settings first, since that is what OBS actually uses, then the optional
    copy in ~/.config. The password is never printed."""
    try:
        cfg = json.load(open(OBS_WS_CONFIG))
        if not cfg.get("server_enabled"):
            sys.exit("OBS WebSocket server is not enabled (Tools > WebSocket Server Settings)")
        if not cfg.get("auth_required"):
            return ""
        if cfg.get("server_password"):
            return cfg["server_password"]
    except FileNotFoundError:
        pass
    try:
        return open(PW_FILE).read().strip()
    except FileNotFoundError:
        sys.exit("no OBS WebSocket settings yet: open OBS and enable the server first")


def step(label, fn):
    try:
        print(f"{label}: {fn()}")
    except Exception as e:  # report and keep going, so one failure doesn't hide the rest
        print(f"{label}: FAILED ({type(e).__name__}: {e})")


def main():
    pw = load_password()
    cl = obs.ReqClient(host="localhost", port=4455, password=pw, timeout=5)
    step("version", lambda: (lambda v: f"OBS {v.obs_version}, websocket {v.obs_web_socket_version}")(cl.get_version()))
    kinds = cl.get_input_kind_list(False).input_kinds
    for k in ("sck_audio_capture", "coreaudio_input_capture"):
        print(f"input kind {k}: {'present' if k in kinds else 'MISSING'}")
    step("sck_audio_capture defaults", lambda: json.dumps(cl.get_input_default_settings("sck_audio_capture").default_input_settings))
    step("coreaudio_input_capture defaults", lambda: json.dumps(cl.get_input_default_settings("coreaudio_input_capture").default_input_settings))
    step("profiles", lambda: cl.get_profile_list().profiles)
    step("scenes", lambda: [s["sceneName"] for s in cl.get_scene_list().scenes])
    step("inputs", lambda: [(i["inputName"], i["inputKind"]) for i in cl.get_input_list().inputs])


if __name__ == "__main__":
    main()
