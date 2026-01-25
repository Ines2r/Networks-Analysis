import requests
import xml.etree.ElementTree as ET
import pandas as pd
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

class ScrutinFetcher:
    def __init__(self, legislature):
        self.base_url = f"https://www.nosdeputes.fr/{legislature}/scrutin"

    def get_scrutin_data(self, scrutin_id):
        url = f"{self.base_url}/{scrutin_id}/xml"
        try:
            response = requests.get(url, timeout=10)
            
            if response.status_code != 200 or not response.content:
                return None

            root = ET.fromstring(response.content)
            
            first_vote = root.find('vote')
            if first_vote is None:
                return None

            votes_list = []
            for vote in root.findall('vote'):
                votes_list.append({
                    'depute': vote.find('parlementaire_slug').text,
                    'groupe': vote.find('parlementaire_groupe_acronyme').text,
                    'position': vote.find('position').text,
                    'scrutin_id': scrutin_id
                })
            return pd.DataFrame(votes_list)
            
        except (requests.exceptions.RequestException, ET.ParseError):
            return None



def download(legislature, workers=10):
    fetcher = ScrutinFetcher(legislature=legislature)
    all_data = []
    scrutin_id_start = 1
    chunk_size = 100
    stop_searching = False
    
    print(f"Exploration rapide de la législature {legislature}...")

    while not stop_searching:
        current_chunk_ids = range(scrutin_id_start, scrutin_id_start + chunk_size)
        print(f"Analyse du bloc {scrutin_id_start} à {scrutin_id_start + chunk_size}...")
        
        chunk_results = []
        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_id = {executor.submit(fetcher.get_scrutin_data, i): i for i in current_chunk_ids}
            for future in as_completed(future_to_id):
                res = future.result()
                if res is not None:
                    chunk_results.append(res)
        
        if not chunk_results:
            print("Aucun scrutin trouvé dans ce bloc. Fin de la législature atteinte.")
            stop_searching = True
        else:
            all_data.extend(chunk_results)
            scrutin_id_start += chunk_size

    return pd.concat(all_data, ignore_index=True)