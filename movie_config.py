import os
from video_config import VideoConfig


class MovieConfig(VideoConfig):
    def __init__(self):
        self.enabled = os.getenv('MOVIE_ENABLED') if 'MOVIE_ENABLED' in os.environ else False
        self.path = os.getenv('MOVIE_PATH') if 'MOVIE_PATH' in os.environ else None
        self.output_pattern = os.getenv('MOVIE_OUTPUT_PATTERN') if 'MOVIE_OUTPUT_PATTERN' in os.environ else None
