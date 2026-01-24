import networkx as nx
from analyzer import sim_matrix
from pyvis.network import Network
import matplotlib.pyplot as plt

sim_matrix.index.name = None
sim_matrix.columns.name = None

links = sim_matrix.stack().reset_index()

links.columns = ['source', 'target', 'weight']

threshold = 0.7
links = links[(links['source'] != links['target']) & (links['weight'] >= threshold)]

print(links)

G = nx.Graph()
for _, row in links.iterrows():
    G.add_edge(row['source'], row['target'], weight=row['weight'])

print(f"Succès ! Graphe créé avec {G.number_of_nodes()} nœuds.")


# net = Network(height='1000px', width='100%', bgcolor='#222222', font_color='white')
# net.from_nx(G)
# net.toggle_physics(True)
# net.write_html('legislative_graph.html')
# print("Visualisation générée : 'legislative_graph.html'")


pos = nx.spring_layout(G, k=0.5, seed=42)
plt.figure(figsize=(12, 12))
nx.draw_networkx_edges(G, pos, alpha=0.2, edge_color='gray')
nx.draw_networkx_nodes(G, pos, node_size=50, node_color='blue', alpha=0.7)
# nx.draw_networkx_labels(G, pos, font_size=8)
plt.title(f"Network Analysis of the Assembly (Threshold: {threshold})")
plt.axis('off')
output_path = "legislative_network.png"
plt.savefig(output_path, dpi=300, bbox_inches='tight', transparent=False)
plt.close()
