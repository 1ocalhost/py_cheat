import re
import json
import requests


class Moji7dayParser:
    def __init__(self):
        self.begin_token = '7天预报'
        self.per_day_token_num = 6
        self.token_num = self.per_day_token_num * 7 + 1
        self.token_catching = False
        self.token_result = []

    def parse(self, match):
        if self.token_num <= 0:
            return

        token = match.group(1)
        if all(c in ['\n', ' '] for c in token):
            return

        if token == self.begin_token:
            self.token_catching = True
            return

        if self.token_catching:
            self.token_result.append(token)
            self.token_num -= 1
            return

    def result(self):
        data = self.token_result
        token_len = self.per_day_token_num

        update_time = data[0]
        data = self.token_result[1:]

        forecast = [data[x: x + token_len]
                    for x in range(0, len(data), token_len)]

        return json.dumps({'update': update_time,
                          'forecast': forecast})


def parse_moji_7day_forecast(url):
    r = requests.get(url)
    assert(r.status_code == 200)

    parser = Moji7dayParser()
    re.sub('>([^<>]+)</', parser.parse, r.text)
    return parser.result()


# usage:
# url = 'https://tianqi.moji.com/forecast7/china/sichuan/qingyang-district'
# print(parse_moji_7day_forecast(url))
