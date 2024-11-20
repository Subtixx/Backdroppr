from config import Config
from generic_api import GenericApi
from pyarr import RadarrAPI 
class RadarrApi(GenericApi):
    
    def __init__(self, config:Config):
        self.__init__(config.radarr_host, config.radarr_key)
        
    def get(self):
        pass
  