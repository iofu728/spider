# -*- coding: utf-8 -*-
# @Author: gunjianpan
# @Date:   2018-10-19 15:33:46
# @Last Modified by:   gunjianpan
# @Last Modified time: 2018-10-20 16:47:10

import requests
from bs4 import BeautifulSoup
import time


headers = {
    'Connection': 'keep-alive',
    'Cache-Control': 'no-cache',
    'Upgrade-Insecure-Requests': '1',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Connection": "keep-alive",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3578.0 Safari/537.36"}

start = 0


def get_html(url, proxies, host):
    """
    get html
    @url requests.url
    @proxys requests.proxys
    @return beautifulSoup analysis result
    """
    headers['Host'] = host
    try:
        if len(proxies):
            html = requests.get(url, headers=headers, verify=False,
                                timeout=5, proxies=proxproxiesys).text
        else:
            html = requests.get(url, headers=headers,
                                verify=False, timeout=5).text

        return BeautifulSoup(html, 'html.parser')
    except Exception as e:
        return BeautifulSoup('<html></html>', 'html.parser')


def get_json(url, proxies, host):
    """
    get json
    @url requests.url
    @proxys requests.proxys
    @return json
    """
    headers['Host'] = host
    try:
        if len(proxies):
            json = requests.get(url, headers=headers, verify=False,
                                timeout=3, proxies=proxies).json()
        else:
            json = requests.get(url, headers=headers,
                                verify=False, timeout=3).json()

        return json
    except Exception as e:
        return {}


def begin_time():
    global start
    start = time.time()


def end_time():
    print(time.time() - start)
