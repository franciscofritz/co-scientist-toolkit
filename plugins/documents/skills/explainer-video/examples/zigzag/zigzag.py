"""Worked example: why gradient descent zig-zags in a narrow valley.

Loss f(x, y) = (x^2 + 10 y^2) / 2, gradient (x, 10 y). A step of size eta multiplies x by
(1 - eta) and y by (1 - 10 eta). With eta = 0.18 these are 0.82 and -0.8; stable only for eta < 0.2.
"""
import os
import sys

import numpy as np
from manim import (DOWN, LEFT, RIGHT, UP, Arrow, Axes, Create, Dot, Ellipse, FadeIn, FadeOut,
                   Line, MathTex, Text, VGroup, Write, config)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from narrated_scene import NarratedScene  # noqa: E402

ETA, START, STEPS = 0.18, np.array([-4.0, 1.0]), 15
INK, MUTED, PATH, ARROW = "#E8ECF0", "#8A96A3", "#F2A541", "#6FB3E0"
config.background_color = "#12171C"


def gd_path():
    pts = [START.copy()]
    for _ in range(STEPS):
        x, y = pts[-1]
        pts.append(np.array([x - ETA * x, y - ETA * 10 * y]))
    return pts


class ZigZag(NarratedScene):
    def construct(self):
        title = Text("Why gradient descent zig-zags", font_size=38, color=INK).to_edge(UP, buff=0.45)
        ax = Axes(x_range=[-5, 5, 1], y_range=[-1.5, 1.5, 0.5], x_length=10, y_length=3,
                  tips=False, axis_config={"color": MUTED, "stroke_width": 1.5}).shift(DOWN * 0.3)
        unit = ax.x_length / 10
        contours = VGroup(*[
            Ellipse(width=2 * np.sqrt(c) * unit, height=2 * np.sqrt(c / 10) * unit,
                    color=MUTED, stroke_width=1.5).move_to(ax.c2p(0, 0))
            for c in [0.5, 2, 5, 10, 16, 22]
        ])
        minimum = Dot(ax.c2p(0, 0), color=INK, radius=0.06)
        along = Text("along the valley", font_size=22, color=MUTED).next_to(ax, DOWN, buff=0.25)
        self.segment("s1", [(Write(title), 0.35), (Create(ax), 0.25),
                            (Create(contours), 0.3), (FadeIn(minimum, along), 0.1)])

        eq = MathTex(r"f(x,y)=\tfrac{1}{2}\left(x^2+10\,y^2\right)", font_size=36, color=INK)
        eq.to_corner(DOWN + LEFT, buff=0.5)
        start = Dot(ax.c2p(*START), color=PATH, radius=0.07)
        g = np.array([START[0], 10 * START[1]])
        d = -g / np.linalg.norm(g)
        arrow = Arrow(ax.c2p(*START), ax.c2p(*(START + 1.1 * d)), buff=0, color=ARROW,
                      stroke_width=4, max_tip_length_to_length_ratio=0.25)
        self.segment("s2", [(Write(eq), 0.4), (FadeIn(start), 0.15), (Create(arrow), 0.3)])

        pts = gd_path()
        lines = [Line(ax.c2p(*pts[i]), ax.c2p(*pts[i + 1]), color=PATH, stroke_width=3)
                 for i in range(STEPS)]
        dots = [Dot(ax.c2p(*p), color=PATH, radius=0.045) for p in pts[1:4]]
        # The arrow points along the first step, so it goes before that step is drawn.
        self.segment("s3", [(FadeOut(arrow), 0.1), (Create(lines[0]), 0.15), (FadeIn(dots[0]), 0.05),
                            (Create(lines[1]), 0.2), (FadeIn(dots[1]), 0.05),
                            (Create(lines[2]), 0.2), (FadeIn(dots[2]), 0.05)])

        factors = VGroup(
            MathTex(r"\text{across: } y \to (1-10\eta)\,y = -0.8\,y", font_size=32, color=INK),
            MathTex(r"\text{along: } x \to (1-\eta)\,x = 0.82\,x", font_size=32, color=INK),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.15).to_corner(DOWN + RIGHT, buff=0.5)
        self.segment("s4", [(Write(factors), 0.25)] + [(Create(lines[i]), 0.06) for i in range(3, STEPS)])

        limit = MathTex(r"\text{stable only if } \eta < \tfrac{2}{10} = 0.2", font_size=32, color=ARROW)
        limit.next_to(title, DOWN, buff=0.2)
        self.segment("s5", [(Write(limit), 0.35)])
