#! /usr/bin/python3
import argparse
import webtv_api, univ_api


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("username", help="username", type=str)
    parser.add_argument("password", help="password", type=str)
    parser.add_argument("url", help="url where to find videos", type=str)
    args = parser.parse_args()

    univses = univ_api.login_session(args.username, args.password)

    response = univses.get(args.url)
    videos = webtv_api.parse_available_videos(response.text, univses)
    if len(videos) == 0:
        print("Error: no video found, maybe not logged in successful")

    for video in videos:
        print("Downloading {} video...".format(video.id))
        webtv_api.download_video(video, univses)

if __name__ == "__main__":
    main()