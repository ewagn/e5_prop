import requests
import pandas as pd
import time

class GetData(object):
    def __init__(self, url) -> None:
        self.url = url

    def __call__(self):
        try:
            start_time = time.time()
            response = requests.get(self.url, timeout=5)  # ajout d'un timeout
            response.raise_for_status()
            api_response_time = time.time() - start_time
            if api_response_time > 5:  # Seuil d'alerte pour le temps de réponse de l'API
                from app import app
                app.logger.warning(f"Temps de réponse de l'API élevé: {api_response_time}s")
            self.data = response.json()
        except requests.RequestException as e:
            from app import app
            app.logger.error(f"Erreur lors de la récupération des données de l'API: {e}")
            raise

        res_df = pd.DataFrame({})
        for data_dict in self.data:
            # Tout le bloc n'était pas correctement indenté donc une erreur d'entré de corrigé
            temp_df = self.processing_one_point(data_dict)
            res_df = pd.concat([res_df, temp_df])
            res_df = res_df[res_df.traffic != 'unknown']
            # Le crochet ici n'était pas fermé donc une autre erreur
        return res_df

    def processing_one_point(self, data_dict: dict):
        temp = pd.DataFrame({key:[data_dict[key]] for key in ['datetime', 'trafficstatus', 'geo_point_2d', 'averagevehiclespeed', 'traveltime', 'trafficstatus']})
        temp = temp.rename(columns={'trafficstatus':'traffic'})
        temp['lat'] = temp.geo_point_2d.map(lambda x : x['lat'])
        temp['lon'] = temp.geo_point_2d.map(lambda x : x['lon'])
        # Les nom des colonnes de longitude et lattitude n'était adapté au dataset
        del temp['geo_point_2d']
        return temp