import os

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from src.config import DEFAULT_COLOR, PARTY_COLORS  # noqa: E402
from src.export_web import DARK_BG_COLORS, load_votes, pca_coords  # noqa: E402

LEGISLATURE = 16
OUT_DIR = os.path.join("Output", "web")

# The 3D grid must stay a notch away from the background; on dark, RN/HOR use their lighter variants.
STYLES = {
    "white": dict(bg="white", grid="#e4e4e4", colors={}, glow=False),
    "night": dict(bg="#1b1d23", grid="#353a45", colors=DARK_BG_COLORS, glow=True),
}

# Grid layout (white backup cover): checkerboard of ("3d", components, (elev, azim)) or ("2d", components).
PANELS = [
    ("3d", (1, 2, 3), (22, -60)),
    ("2d", (1, 2)),
    ("3d", (1, 2, 4), (20, -60)),
    ("2d", (1, 3)),
    ("3d", (1, 2, 3), (35, 45)),
    ("2d", (2, 4)),
]

# Hero layout (cover in use): one large 3D view, four small 2D views.
HERO_3D = ((1, 2, 3), (35, 45))
HERO_2D = [(1, 2), (1, 3), (2, 3), (2, 4)]


def color(group, st):
    return st["colors"].get(group, PARTY_COLORS.get(group, DEFAULT_COLOR))


# A handful of outlier MPs would otherwise stretch each axis and shrink the main structure.
def robust_limits(values, pad=0.08):
    lo, hi = np.percentile(values, [1, 99])
    return lo - pad * (hi - lo), hi + pad * (hi - lo)


def draw_3d(ax, coords, groups, comps, view, st, size=7, zoom=1.2, box=(1.3, 1, 1)):
    for group in groups.value_counts().index:
        pts = coords[groups == group]
        xyz = [pts[c - 1] for c in comps]
        if st["glow"]:
            ax.scatter(*xyz, s=size * 6, alpha=0.06, color=color(group, st), linewidths=0,
                       depthshade=False, axlim_clip=True)
        ax.scatter(*xyz, s=size, alpha=0.9 if not st["glow"] else 0.92, depthshade=True, axlim_clip=True,
                   color=color(group, st), linewidths=0)
    ax.set_xlim(*robust_limits(coords[comps[0] - 1]))
    ax.set_ylim(*robust_limits(coords[comps[1] - 1]))
    ax.set_zlim(*robust_limits(coords[comps[2] - 1]))
    ax.view_init(elev=view[0], azim=view[1])
    ax.set_box_aspect(box, zoom=zoom)
    ax.set_facecolor(st["bg"])
    for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
        axis.set_ticklabels([])
        axis.pane.set_facecolor(st["bg"])
        axis.pane.set_edgecolor(st["grid"])
        axis.line.set_color(st["grid"])
        axis._axinfo["tick"]["inward_factor"] = 0
        axis._axinfo["tick"]["outward_factor"] = 0
        axis._axinfo["grid"].update(color=st["grid"], linewidth=0.5)


def draw_2d(ax, coords, groups, comps, st, size=9):
    x, y = coords[comps[0] - 1], coords[comps[1] - 1]
    (x0, x1), (y0, y1) = robust_limits(x, pad=0.1), robust_limits(y, pad=0.1)
    # Drop the outliers instead of letting the axes clip their markers in half.
    inside = x.between(x0, x1) & y.between(y0, y1)
    for group in groups.value_counts().index:
        mask = inside & (groups == group)
        if st["glow"]:
            ax.scatter(x[mask], y[mask], s=size * 6, alpha=0.06, color=color(group, st), linewidths=0)
        ax.scatter(x[mask], y[mask], s=size, alpha=0.9 if not st["glow"] else 0.92,
                   color=color(group, st), edgecolors=st["bg"], linewidths=0.2)
    ax.set_facecolor(st["bg"])
    ax.set_axis_off()
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)


# The blog theme crops covers to ~2:1 (article header) and ~2.7:1 (home card): both layouts keep
# every panel within 6.5% of the sides and 7.5% of the top/bottom, the area visible in both.
def grid_figure(coords, groups, st):
    fig = plt.figure(figsize=(13.8, 6.0), dpi=150, facecolor=st["bg"])
    for i, panel in enumerate(PANELS, start=1):
        if panel[0] == "3d":
            draw_3d(fig.add_subplot(2, 3, i, projection="3d"), coords, groups, panel[1], panel[2], st)
        else:
            draw_2d(fig.add_subplot(2, 3, i), coords, groups, panel[1], st)
    fig.subplots_adjust(left=0.065, right=0.935, top=0.925, bottom=0.075, wspace=0.06, hspace=0.08)
    return fig


def hero_figure(coords, groups, st):
    fig = plt.figure(figsize=(13.8, 6.0), dpi=150, facecolor=st["bg"])
    big = fig.add_axes([0.075, 0.085, 0.43, 0.83], projection="3d")
    draw_3d(big, coords, groups, HERO_3D[0], HERO_3D[1], st, size=13, zoom=1.0, box=(1.15, 1, 1))
    x0, y0, w, h, gap_x, gap_y = 0.535, 0.085, 0.19, 0.4, 0.02, 0.03
    for k, comps in enumerate(HERO_2D):
        col, row = k % 2, 1 - k // 2
        ax = fig.add_axes([x0 + col * (w + gap_x), y0 + row * (h + gap_y), w, h])
        draw_2d(ax, coords, groups, comps, st, size=7)
    return fig


def main():
    pivot, groups = load_votes(LEGISLATURE)
    coords, _ = pca_coords(pivot)
    groups = groups.loc[coords.index]
    for name, figure, style in (("cover_night.png", hero_figure, "night"), ("cover_white.png", grid_figure, "white")):
        fig = figure(coords, groups, STYLES[style])
        path = os.path.join(OUT_DIR, name)
        fig.savefig(path, facecolor=fig.get_facecolor())
        plt.close(fig)
        print(f"Cover saved: {path}")


if __name__ == "__main__":
    main()
