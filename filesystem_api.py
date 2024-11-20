import logging
import os

from config import Config
from generic_api import GenericApi
from movie import Movie

class FilesystemApi(GenericApi):
    video_formats = ['webm','mkv','flv','vob','ogv','ogg','rrc','gifv','mng','mov','avi','qt','wmv','yuv','rm','asf','amv','mp4','m4p','m4v','mpg','mp2','mpeg','mpe','mpv','m4v','svi','3gp','3g2','mxf','roq','nsv','flv','f4v','f4p','f4a','f4b','mod']
    
    movie_path: str = None
    tv_path: str = None    

    def __init__(self, trailer_downloader, config:Config):
        self.trailer_downloader = trailer_downloader
        self.tv_path = config.tv_config.path
        self.movie_path = config.movie_config.path
        
        
    def get_movies(self) -> list[Movie]:
        # enumerate files in directory
        movies = []
        for root, dirs, files in os.walk(self.movie_path):
            for file in files:
                if file.split('.')[-1] in self.video_formats:
                    movie = Movie()
                    movie.title = file.split('.')[0]
                    movie.path = os.path.join(root, file)
                    movies.append(movie)
                    logging.info(f"FilesytemApi found movie: {movie.title} at {movie.path}")
        
        # check if file is in cache
        for movie in movies:
            if not self.trailer_downloader.cache.has_movie(movie.path):
                logging.warning(f"Movie not found in cache: {movie.path}")
                self.trailer_downloader.cache.add_movie(movie)
                continue
            cached_movie = self.trailer_downloader.cache.get_movie(movie.path)
            if cached_movie.tmdb_id is None:
                logging.warning(f"TMDB ID not found in cache: {movie.path}")
                continue
            movie.tmdb_id = cached_movie.tmdb_id
            if cached_movie.trailer_url is None:
                logging.warning(f"Trailer URL not found in cache: {movie.path}")
                continue
            # now copy over all the other attributes from the cached movie
            for key, value in vars(cached_movie).items():
                if key not in ['title', 'path', 'tmdb_id']:
                    setattr(movie, key, value)
        
        return movies
    
    def get_series(self):
        pass
    
    def get(self):
        pass
