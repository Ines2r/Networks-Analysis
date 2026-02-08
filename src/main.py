import pandas as pd
import os
from src.fetcher import ScrutinFetcher, download
from src.similarity import compute_similarity, MAP_VOTE, filter_by_voters
from src.distribution import generate_distrib_plot
from src.graph import generate_graph, generate_pca_plot
from src.config import LEGIS_MAP
from src.properties import compute_graph_metrics, print_report
from src.classification import get_scrutins_by_theme


import pandas as pd


def run_full_pipeline(legislature, method, k_neighbors, min_voters, theme_name="Global", target_ids=None):
    years = LEGIS_MAP.get(legislature, f"legis_{legislature}")

    theme_slug = theme_name.replace(" ", "_").replace("&", "et")
    output_dir = os.path.join("Output", years)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Dossier créé : \"{output_dir}\"")

    csv_path = os.path.join("Output", years, f"dataset_scrutins_{legislature}.csv")
    
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
    else:
        os.makedirs(os.path.join("Output", years), exist_ok=True)
        df = download(legislature=legislature, workers=10)   
        df.to_csv(csv_path, index=False)

    if target_ids is not None:
        initial_count = df['scrutin_id'].nunique()
        df = df[df['scrutin_id'].isin(target_ids)]
        print(f"Thème {theme_name} : {df['scrutin_id'].nunique()} scrutins conservés sur {initial_count}")

    if df.empty:
        print(f"Aucun vote trouvé pour le thème {theme_name}. Passage au suivant.")
        return

    df = filter_by_voters(df, min_voters)
    df['vote_val'] = df['position'].map(MAP_VOTE)
    
    pivot_votes = df.pivot_table(index='depute', columns='scrutin_id', values='vote_val')

    pca_output = os.path.join(output_dir, f"pca_{theme_name.replace(' ', '_')}.png")
    generate_pca_plot(pivot_votes, df, pca_output, theme_name)
    print(f"ACP générée : {pca_output}")

    if theme_name=="Global":


        generate_distrib_plot(df, legislature, output_path=os.path.join(os.path.join("Output", years), f"distribution.png"))

        print(pivot_votes.describe())

        sim_matrix = compute_similarity(pivot_votes, method=method)

        G = generate_graph(sim_matrix, df, legislature, k_neighbors, min_voters, 
                        output_path=os.path.join(output_dir, f"network_{method}.png"))
        

        print(f"\nStats pour {theme_name} ({method}):")
        print(sim_matrix.describe())

        report = compute_graph_metrics(G, df, top_n=10)
        print_report(report, legislature)

if __name__ == "__main__":

    for legislature in [15, 16]:
        print(f"\n{'='*60}")
        print(f" RAPPORT D'ANALYSE : LÉGISLATURE {legislature}")
        print(f"{'='*60}")

        dict_themes = get_scrutins_by_theme(legislature=legislature)

        for method in ['cosine']:
                run_full_pipeline(
                    legislature=legislature, 
                    method=method, 
                    k_neighbors=5, 
                    min_voters=0,
                    theme_name='Global',
                    target_ids=None
                )

        for theme_name, ids in dict_themes.items():
            
            if not ids: continue
            
            print(f"\n{'-'*60}")
            print(f" FOCUS THÉMATIQUE : {theme_name}")
            print(f"{'-'*60}")

            for method in ['cosine']:
                run_full_pipeline(
                    legislature=legislature, 
                    method=method, 
                    k_neighbors=5, 
                    min_voters=0,
                    theme_name=theme_name,
                    target_ids=ids
                )