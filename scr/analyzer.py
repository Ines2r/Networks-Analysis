import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from config import MAP_VOTE
from sklearn.metrics import jaccard_score

def filter_by_voters(df, min_voters):
    """
    Ne conserve que les scrutins ayant reçu au moins 'min_voters' votes.
    """
    counts = df.groupby('scrutin_id')['depute'].count()
    valid_ids = counts[counts >= min_voters].index
    df_filtered = df[df['scrutin_id'].isin(valid_ids)].copy()
    print(f"Filtrage : {len(valid_ids)} scrutins conservés (seuil > {min_voters} votants).")
    return df_filtered

def compute_similarity(pivot_df, method='cosine'):
    if method == 'cosine':
        avg = pivot_df.mean(axis=1)
        filled_df = pivot_df.sub(avg, axis=0).fillna(0)
        sim_matrix = cosine_similarity(filled_df)
        return pd.DataFrame(sim_matrix, index=pivot_df.index, columns=pivot_df.index)

    elif method == 'correlation':
        return pivot_df.T.corr(method='pearson')

    elif method == 'jaccard':
        data = pivot_df.values
        n_deputes = data.shape[0]
        sim_matrix = np.eye(n_deputes) # Diagonale à 1

        for i in range(n_deputes):
            for j in range(i + 1, n_deputes):
                mask = ~np.isnan(data[i]) & ~np.isnan(data[j])
                if np.sum(mask) < 5:
                    score = 0
                else:
                    matches = np.sum(data[i][mask] == data[j][mask])
                    union = np.sum(~np.isnan(data[i]) | ~np.isnan(data[j]))
                    score = matches / union if union > 0 else 0
                
                sim_matrix[i, j] = sim_matrix[j, i] = score
        
        return pd.DataFrame(sim_matrix, index=pivot_df.index, columns=pivot_df.index)

    elif method == 'agreement_weighted':
        data = pivot_df.values 
        n_deputes = data.shape[0]
        sim_matrix = np.zeros((n_deputes, n_deputes))

        for i in range(n_deputes):
            for j in range(i, n_deputes):
                mask = ~np.isnan(data[i]) & ~np.isnan(data[j])
                presence_commune = np.sum(mask)
                
                if presence_commune < 5:
                    score = 0
                else:
                    accords = np.sum(data[i][mask] == data[j][mask])
                    score = accords / presence_commune
                
                sim_matrix[i, j] = sim_matrix[j, i] = score
        
        return pd.DataFrame(sim_matrix, index=pivot_df.index, columns=pivot_df.index)