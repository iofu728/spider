# -*- coding: utf-8 -*-
# @Description: Get High Availability Proxy
# @Author: gunjianpan
# @Date:   2018-10-18 23:10:19
# @Last Modified by:   gunjianpan
# @Last Modified time: 2018-10-21 11:06:26
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
from utils.utils import get_html, get_json, begin_time, end_time

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
        self.db = pymysql.connect("localhost", "root", "", "netease")
        self.insert_sql = '''INSERT INTO ip_proxy( `address`, `http_type`, `is_failured`) VALUES ('%s',%d,%d)'''
        self.select_not = '''SELECT * from ip_proxy WHERE `address` = '%s' AND `is_failured` < 5 '''
        self.select_list = '''SELECT address from ip_proxy WHERE `is_failured` = 0 AND http_type = 0'''
        self.select_sql = '''SELECT * from ip_proxy WHERE `address` = '%s' '''
        self.select_all = '''SELECT * from ip_proxy'''
        self.update_sql = '''UPDATE ip_proxy SET `is_failured` = %d WHERE `id` = %d'''
        self.canuseip = []
        self.proxylist = []
        self.waitjudge = []
        self.cannotuseip = []
        self.initproxy()

    def get_request_proxy(self, url, host, types):
        """
        use proxy to send requests, and record the proxy cann't use
        @types 1:json, 0:html
        """

        if not len(self.proxylist):
            self.initproxy()

        index = random.randint(0, len(self.proxylist) - 1)
        proxies = {'http': self.proxylist[index]}

        try:
            if types:
                return get_json(url, proxies, host)
            else:
                return get_html(url, proxies, host)
        except Exception as e:
            self.updatecannotuse(proxies['http'])
            if proxies['http'] == self.proxylist[index]:
                self.proxylist.remove(proxies['http'])
            if types:
                return {}
            else:
                return BeautifulSoup('<html></html>', 'html.parser')

    def insertproxy(self, http):
        """
        insert data to db
        """

        try:
            cursor = self.db.cursor()
            cursor.execute(self.insert_sql % (http, 0, 0))
            self.db.commit()
            print('Insert ' + http + ' Success!')
        except Exception as e:
            self.db.rollback()
            pass

    def updateproxy(self, id, time):
        """
        update data to db
        """

        try:
            cursor = self.db.cursor()
            cursor.execute(self.update_sql % (int(time), int(id)))
            self.db.commit()
            print('Update ' + str(id) + ' Success!')
        except Exception as e:
            self.db.rollback()
            pass

    def testproxy(self, http):
        """
        test db have or not this data
        """

        try:
            cursor = self.db.cursor()
            cursor.execute(self.select_sql % http)
            results = cursor.fetchall()
            if not len(results):
                print('Insert ' + http)
                self.insertproxy(http)
            elif results[0][3]:
                print('Update ' + http)
                self.updateproxy(results[0][0], 0)
            else:
                print('Have exist ' + http)
                pass
        except Exception as e:
            pass

    def updatecannotuse(self, http):
        """
        update db proxy cann't use
        """

        try:
            cursor = self.db.cursor()
            cursor.execute(self.select_not % http)
            results = cursor.fetchall()
            if len(results):
                print('Update can not use ' + http)
                for index in results:
                    self.updateproxy(index[0], index[3] + 1)
        except Exception as e:
            pass

    def initproxy(self):
        """
        init proxy list
        """
        self.proxylist = []
        try:
            cursor = self.db.cursor()
            cursor.execute(self.select_list)
            results = cursor.fetchall()
            for index in results:
                self.proxylist.append(index[0])
        except Exception as e:
            pass

    def judgehttp(self, http):
        """
        use /api/playlist to judge proxy can be proxy
        1. don't timeout = 2
        2. response.result.tracks.size() != 1
        """

        print(http)
        proxies = {'http': http}
        test_url = 'http://music.163.com/api/playlist/detail?id=432853362'
        try:
            data = get_json(test_url, proxies, test_url[7:20])
            result = data['result']
            tracks = result['tracks']
            print(len(tracks))
            if len(tracks) != 1:
                self.canuseip.append(proxies['http'])
            else:
                self.cannotuseip.append(proxies['http'])
        except Exception as e:
            self.cannotuseip.append(proxies['http'])
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
                    target=self.judgehttp, args=(text[index],))
                blockthreads.append(work)
            for work in blockthreads:
                work.start()
            for work in blockthreads:
                work.join()
            for index in self.canuseip:
                self.testproxy(index)
            for index in self.cannotuseip:
                self.updatecannotuse(index)
            self.cannotuseip = []
            self.canuseip = []
        self.waitjudge = []

    def testdb(self):
        '''
        test proxy in db can use
        '''

        begin_time()
        try:
            cursor = self.db.cursor()
            cursor.execute(self.select_all)
            results = cursor.fetchall()
            for index in results:
                self.waitjudge.append(index[1])
            self.threadjude()
        except Exception as e:
            pass
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
                temp = tds[5].text.lower()
                if temp == 'http':
                    self.waitjudge.append(
                        temp + '://' + tds[1].text + ':' + tds[2].text)
        self.threadjude()
        end_time()

    def gatherproxy(self):
        """
        :100: very nice website
        first of all you should download proxy ip txt from:
        http://www.gatherproxy.com/zh/proxylist/country/?c=China
        """

        begin_time()
        file_d = open('gatherproxy', 'r')
        for index in file_d.readlines():
            self.waitjudge.append('http://' + index[0:-1])
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

        trs = html.find_all('tr', class_='warning')
        for tr in trs:
            tds = tr.find_all('td')
            if tds[2].find_all('a')[0].text == 'http':
                ip = 'http://'
                iplist = tds[0].find_all(
                    ['div', 'span', not 'p'], class_=not 'port')
                for index in iplist:
                    ip += index.text
                encode = tds[0].find_all(['div', 'span', 'p'], class_='port')[
                    0]['class'][1]
                uncode = functools.reduce(
                    lambda x, y: x * 10 + (ord(y) - ord('A')), map(lambda x: x, encode), 0)
                self.waitjudge.append(ip + ':' + str(int(uncode / 8)))
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
            table = html.find_all('ul', class_='l2')
            for index in table:
                tds = index.find_all('li')
                if tds[3].text == 'http':
                    self.waitjudge.append(
                        'http://' + tds[0].text + ':' + tds[1].text)
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
        if not len(html.find_all('table')):
            return []
        trs = html.find_all('table')[2].find_all('tr')
        for test in range(1, len(trs) - 1):
            tds = trs[test].find_all('td')
            self.waitjudge.append('http://' + tds[0].text + ':' + tds[1].text)

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
        trs = html.find_all('tr')
        for index in range(1, len(trs)):
            tds = trs[index].find_all('td')
            ip = tds[3].text.lower()
            if ip == 'http':
                ip += "://" + tds[0].text + ':' + tds[1].text
                self.waitjudge.append(ip)


if __name__ == '__main__':
    GetFreeProxy.testdb()
    GetFreeProxy.initproxy()
