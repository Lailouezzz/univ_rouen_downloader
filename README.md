# Downloader for webtv univ Rouen

# Usage

Use the MultiPass username and password.

## GUI (User friendly)

Use this command line to login and show the GUI :

`downloader.py [username] [password] -g`

## CLI (Command line)

`url` is a page where is one or more universitice video (the multipass account need the permission to this page to parse the videos)

`downloader.py [username] [password] [url]`

## Notes

The program first parse the videos, then download the stream files (m3u8 for the playlist and ts for the video parts) and then use ffmpeg to join all video into one mp4 file.


# Dependecies


`python >= 3.6`

`python3 -m pip install requests pysimplegui`

or

`py -m pip install requests pysimplegui`

---

## Linux

### Debian like (apt)

`apt install ffmpeg`

### Fedora (dnf)

`dnf install ffmpeg`

---

## Windows

ffmpeg already included in repositery.
