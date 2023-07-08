import os
import re
import asyncio
import aiohttp
from aiohttp_socks import ProxyConnector


def http_session(timeout=5):
    connector = ProxyConnector.from_url('http://127.0.0.1:1080')
    timeout_ = aiohttp.ClientTimeout(total=timeout)
    return aiohttp.ClientSession(
        connector=connector, timeout=timeout_)


class FileChecker:
    def __init__(self, base_url, files):
        self.base_url = base_url
        self.files = files
        self.file_total = len(files)
        self.file_done = 0
        self.file_720 = 0
        self.result = {}

    @staticmethod
    async def http_req_impl(url):
        async with http_session() as session:
            async with session.get(url) as resp:
                return resp.status

    async def http_req(self, url):
        for i in range(10):
            try:
                return await self.http_req_impl(url)
            except Exception as e:
                print('\t' * 4 + f'{type(e).__name__}: {e}')
                await asyncio.sleep(1)

        raise Exception('retry too many times!')

    def make_url(self, file, quality):
        return f'{self.base_url}/hls_{quality}p/{file}'

    async def check_file(self, file):
        status = await self.http_req(self.make_url(file, 1080))
        if status == 200:
            return True

        assert status == 404
        status = await self.http_req(self.make_url(file, 720))
        assert status == 200
        self.file_720 += 1
        print(f'[*] found 720p: {file}')
        return False

    async def worker(self):
        while True:
            try:
                file = self.files.pop(0)
                self.file_done += 1
            except IndexError:
                return

            if self.file_done % 10 == 0:
                progress = self.file_done * 100 // self.file_total
                print(f'[{progress}% done]')

            self.result[file] = await self.check_file(file)

    def start(self, worker_number):
        assert worker_number < 100
        workers = [self.worker() for i in range(worker_number)]
        future = asyncio.gather(*workers)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(future)


def fetch_playlist(url):
    async def fetch():
        async with http_session() as session:
            async with session.get(url) as resp:
                assert resp.status == 200
                return await resp.text()

    loop = asyncio.get_event_loop()
    return loop.run_until_complete(fetch())


def check_ts_files(content, base_url):
    files = []

    for line in content.splitlines():
        if line.startswith('#'):
            continue
        assert line.endswith('.ts'), line
        files.append(line)

    checker = FileChecker(base_url, files)
    checker.start(20)
    return checker


def make_new_file(content, checker, file_path):
    def convert(line):
        if line.startswith('#'):
            return line
        quality = 1080 if checker.result[line] else 720
        return checker.make_url(line, quality)

    new_lines = map(convert, content.splitlines())
    new_lines = '\n'.join(new_lines)

    with open(file_path, 'w') as file:
        file.write(new_lines)


def main():
    if os.name == 'nt':
        policy = asyncio.WindowsSelectorEventLoopPolicy()
        asyncio.set_event_loop_policy(policy)

    url = input('playlist.m3u8: ').strip()
    matched = re.match(r'(.*)/hls_[0-9]+p/playlist\.m3u8$', url)
    base_url = matched.group(1)

    content = fetch_playlist(url)
    checker = check_ts_files(content, base_url)
    make_new_file(content, checker, 'new.m3u8')
    print(f'[complete! {checker.file_720}/{checker.file_total}]')


if __name__ == '__main__':
    main()
