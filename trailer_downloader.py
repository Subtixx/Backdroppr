from glob import glob
import logging
import os
import subprocess
import requests
import yt_dlp

from themoviedb import TMDb, PartialMovie, Video

from cache import Cache
from config import Config
from jellyfin_api import JellyfinApi
from movie import Movie
from radarr_api import RadarrApi
from sonarr_api import SonarrApi
from filesystem_api import FilesystemApi

class TrailerDownloader:
    tmdb_api = None
    active_api = None
    config: Config = None
    cache: Cache = None
    
    def __init__(self):
        self.config = Config()
        self.config.load_config()
        
        self.cache = Cache()
        self.cache.load_cache()
        
        self.tmdb_api = TMDb(
            key=self.config.tmdb_key,
            language=self.config.tmdb_language,
            region=self.config.tmdb_region
        )
        
        if self.config.jellyfin_key is not None and self.config.jellyfin_host is not None:
            self.active_api = JellyfinApi(self, self.config)
            logging.info("Using Jellyfin API.")
        elif self.config.radarr_host is not None and self.config.radarr_key is not None:
            self.active_api = RadarrApi(self, self.config)
            logging.info("Using Radarr API.")
        elif self.config.sonarr_host is not None and self.config.sonarr_key is not None:
            self.active_api = SonarrApi(self, self.config)
            logging.info("Using Sonarr API.")
        elif self.config.movie_config is not None:
            logging.warning("No API found, using filesystem.")
            self.active_api = FilesystemApi(self, self.config)
        else:
            logging.error("No API found, exiting.")
            
    def run(self):
        if self.active_api is None:
            logging.error("No API found, exiting.")
            return
        
        logging.info("Pulling trailers...")
        movies = self.active_api.get_movies()
        for movie in movies:
            logging.info(f"Processing movie: {movie}")
            if movie.tmdb_id is None:
                logging.info("No TMDB ID found, searching for movie.")
                tmdb_movie_result = self.search_movie(movie.title)
                if tmdb_movie_result is None:
                    continue
                movie.title = tmdb_movie_result.title
                movie.year = tmdb_movie_result.year
                movie.tmdb_id = tmdb_movie_result.id
            if movie.trailer_url is None:
                logging.info("No trailer URL found, searching for trailer.")
                movie.trailer_url = self.get_trailer(movie.tmdb_id)
                if movie.trailer_url is None:
                    continue
                
            if movie.trailer_path is None:
                self.trailer_download(movie)
                movie.trailer_path = glob(f'trailers/{self.get_trailer_name(movie)}.*')[0]
                #crop_value = self.crop_check(movie)
                #if crop_value is not None:
                #    self.post_process(movie, crop_value)
            else:
                logging.info("Trailer already downloaded.")
            
            self.cache.update_movie(movie)
                
    def search_movie(self, title) -> PartialMovie|None:
        logging.info("Searching for movie: " + title)
        movies: list[PartialMovie] = self.tmdb_api.search().movies(title)
        if len(movies) == 0:
            logging.error("No movie with title: " + title + " found.")
            return None
        result:PartialMovie = movies[0]
        if len(movies) > 1:
            logging.warning(
                f"Multiple movies with title: {title} found, using first found {result.title} - {result.year} ({str(result.id)})")
            
        return result
        
    def shutdown(self):
        self.cache.save_cache()
        
    
    def get_trailer(self, tmdb_id: int):
        logging.info("Retrieving trailer information from TMDB using TMDB ID: " + str(tmdb_id))
        moviedb_videos = self.tmdb_api.movie(tmdb_id).videos()
        if moviedb_videos is None:
            logging.error("No trailer found for TMDB ID: " + str(tmdb_id))
            return None
        
        moviedb_trailers: list[Video] = list(filter(self.filter_trailer, moviedb_videos))
        if len(moviedb_trailers) == 0:
            logging.error("No trailer found for TMDB ID: " + str(tmdb_id))
            return None
        
        return sorted(moviedb_trailers, key=self.sort_trailers)[-1].key
        
    def sort_trailers(self, video:Video):
        return video.size
    def filter_trailer(self, video:Video):
        return video.type == 'Trailer' and video.site == 'YouTube'
    
    def get_trailer_name(self, movie:Movie):
        if self.config.movie_config.output_pattern is None:
            return f"{movie.title} ({movie.year}) - {movie.tmdb_id} trailer"
        return self.config.movie_config.output_pattern.format(title=movie.title, year=movie.year, id=movie.tmdb_id)
    
    def crop_check(self, movie:Movie):
        logging.info("Looking for black borders...")
        cropvalue = subprocess.check_output(
            f"ffmpeg -i '{movie.trailer_path}' -t 30 -vf cropdetect -f null - 2>&1 | awk "
            "'/crop/ {{ print $NF }}' | tail -1",
            shell=True
        ).decode('utf-8').strip()
        logging.debug(cropvalue)
        l = [j for i, j in {720: 20, 1280: 24, 1920: 28, 3840: 35}.items()
            if i >= int(cropvalue.split('crop=')[1].split(':')[0])]
        return cropvalue, l[0] if len(l) > 0 else None
    
    # def post_process(self, movie:Movie, cropvalue, item_path, bitrate):
    #     try:
    #         try:
    #             os.mkdir(f'{item_path}/{config["output_dirs"].split(",")[0]}')
    #         except:
    #             logging.debug("Output directory found.")
    #         sub_file = ""
    #         if config['filetype'] == "webm":
    #             if config['subs']:
    #                 if f"{filename}.en.vtt" in os.listdir("cache/"):
    #                     logging.info("Subs found")
    #                     sub_file = f"-i \"cache/{filename}.en.vtt\" -map 0:v -map 0:a -map 1 -metadata:s:s:0 language=eng"
    #             subprocess.check_call(
    #                 f'ffmpeg -i "{filename}" {sub_file} -threads {thread_count} -vf {cropvalue} -c:v libvpx-vp9 -crf {bitrate} -b:v '
    #                 f'4500k -af "volume=-5dB" -y "{item_path}/{config["output_dirs"].split(",")[0]}/video1.webm"',
    #                                         shell=True)
    #         else:
    #             if config['subs']:
    #                 if f"{filename}.en.vtt" in os.listdir("cache/"):
    #                     logging.info("Subs found")
    #                     sub_file = f"-i \"cache/{filename}.en.vtt\" -map 0:v -map 0:a -map 1 -metadata:s:s:0 language=eng " \
    #                             f"-disposition:s:0 forced -c:s ssa "
    #             subprocess.check_call(f'ffmpeg -i "{filename}" {sub_file} -threads {thread_count} -vf {cropvalue} -c:v libx264 -b:v {bitrate*140}'
    #                                 f'-maxrate {bitrate*140} -bufsize 2M -preset slow -c:a aac -af "volume=-7dB" '
    #                                 f'-y "{item_path}/{config["output_dirs"].split(",")[0]}/video1.mp4"',
    #                                         shell=True)
    #         os.remove(f"{filename}")
    #     except Exception as e:
    #         logging.error(f"ERROR: {e}")
    
    def trailer_download(self, item:Movie):
        logging.info(f"Downloading trailer for {item.title} ({item.year})")
        
        ytdl_opts = {
            'progress_hooks': [self.download_progress],
            'format': 'bestvideo+bestaudio',
            'outtmpl': f'trailers/{self.get_trailer_name(item)}.%(ext)s',
            'quiet': True,
            'no_warnings': True,
        }
        if self.config.min_length is not None and self.config.max_length is not None:
            logging.info(f"Setting length range to {self.config.min_length} - {self.config.max_length}")
            try:
                ytdl_opts.update({'match_filter': self.check_duration})
            except Exception as e:
                logging.error(e)
        if self.config.skip_intros:
            logging.info("Removing sponsor segments: intro, outro, selfpromo, preview, filler, interaction")
            try:
                ytdl_opts.update({
                    'postprocessors': [
                        {'key': 'SponsorBlock'}, 
                        {'key': 'ModifyChapters',
                        'remove_sponsor_segments': 
                            ['sponsor', 'intro', 'outro', 'selfpromo', 'preview', 'filler', 'interaction'
                            ]
                            }
                        ]
                    })
            except Exception as e:
                logging.error(e)
        #fileout = glob(f'cache/{item["sortTitle"]}.*')
        #os.remove(fileout[0]) if len(fileout) > 1 else None
        try:
            ydl = yt_dlp.YoutubeDL(ytdl_opts)
            ydl.download([item.trailer_url])
            logging.info("Finished downloading trailer.")
        except Exception as e:
            logging.error(e)
            
    def check_duration(self, info, *, incomplete):
        min_length = self.config.min_length
        max_length = self.config.max_length
        duration = info.get('duration')
        if duration not in range(min_length, max_length):
            return 'Video too long/short'
            
    def download_progress(self, d):
        if d['status'] == 'downloading':
            logging.info(f"Downloading {d['_percent_str']}")
        #elif d['status'] == 'finished':
        #    logging.info('Done downloading')
