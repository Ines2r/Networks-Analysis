import numpy as np

LEGIS_MAP = {
    13: "2007-2012",
    14: "2012-2017",
    15: "2017-2022",
    16: "2022-2024",
    17: "2024-2026"
}

MAP_VOTE = {
    'pour': 1, 
    'contre': -1, 
    'abstention': 0,
    'nonVotant': np.nan
}

PARTY_COLORS = {
    # --- 16ème et 15ème ---
    'ECOLO': '#2ecc71',      # Vert
    'Écolo': '#2ecc71',
    'LFI-NUPES': '#e74c3c',  # Rouge
    'LFI': '#e74c3c',        # Rouge
    'GDR-NUPES': '#c0392b',  # Rouge foncé
    'GDR': '#c0392b',        # Rouge foncé

    'REN': '#f1c40f',        # Jaune (Renaissance)
    'LREM': '#f1c40f',       # Jaune (Renaissance)

    'UAI': '#f39c12',        # Orange-jaune (Union des indépendants et apparentés)
    'AGIR-E': "#7cdaff",     # Bleu clair (Agir ensemble, centre droit pro-majorité)

    'RN': '#2564a4',         # Bleu marine
    'LR': '#3498db',         # Bleu
    'LC': '#00adff',         # Bleu clair (Les Constructifs)

    'SOC-A': '#e84393',      # Rose (Socialistes et apparentés)
    'SOC': '#e84393',        # Rose (Socialistes)
    'NG': '#fd79a8',         # Rose clair (Nouvelle Gauche)

    'DEM': '#e67e22',        # Orange (MoDem)
    'MODEM': '#e67e22',      # Orange (MoDem)

    'UDI_I': '#d35400',      # Orange foncé (UDI et Indépendants)

    'HOR': '#8e44ad',        # Violet (Horizons)
    'LT': '#9b59b6',         # Violet clair (Libertés et Territoires)

    'LIOT': '#95a5a6',       # Gris
    'NI': '#bdc3c7',         # Gris clair

    'UMP': '#3498db',        # Bleu (Union pour un Mouvement Populaire - prédécesseur de LR)
    'Les Républicains': '#3498db', # Bleu (Nom adopté par l'UMP en 2015)
    'SRC': '#e84393',        # Rose (Socialiste, Républicain et Citoyen)
    'SER': '#e84393',        # Rose (Socialiste, Écologiste et Républicain - succède à SRC)
    'RRDP': '#e67e22',       # Orange (Radical, Républicain, Démocrate et Progressiste - centre-gauche)
    'UDI': '#d35400',        # Orange foncé (Union des démocrates et indépendants)
}

DEFAULT_COLOR = '#7f8c8d'