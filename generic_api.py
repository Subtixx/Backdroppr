class GenericApi:
    trailer_downloader = None
    host = None
    key = None
    
    def __init__(self, trailer_downloader, host, key):
        self.trailer_downloader = trailer_downloader
        self.host = host
        self.key = key
    
    def get_movies(self):
        pass
    
    def get_series(self):
        pass
        
    # Virtual method
    def get(self):
        pass
