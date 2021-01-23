#! /usr/bin/python3
import requests
import re
import json
import shutil
import os
import subprocess
import unicodedata
import concurrent.futures
from urllib.parse import unquote
from dataclasses import dataclass
from time import sleep
from univ_api import *


@dataclass
class VideoResource:
    name: str
    url: str
    format: str
    bitrate: int
    resolution: tuple

@dataclass
class Video:
    id: str
    title: str
    layout: str
    duration: float
    available_resource: VideoResource

class DownloadStatus:

    def __init__(self, max=0):
        self.max = max
        self.value = 0

    def inc(self):
        self.value = self.value + 1

    def add(self, n):
        self.value = self.value + n


def slugify(value, allow_unicode=False):
    """
    Taken from https://github.com/django/django/blob/master/django/utils/text.py
    Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
    dashes to single dashes. Remove characters that aren't alphanumerics,
    underscores, or hyphens. Convert to lowercase. Also strip leading and
    trailing whitespace, dashes, and underscores.
    """
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize('NFKC', value)
    else:
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value.lower())
    return re.sub(r'[-\s]+', '-', value).strip('-_')

def download_file(url: str, file: str, ses=requests.session()):
    try:
        response = requests.get(url, stream=True)
        with open(file, 'wb') as out_file:
            shutil.copyfileobj(response.raw, out_file)
    except:
        return False
    return True

def url_to_filename(url: str):
    return url.split('/')[-1:][0].split('?')[0]

def url_parent_dir(url: str):
    i = len(url) - 1

    while i >= 0:
        if url[i] == '/':
            break
        i = i - 1

    return url[:i+1]

def get_files_in_playlist(filename: str):
    with open(filename, 'r') as file:
        lines = [line.rstrip() for line in file]
    files = list()
    for line in lines:
        if line[0] == '#':
            continue
        files.append(line)
    return files

def get_video_title(id: str, ses=requests.session()):
    regex = "<title>(.*)</title>"
    response = ses.get("https://webtv.univ-rouen.fr/permalink/{}/iframe/".format(id))

    title = re.findall(regex, response.text)[0]

    if title == None:
        raise Exception("iframe page return invalid content")

    return title

def alives_process(process_list):
    i = 0
    for process in process_list:
        if process.is_alive():
            i = i + 1
    return i

def get_video_info(id: str, ses=requests.session()):
    response = ses.get("https://webtv.univ-rouen.fr/api/v2/medias/modes/?oid={}&html5=webm_ogg_ogv_oga_mp4_mp3_m3u8".format(id))
    infos = response.json()

    if infos['success'] == False:
        print('Error: failed to parse {} infos maybe not logged successful'.format(id))
        return None

    title = get_video_title(id, ses)

    sources = list()
    for sourcename in infos['names']:
        tmpsource = infos[sourcename]
        try:
            infos[sourcename]['tracks']
            if infos[sourcename]['tracks'] != None:
                tmpsource = tmpsource['tracks'][0]
        except:
            tmpsource = tmpsource['resource']
            if sourcename == 'audio':
                print('Warn: audio format not supported yet')
                continue

        try:

            if tmpsource['format'] != 'm3u8':
                print('Warn: format {} not supported'.format(tmpsource['format']))

            try:
                source = VideoResource(sourcename, tmpsource['url'],
                    tmpsource['format'],
                    tmpsource['bitrate'],
                    (tmpsource['width'],
                    tmpsource['height']))
            except:
                source = VideoResource(sourcename, tmpsource['url'],
                    tmpsource['format'],
                    tmpsource['bitrate'],
                    (0, 0))

        except:
            pass

        sources.append(source)
    
    return Video(id, title, infos['layout'], infos['duration'], sources)

def parse_available_ids(htmlcontent: str):
    regex = "https://webtv.univ-rouen.fr/permalink/([a-z0-9]*)/"

    # This remove duplicate
    ids = list(set(re.findall(regex, htmlcontent)))

    regex = "&mediaid=([a-z0-9]*)\""

    # This remove duplicate
    ids = ids + list(set(re.findall(regex, htmlcontent)))

    return ids

def parse_available_videos(htmlcontent: str, ses=requests.session()):
    ids = parse_available_ids(htmlcontent)
    videos = list()

    for id in ids:
        video = get_video_info(id, ses)
        if video == None:
            continue
        videos.append(video)
    
    return videos

def download_resource(resource: VideoResource, out_file: str, stat: DownloadStatus, download_dir='download/', ses=requests.session()):
    playlist_file = download_dir + url_to_filename(resource.url)
    directory = playlist_file.split('.')[0]
    url_dir = url_parent_dir(resource.url)

    try:
        os.mkdir(download_dir)
    except FileExistsError:
        if os.path.isfile(download_dir):
            print("Error: {} is already a file".format(download_dir))
            return False
        pass

    try:
        os.mkdir(directory)
    except FileExistsError:
        if os.path.isfile(directory):
            print("Error: {} is already a file".format(directory))
            return False
        pass

    # Download the playlist file
    download_file(resource.url, playlist_file, ses)

    files = get_files_in_playlist(playlist_file)

    stat.max = len(files)
    
    args = (list(), list(), list())

    for file in files:
        current_url = url_dir + file

        args[0].append(current_url)
        args[1].append(download_dir + file)
        args[2].append(ses)


    i = 0
    with concurrent.futures.ThreadPoolExecutor() as pool:
        for res in pool.map(download_file, args[0], args[1], args[2]):
            if res != True:
                print('Error when downloading ts files')
                return False
            stat.inc()
            i = i + 1

    os.system('ffmpeg -y -i {} -codec copy -loglevel panic -hide_banner {}'.format(playlist_file, out_file))

    return True

def download_video(video: Video, out_file: str, stat: DownloadStatus, ses=requests.session(), download_dir='download/'):
    video_file = download_dir + slugify(video.title) + '.mp4'
    download_resource(video.available_resource[0], video_file, stat, download_dir, ses)

    if video.layout == 'composition' or len(subprocess.check_output(['ffprobe', '-i', video_file, '-show_streams', '-select_streams', 'a', '-loglevel', 'error'])) == 0:
        for resource in video.available_resource:
            if resource.name == 'audio':
                stat.value = 0
                audio_file = download_dir + slugify(video.title) + '.aac'
                download_resource(resource, audio_file, stat, download_dir, ses) # TODO : Handle more codec
                os.system('ffmpeg -y -i {} -i {} -codec copy -shortest -loglevel panic -hide_banner {}'.format(video_file, audio_file, out_file))
                os.remove(video_file)
                os.remove(audio_file)
                break
    else:
        os.system('ffmpeg -y -i {} -codec copy -loglevel panic -hide_banner {}'.format(video_file, out_file))
        os.remove(video_file)
