import networkx as nx
import pandas as pd
import matplotlib.pyplot as plt
from analyzer import sim_matrix
from config import PARTY_COLORS, DEFAULT_COLOR

sim_matrix.index.name = None
sim_matrix.columns.name = None
links = sim_matrix.stack().reset_index()
links.columns = ['source', 'target', 'weight']

threshold = 0.7
links = links[(links['source'] != links['target']) & (links['weight'] >= threshold)]

G = nx.Graph()
for _, row in links.iterrows():
    G.add_edge(row['source'], row['target'], weight=row['weight'])

print(f"Graphe créé avec {G.number_of_nodes()} nœuds.")

# --- AJOUT DES COULEURS PAR PARTI ---

df_meta = pd.read_csv("dataset_scrutins.csv")
depute_to_group = df_meta.groupby('depute')['groupe'].last().to_dict()

node_colors = []
for node in G.nodes():
    group = depute_to_group.get(node, 'NI')
    node_colors.append(PARTY_COLORS.get(group, DEFAULT_COLOR))

# --- VISUALISATION ---

plt.figure(figsize=(14, 14))
pos = nx.spring_layout(G, k=0.4, seed=42) # k ajuste l'espacement

nx.draw_networkx_edges(G, pos, alpha=0.1, edge_color='gray')

nx.draw_networkx_nodes(G, pos, 
                       node_size=60, 
                       node_color=node_colors, 
                       alpha=0.8)

plt.title(f"Analyse des réseaux de l'Assemblée (Seuil: {threshold})")
plt.axis('off')

# Sauvegarde
output_path = "legislative_network_colors.png"
plt.savefig(output_path, dpi=300, bbox_inches='tight')
plt.close()

print(f"Succès ! Image sauvegardée sous : {output_path}")