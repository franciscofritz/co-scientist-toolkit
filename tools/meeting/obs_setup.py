"""Configure OBS for two-track meeting recording. Safe to re-run.

Track 1: microphone, following the system default input.
Track 2: the remote side. By default this is all system audio (Desktop Audio through
ScreenCaptureKit), so the call is captured whatever app or browser it runs in. Set
"remote_app" in the config file to a bundle identifier (for example "com.apple.Safari")
to capture that application's audio only; a call held in any other application then
records as silence.
Track 3: both, as a listening mix.

Settings come from ~/.config/meeting/config.json (see meeting_config.py).
"""
import json
import os
import time

import obsws_python as obs

import meeting_config
from obs_probe import load_password

CFG = meeting_config.load()
PROFILE, SCENE = "Meetings", "Meeting"
MIC, REMOTE = "Mic/Aux", "Remote audio"
OLD_REMOTE = ("Remote (desktop)", "Remote (Safari)")  # names from earlier versions of this script
DESKTOP_AUDIO, APPLICATION_AUDIO = 0, 1  # the capture types of an sck_audio_capture source
REMOTE_APP = CFG["remote_app"]
REC_DIR = CFG["recordings_dir"]


def wait_for(check, timeout=8.0):
    """OBS applies profile and scene changes asynchronously, so confirm each one landed."""
    end = time.time() + timeout
    while time.time() < end:
        if check():
            return True
        time.sleep(0.25)
    return False


def main():
    cl = obs.ReqClient(host="localhost", port=4455, password=load_password(), timeout=10)

    def r(req, data=None):
        return cl.send(req, data or {}, raw=True)

    # profile
    def current_profile():
        return r("GetProfileList")["currentProfileName"]

    def switch_profile(name):
        if current_profile() != name:
            r("SetCurrentProfile", {"profileName": name})
            if not wait_for(lambda: current_profile() == name):
                raise SystemExit(f"OBS did not switch to profile {name!r}")

    if PROFILE not in r("GetProfileList")["profiles"]:
        r("CreateProfile", {"profileName": PROFILE})
        if not wait_for(lambda: PROFILE in r("GetProfileList")["profiles"]):
            raise SystemExit("OBS did not create the Meetings profile")
    switch_profile(PROFILE)

    # scene
    scenes = [s["sceneName"] for s in r("GetSceneList")["scenes"]]
    if SCENE not in scenes:
        if "Scene" in scenes:
            r("SetSceneName", {"sceneName": "Scene", "newSceneName": SCENE})
        else:
            r("CreateScene", {"sceneName": SCENE})
        if not wait_for(lambda: SCENE in [x["sceneName"] for x in r("GetSceneList")["scenes"]]):
            raise SystemExit("OBS did not create the Meeting scene")
    r("SetCurrentProgramScene", {"sceneName": SCENE})

    inputs = {i["inputName"]: i["inputKind"] for i in r("GetInputList")["inputs"]}

    # microphone: OBS's global Mic/Aux source, pinned to the default input
    if MIC not in inputs:
        r("CreateInput", {"sceneName": SCENE, "inputName": MIC, "inputKind": "coreaudio_input_capture",
                          "inputSettings": {"device_id": "default"}, "sceneItemEnabled": True})
    r("SetInputSettings", {"inputName": MIC, "inputSettings": {"device_id": "default"}, "overlay": True})

    # remote: ScreenCaptureKit audio, all of it or one application's (renames a source made
    # by an earlier version of this script)
    for old in OLD_REMOTE:
        if old in inputs and REMOTE not in inputs:
            r("SetInputName", {"inputName": old, "newInputName": REMOTE})
            inputs[REMOTE] = inputs.pop(old)
    if REMOTE not in inputs:
        r("CreateInput", {"sceneName": SCENE, "inputName": REMOTE, "inputKind": "sck_audio_capture",
                          "inputSettings": {}, "sceneItemEnabled": True})
    # Never ask OBS for the "application" list over the WebSocket: in OBS 32.2.2 (obs-websocket
    # 5.7.4) that request segfaults OBS. The capture types were read safely once:
    # 0 = Desktop Audio Capture, 1 = Application Audio Capture. So the application is set
    # by bundle identifier, never chosen from the list.
    if REMOTE_APP:
        remote = {"type": APPLICATION_AUDIO, "application": REMOTE_APP}
    else:
        remote = {"type": DESKTOP_AUDIO}
    r("SetInputSettings", {"inputName": REMOTE, "inputSettings": remote, "overlay": True})
    print("remote settings:", r("GetInputSettings", {"inputName": REMOTE})["inputSettings"])

    # tracks
    def tracks(on):
        return {str(i): i in on for i in range(1, 7)}
    r("SetInputAudioTracks", {"inputName": MIC, "inputAudioTracks": tracks({1, 3})})
    r("SetInputAudioTracks", {"inputName": REMOTE, "inputAudioTracks": tracks({2, 3})})
    for name, kind in [(i["inputName"], i["inputKind"]) for i in r("GetInputList")["inputs"]]:
        t = r("GetInputAudioTracks", {"inputName": name})["inputAudioTracks"]
        flag = "" if name in (MIC, REMOTE) else "   <- unexpected source, check it"
        print(f"tracks {name!r} ({kind}): {[k for k, v in t.items() if v]}{flag}")

    # output: advanced mode, mkv, tracks 1-3, dated filenames
    params = [("Output", "Mode", "Advanced"), ("AdvOut", "RecType", "Standard"),
              ("AdvOut", "RecFormat2", "mkv"), ("AdvOut", "RecFormat", "mkv"), ("AdvOut", "RecTracks", "7"),
              ("AdvOut", "Track1Bitrate", "160"), ("AdvOut", "Track2Bitrate", "160"), ("AdvOut", "Track3Bitrate", "160"),
              ("Output", "FilenameFormatting", "%CCYY-%MM-%DD %hh-%mm-%ss")]
    for cat, name, val in params:
        r("SetProfileParameter", {"parameterCategory": cat, "parameterName": name, "parameterValue": val})
    others = [p for p in r("GetProfileList")["profiles"] if p != PROFILE]
    if others:  # a profile's output settings are re-read when it is switched to
        switch_profile(others[0])
        switch_profile(PROFILE)
    os.makedirs(REC_DIR, exist_ok=True)
    r("SetRecordDirectory", {"recordDirectory": REC_DIR})
    for cat, name, _ in params:
        print(f"    {cat}/{name} = {r('GetProfileParameter', {'parameterCategory': cat, 'parameterName': name})['parameterValue']}")
    print("record directory:", r("GetRecordDirectory")["recordDirectory"])

    # no video sources, so keep the video track as small as possible
    try:
        r("SetVideoSettings", {"fpsNumerator": 10, "fpsDenominator": 1, "baseWidth": 320, "baseHeight": 180,
                               "outputWidth": 320, "outputHeight": 180})
    except Exception as e:
        print("video settings unchanged:", e)
    v = r("GetVideoSettings")
    print(f"video: {v['baseWidth']}x{v['baseHeight']} at {v['fpsNumerator']}/{v['fpsDenominator']} fps")
    # Recording uses the stream encoder (AdvOut RecEncoder=none, Encoder=obs_x264). With no
    # settings file x264 ran at about 6 Mbit/s even on this black frame, so the empty video
    # was 92 % of every file, nearly 3 GB an hour (measured on a test recording). Quality-based
    # encoding of a frame that never changes costs almost nothing. OBS can rewrite a loaded
    # profile's files, so write this one while another profile is active.
    enc_file = os.path.join(os.path.expanduser("~/Library/Application Support/obs-studio/basic/profiles"),
                            PROFILE, "streamEncoder.json")
    wanted = {"rate_control": "CRF", "crf": 30, "preset": "veryfast", "keyint_sec": 10}
    current = json.load(open(enc_file)) if os.path.exists(enc_file) else {}
    if any(current.get(k) != v for k, v in wanted.items()):
        others = [p for p in r("GetProfileList")["profiles"] if p != PROFILE]
        if others:
            switch_profile(others[0])
            current.update(wanted)
            json.dump(current, open(enc_file, "w"), indent=2)
            switch_profile(PROFILE)
        else:
            print("no second profile to switch through; video encoder left at its default")
    print("video encoder:", json.load(open(enc_file)) if os.path.exists(enc_file) else "default")
    print("profile:", r("GetProfileList")["currentProfileName"], "| scene:", r("GetSceneList")["currentProgramSceneName"])


if __name__ == "__main__":
    main()
