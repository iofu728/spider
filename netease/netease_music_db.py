# -*- coding: utf-8 -*-
# @Description: V2 netease spider
# @Author: gunjianpan
# @Date:   2018-10-21 11:00:24
# @Last Modified by:   gunjianpan
# @Last Modified time: 2018-11-16 00:00:11

import codecs
import threading

from bs4 import BeautifulSoup
from proxy.getproxy import GetFreeProxy
from utils.db import Db
from utils.utils import begin_time, get_html, end_time


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
        self.failuredmap = {}
        self.songmap = {}
        self.songlist = []
        self.finishlist = []
        self.get_classify()
        self.select_one = '''SELECT playlist_id from playlist_queue WHERE `playlist_id` in %s AND classify = '%s' '''
        self.select_ids = '''SELECT `id`, playlist_id from playlist_queue WHERE classify = '%s' AND is_finished = 0 '''
        self.select_song = '''SELECT `id`, `song_id`, `time`, `play_time` from playlist_detail WHERE song_id in %s AND classify = '%s' '''
        self.insert_sql = '''INSERT INTO playlist_queue(`playlist_id`, `classify`) VALUES %s'''
        self.insert_song = '''LOAD DATA INFILE '/Users/gunjianpan/Desktop/git/spider/song_detail' INTO TABLE playlist_detail FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' LINES TERMINATED BY '\n' (`song_id`, `song_name`, `classify`, `time`, `play_time`)'''  # change to your file absolute address
        self.replace_song = '''REPLACE INTO playlist_detail(`id`,`song_id`,`classify`,`song_name`,`time`,`play_time`) VALUES %s'''
        self.replace_queue = '''REPLACE INTO playlist_queue(`id`, `playlist_id`, `classify`, `is_finished`) VALUES %s'''

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
            if self.can_retry(host):
                self.get_classify()
            return []

        alist = html.find_all('a', class_='s-fc1')
        if not len(alist):
            if self.can_retry(host):
                self.get_classify()
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
        # html = self.proxyclass.get_request_proxy(url, host[8:], 0)
        html = get_html(url, {}, host[8:])

        if not html:
            if self.can_retry(url):
                self.get_playlist_id(classify, offset)
            else:
                self.proxyclass.log_write(url)
            return []
        alist = html.find_all('a', class_='icon-play')
        if not len(alist):
            if self.can_retry(url):
                self.get_playlist_id(classify, offset)
            else:
                self.proxyclass.log_write(url)
        for index in alist:
            self.playlists.append(index['data-res-id'])

    def can_retry(self, url):
        """
        judge can retry once
        """

        if url not in self.failuredmap:
            self.failuredmap[url] = 0
            # print("Retry " + str(self.failuredmap[url]) + ' ' + url)
            return True
        elif self.failuredmap[url] < 2:
            self.failuredmap[url] += 1
            # print("Retry " + str(self.failuredmap[url]) + ' ' + url)
            return True
        else:
            print("Failured " + url)
            self.proxyclass.log_write(url)
            self.failuredmap[url] = 0
            return False

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
                    target=self.get_playlist_id, args=(index, offset * 35,))
                threadings.append(work)
            for work in threadings:
                work.start()
            for work in threadings:
                work.join()
            self.proxyclass.cleancannotuse()
            print(len(self.playlists))
            self.test_queue(index)
            self.playlists = []
            print(index + " Over")
        end_time()

    def test_queue(self, classify):
        """
        test data if in playlist_queue
        """
        if len(self.playlists) == 1:
            waitlist = '(' + str(self.playlists[0]) + ')'
        else:
            waitlist = tuple(self.playlists)
        results = self.Db.select_db(self.select_one %
                                    (str(waitlist), classify))
        if not results:
            return []
        hadexist = []
        for index in results:
            hadexist.append(index[0])
        insertlist = []
        for index in self.playlists:
            if index not in hadexist:
                # file_d.write(str([index, classify])[1:-1] + '\n')
                insertlist.append((index, classify))
        print('Insert ' + str(len(insertlist)) + ' ' + classify)
        self.insert_queue(insertlist)

    def insert_queue(self, ids):
        """
        insert data to playlist_queue
        """

        if not len(ids):
            return []
        results = self.Db.insert_db(self.insert_sql % str(ids)[1:-1])
        if results:
            if len(ids):
                print('Insert ' + ids[0][1] + ' ' +
                      str(len(ids)) + ' Success!')
        else:
            pass

    def get_list_ids(self, classify):
        """
        get list ids from db
        """
        results = self.Db.select_db(self.select_ids % classify)
        ids = []
        if results:
            for index in results:
                ids.append([index[0], index[1]])
        return ids

    def get_song_detail_thread(self):
        """
        get song detail threadings
        """

        begin_time()
        for classify in self.classifylist:
            ids = self.get_list_ids(classify)
            threadings = []
            for oneid in ids:
                work = threading.Thread(
                    target=self.get_song_detail, args=(oneid[1],))
                threadings.append(work)
            for work in threadings:
                work.start()
            for work in threadings:
                work.join()
            self.clean_data()
            self.test_song(classify, ids)
            self.songlist = []
            self.songmap = {}
            self.finishlist = []
            self.successtime = 0
            print(classify + ' Over!')
        end_time()

    def clean_data(self):
        """
        aggregation data
        """
        for song in self.songlist:
            [songid, songname, playcount] = song
            if songid not in self.songmap:
                self.songmap[songid] = [1, playcount, songname]
            else:
                orgin = self.songmap[songid]
                self.songmap[songid] = [orgin[0] + 1,
                                        orgin[1] + playcount, songname]

    def get_song_detail(self, id):
        """
        get song detail form playlist
        """

        host = 'http://music.163.com/api/playlist/detail?id=' + str(id)
        json = self.proxyclass.get_request_proxy(host, host[7:20], 1)
        if json == 0:
            if self.can_retry(host):
                self.get_song_detail(id)
            else:
                self.proxyclass.log_write(host)
            return []
        result = json['result']
        tracks = result['tracks']

        if len(tracks) <= 1:
            if self.can_retry(host):
                self.get_song_detail(id)
            else:
                self.proxyclass.log_write(host)
                return []
        else:
            playcount = result['playCount']
            for track in tracks:
                songid = track['id']
                songname = track['name']
                self.songlist.append([songid, songname, playcount])
            self.finishlist.append(id)

    def test_song(self, classify, ids):
        """
        test song if in db
        """
        songs = []
        for song in self.songmap:
            songs.append(song)
        if not len(songs):
            return []
        elif len(songs) == 1:
            waitlist = '(' + songs[0] + ')'
        else:
            waitlist = tuple(songs)
        results = self.Db.select_db(self.select_song %
                                    (str(waitlist), classify))
        resultmap = {}
        for detail in results:
            resultmap[detail[1]] = [detail[0], detail[2], detail[3]]

        replacelist = []
        insertlist = []
        replacequeue = []
        file_d = codecs.open("song_detail", 'a', encoding='utf-8')
        file_d.seek(0)
        file_d.truncate()
        idsmap = {}
        for indexid in ids:
            idsmap[indexid[1]] = indexid[0]
        for song in self.songmap:
            songdetail = self.songmap[song]
            if song in resultmap:
                dbdetail = resultmap[song]
                replacelist.append(
                    (dbdetail[0], song, classify, songdetail[2], songdetail[0] + dbdetail[1], songdetail[1] + dbdetail[2]))
            else:
                file_d.write(
                    u'' + str([song, u'' + str(u'' + songdetail[2].replace(',', ' '))[0:20], classify, songdetail[0], songdetail[1]])[1:-1] + '\n')
                insertlist.append(
                    (song, songdetail[2], classify, songdetail[0], songdetail[1]))
        for playlist in self.finishlist:
            replacequeue.append((idsmap[playlist], playlist, classify, 1))
        file_d.close()
        if len(insertlist):
            self.db_song_detail(insertlist, 'Insert', replacequeue)
        if len(replacelist):
            self.db_song_detail(replacelist, 'Update', [])

    def db_song_detail(self, waitlist, types, replacequeue):
        """
        batch insert/update song detail
        """

        if types == 'Update':
            results = self.Db.update_db(
                self.replace_song % str(blocklist)[1:-1])
        else:
            results = self.Db.update_db(self.insert_song)
        if results:
            if len(waitlist):
                print(types + ' song detail for ' +
                      waitlist[0][2] + ' ' + str(len(waitlist)) + ' Success!')
            if types == 'Insert':
                self.replace_queue_db(replacequeue)

    def replace_queue_db(self, replacequeue):
        """
        replace db for fininsh playlist id
        """

        results = self.Db.update_db(
            self.replace_queue % str(replacequeue)[1:-1])
        if results:
            if len(replacequeue):
                print('Update queue fininsh for ' +
                      str(len(replacequeue)) + ' item!')
        else:
            pass
