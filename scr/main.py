import pandas as pd
from fetcher import ScrutinFetcher, download
from similarity import compute_similarity, MAP_VOTE, filter_by_voters
from distribution import generate_distrib_plot
from graph import generate_graph
from config import LEGIS_MAP
import os
from properties import compute_graph_metrics, print_report

def run_full_pipeline(legislature, method, k_neighbors, min_voters):

    years = LEGIS_MAP.get(legislature, f"legis_{legislature}")
    output_dir = os.path.join("Output", years)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"The folder \"{output_dir}\" was created.")

    csv_path = os.path.join(output_dir, f"dataset_scrutins_{legislature}.csv")
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
    else:
        df = download(legislature=legislature, workers=10)   
        df.to_csv(csv_path, index=False)

    df = filter_by_voters(df, min_voters)

    df['vote_val'] = df['position'].map(MAP_VOTE)
    pivot_votes = df.pivot_table(index='depute', columns='scrutin_id', values='vote_val').fillna(0)

    sim_matrix = compute_similarity(pivot_votes, method=method)

    G = generate_graph(sim_matrix, df, legislature, k_neighbors, min_voters, output_path=os.path.join(output_dir, f"network_{method}.png"))
    generate_distrib_plot(df, legislature, output_path=os.path.join(output_dir, f"distribution.png"))

    report = compute_graph_metrics(G, df, top_n=10)
    print_report(report, legislature)

if __name__ == "__main__":
    # 2007-2012 = 13 | 2012-2017 = 14 | 2017-2022 = 15 | 2022-2024 = 16 | 2024-2026 = 17
    for legislature in [15, 16]:
        print(f"\n{'='*60}")
        print(f" RAPPORT D'ANALYSE : LÉGISLATURE {legislature}")
        print(f"{'='*60}")
        for method in ['cosine', 'agreement_weighted']:
            print(f"\n{'-'*60}")
            print(f" Mesure de similarité {method}")
            print(f"{'-'*60}")
            run_full_pipeline(legislature=legislature, method=method, k_neighbors=15, min_voters=10)


# ================================================

# Se focaliser sur cosine vs agreement weighted
# Se focaliser sur k et min_voters
# Propriétés statistiques des graphes


# Premières analyses :
# - k = 10 | min = 500 : les scrutins très importants sont gardés.
#   Les députés votent selon leur famille politique (des petites familles)
#   On observe des clusters par famille

# - k = 10 | min = 10 : on garde tous les scrutins (même les sujets techniques)
#   Les consignes de vote sont moins nettes, les députés sont plus "libres"
#   On voit des clusters un peu plus larges apparaitre, des coalitions, des députés pivots etc

# - k = 15 | min = 10
# - k = 10 | min = 10
# - k =  5 | min = 10
#  Les résultats sonnt un peu différents

# ================================================


# degré pondéré : Top 5 des députés les plus connectés
# analyse globale - groupe : pareil mais en ne gardant qu'un député par parti
# analyse intra-groupe : pour chaque groupe, qui est le député le plus connecté à l'intérieur de son groupe

#   X | victor-xxx (7.1) | victor-xxx (7.1)
#   Interpretation score global / intra : le groupe X ne rayonne pas à l'extérieur
# Top 5 des piliers : évolue entre L15 et L16 : nvx groupes dedans : la majorité perd du terrain
# Lorsque le député global != député intra : différence de préférence entre en interne et externe
