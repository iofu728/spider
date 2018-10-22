# -*- coding: utf-8 -*-
# @Author: gunjianpan
# @Date:   2018-10-21 11:00:24
# @Last Modified by:   gunjianpan
# @Last Modified time: 2018-10-22 09:17:39

import threading

from bs4 import BeautifulSoup
from proxy.getproxy import GetFreeProxy
from utils.db import Db
from utils.utils import begin_time, end_time


class Get_playlist_song():
    """
    1. get playlist id from classify;
    2. get song from play list;
    use url:
    """

    def __init__(self):
        self.Db = Db()
        self.classifylist = {}
        self.proxyclass = GetFreeProxy()
        self.playlists = []
        self.get_classify()
        self.select_one = '''SELECT * from playlist_queue WHERE `playlist_id` = %ld'''
        self.insert_sql = '''INSERT INTO playlist_queue(`playlist_id`, `classify`) VALUES (%ld, '%s')'''

    def get_classify(self):
        """
        get classify from /discover/playlist
        """

        begin_time()
        self.classifylist = {}
        host = 'https://music.163.com/discover/playlist'
        html = self.proxyclass.get_request_proxy(host, host[8:21], 0)

        if not html:
            print('Empty')
            self.proxyclass.cleancannotuse()
            return []

        alist = html.find_all('a', class_='s-fc1')
        if not len(alist):
            print(html)
        for index in alist:
            self.classifylist[index.text] = index['href']
        self.proxyclass.cleancannotuse()
        end_time()

    def get_playlist_id(self, classify, offset):
        """
        get playlist id from classify
        """

        host = 'https://music.163.com'
        allclassify = classify == '全部风格'
        url = host + self.classifylist[classify] + (
            '?' if allclassify else '&') + 'order=hot&limit=35&offset=' + str(offset)
        html = self.proxyclass.get_request_proxy(url, host[8:], 0)

        if not html:
            return []
        alist = html.find_all('a', class_='icon-play')
        if not len(alist):
            print(html)
        for index in alist:
            temp = [classify, index['data-res-id']]
            self.playlists.append(temp)

    def get_playlist_id_thread(self):
        """
        get play list id in threading
        """

        begin_time()
        if not len(self.classifylist):
            self.get_classify()

        for index in self.classifylist:
            threadings = []
            for offset in range(41):
                work = threading.Thread(
                    target=self.get_playlist_id, args=(index, offset,))
                threadings.append(work)
            for work in threadings:
                work.start()
            for work in threadings:
                work.join()
            self.proxyclass.cleancannotuse()
            for ids in self.playlists:
                self.test_queue(ids)
            self.playlists = []
            print(index + " Over")
        end_time()

    def test_queue(self, ids):
        """
        test data if in playlist_queue
        """

        results = self.Db.select_db(self.select_one % int(ids[1]))
        if results != 0 and not len(results):
            print('Insert ' + ids[0] + ' ' + str(ids[1]))
            self.insert_queue(ids)
        else:
            pass

    def insert_queue(self, ids):
        """
        insert data to playlist_queue
        """

        results = self.Db.insert_db(self.insert_sql % (int(ids[1]), ids[0]))
        if results:
            print('Insert ' + ids[0] + ' ' + str(ids[1]) + ' Success!')
        else:
            pass
