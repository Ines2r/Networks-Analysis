import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from src.config import MAP_VOTE
from sklearn.metrics import jaccard_score

def filter_by_voters(df, min_voters):
    """
    Ne conserve que les scrutins ayant reçu au moins 'min_voters' votes.
    """
    counts = df.groupby('scrutin_id')['depute'].count()
    valid_ids = counts[counts >= min_voters].index
    df_filtered = df[df['scrutin_id'].isin(valid_ids)].copy()
    print(f"Filtrage des scrutins : {len(valid_ids)} scrutins analysés (plus de {min_voters} votants).")
    return df_filtered


def compute_similarity(pivot_df, method='cosine'):
    min_commun = 5

    if method == 'cosine':
        avg = pivot_df.mean(axis=1)
        filled_df = pivot_df.fillna(0)
        sim_matrix = cosine_similarity(filled_df)
        return pd.DataFrame(sim_matrix, index=pivot_df.index, columns=pivot_df.index)

    elif method == 'correlation':
        return pivot_df.T.corr(method='pearson')


    elif method == 'jaccard':
        data = pivot_df.values
        n_deputes = data.shape[0]
        sim_matrix = np.eye(n_deputes)

        for i in range(n_deputes):
            for j in range(i + 1, n_deputes):
                # Intersection : Ils ont voté la même chose ET les deux ont voté
                matches = np.sum((data[i] == data[j]) & ~np.isnan(data[i]) & ~np.isnan(data[j]))
                
                # Union : Nombre de scrutins où i OU j a voté
                union = np.sum(~np.isnan(data[i]) | ~np.isnan(data[j]))
                
                if union < min_commun:
                    score = 0
                else:
                    score = matches / union
                
                sim_matrix[i, j] = sim_matrix[j, i] = score
        
        return pd.DataFrame(sim_matrix, index=pivot_df.index, columns=pivot_df.index)


    elif method == 'agreement_weighted':
        data = pivot_df.values 
        n_deputes = data.shape[0]
        sim_matrix = np.eye(n_deputes)

        for i in range(n_deputes):
            for j in range(i + 1, n_deputes):
                # Masque : les deux députés ont voté ce scrutin
                mask = ~np.isnan(data[i]) & ~np.isnan(data[j])
                presence_commune = np.sum(mask)
                
                if presence_commune < min_commun:
                    score = 0
                else:
                    # Accords : votes identiques où les deux sont présents
                    accords = np.sum(data[i][mask] == data[j][mask])
                    score = accords / presence_commune
                
                sim_matrix[i, j] = sim_matrix[j, i] = score
        
        return pd.DataFrame(sim_matrix, index=pivot_df.index, columns=pivot_df.index)


if __name__ == "__main__":
    # Test rapide de la fonction de similarité
    data = {
        'S1': [1, 1],
        'S2': [-1, -1],
        'S3': [1, -1],
        'S4': [1, np.nan],
        'S5': [np.nan, 1],
        'S6': [np.nan, np.nan]
    }
    
    test_df = pd.DataFrame(data, index=['Depute_A', 'Depute_B'])
    
    print("=== MATRICE DE TEST ===")
    print(test_df)
    print("\n=== RÉSULTATS DES SIMILARITÉS ===")
    
    for m in ['cosine', 'correlation', 'jaccard', 'agreement_weighted']:
        res = compute_similarity(test_df, method=m)
        score = res.loc['Depute_A', 'Depute_B']
        print(f"{m:18} : {score:.4f}")