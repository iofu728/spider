# -*- coding: utf-8 -*-
# @Description: Get High Availability Proxy
# @Author: gunjianpan
# @Date:   2018-10-18 23:10:19
# @Last Modified by:   gunjianpan
# @Last Modified time: 2018-10-22 09:17:12
# -*- coding: utf-8 -*-
# !/usr/bin/env python

import functools
import pymysql
import random
import requests
import threading
import time

from apscheduler.schedulers.blocking import BlockingScheduler
from bs4 import BeautifulSoup
from utils.db import Db
from utils.utils import begin_time, end_time, get_html, get_json

"""
  * gatherproxy.com
  * goubanjia.com
    xicidaili.com
    data5u.com
    66ip.com
    kuaidaili.com
"""


class GetFreeProxy(object):
    """
    proxy getter
    """

    def __init__(self):
        self.Db = Db()
        self.insert_sql = '''INSERT INTO ip_proxy( `address`, `http_type`) VALUES ('%s',%d)'''
        self.select_not = '''SELECT * from ip_proxy WHERE `address` = '%s' AND `is_failured` < 5 AND http_type=%d'''
        self.select_list = '''SELECT address, http_type from ip_proxy WHERE `is_failured` = 0'''
        self.select_sql = '''SELECT * from ip_proxy WHERE `address` = '%s' AND http_type = %d '''
        self.select_all = '''SELECT * from ip_proxy WHERE `is_failured` != 5 AND http_type = 1'''
        self.update_sql = '''UPDATE ip_proxy SET `is_failured` = %d WHERE `id` = %d'''
        self.typemap = {1: 'https', 0: 'http'}
        self.canuseip = []
        self.waitjudge = []
        self.proxylist = []
        self.proxylists = []
        self.cannotuseip = []
        self.failuredtime = {}
        self.initproxy()

    def get_request_proxy(self, url, host, types):
        """
        use proxy to send requests, and record the proxy cann't use
        @types 1:json, 0:html
        support failured retry
        """

        if not len(self.proxylist):
            self.initproxy()

        httptype = url[4] == 's'
        index = random.randint(
            0, len(self.proxylists if httptype else self.proxylists) - 1)
        if httptype:
            proxies = {'https': self.proxylists[index]}
        else:
            proxies = {'http': self.proxylist[index]}

        try:
            if types:
                json = get_json(url, proxies, host)
                if 'code' in json and json['code'] != 200:
                    ppap = self.retry(url, host, types)
                    if not ppap:
                        return False
                else:
                    return json
            else:
                html = get_html(url, proxies, host)
                if 'code' in html or not html:
                    ppap = self.retry(url, host, types)
                    if not ppap:
                        return False
                else:
                    return html
        except Exception as e:
            self.cannotuseip.append(
                [proxies[self.typemap[httptype]], httptype])
            if httptype:
                if index < len(self.proxylists) and proxies['https'] == self.proxylists[index]:
                    self.proxylists.remove(proxies['https'])
            else:
                if index < len(self.proxylist) and proxies['http'] == self.proxylist[index]:
                    self.proxylist.remove(proxies['http'])
            ppap = self.retry(url, host, types)
            if not ppap:
                return False

    def retry(self, url, host, types):
        """
        retry once
        """

        if url not in self.failuredtime:
            self.failuredtime[url] = 0
            print("retry " + str(self.failuredtime[url]))
            self.get_request_proxy(url, host, types)
        elif self.failuredtime[url] < 3:
            self.failuredtime[url] += 1
            print("retry " + str(self.failuredtime[url]))
            self.get_request_proxy(url, host, types)
        else:
            print("Request Failured three times!")
            file_d = open("log", 'a')
            file_d.write(time.strftime("%Y-%m-%d %H:%M:%S ",
                                       time.localtime()) + url + '\n')
            file_d.close()
            return False

    def insertproxy(self, ids):
        """
        insert data to db
        """
        results = self.Db.insert_db(self.insert_sql % (ids[0], int(ids[1])))
        if results:
            print('Insert ' + ids[0] + ' ' + str(ids[1]) + ' Success!')
        else:
            pass

    def updateproxy(self, id, time):
        """
        update data to db
        """

        results = self.Db.update_db(self.update_sql % (int(time), int(id)))
        if results:
            print('Update ' + str(id) + ' Success!')
        else:
            pass

    def testproxy(self, ids):
        """
        test db have or not this data
        """
        results = self.Db.select_db(self.select_sql % (ids[0], int(ids[1])))
        if results != 0:
            idindex = ids[0] + ' ' + str(ids[1])
            if not len(results):
                print('Insert ' + idindex)
                self.insertproxy(ids)
            elif results[0][3]:
                print('Update ' + idindex)
                self.updateproxy(results[0][0], 0)
            else:
                print('Have exist ' + idindex)
                pass
        else:
            pass

    def updatecannotuse(self, ids):
        """
        update db proxy cann't use
        """
        results = self.Db.select_db(self.select_not % (ids[0], int(ids[1])))
        if results != 0 and len(results):
            print('Update can not use ' + ids[0] + ' ' + str(ids[1]))
            for index in results:
                self.updateproxy(index[0], index[3] + 1)
        else:
            pass

    def cleancannotuse(self):
        """
        clean cann't use ip list
        """
        for index in self.cannotuseip:
            self.updatecannotuse(index)
        self.cannotuseip = []

    def initproxy(self):
        """
        init proxy list
        """

        results = self.Db.select_db(self.select_list)
        if results != 0:
            self.proxylist = []
            self.proxylists = []
            for index in results:
                if index[1]:
                    self.proxylists.append(index[0])
                else:
                    self.proxylist.append(index[0])
            print(str(len(self.proxylist)) + ' http proxy can use.')
            print(str(len(self.proxylists)) + ' https proxy can use.')
        else:
            pass

    def judgeurl(self, urls):
        """
        use /api/playlist to judge http; use /discover/playlist judge https
        1. don't timeout = 5
        2. response.result.tracks.size() != 1
        """

        print(urls)
        proxies = {self.typemap[urls[1]]: urls[0]}

        test_url = 'https://music.163.com/discover/playlist/?order=hot&limit=35&offset=0' if urls[
            1] else 'http://music.163.com/api/playlist/detail?id=432853362'
        if urls[1]:
            try:
                html = get_html(test_url, proxies, test_url[8:21])
                alist = html.find_all('a', class_='s-fc1')
                if len(alist) == 73:
                    self.canuseip.append([urls[0], urls[1]])
                else:
                    self.cannotuseip.append([urls[0], urls[1]])
            except Exception as e:
                self.cannotuseip.append([urls[0], urls[1]])
                pass
        else:
            try:
                data = get_json(test_url, proxies, test_url[7:20])
                result = data['result']
                tracks = result['tracks']
                print(len(tracks))
                if len(tracks) == 56:
                    self.canuseip.append([urls[0], urls[1]])
                else:
                    self.cannotuseip.append([urls[0], urls[1]])
            except Exception as e:
                self.cannotuseip.append([urls[0], urls[1]])
                pass

    def threadjude(self):
        """
        threading to judge proxy
        """

        text = self.waitjudge
        num = len(text)
        for block in range(int(num / 1000) + 1):
            blockthreads = []
            for index in range(block * 1000, min(num, 1000 * (block + 1))):
                work = threading.Thread(
                    target=self.judgeurl, args=(text[index],))
                blockthreads.append(work)
            for work in blockthreads:
                work.start()
            for work in blockthreads:
                work.join()
            for index in self.canuseip:
                self.testproxy(index)
            self.cleancannotuse()
            self.canuseip = []
        self.waitjudge = []

    def testdb(self):
        '''
        test proxy in db can use
        '''

        begin_time()
        results = self.Db.select_db(self.select_all)
        if results != 0:
            for index in results:
                self.waitjudge.append([index[1], index[2]])
            self.threadjude()
        else:
            pass
        self.initproxy()
        end_time()

    def xiciproxy(self, page):
        """
        xici proxy http://www.xicidaili.com/nn/{page}
        The first proxy I use, but now it can not use it mostly.
        """

        if not str(page).isdigit():
            print("Please input num!")
            return []

        begin_time()
        host = 'http://www.xicidaili.com/nn/'
        for index in range(1, page + 1):
            html = get_html(host + str(index), {}, host[7:-4])
            # html = self.get_request_proxy(host + str(index), host[7:-4], 0)
            tem = html.find_all('tr')
            for index in range(1, len(tem)):
                tds = tem[index].find_all('td')
                ip = tds[5].text.lower()
                self.waitjudge.append(
                    [ip + '://' + tds[1].text + ':' + tds[2].text, ip == 'https'])
        self.threadjude()
        end_time()

    def gatherproxy(self):
        """
        :100: very nice website
        first of all you should download proxy ip txt from:
        http://www.gatherproxy.com/zh/proxylist/country/?c=China
        """

        begin_time()
        file_d = open('proxy/gatherproxy', 'r')
        for index in file_d.readlines():
            self.waitjudge.append(['http://' + index[0:-1], 0])
            self.waitjudge.append(['https://' + index[0:-1], 1])
        text = file_d.readlines()
        num = len(text)
        self.threadjude()
        end_time()

    def goubanjia(self):
        """
        :-1: html tag mixed with invalid data
        :100:And the most important thing is the port writed in 'class' rather in text.
        The website is difficult to spider, but the proxys are very goog
        goubanjia proxy http://www.goubanjia.com
        """

        begin_time()
        host = 'http://www.goubanjia.com'
        html = self.get_request_proxy(host, host[7:], 0)

        if not html:
            return []
        trs = html.find_all('tr', class_=['warning', 'success'])
        for tr in trs:
            tds = tr.find_all('td')
            ip = tds[2].find_all('a')[0].text + '://'
            iplist = tds[0].find_all(
                ['div', 'span', not 'p'], class_=not 'port')
            for index in iplist:
                ip += index.text
            encode = tds[0].find_all(['div', 'span', 'p'], class_='port')[
                0]['class'][1]
            uncode = functools.reduce(
                lambda x, y: x * 10 + (ord(y) - ord('A')), map(lambda x: x, encode), 0)
            self.waitjudge.append(
                [ip + ':' + str(int(uncode / 8)), ip[4] == 's'])
        self.threadjude()
        end_time()

    def schedulegou(self):
        sched = BlockingScheduler()
        sched.add_job(self.goubanjia, 'interval', seconds=100)
        sched.start()

    def data5u(self):
        """
        data5u proxy http://www.data5u.com/
        no one can use
        """

        begin_time()
        url_list = [
            '', 'free/gngn/index.shtml', 'free/gwgn/index.shtml'
        ]
        host = 'http://www.data5u.com/'
        for uri in url_list:
            html = self.get_request_proxy(host + uri, host[7:-1], 0)
            if not html:
                continue
            table = html.find_all('ul', class_='l2')
            for index in table:
                tds = index.find_all('li')
                ip = tds[3].text
                self.waitjudge.append(
                    [ip + '://' + tds[0].text + ':' + tds[1].text, ip == 'https'])
        self.threadjude()
        end_time()

    def sixsixip(self, area, page):
        """
        66ip proxy http://www.66ip.cn/areaindex_{area}/{page}.html
        """

        begin_time()
        threadings = []
        for index in range(1, area + 1):
            for pageindex in range(1, page + 1):
                print(str(index) + ' ' + str(pageindex))
                work = threading.Thread(
                    target=self.sixsixthread, args=(index, pageindex))
                threadings.append(work)
        for work in threadings:
            work.start()
        for work in threadings:
            work.join()
        self.threadjude()
        end_time()

    def sixsixthread(self, index, pageindex):
        host = '''http://www.66ip.cn/areaindex_%d/%d.html'''
        html = self.get_request_proxy(
            host % (index, pageindex), host[7:-21], 0)
        if not html:
            return []
        trs = html.find_all('table')[2].find_all('tr')
        for test in range(1, len(trs) - 1):
            tds = trs[test].find_all('td')
            self.waitjudge.append(
                ['http://' + tds[0].text + ':' + tds[1].text, 0])
            self.waitjudge.append(
                ['https://' + tds[0].text + ':' + tds[1].text, 1])

    def kuaidaili(self, page):
        """
        kuaidaili https://www.kuaidaili.com/free/
        """

        begin_time()
        threadings = []
        for index in range(1, page + 1):
            work = threading.Thread(
                target=self.kuaidailithread, args=(index,))
            threadings.append(work)
        for work in threadings:
            work.start()
        for work in threadings:
            work.join()
        self.threadjude()
        end_time()

    def kuaidailithread(self, index):
        host = '''https://www.kuaidaili.com/free/inha/%d/'''
        html = self.get_request_proxy(host % index, host[8:25], 0)
        if not html:
            return []
        trs = html.find_all('tr')
        for index in range(1, len(trs)):
            tds = trs[index].find_all('td')
            ip = tds[3].text.lower() + "://" + tds[0].text + ':' + tds[1].text
            self.waitjudge.append([ip, ip[4] == 's'])


if __name__ == '__main__':
    GetFreeProxy.testdb()
    GetFreeProxy.initproxy()
