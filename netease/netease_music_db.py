# -*- coding: utf-8 -*-
# @Author: gunjianpan
# @Date:   2018-10-21 11:00:24
# @Last Modified by:   gunjianpan
# @Last Modified time: 2018-10-21 11:55:54

import threading

from bs4 import BeautifulSoup
from proxy.getproxy import GetFreeProxy
from utils.utils import begin_time, end_time


class Get_playlist_song():
    """
    1. get playlist id from classify;
    2. get song from play list;
    use url:
    """

    def __init__(self):
        self.classifylist = {}
        self.proxyclass = GetFreeProxy()
        self.get_classify()

    def get_classify(self):
        """
        get classify from /discover/playlist
        """

        begin_time()
        host = 'https://music.163.com/discover/playlist'
        html = self.proxyclass.get_request_proxy(host, host[8:21], 0)

        alist = html.find_all('a', class_='s-fc1')
        for index in alist:
            self.classifylist[index.text] = index['href']
        print(self.classifylist)
        end_time()
