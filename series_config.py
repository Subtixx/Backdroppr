import os

from video_config import VideoConfig

class SeriesConfig(VideoConfig):
    def __init__(self):
        self.enabled = os.getenv('TV_ENABLED') if 'TV_ENABLED' in os.environ else False
        self.path = os.getenv('TV_PATH') if 'TV_PATH' in os.environ else None
        self.output_pattern = os.getenv('TV_OUTPUT_PATTERN') if 'TV_OUTPUT_PATTERN' in os.environ else None