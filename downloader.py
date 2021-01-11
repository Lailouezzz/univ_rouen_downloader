#! /usr/bin/python3
import argparse
import webtv_api, univ_api
from multiprocessing.pool import ThreadPool
from time import sleep


def main_gui(univses):
    import PySimpleGUI as sg
    layout = [
        [sg.Text('Enter link to search webtv video : ')],
        [sg.InputText(key=('in_url'))],
        [sg.Button('Search', key='Search'), sg.Button('Download', key='Download')],
        [sg.Text(size=(40, 5), key='infos')],
        [sg.ProgressBar(1000, orientation='h', size=(30, 20), key='progbar')]
    ]

    window = sg.Window('Downloader', layout)

    cur_videos = list()

    downloading = False

    cur_status = None

    cur_ind = 0

    pool = ThreadPool(processes=1)

    cur_task = None

    while True:
        event, values = window.read(timeout=0.5)

        if event == sg.WIN_CLOSED:
            break

        if downloading:
            if cur_ind < len(cur_videos) and cur_task == None:
                #print('CREATE TASK')
                cur_status = webtv_api.DownloadStatus()
                args = (cur_videos[cur_ind], webtv_api.slugify(cur_videos[cur_ind].title) + '.mp4', cur_status, univses)
                cur_task = pool.apply_async(webtv_api.download_video, args)
                window['infos'].update('DOWNLOADING {} of {} ({})'.format(cur_ind+1, len(cur_videos), cur_videos[cur_ind].title))
            elif cur_task != None and cur_task.ready():
                #print('FINISH')
                cur_task = None
                cur_ind = cur_ind + 1
            elif cur_task != None and not cur_task.ready():
                #print('DOWNLOADING...')
                if cur_status.max == 0:
                    window['progbar'].update_bar(0)
                else:
                    window['progbar'].update_bar((float(cur_status.value) / cur_status.max) * 1000)
            else:
                #print('ALL FINISH')
                window['infos'].update('DOWNLOAD COMPLETE !')
                window['progbar'].update_bar(0)
                downloading = False
            continue
        
        if event == 'Search':
            try:
                response = univses.get(values['in_url'])
                cur_videos = webtv_api.parse_available_videos(response.text, univses)
            except:
                window['infos'].update('ERROR INVALID URL')
                continue
            # ADD infos and button for download
            window['infos'].update('FOUND {} VIDEOS'.format(len(cur_videos)))
        
        if event == 'Download':
            cur_ind = 0
            downloading = True
        

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("username", help="username", type=str)
    parser.add_argument("password", help="password", type=str)
    parser.add_argument("url", help="url where to find videos", nargs='*', default=[])
    parser.add_argument("-g", "--gui", help="enable gui mode",
                    action="store_true")
    args = parser.parse_args()

    univses = univ_api.login_session(args.username, args.password)

    if args.gui:
        print('GUI mode')
        main_gui(univses)

    for cur_url in args.url:

        response = univses.get(cur_url)
        videos = webtv_api.parse_available_videos(response.text, univses)
        if len(videos) == 0:
            print("Error: no video found in {}, maybe not logged in successful".format(cur_url))

        for video in videos:
            print("Downloading {}...".format(video.title))
            cur_status = webtv_api.DownloadStatus()
            args = (video, webtv_api.slugify(video.title) + '.mp4', cur_status, univses)
            with ThreadPool(processes=1) as pool:
                async_result = pool.apply_async(webtv_api.download_video, args)
                while async_result.ready() != True:
                    # Here when is downloading video
                    sleep(0.1)

                if async_result.get():
                    print('Error when downloading {}'.format(video.title))
            

if __name__ == "__main__":
    main()
