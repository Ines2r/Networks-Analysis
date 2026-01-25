import networkx as nx
import pandas as pd
import matplotlib.pyplot as plt
from config import PARTY_COLORS, DEFAULT_COLOR, MAP_VOTE


def generate_graph(sim_matrix, df_meta, legislature, k_neighbors, min_voters, output_path="graph.png"):
    sim_matrix.index.name = None
    sim_matrix.columns.name = None
    links = sim_matrix.stack().reset_index()
    links.columns = ['source', 'target', 'weight']
    links = links[links['source'] != links['target']]

    links = links.sort_values(['source', 'weight'], ascending=[True, False])
    links = links.groupby('source').head(k_neighbors)

    G = nx.Graph()
    for _, row in links.iterrows():
        G.add_edge(row['source'], row['target'], weight=row['weight']**3)


    pos = nx.spring_layout(G, k=0.1, weight='weight', iterations=100, seed=42)

    plt.figure(figsize=(16, 16))

    depute_to_group = df_meta.groupby('depute')['groupe'].last().to_dict()
    nodes = G.nodes()
    colors = [PARTY_COLORS.get(depute_to_group.get(n, 'NI'), DEFAULT_COLOR) for n in nodes]

    weights = [G[u][v]['weight'] for u, v in G.edges()]
    widths = [w * 2 for w in weights]

    nx.draw_networkx_edges(G, pos, width=widths, alpha=0.1, edge_color='gray')

    nx.draw_networkx_nodes(G, pos, 
                           node_size=80, 
                           node_color=colors, 
                           alpha=0.9,
                           edgecolors='white',
                           linewidths=0.5)

    plt.title(f"Législature {legislature} | N_neighbors = {k_neighbors} | min_voters = {min_voters}", fontsize=18)
    plt.axis('off')
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()