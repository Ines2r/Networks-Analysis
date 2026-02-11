import xml.etree.ElementTree as ET
import unicodedata
import csv
import os


def slugify(name: str) -> str:
    if not name:
        return ""
    name = unicodedata.normalize('NFKD', name)
    name = ''.join([c for c in name if not unicodedata.combining(c)])
    name = name.strip().lower()
    name = name.replace('_', ' ')
    cleaned = []
    for c in name:
        if c.isalnum() or c in [' ', '-']:
            cleaned.append(c)
    s = ''.join(cleaned)
    s = s.replace(' ', '-')
    while '--' in s:
        s = s.replace('--', '-')
    return s


def parse_table_noms(path):
    tree = ET.parse(path)
    root = tree.getroot()

    organ_map = {}
    for org in root.findall('.//organe'):
        type_attr = None
        for k, v in org.attrib.items():
            if k.endswith('type'):
                type_attr = v
                break

        if type_attr == 'GroupePolitique_type':
            uid_el = org.find('uid')
            abbrev_el = org.find('libelleAbrege')
            if uid_el is not None and uid_el.text:
                uid = uid_el.text.strip()
                abbrev = abbrev_el.text.strip() if (abbrev_el is not None and abbrev_el.text) else uid
                organ_map[uid] = abbrev

    actor_map = {}
    for actor in root.findall('.//acteur'):
        uid_el = actor.find('uid')
        if uid_el is None or not uid_el.text:
            continue
        uid = uid_el.text.strip()
        prenom_el = actor.find('./etatCivil/ident/prenom')
        nom_el = actor.find('./etatCivil/ident/nom')
        prenom = prenom_el.text.strip() if (prenom_el is not None and prenom_el.text) else ''
        nom = nom_el.text.strip() if (nom_el is not None and nom_el.text) else ''
        actor_map[uid] = {'prenom': prenom, 'nom': nom}

    return organ_map, actor_map


def build_dataset(scrutins_path, table_noms_path, out_path):
    print('Parsing noms (peut prendre quelques secondes)...')
    organ_map, actor_map = parse_table_noms(table_noms_path)

    rows = []
    print('Parcours des scrutins...')
    context = ET.iterparse(scrutins_path, events=('end',))
    for event, elem in context:
        if elem.tag == 'scrutin':
            numero_el = elem.find('numero')
            scrutin_id = numero_el.text.strip() if (numero_el is not None and numero_el.text) else None

            for groupe in elem.findall('.//groupes/groupe'):
                org_ref_el = groupe.find('organeRef')
                if org_ref_el is None or not org_ref_el.text:
                    continue
                org_ref = org_ref_el.text.strip()
                groupe_acro = organ_map.get(org_ref, org_ref)

                vote = groupe.find('vote')
                if vote is None:
                    continue
                decomp = vote.find('decompteNominatif')
                if decomp is None:
                    continue

                for pos_block in list(decomp):
                    tag = pos_block.tag.lower()
                    if 'pour' in tag:
                        position = 'pour'
                    elif 'contre' in tag:
                        position = 'contre'
                    elif 'abst' in tag:
                        position = 'abstention'
                    else:
                        continue

                    for votant in pos_block.findall('votant'):
                        acteur_el = votant.find('acteurRef')
                        if acteur_el is None or not acteur_el.text:
                            continue
                        pa = acteur_el.text.strip()
                        actor = actor_map.get(pa)
                        if actor:
                            name = f"{actor['prenom']} {actor['nom']}".strip()
                            depute = slugify(name)
                        else:
                            depute = pa.lower()

                        rows.append((depute, groupe_acro, position, scrutin_id))

            elem.clear()

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    print(f'Ecriture de {out_path} ({len(rows)} lignes)')
    with open(out_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['depute', 'groupe', 'position', 'scrutin_id'])
        for r in rows:
            writer.writerow(r)


if __name__ == '__main__':
    scrutins_path = os.path.join('Data', 'scrutins.xml')
    table_noms_path = os.path.join('Data', 'table_noms.xml')
    out_path = os.path.join('Output', '2012-2017', 'dataset_scrutins_14.csv')
    build_dataset(scrutins_path, table_noms_path, out_path)
