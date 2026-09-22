import os
import json
import re
import shutil
import subprocess
from time import sleep
import logging
import requests
import yaml
import yt_dlp
from yt_dlp.postprocessor import PostProcessor
from pyarr import SonarrAPI, RadarrAPI


def load_config():
    with open('config/config.yaml', 'r') as f:
        global config
        config = yaml.load(f, Loader=yaml.Loader)
        if not isinstance(config.get('validate_trailers', True), bool):
            raise ValueError('validate_trailers must be true or false')


def dl_progress(d):
    if d['status'] == 'finished':
        logging.info("Stream downloaded; finishing trailer processing...")


def check_duration(info, *, incomplete):
    duration = info.get('duration')
    if duration is None:
        return None
    minimum, maximum = map(int, config['length_range'].split(','))
    if not minimum <= duration < maximum:
        return 'Video too long/short'


def trailer_pull(tmdb_id, item_type):
    logging.info("Getting information about the item...")
    try:
        item_trailers = requests.get(
            f"http://api.themoviedb.org/3/{item_type}/{tmdb_id}/videos?api_key={config['tmdb_api']}").json()['results']
        item_trailers = list(filter(lambda x: x['type'] == 'Trailer' and x['site'] == 'YouTube', item_trailers))
        return sorted(item_trailers, key=lambda x: x['size'])[-1]['key']
    except IndexError:
        return 1


def movie_finder():
    logging.info("Movie trailer finder started.")
    movie_num = 0
    try:
        movie_json = radarr.get_movie()
    except Exception as e:
        logging.error(f"Can't communicate with Radarr! {e}")
        exit(1)
    for movie_item in movie_json:
        if movie_item['hasFile']:
            movie_num = movie_num + 1
            try:
                if 'moviepath' in config:
                    if movie_item['path'][-1] == "/":
                        movie_item['path'] = f"{config['moviepath']}/{movie_item['path'][0:-1].split('/')[-1]}"
                    else:
                        movie_item['path'] = f"{config['moviepath']}/{movie_item['path'].split('/')[-1]}"
                logging.info(
                    f"[{movie_num}] -- Title: {movie_item['title']}: Path: {movie_item['path']} -- TMDB-ID: "
                    f"{movie_item['tmdbId']}")
                if os.path.isfile(f"{movie_item['path']}/{config['output_dirs'].split(',')[0]}/video1.{config['filetype']}"):
                    logging.info("Trailer exists!")
                else:
                    tmdb_id = movie_item['tmdbId']
                    try:
                        link = trailer_pull(tmdb_id, "movie")
                    except Exception as e:
                        logging.warning(f"TMDB lookup failed: {e}")
                        link = None
                    fileout = trailer_download(link, movie_item)
                    result = crop_check(fileout)
                    if result[1] is None:
                        logging.error("ERROR!")
                        continue
                    post_process(fileout, result[0], movie_item['path'], result[1])
                logging.info("Copying trailer to additional directories from the config, if not copied yet...")
                for dir in config['output_dirs'].split(',')[1:]:
                    try:
                        os.makedirs(f"{movie_item['path']}/{dir}", exist_ok=True)
                    except OSError:
                        continue
                    if not os.path.isfile(f"{movie_item['path']}/{dir}/video1.{config['filetype']}"):
                        copy_trailer(
                            f"{movie_item['path']}/{config['output_dirs'].split(',')[0]}/video1.{config['filetype']}",
                            f"{movie_item['path']}/{dir}/video1.{config['filetype']}")
                        logging.info("Copied trailer.")
            except Exception as e:
                logging.error(e)


def show_finder():
    logging.info("Show trailer finder started.")
    tv_num = 0
    try:
        shows_json = sonarr.get_series()
    except Exception as e:
        logging.error(f"Can't communicate with Sonarr! {e}")
        exit(1)
    for show_item in shows_json:
        try:
            if 'tvpath' in config:
                if show_item['path'][-1] == "/":
                    show_item['path'] = f"{config['tvpath']}/{show_item['path'][0:-1].split('/')[-1]}"
                else:
                    show_item['path'] = f"{config['tvpath']}/{show_item['path'].split('/')[-1]}"
            if show_item['statistics']['episodeFileCount'] > 0:
                tv_num = tv_num + 1
                logging.info(
                    f"[{tv_num}] -- Title: {show_item['title']}: Path: {show_item['path']} -- IMDB-ID: "
                    f"{show_item['imdbId']}")
                if os.path.isfile(f"{show_item['path']}/{config['output_dirs'].split(',')[0]}/video1.{config['filetype']}"):
                    logging.info("Trailer exists!")
                else:
                    try:
                        show_id = requests.get(
                            f"https://api.themoviedb.org/3/find/{show_item['imdbId']}?api_key={config['tmdb_api']}"
                            f"&external_source=imdb_id").json()['tv_results']
                        link = trailer_pull(show_id[0]['id'], "tv") if show_id else None
                    except Exception as e:
                        logging.warning(f"TMDB lookup failed: {e}")
                        link = None
                    fileout = trailer_download(link, show_item)
                    result = crop_check(fileout)
                    if result[1] is None:
                        logging.error("ERROR!")
                        continue
                    post_process(fileout, result[0], show_item['path'], result[1])
                logging.info("Copying trailer to additional directories from the config, if not copied yet...")
                for dir in config['output_dirs'].split(',')[1:]:
                    try:
                        os.makedirs(f"{show_item['path']}/{dir}", exist_ok=True)
                    except OSError:
                        continue
                    if not os.path.isfile(f"{show_item['path']}/{dir}/video1.{config['filetype']}"):
                        copy_trailer(
                            f"{show_item['path']}/{config['output_dirs'].split(',')[0]}/video1.{config['filetype']}",
                            f"{show_item['path']}/{dir}/video1.{config['filetype']}")
                        logging.info("Copied trailer.")
        except Exception as e:
            logging.error(e)


def copy_trailer(source, destination):
    temporary = destination + '.tmp'
    try:
        shutil.copy(source, temporary)
        os.replace(temporary, destination)
    finally:
        if os.path.isfile(temporary):
            os.remove(temporary)


def validate_trailer(filename):
    if not config.get('validate_trailers', True):
        return
    if os.path.getsize(filename) == 0:
        raise ValueError(f'Empty trailer: {filename}')
    result = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_streams', '-of', 'json', filename],
        capture_output=True, text=True, check=True, timeout=30,
    )
    streams = json.loads(result.stdout).get('streams', [])
    video = any(s.get('codec_type') == 'video' and
                not s.get('disposition', {}).get('attached_pic') for s in streams)
    audio = any(s.get('codec_type') == 'audio' for s in streams)
    if not video or not audio:
        raise ValueError(f'Trailer must contain video and audio: {filename}')


class FinalFilePP(PostProcessor):
    def __init__(self, downloader):
        super().__init__(downloader)
        self.filename = None

    def run(self, info):
        self.filename = info['filepath']
        return [], info


def trailer_candidates(link, item):
    if link and link != 1:
        yield link
    logging.info('Searching for another trailer...')
    with yt_dlp.YoutubeDL({'extract_flat': True, 'skip_download': True, 'socket_timeout': 30}) as ydl:
        results = ydl.extract_info(
            f"ytsearch5:{item['title']} ({item['year']}) Trailer", download=False,
        )
    for entry in (results or {}).get('entries', []):
        if entry and entry.get('id') and entry['id'] != link:
            yield f"https://www.youtube.com/watch?v={entry['id']}"


def trailer_download(link, item):
    ytdl_opts = {
        'progress_hooks': [dl_progress],
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': 'cache/%(id)s.%(ext)s',
        'continuedl': True,
        'retries': 3,
        'fragment_retries': 3,
        'skip_unavailable_fragments': False,
        'socket_timeout': 30,
        'noplaylist': True,
    }
    if 'length_range' in config:
        ytdl_opts['match_filter'] = check_duration
    if config.get('skip_intros', False):
        ytdl_opts['postprocessors'] = [
            {'key': 'SponsorBlock'},
            {'key': 'ModifyChapters', 'remove_sponsor_segments': [
                'sponsor', 'intro', 'outro', 'selfpromo', 'preview', 'filler', 'interaction',
            ]},
        ]
    for candidate in trailer_candidates(link, item):
        for attempt in range(1, 3):
            try:
                with yt_dlp.YoutubeDL(ytdl_opts) as ydl:
                    completed = FinalFilePP(ydl)
                    ydl.add_post_processor(completed, when='after_move')
                    ydl.extract_info(candidate, download=True)
                filename = completed.filename
                if not filename:
                    logging.info(f'No completed download for {candidate}; trying another trailer.')
                    break
                if filename.endswith(('.part', '.ytdl', '.tmp')) or not os.path.isfile(filename):
                    raise ValueError('Download did not produce a completed file')
                try:
                    validate_trailer(filename)
                except (ValueError, subprocess.CalledProcessError):
                    os.remove(filename)
                    raise
                return filename
            except Exception as e:
                logging.warning(f'Trailer attempt {attempt}/2 failed for {candidate}: {e}')
    raise RuntimeError(f"No downloadable trailer found for {item['title']}")


def crop_check(filename):
    logging.info('Looking for black borders...')
    result = subprocess.run(
        ['ffmpeg', '-nostdin', '-i', filename, '-t', '30', '-vf', 'cropdetect',
         '-an', '-f', 'null', '-'],
        capture_output=True, text=True, check=True,
    )
    crops = re.findall(r'crop=\d+:\d+:\d+:\d+', result.stderr)
    if not crops:
        return 'null', 28
    cropvalue = crops[-1]
    width = int(cropvalue.split('=')[1].split(':')[0])
    bitrate = next((value for limit, value in {720: 20, 1280: 24, 1920: 28, 3840: 35}.items()
                    if width <= limit), 35)
    return cropvalue, bitrate


def post_process(filename, cropvalue, item_path, bitrate):
    filetype = config['filetype']
    directory = os.path.join(item_path, config['output_dirs'].split(',')[0])
    os.makedirs(directory, exist_ok=True)
    destination = os.path.join(directory, f'video1.{filetype}')
    temporary = os.path.join(directory, f'video1.tmp.{filetype}')
    command = ['ffmpeg', '-nostdin', '-i', filename]
    subtitle = os.path.splitext(filename)[0] + '.en.vtt'
    if config.get('subs', False) and os.path.isfile(subtitle):
        command += ['-i', subtitle, '-map', '0:v:0', '-map', '0:a:0?', '-map', '1:0',
                    '-metadata:s:s:0', 'language=eng', '-c:s',
                    'webvtt' if filetype == 'webm' else 'mov_text']
    else:
        command += ['-map', '0:v:0', '-map', '0:a:0?']
    command += ['-threads', str(thread_count), '-vf', cropvalue]
    if filetype == 'webm':
        command += ['-c:v', 'libvpx-vp9', '-crf', str(bitrate), '-b:v', '4500k',
                    '-af', 'volume=-5dB']
    else:
        command += ['-c:v', 'libx264', '-b:v', str(bitrate * 140),
                    '-maxrate', str(bitrate * 140), '-bufsize', '2M', '-preset', 'slow',
                    '-c:a', 'aac', '-af', 'volume=-7dB']
    try:
        subprocess.run(command + ['-y', temporary], check=True)
        validate_trailer(temporary)
        os.replace(temporary, destination)
    finally:
        if os.path.isfile(temporary):
            os.remove(temporary)
    os.remove(filename)


logging.basicConfig(format='%(asctime)s %(message)s', encoding='utf-8', level=logging.INFO)
try:
    os.mkdir("cache")
    logging.debug("Created cache directory.")
except FileExistsError:
    logging.debug("Cache directory found.")
while True:
    load_config()
    thread_count = config['thread_count'] if 'thread_count' in config else 0
    if all(x in config for x in ['radarr_host', 'radarr_api']):
        radarr = RadarrAPI(config['radarr_host'], config['radarr_api'])
        movie_finder()
    else:
        logging.info("No Radarr API key/host were found, skipping...")
    if all(x in config for x in ['sonarr_host', 'sonarr_api']):
        sonarr = SonarrAPI(config['sonarr_host'], config['sonarr_api'])
        show_finder()
    else:
        logging.info("No Sonarr API key/host were found, skipping...")
    if 'sleep_time' in config:
        if isinstance(config['sleep_time'], int):
            logging.info(
                f"Operation complete. Sleeping for {config['sleep_time']} hour(s).")
        else:
            logging.info(
                f"Operation complete. Sleeping for {config['sleep_time'] * 60} minute(s).")
        sleep(float(config['sleep_time']) * 3600)
    else:
        exit(logging.info("Operation complete. No sleep time was set, stopping."))
