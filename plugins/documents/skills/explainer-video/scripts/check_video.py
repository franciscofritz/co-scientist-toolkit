#!/usr/bin/env python3
"""Check a rendered explainer before anyone sees it.

    check_video.py <project folder> <video.mp4> [--out sheet.png]

Prints the video and audio stream lengths against the narration, fails if the audio track is
shorter than the narration (a cached Manim re-render can drop sound), and writes a contact
sheet with two frames per narration line (middle and just before the end) for the overlap check.
"""
import argparse
import json
import math
import os
import subprocess
import sys

GAP = 0.4

ap = argparse.ArgumentParser()
ap.add_argument("folder")
ap.add_argument("video")
ap.add_argument("--out")
args = ap.parse_args()

folder = os.path.abspath(args.folder)
lines = json.load(open(os.path.join(folder, "narration.json")))
dur = json.load(open(os.path.join(folder, "audio", "durations.json")))

probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,duration",
                        "-of", "json", args.video], capture_output=True, text=True, check=True)
streams = {s["codec_type"]: float(s.get("duration", 0)) for s in json.loads(probe.stdout)["streams"]}
narr = sum(dur[ln["id"]] for ln in lines)
print(f"video {streams.get('video', 0):.2f} s, audio {streams.get('audio', 0):.2f} s, "
      f"narration {narr:.2f} s")
ok = True
if "audio" not in streams:
    print("FAIL: no audio track"); ok = False
elif streams["audio"] < narr - 0.5:
    print("FAIL: audio track shorter than the narration; re-render with --disable_caching"); ok = False

# Segment start times follow NarratedScene: each line plays for its length plus GAP. Any
# animation outside segments (an intro before the first line) shifts these; pass the sheet
# through a look rather than trusting the times exactly.
times, t = [], 0.0
for ln in lines:
    d = dur[ln["id"]] + GAP
    times += [t + d * 0.5, t + d - 0.15]
    t += d
cols = 2
rows = math.ceil(len(times) / cols)
out = args.out or os.path.join(folder, "contact-sheet.png")
sel = "+".join(f"lt(prev_pts*TB\\,{x:.3f})*gte(pts*TB\\,{x:.3f})" for x in times)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", args.video, "-vf",
                f"select='{sel}',scale=640:-1,tile={cols}x{rows}", "-frames:v", "1", out], check=True)
print(f"contact sheet: {out} ({len(times)} frames, middle and end of each line)")
sys.exit(0 if ok else 1)
