import requests
import xml.etree.ElementTree as ET
from pathlib import Path

URL = "https://www.nosdeputes.fr/{legislature}/scrutins/xml"

THEMATIQUES = {
    "Solidarité & Social": [
        "pauvreté", "handicap", "retraite", "social", "précarité", "apl", 
        "famille", "prestations", "rsa", "solidarité", "chômage"
    ],
    "Écologie & Territoires": [
        "écologie", "environnement", "climat", "nucléaire", "énergie", "biodiversité", 
        "eau", "agriculture", "agricole", "pesticide", "rural", "transport"
    ],
    "Économie & État": [
        "économie", "fiscal", "impôt", "inflation", 
        "douanes", "entreprises", "croissance"
    ],
    "Sécurité & International": [
        "justice", "sécurité", "police", "prison", "immigration", 
        "étranger", "asile", "frontière", "armée", "défense", "europe"
    ]
}

def classifier_titre(titre):
    titre_clean = titre.lower()
    for categorie, mots_cles in THEMATIQUES.items():
        if any(mot in titre_clean for mot in mots_cles):
            return categorie
    return "Autres / Divers"


def get_scrutins_by_theme(legislature=16):
    """Retourne un dict {theme: [ids]}.

    Pour la 14e législature, le flux distant n'est pas utilisable — on lit
    le fichier local `Data/scrutins.xml` et on applique les mêmes mots-clés.
    Pour les autres législatures, on conserve l'accès distant comme avant.
    """
    themes_map = {theme: [] for theme in THEMATIQUES.keys()}

    if int(legislature) == 14:
        local_path = Path(__file__).resolve().parents[1] / 'Data' / 'scrutins.xml'
        if not local_path.exists():
            raise FileNotFoundError(f"Fichier local attendu introuvable: {local_path}")

        tree = ET.parse(local_path)
        root = tree.getroot()
    else:
        url = URL.format(legislature=legislature)
        response = requests.get(url)
        response.raise_for_status()
        root = ET.fromstring(response.content)

    for s in root.findall('scrutin'):
        num_el = s.find('numero')
        titre_el = s.find('titre')
        if num_el is None or titre_el is None or titre_el.text is None:
            continue

        try:
            id_scrutin = int(num_el.text)
        except Exception:
            continue

        titre = titre_el.text.lower()

        matched = False
        for theme, mots in THEMATIQUES.items():
            if any(mot in titre for mot in mots):
                themes_map[theme].append(id_scrutin)
                matched = True
                break

    return themes_map

themes_map = get_scrutins_by_theme()
print("Nombre de scrutins par thème :")
for theme, ids in themes_map.items():
    print(f"  {theme}: {len(ids)} scrutins")

def main():
    print(f"Connexion à l'API NosDéputés.fr...")
    try:
        response = requests.get(URL)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        scrutins_xml = root.findall('scrutin')

        data_par_theme = {theme: [] for theme in THEMATIQUES.keys()}
        data_par_theme["Autres / Divers"] = []

        for s in scrutins_xml:
            info = {
                "numero": s.find('numero').text,
                "titre": s.find('titre').text,
                "sort": s.find('sort').text,
                "date": s.find('date').text
            }
            theme = classifier_titre(info["titre"])
            data_par_theme[theme].append(info)

        print("\n=== RÉSUMÉ DES SCRUTINS PAR THÉMATIQUE ===")
        themes_list = list(data_par_theme.keys())
        for i, theme in enumerate(themes_list, 1):
            count = len(data_par_theme[theme])
            print(f"{i}. {theme:<20} : {count} scrutins")

        while True:
            choix = input("\nEntrez le numéro d'un thème pour voir le détail (ou 'q' pour quitter) : ")
            if choix.lower() == 'q':
                break
            
            try:
                idx = int(choix) - 1
                theme_choisi = themes_list[idx]
                scrutins_du_theme = data_par_theme[theme_choisi]

                print(f"\n--- Détails pour : {theme_choisi} ({len(scrutins_du_theme)} résultats) ---")
                for s in scrutins_du_theme:
                    print(f"[{s['numero']}] ({s['date']}) - {s['sort'].upper()}")
                    print(f"Titre : {s['titre']}\n{'-'*40}")
            except (ValueError, IndexError):
                print("Choix invalide, veuillez entrer un nombre de la liste.")

    except Exception as e:
        print(f"Erreur : {e}")


if __name__ == "__main__":
    main()