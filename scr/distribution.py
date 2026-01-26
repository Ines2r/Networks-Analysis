import pandas as pd
import matplotlib.pyplot as plt
from config import PARTY_COLORS, DEFAULT_COLOR

def generate_distrib_plot(df, legislature, output_path="distribution.png"):

    df_unique_deputes = df.groupby('depute')['groupe'].last().reset_index()

    group_counts = df_unique_deputes['groupe'].value_counts()

    colors = [PARTY_COLORS.get(g, DEFAULT_COLOR) for g in group_counts.index]

    plt.figure(figsize=(12, 7))
    bars = plt.bar(group_counts.index, group_counts.values, color=colors, edgecolor='black', alpha=0.8)

    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2, yval + 2, yval, ha='center', va='bottom', fontweight='bold')

    plt.title(f"Répartition des députés par groupe parlementaire (Législature {legislature})", fontsize=14)
    plt.ylabel("Nombre de députés")
    plt.xlabel("Groupes Parlementaires")
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()