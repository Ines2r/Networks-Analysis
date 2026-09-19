import json
import os
import xml.etree.ElementTree as ET

import networkx as nx
import numpy as np
import pandas as pd
import requests
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

from src.config import DEFAULT_COLOR, LEGIS_MAP, MAP_VOTE, PARTY_COLORS
from src.convert import parse_table_noms, slugify
from src.similarity import compute_similarity, filter_by_voters
from src.themes import THEMES, classify

K_NEIGHBORS = 5
K_CHOICES = (3, 5, 10, 15)
N_COMPONENTS = 6
OUT_DIR = os.path.join("Output", "web")

# Below this many voters a ballot is an amendment vote attended by a handful of MPs, where the
# explorer map would be almost empty: it only keeps the ones the Assembly actually turned up for.
EXPLORER_MIN_VOTERS = 200
# Same force layout as the page, run once here so the explorer map is stable and shows instantly.
LAYOUT_ITERATIONS = 400
LAYOUT_K = 0.15

# nosdeputes.fr serves the 16th legislature on its main domain (no 2022-2024 subdomain).
NOSDEPUTES_URLS = {
    14: "https://2012-2017.nosdeputes.fr/deputes/json",
    15: "https://2017-2022.nosdeputes.fr/deputes/json",
    16: "https://www.nosdeputes.fr/deputes/json",
}
# Ballot titles and dates; the 14th legislature uses the local Assemblée nationale file instead.
SCRUTINS_URLS = {
    15: "https://2017-2022.nosdeputes.fr/15/scrutins/xml",
    16: "https://www.nosdeputes.fr/16/scrutins/xml",
}
VOTE_CHARS = {"pour": "p", "contre": "c", "abstention": "a", "nonVotant": "n"}
CAST = ("pour", "contre", "abstention")

# Same rules as properties.compute_graph_metrics: leaders only for groups with enough members to lead.
MIN_GROUP_FOR_LEADERS = 10
N_PIVOTS = 10

# Themes with fewer classified ballots are not exported: their PCA would rest on one or two texts.
MIN_THEME_BALLOTS = 60
# Explained variance mechanically grows as ballots are removed: each theme is compared with random
# subsets of the same size, drawn without replacement from all the ballots of the legislature. Drawing
# with replacement would repeat ballots and inflate the very variance the baseline is meant to measure.
BASELINE_DRAWS = 200
THEME_LEGISLATURES = (15, 16)

# The web figures use a dark background: same hue, higher OKLCH lightness so these dots stay visible.
DARK_BG_COLORS = {"RN": "#3b79bb", "HOR": "#ad63ce"}


def cached_download(url, path, timeout=300):
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        with open(path, "wb") as f:
            f.write(response.content)
    return path


def table_noms_names():
    _, actors = parse_table_noms(os.path.join("Data", "table_noms.xml"))
    names = {}
    for a in actors.values():
        full = f"{a['prenom']} {a['nom']}".strip()
        names[slugify(full)] = full
    return names


def nosdeputes_records(legislature):
    path = cached_download(NOSDEPUTES_URLS[legislature], os.path.join("Data", "nosdeputes", f"deputes_{legislature}.json"))
    with open(path, encoding="utf-8") as f:
        return [d["depute"] for d in json.load(f)["deputes"]]


def display_name(slug, names):
    return names.get(slug) or slug.replace("-", " ").title()


def read_votes_csv(legislature):
    path = os.path.join("Output", LEGIS_MAP[legislature], f"dataset_scrutins_{legislature}.csv")
    return pd.read_csv(path)


def load_votes(legislature, df=None):
    df = read_votes_csv(legislature) if df is None else df
    df = filter_by_voters(df, 0)
    df["vote_val"] = df["position"].map(MAP_VOTE)
    pivot = df.pivot_table(index="depute", columns="scrutin_id", values="vote_val")
    groups = df.groupby("depute")["groupe"].last().fillna("NI")
    return pivot, groups


def ballot_meta(legislature):
    """Ballot number -> date, title, outcome."""
    meta = {}
    if legislature == 14:
        for _, elem in ET.iterparse(os.path.join("Data", "scrutins.xml"), events=("end",)):
            if elem.tag != "scrutin":
                continue
            numero = elem.findtext("numero")
            if numero:
                meta[numero] = {
                    "date": elem.findtext("dateScrutin") or "",
                    "title": (elem.findtext("titre") or "").strip(),
                    "sort": elem.findtext("sort/code") or "",
                }
            elem.clear()
    else:
        path = cached_download(SCRUTINS_URLS[legislature], os.path.join("Data", "nosdeputes", f"scrutins_{legislature}.xml"))
        for scrutin in ET.parse(path).getroot().findall("scrutin"):
            numero = scrutin.findtext("numero")
            if numero:
                meta[numero] = {
                    "date": scrutin.findtext("date") or "",
                    "title": (scrutin.findtext("titre") or "").strip(),
                    "sort": scrutin.findtext("sort") or "",
                }
    return meta


def participation(df, meta, records):
    """Share of the ballots held during an MP's mandate where their vote was recorded."""
    ballots = df[["scrutin_id"]].drop_duplicates()
    ballots["date"] = ballots["scrutin_id"].astype(str).map({k: v["date"] for k, v in meta.items()})
    ballots = ballots.dropna(subset=["date"])
    all_dates = np.sort(ballots["date"].to_numpy())
    cast = df[df["position"].isin(CAST)].merge(ballots, on="scrutin_id")
    windows = {r["slug"]: mandate_windows(r) for r in records}

    rates = {}
    for depute, voted_dates in cast.groupby("depute")["date"]:
        voted_dates = np.sort(voted_dates.to_numpy())
        # MPs missing from the nosdeputes list fall back to their own first and last recorded ballot.
        spans = windows.get(depute) or [(voted_dates[0], voted_dates[-1])]
        # Both sides of the ratio are restricted to the mandates: an MP who leaves for the government
        # and comes back is measured against the ballots held while they sat, not the whole legislature.
        eligible = voted = 0
        for start, end in spans:
            eligible += np.searchsorted(all_dates, end, "right") - np.searchsorted(all_dates, start, "left")
            voted += np.searchsorted(voted_dates, end, "right") - np.searchsorted(voted_dates, start, "left")
        if eligible:
            rates[depute] = voted / eligible
    return pd.Series(rates)


def mandate_windows(record):
    """Every (start, end) an MP sat, as ISO dates.

    `mandat_debut` / `mandat_fin` only hold the latest mandate: an MP who left for the government and
    came back would be measured on their last weeks only. `anciens_mandats` lists all of them
    ("21/06/2017 / 06/08/2020 / nomination comme membre du gouvernement"), across legislatures;
    windows outside the legislature simply contain none of its ballots.
    """
    iso = lambda d: "-".join(reversed(d.strip().split("/"))) if d.strip() else "9999-12-31"
    spans = {(record["mandat_debut"], record.get("mandat_fin") or "9999-12-31")} if record.get("mandat_debut") else set()
    for item in record.get("anciens_mandats") or []:
        parts = item["mandat"].split(" / ")
        if len(parts) >= 2 and parts[0].strip():
            spans.add((iso(parts[0]), iso(parts[1])))
    # Overlapping entries (the current mandate is often listed twice) must not count ballots twice.
    merged = []
    for start, end in sorted(spans):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def groups_summary(member_groups):
    counts = pd.Series(member_groups).value_counts()
    return [
        {"name": g, "color": DARK_BG_COLORS.get(g, PARTY_COLORS.get(g, DEFAULT_COLOR)), "count": int(c)}
        for g, c in counts.items()
    ]


def rate_of(rates, depute):
    value = rates.get(depute)
    return None if value is None or pd.isna(value) else round(float(value), 4)


def pca_coords(pivot):
    """MP coordinates, explained variance, and where an MP with no recorded vote would land.

    Absences are 0 before standardization, so after it they are not 0: an MP who never votes has the
    row -mean/std, which projects to a fixed point away from the origin. The fewer ballots an MP
    votes on, the closer they get to that point.
    """
    scaler = StandardScaler()
    scaled = scaler.fit_transform(pivot.fillna(0))
    pca = PCA(n_components=N_COMPONENTS, random_state=0)
    coords = pd.DataFrame(pca.fit_transform(scaled), index=pivot.index)
    absent = pca.transform(scaler.transform(np.zeros((1, pivot.shape[1]))))[0]
    return coords, pca.explained_variance_ratio_, absent


def export_network(pivot, groups, names, legislature, coords, rates):
    sim = compute_similarity(pivot, method="cosine")

    # Same rule as graph.generate_graph (top-k neighbours, positive weights, undirected), computed for
    # the largest k; each edge keeps the smallest k at which it appears so the page can filter by k.
    edges = {}
    for depute in sim.index:
        top = sim.loc[depute].drop(labels=[depute]).nlargest(max(K_CHOICES))
        for rank, (neighbor, weight) in enumerate(top.items(), start=1):
            if weight > 0:
                key = tuple(sorted((depute, neighbor)))
                edges[key] = (min(rank, edges[key][0]) if key in edges else rank, float(weight))

    in_graph = {d for edge in edges for d in edge}
    order = [d for d in sim.index if d in in_graph]
    index = {d: i for i, d in enumerate(order)}

    out = {
        "legislature": legislature,
        "years": LEGIS_MAP[legislature],
        "k": K_NEIGHBORS,
        "k_choices": list(K_CHOICES),
        "n_scrutins": int(pivot.shape[1]),
        "groups": groups_summary([groups[d] for d in order]),
        # PC1/PC2 are only used to orient the converged layout like the PCA plot.
        "nodes": [
            {
                "id": d,
                "name": display_name(d, names),
                "group": groups[d],
                "part": rate_of(rates, d),
                "pc": [round(float(coords.at[d, 0]), 4), round(float(coords.at[d, 1]), 4)],
            }
            for d in order
        ],
        "links": [[index[a], index[b], round(w, 4), r] for (a, b), (r, w) in edges.items()],
    }
    path = os.path.join(OUT_DIR, f"network_L{legislature}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    per_k = ", ".join(f"k={k}: {sum(r <= k for r, _ in edges.values())}" for k in K_CHOICES)
    print(f"L{legislature} network: {len(order)} MPs, edges {per_k} -> {path}")
    return order, edges


def graph_roles(order, edges, groups):
    """Cohesion and hub leaders of each group and the top betweenness pivots, on the k=5 graph.

    Cohesion leader: highest weighted degree inside the group's subgraph. Hub leader: highest
    weighted degree in the whole graph. Pivots: highest betweenness, with 1 / similarity as distance.
    """
    G = nx.Graph()
    for (a, b), (rank, weight) in edges.items():
        if rank <= K_NEIGHBORS:
            G.add_edge(a, b, weight=weight, distance=1.0 / (weight + 1e-6))
    degree = dict(G.degree(weight="weight"))

    roles = {}
    members = pd.Series({d: groups[d] for d in order})
    for group, ids in members.groupby(members):
        ids = [d for d in ids.index if d in G]
        if len(ids) < MIN_GROUP_FOR_LEADERS:
            continue
        intra = dict(G.subgraph(ids).degree(weight="weight"))
        roles.setdefault(max(ids, key=intra.get), {})["intra"] = True
        roles.setdefault(max(ids, key=degree.get), {})["hub"] = True

    betweenness = nx.betweenness_centrality(G, weight="distance")
    for rank, d in enumerate(sorted(betweenness, key=betweenness.get, reverse=True)[:N_PIVOTS], start=1):
        roles.setdefault(d, {})["pivot"] = rank
    return roles


def export_pca(groups, names, legislature, n_scrutins, coords, variance_ratio, absent, rates, roles):
    radius = np.hypot(coords[0] - absent[0], coords[1] - absent[1])
    shared = [d for d in coords.index if rate_of(rates, d) is not None]
    ranked = pd.DataFrame({"r": radius.loc[shared], "p": rates.loc[shared]}).rank()
    spearman = float(ranked["r"].corr(ranked["p"]))

    out = {
        "legislature": legislature,
        "years": LEGIS_MAP[legislature],
        "n_scrutins": n_scrutins,
        "explained_variance": [round(float(v), 5) for v in variance_ratio],
        # Position of an MP with no recorded vote, on each component.
        "absent_point": [round(float(v), 4) for v in absent],
        "groups": groups_summary([groups[d] for d in coords.index]),
        "points": [
            {
                "id": d,
                "name": display_name(d, names),
                "group": groups[d],
                "part": rate_of(rates, d),
                "pc": [round(float(v), 4) for v in row],
                **roles.get(d, {}),
            }
            for d, row in coords.iterrows()
        ],
    }
    path = os.path.join(OUT_DIR, f"pca_L{legislature}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    variance = ", ".join(f"{v:.1%}" for v in variance_ratio)
    print(f"L{legislature} PCA: {len(coords)} MPs, variance [{variance}], "
          f"no-vote point ({absent[0]:.1f}, {absent[1]:.1f}), Spearman(participation, distance to it on "
          f"PC1-PC2) {spearman:.2f} -> {path}")


def export_themes(legislature, pivot, groups, names, coords, meta, rates):
    """One PCA per theme, on the ballots classified in that theme only."""
    by_theme = {key: [] for key in THEMES}
    for scrutin_id in pivot.columns:
        info = meta.get(str(scrutin_id))
        key = classify(info["title"]) if info else None
        if key:
            by_theme[key].append(scrutin_id)

    rng = np.random.default_rng(0)
    mps = list(coords.index)
    themes = []
    for key, ids in by_theme.items():
        if len(ids) < MIN_THEME_BALLOTS:
            print(f"L{legislature} theme {key}: {len(ids)} ballots, skipped")
            continue
        sub = pivot[ids].dropna(how="all")
        theme_coords, variance_ratio, absent = pca_coords(sub)
        # A component's sign is arbitrary: each one is flipped to agree with the global component of
        # the same rank, so switching themes does not mirror the plot for no reason.
        shared = theme_coords.index
        correlation = []
        for k in range(N_COMPONENTS):
            r = float(np.corrcoef(theme_coords[k], coords.loc[shared, k])[0, 1])
            if r < 0:
                theme_coords[k] *= -1
                absent[k] *= -1
            correlation.append(round(abs(r), 3))
        baseline = [
            pca_coords(pivot[rng.choice(pivot.columns, len(ids), replace=False)].dropna(how="all"))[1]
            for _ in range(BASELINE_DRAWS)
        ]
        themes.append({
            "key": key,
            "label": THEMES[key]["label"],
            "n_scrutins": len(ids),
            "explained_variance": [round(float(v), 5) for v in variance_ratio],
            "baseline_variance": [round(float(v), 5) for v in np.mean(baseline, axis=0)],
            # 5th-95th percentile over the random draws, per component: the extremes of a finite number
            # of draws are unstable and widen with the number of draws, percentiles do neither.
            "baseline_range": [[round(float(lo), 5), round(float(hi), 5)]
                               for lo, hi in zip(np.percentile(baseline, 5, axis=0), np.percentile(baseline, 95, axis=0))],
            # Share of the random draws reaching the theme's own share, per component.
            "baseline_p": [round(float(np.mean(np.asarray(baseline)[:, k] >= variance_ratio[k])), 3)
                           for k in range(N_COMPONENTS)],
            # |Pearson r| between each theme component and the global component of the same rank.
            "global_correlation": correlation,
            "absent_point": [round(float(v), 3) for v in absent],
            "pc": [
                [round(float(v), 3) for v in theme_coords.loc[d]] if d in theme_coords.index else None
                for d in mps
            ],
            # Ballots of the theme where the MP's vote was recorded: the absence effect, theme by theme.
            "cast": [int(v) for v in pivot.loc[mps, ids].notna().sum(axis=1)],
        })
        print(f"L{legislature} theme {key}: {len(ids)} ballots, PC1 {variance_ratio[0]:.1%} "
              f"(random subsets {themes[-1]['baseline_variance'][0]:.1%}), r(PC1, global PC1) {correlation[0]:.2f}")

    out = {
        "legislature": legislature,
        "years": LEGIS_MAP[legislature],
        "n_scrutins": int(pivot.shape[1]),
        "min_ballots": MIN_THEME_BALLOTS,
        "groups": groups_summary([groups[d] for d in mps]),
        "mps": [
            {"id": d, "name": display_name(d, names), "group": groups[d], "part": rate_of(rates, d)}
            for d in mps
        ],
        "themes": themes,
    }
    path = os.path.join(OUT_DIR, f"pca_themes_L{legislature}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print(f"L{legislature} themes: {len(themes)} exported -> {path}")


def force_layout(order, edges, coords, seed=0):
    """Fruchterman-Reingold on the k=5 graph, oriented like the PCA, as the page does it."""
    n = len(order)
    index = {d: i for i, d in enumerate(order)}
    adj = np.zeros((n, n))
    for (a, b), (rank, weight) in edges.items():
        if rank <= K_NEIGHBORS:
            i, j = index[a], index[b]
            adj[i, j] = adj[j, i] = weight

    pos = np.random.default_rng(seed).random((n, 2))
    t = 0.1 * max(np.ptp(pos[:, 0]), np.ptp(pos[:, 1]))
    dt = t / (LAYOUT_ITERATIONS + 1)
    for _ in range(LAYOUT_ITERATIONS):
        delta = pos[:, None, :] - pos[None, :, :]
        dist = np.clip(np.linalg.norm(delta, axis=-1), 0.01, None)
        disp = np.einsum("ijk,ij->ik", delta, LAYOUT_K**2 / dist**2 - adj * dist / LAYOUT_K)
        length = np.linalg.norm(disp, axis=-1)
        step = disp * (t / np.where(length < 0.01, 0.1, length))[:, None]
        pos += step
        t -= dt
        if np.linalg.norm(step) / n < 1e-4:
            break

    target = coords.loc[order, [0, 1]].to_numpy()
    target = target - target.mean(0)
    pos = pos - pos.mean(0)
    best, best_score = pos, -np.inf
    for mirror in (1, -1):
        p = pos * [mirror, 1]
        a = float((p * target).sum())
        b = float((p[:, 0] * target[:, 1] - p[:, 1] * target[:, 0]).sum())
        score = float(np.hypot(a, b))
        if score > best_score:
            theta = np.arctan2(b, a)
            rot = np.array([[np.cos(theta), -np.sin(theta)], [np.sin(theta), np.cos(theta)]])
            best, best_score = p @ rot.T, score
    return best / np.abs(best).max()


def export_ballots(legislature, df, meta, groups, names, order, edges, coords, rates):
    layout = force_layout(order, edges, coords)
    index = {d: i for i, d in enumerate(order)}

    kept = []
    for scrutin_id, rows in df.groupby("scrutin_id"):
        info = meta.get(str(scrutin_id))
        if info is None:
            continue
        votes = ["."] * len(order)
        counts = dict.fromkeys(CAST, 0)
        for depute, position in zip(rows["depute"], rows["position"]):
            i = index.get(depute)
            if i is None or position not in VOTE_CHARS:
                continue
            votes[i] = VOTE_CHARS[position]
            if position in counts:
                counts[position] += 1
        if sum(counts.values()) < EXPLORER_MIN_VOTERS:
            continue
        kept.append({
            "n": int(scrutin_id),
            "d": info["date"],
            "t": info["title"],
            "s": info["sort"],
            "c": [counts["pour"], counts["contre"], counts["abstention"]],
            "v": "".join(votes),
        })
    kept.sort(key=lambda b: (b["d"], b["n"]))

    out = {
        "legislature": legislature,
        "years": LEGIS_MAP[legislature],
        "min_voters": EXPLORER_MIN_VOTERS,
        "n_total": int(df["scrutin_id"].nunique()),
        "groups": groups_summary([groups[d] for d in order]),
        "mps": [
            {"id": d, "name": display_name(d, names), "group": groups[d], "part": rate_of(rates, d)}
            for d in order
        ],
        "layout": [[round(float(x), 4), round(float(y), 4)] for x, y in layout],
        "ballots": kept,
    }
    path = os.path.join(OUT_DIR, f"ballots_L{legislature}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    size = os.path.getsize(path) / 1e6
    print(f"L{legislature} ballots: {len(kept)} of {out['n_total']} kept "
          f"(>= {EXPLORER_MIN_VOTERS} voters), {size:.2f} MB -> {path}")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    base_names = table_noms_names()
    for legislature in (14, 15, 16):
        records = nosdeputes_records(legislature)
        names = {**base_names, **{r["slug"]: r["nom"] for r in records}}
        df = read_votes_csv(legislature)
        pivot, groups = load_votes(legislature, df)
        coords, variance_ratio, absent = pca_coords(pivot)
        meta = ballot_meta(legislature)
        rates = participation(df, meta, records)
        print(f"L{legislature} participation: median {rates.median():.1%} over {len(meta)} dated ballots")
        order, edges = export_network(pivot, groups, names, legislature, coords, rates)
        roles = graph_roles(order, edges, groups)
        export_pca(groups, names, legislature, int(pivot.shape[1]), coords, variance_ratio, absent, rates, roles)
        export_ballots(legislature, df, meta, groups, names, order, edges, coords, rates)
        if legislature in THEME_LEGISLATURES:
            export_themes(legislature, pivot, groups, names, coords, meta, rates)


if __name__ == "__main__":
    main()
