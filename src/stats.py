import matplotlib.pyplot as plt
import seaborn as sns # type: ignore

def plot_voter_distribution(df, theme_name, output_path):
    """
    Génère un histogramme de la participation (nombre de votants par scrutin).
    """
    voters_per_scrutin = df.groupby('scrutin_id')['depute'].nunique()
    
    plt.figure(figsize=(10, 6))
    sns.histplot(voters_per_scrutin, bins=30, kde=True, color='skyblue')
    
    plt.title(f"Distribution de la participation : {theme_name}")
    plt.xlabel("Nombre de votants")
    plt.ylabel("Nombre de scrutins")
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    
    plt.savefig(output_path)
    plt.close()
    print(f"Graphique de distribution sauvegardé : {output_path}")

    print(f"\nStats de participation pour {theme_name} :")
    print(voters_per_scrutin.describe())

def analyze_attendance(df, theme_name, top_n=10):
    """
    Calcule et affiche les stats de présence/absence par député et par groupe.
    """
    total_scrutins = df['scrutin_id'].nunique()
    
    att = df.groupby(['depute', 'groupe']).size().reset_index(name='presences')
    att['absences'] = total_scrutins - att['presences']
    att['taux_presence_pct'] = (att['presences'] / total_scrutins) * 100

    print(f"\n--- STATS D'ASSIDUITÉ : {theme_name} ({total_scrutins} scrutins) ---")

    print(f"\nTOP {top_n} DES PLUS PRÉSENTS :")
    print(att.sort_values(by='presences', ascending=False).head(top_n)[['depute', 'groupe', 'presences']])

    print(f"\nTOP {top_n} DES PLUS ABSENTS :")
    print(att.sort_values(by='absences', ascending=False).head(top_n)[['depute', 'groupe', 'absences']])

    group_stats = att.groupby('groupe').agg({
        'depute': 'count',
        'presences': 'mean',
        'taux_presence_pct': 'mean'
    }).rename(columns={'depute': 'nb_deputes', 'presences': 'moyenne_presences'})

    print(f"\nSTATS PAR GROUPE (Moyenne du taux de présence) :")
    print(group_stats.sort_values(by='taux_presence_pct', ascending=False))
    
    return att, group_stats