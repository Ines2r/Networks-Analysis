import pandas as pd
import matplotlib.pyplot as plt
from config import PARTY_COLORS, DEFAULT_COLOR

df = pd.read_csv("dataset_scrutins.csv")

df_unique_deputes = df.groupby('depute')['groupe'].last().reset_index()

group_counts = df_unique_deputes['groupe'].value_counts()

colors = [PARTY_COLORS.get(g, DEFAULT_COLOR) for g in group_counts.index]

plt.figure(figsize=(12, 7))
bars = plt.bar(group_counts.index, group_counts.values, color=colors, edgecolor='black', alpha=0.8)

for bar in bars:
    yval = bar.get_height()
    plt.text(bar.get_x() + bar.get_width()/2, yval + 2, yval, ha='center', va='bottom', fontweight='bold')

plt.title("Répartition des députés par groupe parlementaire (Législature 16)", fontsize=14)
plt.ylabel("Nombre de députés")
plt.xlabel("Groupes Parlementaires")
plt.grid(axis='y', linestyle='--', alpha=0.7)

# Sauvegarder
plt.savefig("repartition_groupes.png", dpi=300, bbox_inches='tight')
print("Graphique de répartition sauvegardé sous 'repartition_groupes.png'")
plt.show()