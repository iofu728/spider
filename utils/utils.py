# -*- coding: utf-8 -*-
# @Author: gunjianpan
# @Date:   2018-10-19 15:33:46
# @Last Modified by:   gunjianpan
# @Last Modified time: 2019-01-31 19:57:46

import requests
from bs4 import BeautifulSoup
import time
import urllib3
import random

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

headers = {
    'pragma': 'no-cache',
    'sec-fetch-dest': 'empty',
    'sec-fetch-site': 'same-origin',
    'sec-fetch-user': '?F',
    # 'sec-origin-policy': '0',
    # 'upgrade-insecure-requests': '1',
    'X-Requested-With': 'XMLHttpRequest',
    'cache-control': 'no-cache',
    'Cookie': '_yadk_uid=k8KAOQIUGyO4c4rVCUlNqIUA4kUFDRYi; OUTFOX_SEARCH_USER_ID_NCOO=1474393958.8972402; OUTFOX_SEARCH_USER_ID="286391570@10.168.17.188"; _ga=GA1.2.638310443.1538404678; _ntes_nnid=3cad562c4927812c1dddd9c50d2fbc0f,1539430622809; Hm_lvt_30b679eb2c90c60ff8679ce4ca562fcc=1539738828,1541134733; UM_distinctid=16827203c6c21c-0d26720168820b-6c350b7c-1aeaa0-16827203c6dba3; P_INFO=iofu728@163.com|1547088005|0|youdao_zhiyun2018|00&99|bej&1546844692&search#US&null#10#0#0|178950&0|search&mail163|iofu728@163.com; Hm_lvt_daa6306fe91b10d0ed6b39c4b0a407cd=1548683344; JSESSIONID=aaaAfmUj78kvK9pC1orIw; YNOTE_SESS=v2|8VIMwTO_xRpLnfU50fwuRkW0fJLRfw40eLRHwK0H6FRkY0MJLP4guR6ukLJK6LYWRPyhMeFRMUG06Zh4UEk4PS0e4PMPLRMeLR; YNOTE_PERS=v2|urstoken||YNOTE||web||-1||1548734008314||103.192.227.202||iofu728@163.com||Y5hfOEOMzm0Ju0LJLnHUA0OfkfpZhLkM0TBn4PLhMpy0gB0MzMO4TF0PuO4kEPLJy0g4nLqzhHwy06FOLeBOfJBR; YNOTE_CSTK=S0RcfVHi; _gid=GA1.2.1164334667.1548840559; arp_scroll_position=0; _gat=1; Hm_lpvt_daa6306fe91b10d0ed6b39c4b0a407cd=1548929812; YNOTE_LOGIN=5||1548929814020',
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
        print(proxies)
        html = requests.get(url, headers=headers, verify=False,
                            timeout=3, proxies=proxies, allow_redirects=False)
        if html.status_code == 301 or html.status_code == 302:
            url = BeautifulSoup(html.text, 'html.parser').a['href']
            headers['Host'] = url.split('/')[2]
            html = requests.get(url, headers=headers, verify=False,
                                timeout=3, proxies=proxies, allow_redirects=False)

        html.encoding = html.apparent_encoding
        html = html.text
    else:
        try:
            html = requests.get(url, headers=headers,
                                verify=False, timeout=3, allow_redirects=False)
            if html.status_code == 301 or html.status_code == 302:
                url = BeautifulSoup(html.text, 'html.parser').a['href']
                headers['Host'] = url.split('/')[2]
                html = requests.get(url, headers=headers, verify=False,
                                    timeout=3, allow_redirects=False)
            html.encoding = html.apparent_encoding
            html = html.text
        except Exception as e:
            print('Error')
            return BeautifulSoup('<html></html>', 'html.parser')

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
        json = requests.get(url, headers=headers, verify=False,
                            timeout=2, proxies=proxies).json()
    else:
        json = requests.get(url, headers=headers,
                            verify=False, timeout=2).json()
    return json


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
        basic = requests.get(url, headers=headers, verify=False,
                             timeout=30, proxies=proxies)
    else:
        basic = requests.get(url, headers=headers,
                             verify=False, timeout=30)
    return basic


start = []
spendList = []


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
