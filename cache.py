import os
import json
import logging

from movie import Movie

class Cache:
    trailer_cache = {}
    movie_cache:list[Movie] = []
    series_cache = {}
    
    def __init__(self):
        pass
        
    def load_cache(self):
        if not os.path.isdir('cache'):
            logging.warning("Cache directory not found. Creating...")
            os.mkdir('cache')
            return True
        
        if os.path.isfile('cache/trailers.json'):
            with open('cache/trailers.json', 'r') as f:
                self.trailer_cache = json.load(f)
        
        self.load_movie_cache()
        
        if os.path.isfile('cache/series.json'):
            with open('cache/series.json', 'r') as f:
                self.series_cache = json.load(f)
        
        logging.info("Cache loaded.")
        
    def load_movie_cache(self):
        if not os.path.isfile('cache/movies.json'):
            return
        
        # should be a list of Movie objects
        with open('cache/movies.json', 'r') as f:
            movie_cache_file = json.load(f)
        
            for movie in movie_cache_file:
                self.movie_cache.append(Movie(**movie))
        
    def save_cache(self):
        with open('cache/trailers.json', 'w') as f:
            json.dump(self.trailer_cache, f)
        
        with open('cache/movies.json', 'w') as f:
            json.dump(self.movie_cache, f, default=vars)
        
        with open('cache/series.json', 'w') as f:
            json.dump(self.series_cache, f)
        
        logging.info("Cache saved.")
        
    def has_movie(self, movie_path:str) -> bool:
        return any(movie.path == movie_path for movie in self.movie_cache)
    
    def add_movie(self, movie:Movie):
        self.movie_cache.append(movie)
        
    def update_movie(self, movie:Movie):
        if self.has_movie(movie.path):
            self.movie_cache.remove(self.get_movie(movie.path))
        self.movie_cache.append(movie)
        
    def get_movie(self, movie_path:str) -> Movie:
        return next((movie for movie in self.movie_cache if movie.path == movie_path), None)
        
    def clear_cache(self):
        self.trailer_cache = {}
        self.movie_cache = []
        self.series_cache = {}