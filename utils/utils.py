# -*- coding: utf-8 -*-
# @Author: gunjianpan
# @Date:   2018-10-19 15:33:46
# @Last Modified by:   gunjianpan
# @Last Modified time: 2019-02-28 10:06:47

import requests
from bs4 import BeautifulSoup
import time
import urllib3
import random

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

headers = {
    'pragma': 'no-cache',
    # 'sec-fetch-dest': 'empty',
    # 'sec-fetch-site': 'same-origin',
    # 'sec-fetch-user': '?F',
    # 'sec-origin-policy': '0',
    # 'upgrade-insecure-requests': '1',
    # 'X-Requested-With': 'XMLHttpRequest',
    'cache-control': 'no-cache',
    'Cookie': '',
    # 'Upgrade-Insecure-Requests': '1',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3',
    "Accept-Encoding": "",
    "Accept-Language": "zh-CN,zh;q=0.9",
    # :todo: change user-agent
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3682.0 Safari/537.36"}

start = 0

file = open('utils/agent', 'r').readlines()
agent_lists = [" ".join(index.split()[1:])[1:-1] for index in file]
agent_len = len(agent_lists) - 1
html_timeout = 5


def get_html(url, proxies):
    """
    get html
    @url requests.url
    @proxys requests.proxys
    @host header host
    @return beautifulSoup analysis result
    """
    headers['Host'] = url.split('/')[2]
    index = random.randint(0, agent_len)
    headers['User-Agent'] = agent_lists[index]

    if len(proxies):
        html = requests.get(url, headers=headers, verify=False,
                            timeout=html_timeout, proxies=proxies, allow_redirects=False)
        if html.status_code == 301 or html.status_code == 302:
            url = BeautifulSoup(html.text, 'html.parser').a['href']
            print(url)
            headers['Host'] = url.split('/')[2]
            html = requests.get(url, headers=headers, verify=False,
                                timeout=html_timeout, proxies=proxies, allow_redirects=False)
        if html.apparent_encoding == 'utf-8' or 'gbk' in html.apparent_encoding:
            html.encoding = html.apparent_encoding
        html = html.text
    else:
        try:
            html = requests.get(url, headers=headers,
                                verify=False, timeout=3, allow_redirects=False)
            if html.status_code == 301 or html.status_code == 302:
                print(url)
                url = BeautifulSoup(html.text, 'html.parser').a['href']
                headers['Host'] = url.split('/')[2]
                html = requests.get(url, headers=headers, verify=False,
                                    timeout=html_timeout, allow_redirects=False)
            if html.apparent_encoding == 'utf-8' or 'gbk' in html.apparent_encoding:
                html.encoding = html.apparent_encoding
            html = html.text
        except Exception as e:
            print('Error')
            return BeautifulSoup('<html></html>', 'html.parser')
    # print(html)
    return BeautifulSoup(html, 'html.parser')


def get_json(url, proxies):
    """
    get json
    @url requests.url
    @proxys requests.proxys
    @host header host
    @return json
    """
    headers['Host'] = url.split('/')[2]
    index = random.randint(0, agent_len)
    headers['User-Agent'] = agent_lists[index]
    if len(proxies):
        try:
            json = requests.get(url, headers=headers, verify=False,
                                timeout=5, proxies=proxies).json()
            return json
        except Exception as e:
            return
    else:
        try:
            json = requests.get(url, headers=headers,
                                verify=False, timeout=5).json()
            return json
        except Exception as e:
            return


def post_json(url, data, proxies):
    """
    post json
    @url requests.url
    @proxies requests.proxys
    @data form-data
    @return json
    """
    headers['Host'] = url.split('/')[2]
    index = random.randint(0, agent_len)
    headers['User-Agent'] = agent_lists[index]
    if len(proxies):
        try:
            json = requests.post(url, headers=headers, verify=False, data=data,
                                 timeout=30, proxies=proxies).json()
            return json
        except Exception as e:
            return
    else:
        try:
            json = requests.post(url, headers=headers, data=data,
                                 verify=False, timeout=30).json()
            return json
        except Exception as e:
            return


def get_basic(url, proxies):
    """
    get img
    @url requests.url
    @proxys requests.proxys
    @host header host
    @return basic
    """
    headers['Accept'] = 'image/webp,image/apng,image/*,*/*;q=0.8'
    headers['Sec-Fetch-Dest'] = 'image'
    headers['Host'] = url.split('/')[2]
    index = random.randint(0, agent_len)
    headers['User-Agent'] = agent_lists[index]
    if len(proxies):
        try:
            basic = requests.get(url, headers=headers, verify=False,
                                 timeout=30, proxies=proxies)
            return basic
        except Exception as e:
            print('Error')
    else:
        try:
            basic = requests.get(url, headers=headers,
                                 verify=False, timeout=30)
            return basic
        except Exception as e:
            print('Error')


def changeCookie(cookie):
    """
    change cookie
    """
    global headers
    headers['Cookie'] = cookie


def changeHeaders(header):
    """
    change Headers
    """
    global headers
    headers = {**headers, **header}


def changeHtmlTimeout(timeout):
    """
    change html timeout
    """
    global html_timeout
    html_timeout = timeout


start = []
spendList = []
failured_map = {}


def begin_time():
    """
    multi-version time manage
    """
    global start
    start.append(time.time())
    return len(start) - 1


def end_time_avage(version):
    termSpend = time.time() - start[version]
    spendList.append(termSpend)
    print(str(termSpend)[0:5] + ' ' +
          str(sum(spendList) / len(spendList))[0:5])


def end_time(version):
    termSpend = time.time() - start[version]
    print(str(termSpend)[0:5])


def spend_time(version):
    return str(time.time() - start[version])[0:5]


def empty():
    spendList = []


def can_retry(url, index=None):
    """
    judge can retry once
    """

    global failured_map

    if url not in failured_map:
        failured_map[url] = 0
        # print("Retry " + str(self.failured_map[url]) + ' ' + url)
        return True
    elif failured_map[url] < 2:
        failured_map[url] += 1
        # print("Retry " + str(self.failured_map[url]) + ' ' + url)
        return True
    else:
        if index is not None:
            index = str(index)
        print("Failured " + url)
        failured_map[url] = 0
        return False
