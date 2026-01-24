import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

df = pd.read_csv("dataset_scrutins.csv")

map_vote = {'pour': 1, 'contre': -1, 'abstention': 0, 'nonVotant': 0}
df['vote_val'] = df['position'].map(map_vote)

pivot_votes = df.pivot_table(index='depute', columns='scrutin_id', values='vote_val').fillna(0)

#print(pivot_votes)

def compute_similarity(pivot_df, method='cosine'):
    if method == 'cosine':
        sim_matrix = cosine_similarity(pivot_df)
        sim_df = pd.DataFrame(sim_matrix, index=pivot_df.index, columns=pivot_df.index)
    
    elif method == 'agreement':
        sim_df = pd.DataFrame(index=pivot_df.index, columns=pivot_df.index)
        for i in pivot_df.index:
            matches = (pivot_df.loc[i] == pivot_df).sum(axis=1) / pivot_df.shape[1]
            sim_df.loc[i] = matches
            
    return sim_df

# --- Exécution ---
sim_matrix = compute_similarity(pivot_votes, method='cosine')
print(sim_matrix)
print(sim_matrix['adrien-quatennens'].sort_values(ascending=False).head(10))

#sim_matrix = compute_similarity(pivot_votes, method='agreement')
#print(sim_matrix['adrien-quatennens'].sort_values(ascending=False).head(10))