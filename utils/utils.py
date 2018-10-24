# -*- coding: utf-8 -*-
# @Author: gunjianpan
# @Date:   2018-10-19 15:33:46
# @Last Modified by:   gunjianpan
# @Last Modified time: 2018-10-24 13:16:42

import requests
from bs4 import BeautifulSoup
import time
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

headers = {
    'Connection': 'keep-alive',
    'Cache-Control': 'no-cache',
    'Upgrade-Insecure-Requests': '1',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Connection": "keep-alive",
    "Sec-Metadata": "cause=forced, destination=document, site=cross-site",
    # :todo: change user-agent
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3586.0 Safari/537.36"}

start = 0


def get_html(url, proxies, host):
    """
    get html
    @url requests.url
    @proxys requests.proxys
    @host header host
    @return beautifulSoup analysis result
    """
    headers['Host'] = host

    if len(proxies):
        # print(proxies)
        html = requests.get(url, headers=headers, verify=False,
                            timeout=3, proxies=proxies).text
    else:
        try:
            html = requests.get(url, headers=headers,
                                verify=False, timeout=3).text
        except Exception as e:
            return BeautifulSoup('<html></html>', 'html.parser')

    return BeautifulSoup(html, 'html.parser')


def get_json(url, proxies, host):
    """
    get json
    @url requests.url
    @proxys requests.proxys
    @host header host
    @return json
    """
    headers['Host'] = host
    if len(proxies):
        json = requests.get(url, headers=headers, verify=False,
                            timeout=2, proxies=proxies).json()
    else:
        json = requests.get(url, headers=headers,
                            verify=False, timeout=2).json()
    return json


def begin_time():
    global start
    start = time.time()


def end_time():
    print(time.time() - start)
