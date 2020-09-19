# Check domain from aaa.su, aab.su... to zzz.su

# Requirements:
#   aiohttp aiohttp-socks

import os
import asyncio
import aiohttp
import logging

from itertools import cycle
from aiohttp_socks import ProxyConnector

logger = None


def fmt_exc(exc):
    return f'{type(exc).__name__}: "{exc}"'


def num2str_base(num, base_symbols, width=None):
    base = len(base_symbols)
    assert base > 1

    def encode(n):
        return str(base_symbols[n])

    def impl(num):
        if num < base:
            return encode(num)
        else:
            return impl(num // base) + encode(num % base)

    result = impl(num)
    if isinstance(width, int):
        fill_width = width - len(result)
        if fill_width > 0:
            return base_symbols[0] * fill_width + result

    return result


def str2num_base(num_str, base_symbols):
    base = len(base_symbols)
    symbol2num = {}
    for i in range(base):
        symbol2num[base_symbols[i]] = i

    result = 0
    tokens = list(reversed(num_str))
    for i in range(len(tokens)):
        result += symbol2num[tokens[i]] * (base ** i)

    return result


class TaskAllocator:
    BASE_SYMBOLS = [chr(ord('a') + i) for i in range(26)]

    def __init__(self, name_begin, name_end):
        assert len(name_begin) == len(name_end)
        self.domain_width = len(name_begin)
        self.task_begin = self.str2num(name_begin)
        self.task_end = self.str2num(name_end)

    def str2num(self, num_str):
        return str2num_base(num_str, self.BASE_SYMBOLS)

    def num2str(self, num):
        return num2str_base(num, self.BASE_SYMBOLS, self.domain_width)

    def get(self, max_task_num=1):
        logger.info(f'TaskAllocator: [{self.task_begin}/{self.task_end}]')

        assert 1 <= max_task_num <= 100
        tasks = []
        for i in range(max_task_num):
            if self.task_begin > self.task_end:
                break

            tasks.append(self.task_begin)
            self.task_begin += 1

        return [self.num2str(t) for t in tasks]


class ProxyAllocator:
    def __init__(self):
        self.proxies = []
        self.read_by_lines('socks5', 'socks5.txt')
        self.read_by_lines('socks4', 'socks4.txt')
        self.proxies_itor = cycle(self.proxies)

    def read_by_lines(self, type_, filename):
        with open(filename) as f:
            lines = f.readlines()

        for line in lines:
            line = line.strip()
            if not line:
                continue

            self.proxies.append((type_, line))

    def get(self):
        type_, server_port = next(self.proxies_itor)
        proxy = f'{type_}://{server_port}'
        logger.info(f'ProxyAllocator: {proxy}')
        return proxy


class Checker:
    def __init__(self, bus):
        self.bus = bus
        self.proxy = None
        self.first_call_api = True

    @staticmethod
    def build_payload(names):
        return {
            'ru': 0,
            'is_bulk_registration': 0,
            'bulk_procedure': 1,
            'istransfer': 0,
            'domains': ' '.join(names),
            'fake_responses': 0,
        }

    async def call_api(self, names):
        if self.first_call_api:
            self.first_call_api = False
        else:
            await asyncio.sleep(1)

        if not self.proxy:
            self.proxy = self.bus.proxy_allocator.get()

        connector = ProxyConnector.from_url(self.proxy)
        timeout = aiohttp.ClientTimeout(total=10)
        url = 'https://www.reg.com/domain/new/check_queue'
        payload = self.build_payload(names)

        try:
            async with aiohttp.ClientSession(
                    connector=connector, timeout=timeout) as session:
                async with session.post(url, data=payload) as resp:
                    return resp.status, (await resp.json())
        except Exception as e:
            logger.warning(f'call_api: {fmt_exc(e)}')
            self.proxy = None
            return None, {}

    async def run(self):
        assigner = self.bus.task_allocator
        while True:
            tasks = [x + '.su' for x in assigner.get(3)]
            if not tasks:
                break

            while tasks:
                code, result = await self.call_api(tasks)
                if code is None:
                    continue

                if code != 200:
                    logger.warning(f'code {code} with {tasks}')
                    self.proxy = None
                    continue

                domains = result.get('domains')
                if domains is None:  # {'error': 'LIMIT_EXCEEDED'}
                    logger.error(f'result: {result}')
                    self.proxy = None
                    continue

                for item in result['domains']:
                    domain = item['domain']
                    tasks.remove(domain)
                    logger.info(f'{domain} => {item["error_code"]}')
                    if item['avail']:
                        self.bus.add_available(domain)


class CheckerBus:
    def __init__(self):
        self.task_allocator = TaskAllocator('aaa', 'zzz')
        self.proxy_allocator = ProxyAllocator()
        self.available_domains = open('available_domains.txt', 'a')

    def add_available(self, domain):
        self.available_domains.write(domain + '\n')
        self.available_domains.flush()

    def bulk_checker_loop(self, worker_num):
        assert 1 <= worker_num <= 200

        async def checker():
            await Checker(self).run()

        workers = [checker() for i in range(worker_num)]
        future = asyncio.gather(*workers)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(future)

    def start(self):
        try:
            self.bulk_checker_loop(100)
        finally:
            self.available_domains.close()


def main():
    FORMAT = '[%(asctime)s] [%(levelname)s] %(message)s'
    logging.basicConfig(format=FORMAT)
    logger_ = logging.getLogger(__name__)
    logger_.setLevel(logging.DEBUG)
    global logger
    logger = logger_

    if os.name == 'nt':
        policy = asyncio.WindowsSelectorEventLoopPolicy()
        asyncio.set_event_loop_policy(policy)

    CheckerBus().start()


if __name__ == '__main__':
    main()
