import requests
import xml.etree.ElementTree as ET
import pandas as pd

class ScrutinFetcher:
    def __init__(self, legislature=17):
        self.base_url = f"https://www.nosdeputes.fr/{legislature}/scrutin"

    def get_scrutin_data(self, scrutin_id):
        url = f"{self.base_url}/{scrutin_id}/xml"
        response = requests.get(url)
        
        if response.status_code != 200:
            print(f"Erreur lors de la récupération du scrutin {scrutin_id}")
            return None, None

        root = ET.fromstring(response.content)
        
        # 1. Extraire les infos générales du scrutin (depuis le premier tag vote)
        first_vote = root.find('vote')
        scrutin_info = {
            'numero': first_vote.find('scrutin/numero').text,
            'titre': first_vote.find('scrutin/titre').text,
            'date': first_vote.find('scrutin/date').text,
            'sort': first_vote.find('scrutin/sort').text
        }

        # 2. Extraire la liste des votes des parlementaires
        votes_list = []
        for vote in root.findall('vote'):
            votes_list.append({
                'depute': vote.find('parlementaire_slug').text,
                'groupe': vote.find('parlementaire_groupe_acronyme').text,
                'position': vote.find('position').text
            })
            
        return scrutin_info, pd.DataFrame(votes_list)


if __name__ == "__main__":
    fetcher = ScrutinFetcher(legislature=16) # 16ème législature par exemple
    info, df_votes = fetcher.get_scrutin_data(1)

    if info:
        print(f"ANALYSE DU SCRUTIN N°{info['numero']}")
        print(f"Sujet : {info['titre']}\n")
        print(df_votes.head(10))

def download_range(start_id, end_id):
    all_data = []
    fetcher = ScrutinFetcher(legislature=16)
    
    for i in range(start_id, end_id + 1):
        info, df = fetcher.get_scrutin_data(i)
        if df is not None:
            df['scrutin_id'] = i
            all_data.append(df)
    
    return pd.concat(all_data)

data_complete = download_range(1, 50) 
data_complete.to_csv("dataset_scrutins.csv")