from config import Config
from generic_api import GenericApi
from pyarr import SonarrAPI

class SonarrApi(GenericApi):
    
    def __init__(self, config:Config):
        self.__init__(config.sonarr_host, config.sonarr_key)
        
    def get(self):
        pass
