# -*- coding: utf-8 -*-
# @Description: Get High Availability Proxy
# @Author: gunjianpan
# @Date:   2018-10-18 23:10:19
# @Last Modified by:   gunjianpan
# @Last Modified time: 2019-03-26 01:12:06

import argparse
import codecs
import functools
import os
import random
import threading
import time
import requests
import http.cookiejar as cj

from apscheduler.schedulers.blocking import BlockingScheduler
from bs4 import BeautifulSoup
from utils.db import Db
from utils.utils import begin_time, end_time, changeJsonTimeout, changeHtmlTimeout, basic_req

"""
  * gatherproxy.com
  * goubanjia.com
    xicidaili.com
    data5u.com
    66ip.com
    kuaidaili.com
    .data/
    ├── gatherproxy  // gather proxy list
    └── passage      // gather passage
"""

data_path = 'proxy/data/'
MAXN = 0x3fffffff
type_map = {1: 'https', 0: 'http'}


class GetFreeProxy:
    """
    proxy pool
    """

    def __init__(self):
        self.Db = Db("netease")
        self.insert_sql = '''INSERT INTO ip_proxy( `address`, `http_type`) VALUES %s '''
        self.select_list = '''SELECT address, http_type from ip_proxy WHERE `is_failured` = 0'''
        self.select_sql = '''SELECT `id`, address, `is_failured` from ip_proxy WHERE `address` in %s '''
        self.select_all = '''SELECT `address`, `http_type` from ip_proxy WHERE `is_failured` != 5 and http_type in %s'''
        self.replace_ip = '''REPLACE INTO ip_proxy(`id`, `address`, `http_type`, `is_failured`) VALUES %s'''
        self.canuseip = {}
        self.waitjudge = []
        self.cannotuseip = {}
        self.failuredtime = {}
        self.initproxy()

    def get_request_proxy(self, url:str, types:int, data=None, test_func=None, header=None):
        """
        use proxy to send requests, and record the proxy cann't use
        @types S0XY: X=0.->get;   =1.->post;
                     Y=0.->html;  =1.->json; =2.->basic
                     S=0.->basic ;=1.->ss

        support failured retry && failured auto record
        """

        httptype = url[4] == 's'
        ss_type = types // 1000
        types %= 1000
        if ss_type:
            proxylist = self.proxylists_ss if httptype else self.proxylist_ss
        else:
            proxylist = self.proxylists if httptype else self.proxylist

        if not len(proxylist):
            if self.Db.db:
                print('Proxy pool empty!!! Please check the db conn & db dataset!!!')
            proxies = {}
        else:
            index = random.randint(0, len(proxylist) - 1)
            proxies_url = proxylist[index]
            proxies = {type_map[httptype]: proxies_url}

        try:
            result = basic_req(url, types, proxies, data, header)
            if not test_func is None:
                if not test_func(result):
                    if self.check_retry(url):
                        self.get_request_proxy(
                            url, types + 1000 * ss_type, data, test_func)
                    else:
                        self.failuredtime[url] = 0
                        return
                else:
                    return result
            else:
                return result

        except:
            self.cannotuseip[random.randint(0, MAXN)] = proxies_url

            if proxies_url in proxylist:
                proxylist.remove(proxylist.index(proxies_url))

            if not len(self.cannotuseip.keys()) % 10:
                self.cleancannotuse()

            if self.check_retry(url):
                self.get_request_proxy(url, types + 1000 * ss_type, data, test_func)
            else:
                return

    def check_retry(self, url):
        """
        check cannt retry
        """
        if url not in self.failuredtime:
            self.failuredtime[url] = 0
            return True
        elif self.failuredtime[url] < 3:
            self.failuredtime[url] += 1
            return True
        else:
            self.log_write(url)
            self.failuredtime[url] = 0
            return False

    def log_write(self, url):
        """
        failure log
        """
        with codecs.open("proxy.log", 'a', encoding='utf-8') as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S ",time.localtime()) + url + '\n')

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
            print('Update', typemap[types],str(len(updatelist)),' items Success!')
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

        results = self.selectproxy([ii[0] for ii in self.canuseip.values()])
        ss_len = len([1 for ii in self.canuseip.values() if ii[1] > 1])
        print("SS proxies %d"%ss_len)

        insertlist = []
        updatelist = []
        ipmap = {}
        if results != False:
            for ip_info in results:
                ipmap[ip_info[1]] = [ip_info[0], ip_info[2]]

            for ip_now in self.canuseip.values():
                http_type = ip_now[1]
                ip_now = ip_now[0]
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
        self.canuseip = {}

    def cleancannotuse(self):
        """
        update db proxy cann't use
        """
        results = self.selectproxy(self.cannotuseip.values())
        updatelist = []
        ipmap = {}
        if results:
            for ip_info in results:
                ipmap[ip_info[1]] = [ip_info[0], ip_info[2]]

            for ip_now in self.cannotuseip.values():
                http_type = ip_now[4] == 's'
                if ip_now in ipmap:
                    updatelist.append(
                        (ipmap[ip_now][0], ip_now, http_type, ipmap[ip_now][1] + 1))

            if len(updatelist):
                self.updateproxy(updatelist, 1)
        else:
            pass
        self.cannotuseip = {}

    def initproxy(self):
        """
        init proxy list
        """

        results = self.Db.select_db(self.select_list)
        self.proxylist = []
        self.proxylists = []
        self.proxylist_ss = []
        self.proxylists_ss = []
        if results != 0:

            for index in results:
                if index[1] == 1:
                    self.proxylists.append(index[0])
                elif index[1] == 2:
                    self.proxylist.append(index[0])
                    self.proxylist_ss.append(index[0])
                elif index[1] == 3:
                    self.proxylists.append(index[0])
                    self.proxylists_ss.append(index[0])
                else:
                    self.proxylist.append(index[0])
            print(len(self.proxylist), ' http proxy can use.')
            print(len(self.proxylists), ' https proxy can use.')
            print(len(self.proxylist_ss), ' ss http proxy can use.')
            print(len(self.proxylists_ss), ' ss https proxy can use.')
        else:
            print('>>>Please check db configure!!! The proxy pool cant use!!!>>>')

    def judgeurl(self, urls, index, times):
        """
        use /api/playlist to judge http; use /discover/playlist judge https
        1. don't timeout = 5
        2. response.result.tracks.size() != 1
        """

        http_type = urls[4] == 's'
        proxies = {type_map[http_type]: urls}

        test_url = type_map[http_type] + '://music.163.com/api/playlist/detail?id=432853362'
        ss_url = 'https://www.google.com/?gws_rd=ssl'
        try:
            # print(test_url, proxies)
            # return
            data = basic_req(test_url, 1, proxies)
            result = data['result']
            tracks = result['tracks']
            if len(tracks) == 56:
                if times < 2:
                    self.judgeurl(urls, index, times + 1)
                else:
                    self.canuseip[index] = [urls, int(http_type)]
                    data = basic_req(ss_url, 0)
                    if len(str(data)) > 5000:
                        self.canuseip[index] = [urls, int(http_type) + 2]
            else:
                self.cannotuseip[index] = urls
        except:
            if not index in self.canuseip:
                self.cannotuseip[index] = urls
            pass

    def threadjude(self):
        """
        threading to judge proxy
        """
        changeJsonTimeout(2)
        changeHtmlTimeout(3)

        text = self.waitjudge
        num = len(text)
        for block in range(num // 1000 + 1):
            blockthreads = []
            for index in range(block * 1000, min(num, 1000 * (block + 1))):
                work = threading.Thread(
                    target=self.judgeurl, args=(text[index],index, 0,))
                blockthreads.append(work)
            for work in blockthreads:
                work.start()
            for work in blockthreads:
                work.join()
            # return
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
            typestr = '(0,1,2,3)'
        elif types == 1:
            typestr = '(1,3)'
        else:
            typestr = '(0,2)'
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
        url = 'http://www.xicidaili.com/nn/%d'
        for index in range(1, page + 1):
            html = basic_req(url%(index), 0)
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
        if not os.path.exists('%sgatherproxy'%data_path):
            print('Gather file not exist!!!')
            return
        with codecs.open('%sgatherproxy'%data_path, 'r', encoding='utf-8') as f:
            file_d = f.readlines()
        if not types:
            waitjudge = ['http://' + ii[:-1] for ii in file_d]
        elif types == 1:
            waitjudge = ['https://' + ii[:-1] for ii in file_d]
        else:
            waitjudge1 = ['http://' + ii[:-1] for ii in file_d]
            waitjudge2 = ['https://' + ii[:-1] for ii in file_d]
            waitjudge = [*waitjudge1, *waitjudge2]
        self.waitjudge = waitjudge
        print('load gather over!')
        # self.threadjude()
        # end_time(version)
        # if types == 2:
        #     self.testdb(2)
        end_time(version)


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

    def get_cookie(self):
        """
        make cookie login
        PS: Though cookie expired time is more than 1 year,
            but It will be break when the connect close.
            So you need reactive the cookie by this function.
        """
        headers = {
            'pragma': 'no-cache',
            'cache-control': 'no-cache',
            'Host': 'www.gatherproxy.com',
            'Origin': 'http://www.gatherproxy.com',
            'Referer': 'http://www.gatherproxy.com/proxylist/anonymity/?t=Transparent',
            'Cookie': '_lang=en-US; _ga=GA1.2.1084455496.1548351129; _gid=GA1.2.1515017701.1552361687; ASP.NET_SessionId=ckin3pzyqyoyt3zg54zrtrct; _gat=1; arp_scroll_position=57',
            'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3',
            "Accept-Encoding": "",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3682.0 Safari/537.36",
        }
        login_url = 'http://www.gatherproxy.com/subscribe/login'

        cookie_html = basic_req(login_url, 0,header=headers)
        verify_text = cookie_html.find_all('div', class_='label')[2].span.text
        verify_list = verify_text.replace('= ','').strip().split()
        num_map = {'Zero': 0,'One': 1,'Two': 2, 'Three':3,'Four':4,'Fine':5,'Six':6,'Seven':7,'Eight': 8, 'Nine':9, 'Ten': 10}
        verify_num = [verify_list[0], verify_list[2]]
        for index, num in enumerate(verify_num):
            if num.isdigit():
                verify_num[index] = int(num)
            elif num in num_map:
                verify_num[index] = num_map[num]
            else:
                print('Error', index)
                # return False
        verify_code = 0
        error = True

        operation = verify_list[1]
        if operation == '+' or operation == 'plus' or operation == 'add' or operation == 'multiplied':
            verify_code = verify_num[0] + verify_num[1]
            error = False
        if operation == '-' or operation == 'minus':
            verify_code = verify_num[0] - verify_num[1]
            error = False
        if operation == 'X' or operation == 'multiplication':
            verify_code = verify_num[0] * verify_num[1]
            error = False
        if error:
            print('Error', operation)
            # return False
        if not os.path.exists('%spassage'%data_path):
            print('gather passage not exist!!!')
            return
        with codecs.open('%spassage'%data_path, 'r', encoding='utf-8') as f:
            passage = [index[:-1] for index in f.readlines()]
        data = {'Username': passage[0], 'Password': passage[1], 'Captcha': str(verify_code)}
        time.sleep(2.163)
        r = requests.session()
        r.cookies = cj.LWPCookieJar()
        login_req = r.post(login_url, headers=headers, data=data, verify=False)

    def load_gather(self):
        """
        load gather proxy pool text
        If failured, you should reactive the cookie.
        """
        headers = {
            'pragma': 'no-cache',
            'cache-control': 'no-cache',
            'Host': 'www.gatherproxy.com',
            'Origin': 'http://www.gatherproxy.com',
            'Referer': 'http://www.gatherproxy.com/proxylist/anonymity/?t=Transparent',
            'Cookie': '_lang=en-US; _ga=GA1.2.1084455496.1548351129; _gid=GA1.2.1515017701.1552361687; ASP.NET_SessionId=ckin3pzyqyoyt3zg54zrtrct; _gat=1; arp_scroll_position=57',
            'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3',
            "Accept-Encoding": "",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3682.0 Safari/537.36",
        }
        url = 'http://www.gatherproxy.com/subscribe/infos'
        sid_url_req = requests.get(url, headers=headers, verify=False)
        sid_url_html = BeautifulSoup(sid_url_req.text, 'html.parser')
        sid_url = sid_url_html.find_all('div', class_='wrapper')[1].find_all('a')[0]['href']
        if len(sid_url.split('sid=')) < 2:
            print('cookie error')
            self.get_cookie()
            self.load_gather()
            return
        sid = sid_url.split('sid=')[1]
        sid_url = 'http://www.gatherproxy.com' + sid_url

        data = {'ID':sid , 'C': '', 'P': '', 'T': '', 'U': '0'}
        gatherproxy = requests.post(sid_url, headers=headers, data=data,verify=False)
        with codecs.open(data_path + 'gatherproxy', 'w', encoding='utf-8') as f:
            f.write(gatherproxy.text)

if __name__ == '__main__':
    if not os.path.exists(data_path):
        os.makedirs(data_path)
    parser = argparse.ArgumentParser(description='gunjianpan proxy pool code')
    parser.add_argument('--model', type=int, default=1, metavar='N',
                        help='model of load_gather or test')
    model = parser.parse_args().model
    a = GetFreeProxy()
    if model==1:
        a.load_gather()
    else:
        a.gatherproxy(2)
        a.testdb(2)
