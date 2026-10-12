"""
figures.py — patterns for rendering slide/PDF figures with matplotlib.

Two things you need again and again:
  1. Typeset EQUATIONS as transparent PNGs (mathtext) — so PowerPoint/the PDF show
     proper ∑ ∫ √ 𝓘 etc. without depending on a system font having them.
  2. Simple NODE-AND-ARROW diagrams (boxes, arrows, loops) for explanatory slides.

mathtext (matplotlib's built-in TeX subset) covers most of what you need:
  \\mathcal \\mathrm \\text \\operatorname \\sum \\int \\frac superscripts/subscripts \\mid \\sim \\Delta etc.
NOT supported: \\big, \\Big, \\bigg and their \\bigl/\\bigr forms. Use plain parentheses
instead of \\big(...\\big), and keep subscripts in braces: x_{t+1}.

Run with a non-interactive backend so it works headless.
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

INK="#1A2433"; PRIMARY="#0F5C6B"; PRIMARY_D="#0B3D47"; BLUE="#1F6FEB"
GREEN="#1B7A3D"; RED="#9A2A2A"; AMBER="#A6680B"; MUTED="#6B7785"; LIGHT="#EEF3F5"

OUT="fig"; os.makedirs(OUT, exist_ok=True)

def eq(tex, name, fs=30, color=INK):
    """Render a single equation to a tight, transparent PNG: fig/<name>.png."""
    fig=plt.figure(figsize=(0.1,0.1)); fig.text(0,0,tex,fontsize=fs,color=color)
    fig.savefig(f"{OUT}/{name}.png", dpi=300, transparent=True, bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)

# --- diagram primitives (axes in 0..10 user units; turn axis off) ---
def box(ax,x,y,w,h,text,fc,tc="white",fs=11,bold=True):
    ax.add_patch(FancyBboxPatch((x-w/2,y-h/2),w,h,boxstyle="round,pad=0.02,rounding_size=0.06",
                fc=fc,ec=fc,lw=1.6,zorder=2))
    ax.text(x,y,text,ha="center",va="center",color=tc,fontsize=fs,
            fontweight="bold" if bold else "normal",zorder=3)

def arrow(ax,p,q,color=INK,lw=2.2,style="-|>",rad=0.0,ls="-"):
    ax.add_patch(FancyArrowPatch(p,q,arrowstyle=style,mutation_scale=14,color=color,lw=lw,
                connectionstyle=f"arc3,rad={rad}",zorder=1,linestyle=ls))

def save(fig,name,**kw):
    fig.savefig(f"{OUT}/{name}.png", dpi=300, transparent=True, bbox_inches="tight", pad_inches=0.1, **kw)
    plt.close(fig)

# --------- examples ---------
if __name__ == "__main__":
    # equations
    eq(r"$H(X)=-\sum_x p(x)\,\log_2 p(x)$", "eq_H", 34)
    eq(r"$D_{\mathrm{KL}}(p\,\|\,q)=\sum_x p(x)\,\log\frac{p(x)}{q(x)}$", "eq_KL", 30, BLUE)

    # a two-panel "loop vs one-way" diagram (the kind that carries a hard idea)
    fig,axes=plt.subplots(1,2,figsize=(10,4.2))
    ax=axes[0]; ax.set_xlim(0,10); ax.set_ylim(0,10); ax.axis("off")
    ax.text(5,9.3,"one-way",ha="center",fontsize=13,fontweight="bold",color=RED)
    box(ax,2.2,5,2.4,1.3,"cause",MUTED,fs=12); box(ax,7.6,5,2.6,1.3,"reading",RED,fs=12)
    arrow(ax,(3.5,5),(6.2,5),RED,2.5)
    ax=axes[1]; ax.set_xlim(0,10); ax.set_ylim(0,10); ax.axis("off")
    ax.text(5,9.3,"closed loop",ha="center",fontsize=13,fontweight="bold",color=GREEN)
    box(ax,5,7,2.6,1.1,"inside",GREEN,fs=11); box(ax,8,4.2,2.1,1.1,"action",GREEN,fs=11)
    box(ax,5,1.6,2.6,1.1,"senses",GREEN,fs=11); box(ax,2,4.2,2.1,1.1,"world",MUTED,fs=11)
    for a,b in [((6.0,6.5),(7.4,5.0)),((7.4,3.5),(6.0,2.0)),((4.0,2.0),(2.6,3.6)),((2.6,4.9),(4.0,6.5))]:
        arrow(ax,a,b,GREEN,2.4,rad=-0.25)
    save(fig,"loop_example")
    print("wrote", os.listdir(OUT))
