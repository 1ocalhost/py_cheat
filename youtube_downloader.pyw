import os
import re
import json
import requests

from tkinter import Frame, messagebox, filedialog, ttk
from urllib.parse import urlsplit, parse_qs
from threading import Thread


def enable(widget, enabled=True):
    if isinstance(widget, ttk.Combobox):
        normal = 'readonly'
    else:
        normal = 'normal'

    state = enabled and normal or 'disabled'
    widget["state"] = state


def filter_filename(name):
    return re.sub(r'[^\w\-_\. ]', '_', name)


def show_error(e):
    messagebox.showwarning(message=f'Error: {type(e).__name__}: {e}')


class AppFrame(Frame):
    def init_ui(self):
        from tkinter import E, W
        RIGHT_WIDTH = 80
        self.winfo_toplevel().title('YouTube Downloader')
        self.grid(padx=10, pady=20)

        row = 0
        self.paste = ttk.Button(
            self, text='Paste from clipboard', command=self.on_paste)
        self.paste.grid(row=row, column=2, sticky=E)

        row += 1
        ttk.Label(self, text='URL:').grid(row=row, column=0, sticky=W)
        self.url = ttk.Label(self, width=RIGHT_WIDTH)
        self.url.grid(row=row, column=1, columnspan=2)

        row += 1
        ttk.Label(self, text='Title:').grid(row=row, column=0, sticky=W)
        self.title = ttk.Label(self, width=RIGHT_WIDTH)
        self.title.grid(row=row, column=1, columnspan=2)

        row += 1
        ttk.Label(self, text='Quality:').grid(row=row, column=0, sticky=W)
        self.quality = ttk.Combobox(self, state='readonly')
        self.quality.grid(row=row, column=1, sticky=W+E)
        self.download = ttk.Button(
            self, text='Download', command=self.on_download)
        self.download.grid(row=row, column=2, sticky=E)

        row += 1
        ttk.Label(self, text='Progress:').grid(row=row, column=0, sticky=W)
        self.progress = ttk.Progressbar(self)
        self.progress.grid(row=row, column=1, columnspan=2, sticky=W+E)

        enable(self.quality, False)
        enable(self.download, False)

    def enable_ui(self, enabled=True):
        enable(self.paste, enabled)
        enable(self.quality, enabled)
        enable(self.download, enabled)

    def extract_video_id(self, url):
        if not url.startswith('https://www.youtube.com/watch?'):
            return

        params = parse_qs(urlsplit(url).query)
        ids = params.get('v')
        if not ids:
            return

        return ids[0]

    def on_paste(self):
        url = str(self.clipboard_get().strip())
        video_id = self.extract_video_id(url)
        if not video_id:
            MAX_LEN = 1024
            url = url.replace('\n', ' ')
            if len(url) > MAX_LEN:
                url = url[:MAX_LEN] + '...'
            messagebox.showwarning(
                message=f'It\'s not a link for YouTube video: "{url}"')
            return

        self.url['text'] = url
        self.update_proxies()
        worker = Thread(target=self.fetch_video_meta, args=(video_id,))
        worker.start()

    def fetch_video_meta(self, video_id):
        self.enable_ui(False)
        try:
            self.fetch_video_meta_impl(video_id)
        except Exception as e:
            show_error(e)
        finally:
            self.enable_ui()

    def fetch_video_meta_impl(self, video_id):
        url = f'https://www.youtube.com/get_video_info?video_id={video_id}'
        r = requests.get(url, proxies=self.proxies, timeout=10)
        if r.status_code != 200:
            raise Exception(f'HTTP {r.status_code}')

        self.extract_download_link(r.text)

    def extract_download_link(self, data):
        params = parse_qs(data)
        info = params['player_response'][0]
        info = json.loads(info)
        formats = info['streamingData']['formats']
        title = info['videoDetails']['title']

        quality_items = []
        self.download_src = {}
        for item in formats:
            lable = item['qualityLabel']
            quality_items.append(lable)
            self.download_src[lable] = item['url']

        self.title['text'] = title
        self.quality['values'] = quality_items
        prefer = '720p'
        if prefer in quality_items:
            self.quality.set(prefer)
        else:
            self.quality.current(0)

    def update_proxies(self):
        http_proxy = 'http://localhost:1080'
        self.proxies = {
            'http': http_proxy,
            'https': http_proxy,
        }

    def on_download(self):
        path = self.get_save_path()
        if not path:
            return

        selected = self.quality.get()
        url = self.download_src.get(selected)
        if not url:
            return

        worker = Thread(target=self.start_download, args=(url, path))
        worker.start()

    def get_save_path(self):
        name = filter_filename(self.title['text'])
        return filedialog.asksaveasfilename(
            initialfile=name,
            defaultextension=".mp4",
            filetypes=(("*.mp4", "*.mp4"),)
        )

    def start_download(self, url, path):
        dl_path = path + '.download'
        self.enable_ui(False)
        try:
            self.download_write_file(url, dl_path)
            os.rename(dl_path, path)
            messagebox.showinfo(message=f'download has completed! ({path})')
        except Exception as e:
            show_error(e)
        finally:
            if os.path.isfile(dl_path):
                os.remove(dl_path)

            self.progress['value'] = 0
            self.enable_ui()

    def download_write_file(self, url, path):
        with open(path, "wb") as f:
            response = requests.get(url, proxies=self.proxies, stream=True)
            total_length = response.headers.get('content-length')
            if not total_length:
                raise Exception('unknown content-length')

            dl = 0
            total_length = int(total_length)
            for data in response.iter_content(chunk_size=4096):
                dl += len(data)
                f.write(data)
                done = int(100 * dl / total_length)
                self.progress['value'] = done


frame = AppFrame()
frame.init_ui()
frame.mainloop()
