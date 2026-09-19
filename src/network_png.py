"""Static network figures of the original article, from the exported k-NN graphs.

Same style as graph.generate_graph, but with the converged layout of export_web.force_layout
(400 iterations, fixed seed, oriented like the PCA) instead of networkx's 50 iterations, whose
result changed noticeably from one run to the next.
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from src.config import DEFAULT_COLOR, LEGIS_MAP, PARTY_COLORS
from src.export_web import K_NEIGHBORS, OUT_DIR, force_layout


def render(legislature):
    with open(os.path.join(OUT_DIR, f"network_L{legislature}.json"), encoding="utf-8") as f:
        data = json.load(f)
    order = [node["id"] for node in data["nodes"]]
    edges = {(order[i], order[j]): (rank, weight) for i, j, weight, rank in data["links"]}
    coords = pd.DataFrame([node["pc"] for node in data["nodes"]], index=order)
    pos = force_layout(order, edges, coords)

    plt.figure(figsize=(15, 12))
    ax = plt.gca()
    for i, j, _, rank in data["links"]:
        if rank <= K_NEIGHBORS:
            ax.plot(pos[[i, j], 0], pos[[i, j], 1], color="gray", alpha=0.1, linewidth=1, zorder=1)
    colors = [PARTY_COLORS.get(node["group"], DEFAULT_COLOR) for node in data["nodes"]]
    ax.scatter(pos[:, 0], pos[:, 1], s=50, c=colors, alpha=0.8, zorder=2)
    plt.title(f"Réseau des Députés - Législature {legislature}\n(k-NN cosine, k={K_NEIGHBORS})", fontsize=15)
    plt.axis("off")

    path = os.path.join("Output", LEGIS_MAP[legislature], "network_cosine.png")
    plt.savefig(path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"L{legislature} network figure -> {path}")


def main():
    for legislature in (14, 15, 16):
        render(legislature)


if __name__ == "__main__":
    main()
