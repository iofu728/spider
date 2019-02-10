# -*- coding: utf-8 -*-
# @Description: Get High Availability Proxy
# @Author: gunjianpan
# @Date:   2018-10-18 23:10:19
# @Last Modified by:   gunjianpan
# @Last Modified time: 2019-02-09 21:50:52
# !/usr/bin/env python

import functools
import random
import threading
import time

from apscheduler.schedulers.blocking import BlockingScheduler
from utils.db import Db
from utils.utils import begin_time, end_time, get_html, get_json, get_basic

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
        self.Db = Db("netease")
        self.insert_sql = '''INSERT INTO ip_proxy( `address`, `http_type`) VALUES %s '''
        self.select_list = '''SELECT address, http_type from ip_proxy WHERE `is_failured` = 0'''
        self.select_sql = '''SELECT `id`, address, `is_failured` from ip_proxy WHERE `address` in %s '''
        self.select_all = '''SELECT `address`, `http_type` from ip_proxy WHERE `is_failured` != 5 and http_type in %s'''
        self.replace_ip = '''REPLACE INTO ip_proxy(`id`, `address`, `http_type`, `is_failured`) VALUES %s'''
        self.typemap = {1: 'https', 0: 'http'}
        self.canuseip = []
        self.waitjudge = []
        self.proxylist = []
        self.proxylists = []
        self.cannotuseip = []
        self.failuredtime = {}
        self.initproxy()

    def get_request_proxy(self, url, types):
        """
        use proxy to send requests, and record the proxy cann't use
        @types 1:json, 0:html
        support failured retry
        """

        if not len(self.proxylist):
            self.initproxy()

        httptype = url[4] == 's'
        index = random.randint(
            0, len(self.proxylists if httptype else self.proxylist) - 1)
        if httptype:
            proxies = {'https': self.proxylists[index]}
        else:
            proxies = {'http': self.proxylist[index]}

        try:
            if types == 1:
                json = get_json(url, proxies)
                # if 'code' in json and json['code'] != 200:
                #     ppap = self.retry(url, types)
                #     if not ppap:
                #         return False
                # else:
                return json
            elif types == 2:
                return get_basic(url, proxies)
            else:
                html = get_html(url, proxies)
                if 'code' in html or not html:
                    ppap = self.retry(url, types)
                    if not ppap:
                        return False
                else:
                    return html
        except Exception as e:
            self.cannotuseip.append(proxies[self.typemap[httptype]])
            if httptype:
                if index < len(self.proxylists) and proxies['https'] == self.proxylists[index]:
                    self.proxylists.remove(proxies['https'])
            else:
                if index < len(self.proxylist) and proxies['http'] == self.proxylist[index]:
                    self.proxylist.remove(proxies['http'])
            ppap = self.retry(url, types)
            if not ppap:
                return False

    def retry(self, url, types):
        """
        retry once
        """
        print('retry')
        if url not in self.failuredtime:
            self.failuredtime[url] = 0
            # print("retry " + str(self.failuredtime[url]))
            self.get_request_proxy(url, types)
        elif self.failuredtime[url] < 3:
            self.failuredtime[url] += 1
            # print("retry " + str(self.failuredtime[url]))
            self.get_request_proxy(url, types)
        else:
            # print("Request Failured three times!")
            self.log_write(url)
            self.failuredtime[url] = 0
            return False

    def log_write(self, url):
        """
        failure log
        """

        file_d = open("log", 'a')
        file_d.write(time.strftime("%Y-%m-%d %H:%M:%S ",
                                   time.localtime()) + url + '\n')
        file_d.close()

    def insertproxy(self, insertlist):
        """
        insert data to db
        """
        results = self.Db.insert_db(self.insert_sql % str(insertlist)[1:-1])
        if results:
            print('Insert ' + str(len(insertlist)) + ' items Success!')
        else:
            pass

    def updateproxy(self, updatelist, types):
        """
        update data to db
        """

        results = self.Db.update_db(self.replace_ip % str(updatelist)[1:-1])
        typemap = {0: 'can use ', 1: 'can not use '}
        if results:
            print('Update ' + typemap[types] +
                  str(len(updatelist)) + ' items Success!')
        else:
            pass

    def selectproxy(self, targetlist):
        """
        select ip proxy by ids
        """
        if not len(targetlist):
            return []
        elif len(targetlist) == 1:
            waitlist = '(\'' + targetlist[0] + '\')'
        else:
            waitlist = tuple(targetlist)
        return self.Db.select_db(self.select_sql % str(waitlist))

    def dbcanuseproxy(self):
        """
        test db have or not this data
        """

        results = self.selectproxy(self.canuseip)

        insertlist = []
        updatelist = []
        ipmap = {}
        if results != False:
            for ip_info in results:
                ipmap[ip_info[1]] = [ip_info[0], ip_info[2]]

            for ip_now in self.canuseip:
                http_type = ip_now[4] == 's'
                if ip_now in ipmap:
                    if ipmap[ip_now][1]:
                        updatelist.append(
                            (ipmap[ip_now][0], ip_now, http_type, 0))
                else:
                    insertlist.append((ip_now, http_type))
            if len(insertlist):
                self.insertproxy(insertlist)
            if len(updatelist):
                self.updateproxy(updatelist, 0)
        else:
            pass
        self.canuseip = []

    def cleancannotuse(self):
        """
        update db proxy cann't use
        """
        results = self.selectproxy(self.cannotuseip)
        updatelist = []
        ipmap = {}
        if results:
            for ip_info in results:
                ipmap[ip_info[1]] = [ip_info[0], ip_info[2]]

            for ip_now in self.cannotuseip:
                http_type = ip_now[4] == 's'
                if ip_now in ipmap:
                    updatelist.append(
                        (ipmap[ip_now][0], ip_now, http_type, ipmap[ip_now][1] + 1))

            if len(updatelist):
                self.updateproxy(updatelist, 1)
        else:
            pass
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

    def judgeurl(self, urls, times):
        """
        use /api/playlist to judge http; use /discover/playlist judge https
        1. don't timeout = 5
        2. response.result.tracks.size() != 1
        """

        http_type = urls[4] == 's'
        proxies = {self.typemap[http_type]: urls}

        test_url = 'https://music.163.com/api/playlist/detail?id=432853362' if http_type else 'http://music.163.com/api/playlist/detail?id=432853362'
        try:
            data = get_json(test_url, proxies)
            result = data['result']
            tracks = result['tracks']
            if len(tracks) == 56:
                if times < 2:
                    self.judgeurl(urls, times + 1)
                else:
                    self.canuseip.append(urls)
            else:
                self.cannotuseip.append(urls)
        except Exception as e:
            self.cannotuseip.append(urls)
            pass
        # if http_type:
        #     try:
        #         html = get_html(test_url, proxies, test_url[8:21])
        #         alist = html.find_all('a', class_='s-fc1')
        #         if len(alist) == 73:
        #             self.canuseip.append(urls)
        #         else:
        #             self.cannotuseip.append(urls)
        #     except Exception as e:
        #         self.cannotuseip.append(urls)
        #         pass
        # else:
        #     try:
        #         data = get_json(test_url, proxies, test_url[7:20])
        #         result = data['result']
        #         tracks = result['tracks']
        #         if len(tracks) == 56:
        #             if times < 2:
        #                 self.judgeurl(urls, times + 1)
        #             else:
        #                 self.canuseip.append(urls)
        #         else:
        #             self.cannotuseip.append(urls)
        #     except Exception as e:
        #         self.cannotuseip.append(urls)
        #         pass

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
                    target=self.judgeurl, args=(text[index], 0,))
                blockthreads.append(work)
            for work in blockthreads:
                work.start()
            for work in blockthreads:
                work.join()
            self.dbcanuseproxy()
            self.cleancannotuse()

        self.waitjudge = []

    def testdb(self, types):
        '''
        test proxy in db can use
        '''

        version = begin_time()
        typestr = ''
        if types == 2:
            typestr = '(0,1)'
        else:
            typestr = '(' + str(types) + ')'
        results = self.Db.select_db(self.select_all % typestr)
        if results != 0:
            for index in results:
                self.waitjudge.append(index[0])
            self.threadjude()
        else:
            pass
        self.initproxy()
        end_time(version)

    def xiciproxy(self, page):
        """
        xici proxy http://www.xicidaili.com/nn/{page}
        The first proxy I use, but now it can not use it mostly.
        """

        if not str(page).isdigit():
            print("Please input num!")
            return []

        version = begin_time()
        host = 'http://www.xicidaili.com/nn/'
        for index in range(1, page + 1):
            html = get_html(host + str(index), {})
            # html = self.get_request_proxy(host + str(index), host[7:-4], 0)
            tem = html.find_all('tr')
            for index in range(1, len(tem)):
                tds = tem[index].find_all('td')
                ip = tds[5].text.lower()
                self.waitjudge.append(
                    ip + '://' + tds[1].text + ':' + tds[2].text)
        self.threadjude()
        end_time(version)

    def gatherproxy(self, types):
        """
        :100: very nice website
        first of all you should download proxy ip txt from:
        http://www.gatherproxy.com/zh/proxylist/country/?c=China
        """

        version = begin_time()
        file_d = open('proxy/gatherproxy', 'r')
        for index in file_d.readlines():
            if types == 0:
                self.waitjudge.append('http://' + index[0:-1])
            elif types == 1:
                self.waitjudge.append('https://' + index[0:-1])
            else:
                self.waitjudge.append('http://' + index[0:-1])
                self.waitjudge.append('https://' + index[0:-1])
        self.threadjude()
        end_time(version)
        if types == 2:
            self.testdb(2)

    def goubanjia(self):
        """
        :-1: html tag mixed with invalid data
        :100:And the most important thing is the port writed in 'class' rather in text.
        The website is difficult to spider, but the proxys are very goog
        goubanjia proxy http://www.goubanjia.com
        """

        version = begin_time()
        host = 'http://www.goubanjia.com'
        html = self.get_request_proxy(host, 0)

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
            self.waitjudge.append(ip + ':' + str(int(uncode / 8)))
        self.threadjude()
        end_time(version)

    def schedulegou(self):
        sched = BlockingScheduler()
        sched.add_job(self.goubanjia, 'interval', seconds=100)
        sched.start()

    def data5u(self):
        """
        data5u proxy http://www.data5u.com/
        no one can use
        """

        version = begin_time()
        url_list = [
            '', 'free/gngn/index.shtml', 'free/gwgn/index.shtml'
        ]
        host = 'http://www.data5u.com/'
        for uri in url_list:
            html = self.get_request_proxy(host + uri, 0)
            if not html:
                continue
            table = html.find_all('ul', class_='l2')
            for index in table:
                tds = index.find_all('li')
                ip = tds[3].text
                self.waitjudge.append(
                    ip + '://' + tds[0].text + ':' + tds[1].text)
        self.threadjude()
        end_time(version)

    def sixsixip(self, area, page):
        """
        66ip proxy http://www.66ip.cn/areaindex_{area}/{page}.html
        """

        version = begin_time()
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
        end_time(version)

    def sixsixthread(self, index, pageindex):
        host = '''http://www.66ip.cn/areaindex_%d/%d.html'''
        html = self.get_request_proxy(
            host % (index, pageindex), 0)
        if not html:
            return []
        trs = html.find_all('table')[2].find_all('tr')
        for test in range(1, len(trs) - 1):
            tds = trs[test].find_all('td')
            self.waitjudge.append('http://' + tds[0].text + ':' + tds[1].text)
            self.waitjudge.append('https://' + tds[0].text + ':' + tds[1].text)

    def kuaidaili(self, page):
        """
        kuaidaili https://www.kuaidaili.com/free/
        """

        version = begin_time()
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
        end_time(version)

    def kuaidailithread(self, index):
        host = '''https://www.kuaidaili.com/free/inha/%d/'''
        html = self.get_request_proxy(host % index, 0)
        if not html:
            return []
        trs = html.find_all('tr')
        for index in range(1, len(trs)):
            tds = trs[index].find_all('td')
            ip = tds[3].text.lower() + "://" + tds[0].text + ':' + tds[1].text
            self.waitjudge.append(ip)


if __name__ == '__main__':
    a = GetFreeProxy()
    a.initproxy()
    a.testdb(0)
