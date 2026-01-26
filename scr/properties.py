import networkx as nx
import pandas as pd

def compute_graph_metrics(G, df_meta, top_n=5):
    """
    Calcule les métriques globales et les leaders par famille politique.
    """
    for u, v, d in G.edges(data=True):
        G[u][v]['distance'] = 1.0 / (d['weight'] + 1e-6)

    betweenness = nx.betweenness_centrality(G, weight='distance')
    degree_weighted = dict(G.degree(weight='weight'))

    depute_to_group = df_meta.groupby('depute')['groupe'].last().to_dict()
    all_groups = sorted(list(set(depute_to_group.values())))

    influence_intra = {}
    influence_global = {}

    for group in all_groups:
        members = [n for n in G.nodes() if depute_to_group.get(n) == group]
        if not members: continue

        # --- ANALYSE GLOBALE : Le plus influent du groupe sur TOUT le graphe ---
        leader_global = max(members, key=lambda m: degree_weighted.get(m, 0))
        influence_global[group] = {
            'nom': leader_global, 
            'score': round(degree_weighted[leader_global], 2)
        }

        # --- ANALYSE INTRA : Le plus influent au sein de son propre groupe ---
        if len(members) > 1:
            subgraph = G.subgraph(members)
            intra_degrees = dict(subgraph.degree(weight='weight'))
            leader_intra = max(intra_degrees, key=lambda m: intra_degrees[m])
            influence_intra[group] = {
                'nom': leader_intra, 
                'score': round(intra_degrees[leader_intra], 2)
            }

    def get_top_entities(metric_dict, n=top_n):
        sorted_items = sorted(metric_dict.items(), key=lambda x: x[1], reverse=True)[:n]
        return [{'nom': name, 'groupe': depute_to_group.get(name, 'NI'), 'score': round(score, 4)} 
                for name, score in sorted_items]

    report = {
        'pivots': get_top_entities(betweenness),
        'piliers': get_top_entities(degree_weighted),
        'intra_leaders': influence_intra,
        'global_leaders': influence_global
    }

    return report

def print_report(report, legislature):

    print(f"\n TOP PIVOTS (Betweenness) :")
    for i, d in enumerate(report['pivots'], 1):
        print(f"{i}. {d['nom']:25} ({d['groupe']:6}) - Score: {d['score']}")

    print(f"\n TOP {len(report['piliers'])} PILIERS (Degree) :")
    for i, d in enumerate(report['piliers'], 1):
        print(f"{i}. {d['nom']} ({d['groupe']}) - Score: {d['score']}")

    print(f"\n LEADERS PAR FAMILLE (Intra-groupe vs Rayonnement global) :")
    print(f"{'Groupe':10} | {'Leader de Cohésion (Intra)':30} | {'Leader Hub (Global)':30}")
    print("-" * 80)
    for grp in report['global_leaders'].keys():
        intra = report['intra_leaders'].get(grp, {'nom': 'N/A', 'score': 0})
        glob = report['global_leaders'][grp]
        print(f"{grp:10} | {intra['nom'][:28]:30} ({intra['score']:7.1f}) | {glob['nom'][:28]:30} ({glob['score']:7.1f})")