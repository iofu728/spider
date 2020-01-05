'''
@Author: gunjianpan
@Date:   2019-04-20 15:04:03
@Last Modified by:   gunjianpan
@Last Modified time: 2019-04-21 21:37:37
'''

import os
import re
import sys
import threading

sys.path.append(os.getcwd())
from proxy.getproxy import GetFreeProxy
from util.util import (begin_time, can_retry, echo, end_time,
                       shuffle_batch_run_thread)

proxy_req = GetFreeProxy().proxy_req
HOMEPAGE_URL = 'https://www.dytt8.net'
movie_list, movie_another, movie_again = [], [], []


def load_index():
    ''' load index '''
    global movie_list
    version = begin_time()
    text = proxy_req(HOMEPAGE_URL, 3)
    if not len(text):
        if can_retry(HOMEPAGE_URL):
            load_index()
        return
    movie_list = re.findall('《(.*?)》', text)
    movie_more = re.findall('href="(.*?)">更多', text)
    for uri in movie_more:
        load_other(uri)

    threading_list = [threading.Thread(
        target=load_other, args=(ii,)) for ii in movie_another]
    shuffle_batch_run_thread(threading_list, 100)
    threading_list = [threading.Thread(
        target=load_other, args=(ii,)) for ii in movie_again]
    shuffle_batch_run_thread(threading_list, 100)
    # 对电影列表去重
    movie_list = set(movie_list)
    # 导出爬取的 电影列表
    out_path = 'dytt8_result.txt'
    with open(out_path, 'w') as f:
        f.write('\n'.join(movie_list))
    url_num = len([*movie_more, *movie_another]) + 1
    movie_num = len(movie_list)
    echo(1, 'Requests num: {}\nMovie num: {}\nOutput path: {}\nSpend time: {:.2f}s\n'.format(
            url_num, movie_num, out_path, end_time(version, 0)))


def load_other(uri):
    ''' load other '''
    global movie_list, movie_another, movie_again
    url = HOMEPAGE_URL + uri if not 'http' in uri else uri
    text = proxy_req(url, 3)
    temp_list = re.findall('《(.*?)》', text)
    echo(2, 'loading', url, 'movie num:', len(temp_list))

    if text == '' or not len(temp_list):
        if can_retry(url):
            load_other(uri)
        else:
            movie_again.append(url)
        return
    if 'index' in url and '共' in text:
        total_page = re.findall('共(.*?)页', text)[0]
        suffix_str = re.findall(r"value=\'(.*?)1.html\' selected", text)[0]
        more_movie = [url.replace('index.html', '{}{}.html'.format(
            suffix_str, ii)) for ii in range(2, int(total_page) + 1)]
    else:
        more_movie = []
    movie_list += temp_list
    movie_another += more_movie


if __name__ == '__main__':
    load_index()
