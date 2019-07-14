import base64
import re
import time
import socket
import functools
import requests
import urllib.parse as uparse


def my_b64_decode(data):
    d = data.replace('_', '/').replace('-', '+')
    return base64.b64decode(d.strip() + '==').decode("utf-8")


def my_b64_url_encode(s):
    return base64.urlsafe_b64encode(s.encode('utf-8')).decode('utf-8')


def my_split_no_empty(obj, sep):
    return list(filter(len, obj.split(sep)))


def parse_proxy_item(uri):
    ssr_scheme = 'ssr://'
    uri_b64 = my_split_no_empty(uri, ssr_scheme)[0]

    conf = re.split('/', my_b64_decode(uri_b64))
    ss_conf = conf[0]
    ssr_conf = conf[1]

    ss_part = ss_conf.split(':', 1)
    ssr_part = uparse.parse_qsl(uparse.urlsplit(ssr_conf).query)

    return ss_part, dict(ssr_part)


class ProxyItemParser:
    def __init__(self):
        self.server = ''
        self.server_ip = ''

    def replace_server(self, host):
        self.server = host
        try:
            ip = socket.gethostbyname(host)
            self.server_ip = ip
            return ip
        except socket.gaierror:
            return server

    def replace_remark(self):
        def replace():
            if not self.server_ip:
                return self.server + '(DNS)'

            url = 'https://freeapi.ipip.net/' + self.server_ip
            print(url)

            try:
                r = requests.get(url)
                time.sleep(0.5)
            except requests.exceptions.RequestException:
                return self.server_ip + '(GET)'

            if r.status_code != 200:
                return self.server_ip + '(API)'

            j = r.json()
            item = j[0]
            if j[1] and j[1] != j[0]:
                item += ','
                item += j[1]
            if j[4]:
                item += ','
                item += j[4].split('/')[0]

            return item

        return my_b64_url_encode(replace())


def item_conv_impl(group, item):
    parser = ProxyItemParser()
    server_host = parser.replace_server(item[0][0])
    item[1]['remarks'] = parser.replace_remark().replace('=', '')
    item[1]['group'] = group.replace('=', '')

    return server_host + ':' + item[0][1], item[1]


def parse_feed_item(feed, group_name):
    all_lines = my_split_no_empty(my_b64_decode(feed), '\n')
    proxy_items = list(map(parse_proxy_item, all_lines))
    proxy_items = {a[0]: (a, b) for a, b in proxy_items[2:]}
    proxy_items = [v for k, v in proxy_items.items()]

    group = my_b64_url_encode(group_name)
    item_conv = functools.partial(item_conv_impl, group)
    return list(map(item_conv, proxy_items))


def encode_feed_item(items):
    def encode_proxy_item(item):
        raw_data = item[0] + '/?' + uparse.urlencode(item[1])
        return 'ssr://' + my_b64_url_encode(raw_data)

    items.sort(key=lambda x: x[1]['remarks'])
    items = list(map(encode_proxy_item, items))

    new_feed_raw = '\n'.join(items)
    return my_b64_url_encode(new_feed_raw)


def convert_feed(url, group_name):
    try:
        r = requests.get(url)
    except requests.exceptions.RequestException:
        print('Failed to connect to server')
        return None

    if r.status_code != 200:
        print('Invalid status code')
        return None

    items = parse_feed_item(r.text, group_name)
    new_feed = encode_feed_item(items)
    return new_feed

# Usage:
# convert_feed('https://example.com/feed.txt', 'GroupName')
