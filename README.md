# Downloader for webtv univ Rouen


Use the MultiPass username and password.

`url` is a page where is one or more universitice video (the multipass account need the permission to this page to parse the videos)

`downloader.py [username] [password] [url]`

The program first parse the videos, then download the stream files (m3u8 for the playlist and ts for the video parts) and then use ffmpeg to join all video into one mp4 file.


# Dependecies


`python >= 3.6`

`python3 -m pip install requests`

---

## Linux

### Debian like (apt)

`apt install ffmpeg`

### Fedora (dnf)

`dnf install ffmpeg`

---

## Windows

TODO