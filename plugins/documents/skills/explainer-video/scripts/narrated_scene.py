"""Base class for narrated Manim scenes.

A scene file sits next to narration.json and an audio/ folder made by narrate.py. Subclass
NarratedScene and call self.segment(id, [(animation, share), ...]) once per narration line:
the line's audio starts with the segment, the animations play one after another, each taking
`share` of the line's length, and the segment then waits out the rest of the line. Shares in a
segment should add up to 1 or less.

Copy this file into the folder beside the scene, and start the scene with

    import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from narrated_scene import NarratedScene
"""
import inspect
import json
import os

from manim import Scene

GAP = 0.4  # seconds of quiet after each narration line


class NarratedScene(Scene):
    def setup(self):
        here = os.path.dirname(os.path.abspath(inspect.getfile(type(self))))
        self.audio_dir = os.path.join(here, "audio")
        path = os.path.join(self.audio_dir, "durations.json")
        if not os.path.exists(path):
            raise FileNotFoundError(f"{path} is missing: run narrate.py on narration.json first")
        with open(path) as fh:
            self.durations = json.load(fh)

    def segment(self, key, animations=()):
        if key not in self.durations:
            raise KeyError(f"no narration line '{key}' in durations.json")
        self.add_sound(os.path.join(self.audio_dir, key + ".wav"))
        total = self.durations[key] + GAP
        shares = sum(s for _, s in animations)
        if shares > 1.0001:
            raise ValueError(f"segment {key}: shares add up to {shares:.2f}, more than 1")
        for anim, share in animations:
            self.play(anim, run_time=max(total * share, 1 / 30))
        rest = total * (1 - shares)
        if rest > 0.05:
            self.wait(rest)
