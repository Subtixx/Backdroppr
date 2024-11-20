class Movie:
    tmdb_id: int = None
    title: str = None
    path: str = None
    year: int|str = None
    trailer_url: str = None
    trailer_path: str = None
    
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            
    def __str__(self):
        return f"{self.title} ({self.year})"    
    