import os
import yaml
import logging
from movie_config import MovieConfig
from series_config import SeriesConfig

class Config:
    tmdb_key = None
    tmdb_language = None
    tmdb_region = None
    
    min_length = 30
    max_length = 300
    
    movie_config:MovieConfig = None
    tv_config:SeriesConfig = None
    
    jellyfin_host = None
    jellyfin_key = None
    radarr_host = None
    radarr_key = None
    sonarr_host = None
    sonarr_key = None
    
    # download config
    skip_intros = True
    
    _loaded_config = None
    
    def __init__(self):
        self.tmdb_key = os.getenv('TMDB_KEY')
        self.tmdb_language = os.getenv('TMDB_LANGUAGE')
        self.tmdb_region = os.getenv('TMDB_REGION')
        
        self.min_length = os.getenv('MIN_LENGTH')
        self.max_length = os.getenv('MAX_LENGTH')
        
        self.jellyfin_host = os.getenv('JELLYFIN_HOST')
        self.jellyfin_key = os.getenv('JELLYFIN_KEY')
        
        self.radarr_host = os.getenv('RADARR_HOST')
        self.radarr_key = os.getenv('RADARR_KEY')
        
        self.sonarr_host = os.getenv('SONARR_HOST')
        self.sonarr_key = os.getenv('SONARR_KEY')
        
        self.skip_intros = os.getenv('SKIP_INTROS')
        
        self.movie_config = MovieConfig()
        self.tv_config = SeriesConfig()
    
    def load_config(self):
        if not os.path.isdir('config'):
            logging.warning("Config directory not found.")
            return True
        
        if not os.path.isfile('config/config.yml'):
            if self.tmdb_key is None and (self.jellyfin_key is None and self.radarr_key is None and self.sonarr_key is None):
                logging.error("Config file not found and missing required values.")
                return False
            return True
        
        try:
            with open('config/config.yml', 'r') as f:
                self._loaded_config = yaml.load(f, Loader=yaml.Loader)
                logging.info("Config loaded.")
                
                self.movie_config = MovieConfig(self._loaded_config['movie'])
                self.tv_config = SeriesConfig(self._loaded_config['tv'])
                
                if self.skip_intros is None and 'skip_intros' in self._loaded_config:
                    self.skip_intros = self._loaded_config['skip_intros']
                
                if self.tmdb_key is None and 'tmdb_api' in self._loaded_config:
                    self.tmdb_key = self._loaded_config['tmdb_api']
                    
                if self.tmdb_language is None and 'tmdb_language' in self._loaded_config:
                    self.tmdb_language = self._loaded_config['tmdb_language']
                    
                if self.tmdb_region is None and 'tmdb_region' in self._loaded_config:
                    self.tmdb_region = self._loaded_config['tmdb_region']
                    
                if self.min_length is None and 'min_length' in self._loaded_config:
                    self.min_length = self._loaded_config['min_length']
                    
                if self.max_length is None and 'max_length' in self._loaded_config:
                    self.max_length = self._loaded_config['max_length']
                
                if self.jellyfin_key is None and 'jellyfin_api' in self._loaded_config:
                    self.jellyfin_key = self._loaded_config['jellyfin_api']
                
                if self.radarr_host is None and 'radarr_host' in self._loaded_config:
                    self.radarr_host = self._loaded_config['radarr_host']
                
                if self.radarr_key is None and 'radarr_api' in self._loaded_config:
                    self.radarr_key = self._loaded_config['radarr_api']
                
                if self.sonarr_host is None and 'sonarr_host' in self._loaded_config:
                    self.sonarr_host = self._loaded_config['sonarr_host']
                
                if self.sonarr_key is None and 'sonarr_api' in self._loaded_config:
                    self.sonarr_key = self._loaded_config['sonarr_api']
        except Exception as e:
            logging.error(f"Failed to load config. {e}")
        return True
