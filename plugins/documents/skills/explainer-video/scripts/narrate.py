#!/usr/bin/env python3
"""Make the narration audio for an explainer and record each line's length.

    narrate.py <project folder> [--voice VOICE]

Reads <folder>/narration.json, a list of {"id", "text"} lines in playing order, writes one
WAV per line to <folder>/audio/ with the tts command (Kokoro, local), and writes
<folder>/audio/durations.json, which NarratedScene reads. Rerun it after any change to the text.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

ap = argparse.ArgumentParser()
ap.add_argument("folder")
ap.add_argument("--voice")
args = ap.parse_args()

folder = os.path.abspath(args.folder)
lines = json.load(open(os.path.join(folder, "narration.json")))
ids = [ln["id"] for ln in lines]
if len(set(ids)) != len(ids):
    sys.exit("narration.json: line ids must be unique")
audio = os.path.join(folder, "audio")
os.makedirs(audio, exist_ok=True)

tts = shutil.which("tts")
if not tts:
    sys.exit("the tts command is not on PATH: install pdf2audio (see the skill's Setup)")
if not shutil.which("ffprobe"):
    sys.exit("ffprobe is not on PATH: brew install ffmpeg")
cmd = [tts, "--batch", os.path.join(folder, "narration.json"),
       "--out-dir", audio, "--format", "wav"]
if args.voice:
    cmd += ["--voice", args.voice]
subprocess.run(cmd, check=True, capture_output=True)

durations = {}
for i in ids:
    wav = os.path.join(audio, i + ".wav")
    if not os.path.exists(wav):
        sys.exit(f"tts wrote no audio for line '{i}'")
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", wav], capture_output=True, text=True, check=True)
    durations[i] = float(out.stdout)
json.dump(durations, open(os.path.join(audio, "durations.json"), "w"), indent=1)
for i in ids:
    print(f"{i}\t{durations[i]:.2f} s")
print(f"total\t{sum(durations.values()):.2f} s")
