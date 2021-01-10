#! /usr/bin/python3
import requests
import re
import json
import shutil
import os
import unicodedata
from urllib.parse import unquote
from dataclasses import dataclass
from multiprocessing import Process
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
    duration: float
    available_resource: VideoResource


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
        if sourcename == 'audio':
            print('Warn: audio format not supported yet')
            continue

        try:
            tmpsource = infos[sourcename]

            if tmpsource['resource']['format'] != 'm3u8':
                print('Warn: format {} not supported'.format(tmpsource['resource']['format']))

            source = VideoResource(sourcename, tmpsource['resource']['url'],
                tmpsource['resource']['format'],
                tmpsource['resource']['bitrate'],
                (tmpsource['resource']['width'],
                tmpsource['resource']['height']))
        except:
            pass

        sources.append(source)
    
    return Video(id, title, infos['duration'], sources)

def parse_available_ids(htmlcontent: str):
    regex = "https://webtv.univ-rouen.fr/permalink/([a-z0-9]*)/"

    # This remove duplicate
    ids = list(set(re.findall(regex, htmlcontent)))

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

def download_video(video: Video, ses=requests.session()):
    resource_id = 0 # TODO auto selection 0 is maybe 720p or the best resolution I don't know
    download_dir = 'download/'

    playlist_file = download_dir + url_to_filename(video.available_resource[resource_id].url)
    directory = playlist_file[:-5]
    out_file = slugify(video.title) + '.mp4'
    url_dir = url_parent_dir(video.available_resource[resource_id].url)

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
    download_file(video.available_resource[resource_id].url, playlist_file, ses)

    files = get_files_in_playlist(playlist_file)
    process_list = list()

    for file in files:
        current_url = url_dir + file

        process_list.append(Process(target=download_file, args=(current_url, download_dir + file, ses,)))
    
    i = 0
    while i < len(process_list):
        sleep(0.005)
        if alives_process(process_list) < 32:
            process_list[i].start()
            print('{}/{}'.format(i, len(process_list)), end='\r')
            i = i + 1
    
    for process in process_list:
        try:
            process.join()
        except:
            pass

    os.system('ffmpeg -i {} -acodec copy -vcodec copy {}'.format(playlist_file, out_file))
