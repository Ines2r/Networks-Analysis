import networkx as nx
import pandas as pd
import matplotlib.pyplot as plt
from src.config import PARTY_COLORS, DEFAULT_COLOR, MAP_VOTE
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

def generate_graph(sim_matrix, df_meta, legislature, k_neighbors=10, min_voters=10, output_path="graph.png"):
    """
    Génère un graphe de réseau basé sur les k plus proches voisins (k-NN).
    """
    G = nx.Graph()

    depute_to_group = df_meta.set_index('depute')['groupe'].to_dict()

    print(f"Construction du graphe (k={k_neighbors})...")
    for depute in sim_matrix.index:
        similarities = sim_matrix.loc[depute].drop(labels=[depute])
        
        top_k = similarities.nlargest(k_neighbors)
        
        for neighbor, weight in top_k.items():
            if weight > 0:
                G.add_edge(depute, neighbor, weight=weight)

    node_colors = []
    nodes_to_remove = []
    
    for node in G.nodes():
        group = depute_to_group.get(node, "NI")
        node_colors.append(PARTY_COLORS.get(group, '#808080'))

    plt.figure(figsize=(15, 12))
    pos = nx.spring_layout(G, k=0.15, iterations=50, weight='weight')

    nx.draw_networkx_edges(G, pos, alpha=0.1, edge_color='gray')
    
    nx.draw_networkx_nodes(G, pos, 
                           node_size=50, 
                           node_color=node_colors, 
                           alpha=0.8)

    plt.title(f"Réseau des Députés - Législature {legislature}\n(k-NN cosine, k={k_neighbors})", fontsize=15)
    plt.axis('off')
    
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    return G


def generate_pca_plot(pivot_votes, df, output_path, theme_name):

    data_clean = pivot_votes.fillna(0)
    
    scaled_data = StandardScaler().fit_transform(data_clean)
    
    pca = PCA(n_components=2)
    coords = pca.fit_transform(scaled_data)
    
    df_pca = pd.DataFrame(coords, columns=['PC1', 'PC2'], index=data_clean.index).reset_index()
    
    meta = df[['depute', 'groupe']].drop_duplicates()
    df_pca = df_pca.merge(meta, on='depute', how='left')
    
    plt.figure(figsize=(12, 8))
    
    for groupe in df_pca['groupe'].unique():
        mask = df_pca['groupe'] == groupe
        
        couleur = PARTY_COLORS.get(groupe, '#808080')
        
        plt.scatter(
            df_pca.loc[mask, 'PC1'], 
            df_pca.loc[mask, 'PC2'], 
            label=groupe, 
            color=couleur,
            alpha=0.7,
            edgecolors='white',
            linewidths=0.5,
            s=40
        )

    var_exp = pca.explained_variance_ratio_
    
    plt.title(f"Analyse en Composantes Principales - Thème : {theme_name}", fontsize=14)
    plt.xlabel(f"PC1 : Clivage principal ({var_exp[0]:.1%} de variance)", fontsize=11)
    plt.ylabel(f"PC2 : Clivage secondaire ({var_exp[1]:.1%} de variance)", fontsize=11)
    
    plt.legend(title="Groupes Politiques", bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.grid(True, linestyle='--', alpha=0.3)
    plt.axhline(0, color='black', linewidth=0.8, alpha=0.5)
    plt.axvline(0, color='black', linewidth=0.8, alpha=0.5)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()

