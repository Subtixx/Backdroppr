import os

import requests
from config import Config
from generic_api import GenericApi
from jellyfin_apiclient_python import JellyfinClient

from movie import Movie

def get_user_id(jellyfin_host, jellyfin_key):
    url = f"{jellyfin_host}/Users"
    headers = {
        'Accept': 'application/json',
        'X-Emby-Token': jellyfin_key}
    user_data = requests.request("GET", url, headers=headers, verify=False)
    for user in user_data.json():
        return user['Id']

class JellyfinApi(GenericApi):
    client: JellyfinClient = None
    
    def __init__(self, trailer_downloader, config:Config):
        super().__init__(trailer_downloader, config.jellyfin_host, config.jellyfin_key)
        
        self.client = JellyfinClient()
        self.client.config.data['app.name'] = 'TrailerDownloader'
        self.client.config.data['app.version'] = '0.1'
        self.client.config.data['auth.ssl'] = False
        self.client.authenticate({"Servers": [
            {"AccessToken": config.jellyfin_key, "address": config.jellyfin_host,
             "DateLastAccessed": 0, "UserId": get_user_id(config.jellyfin_host, config.jellyfin_key)}]}, discover=False)
    
    def get_movies(self):
        #results = self.client.jellyfin.get_suggestion()
        results = self.client.jellyfin.get_recommendation(limit=100)
        
        movies = []
        for result in results[0]['Items']:
            if result['Type'] == 'Movie':
                movie = Movie()
                movie.title = result['Name']
                movie.year = result['ProductionYear']
                movie.path = result['Id']
                movies.append(movie)
                
        return movies
        
    def get(self):
        pass
   