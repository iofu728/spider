# -*- coding: utf-8 -*-
# @Author: gunjianpan
# @Date:   2018-10-18 23:10:19
# @Last Modified by:   gunjianpan
# @Last Modified time: 2021-06-21 18:11:00

import codecs
import functools
import http.cookiejar as cj
import os
import random
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from apscheduler.schedulers.blocking import BlockingScheduler
from bs4 import BeautifulSoup

sys.path.append(os.getcwd())
from util.db import Db
from util.util import (
    basic_req,
    begin_time,
    can_retry,
    changeHtmlTimeout,
    changeJsonTimeout,
    create_argparser,
    echo,
    end_time,
    read_file,
    time_str,
    get_accept,
    get_content_type,
    set_args,
    load_cfg,
)


"""
  * www.proxyserverlist24.top
  * www.live-socks.net
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

data_dir = "proxy/data/"
MAXN = 0x3FFFFFFF
type_map = {1: "https", 0: "http"}
ASSIGN_PATH = f"{data_dir}proxy.ini"


class GetFreeProxy:
    """ proxy pool """

    def __init__(self):
        self.Db = Db("proxy")
        self.insert_sql = """INSERT INTO ip_proxy( `address`, `http_type`) VALUES %s """
        self.select_list = (
            """SELECT address, http_type from ip_proxy WHERE `is_failured` = 0"""
        )
        self.select_sql = """SELECT `id`, address, `is_failured` from ip_proxy WHERE `address` in %s """
        self.select_all = """SELECT `address`, `http_type` from ip_proxy WHERE `is_failured` != 5 and http_type in %s"""
        self.random_select = """SELECT `address`, `http_type` FROM ip_proxy WHERE `is_failured` >= 5 and (`id` >= ((SELECT MAX(`id`) FROM ip_proxy)-(SELECT MIN(`id`) FROM ip_proxy)) * RAND() + (SELECT MIN(`id`) FROM ip_proxy)) and http_type in %s LIMIT 6000"""
        self.replace_ip = """REPLACE INTO ip_proxy(`id`, `address`, `http_type`, `is_failured`) VALUES %s"""
        self.can_use_ip = {}
        self.waitjudge = []
        self.cannot_use_ip = {}
        self.failured_time = {}
        self.canuse_proxies = []
        self.init_proxy()
        self.load_configure()

    def proxy_req(
        self,
        url: str,
        types: int,
        data=None,
        header=None,
        test_func=None,
        need_cookie: bool = False,
        config: dict = {},
        proxies: dict = {},
    ):
        """
        use proxy to send requests, and record the proxy can't use
        @types S0XY: X=0.->get;   =1.->post;
                     Y=0.->html;  =1.->json; =2.->basic
                     S=0.->basic ;=1.->ss

        support failured retry && failured auto record
        """

        httptype = url[4] == "s"
        ss_type = types // 1000
        types %= 1000
        if ss_type:
            proxylist = self.proxylists_ss if httptype else self.proxylist_ss
        else:
            proxylist = self.proxylists if httptype else self.proxylist

        if proxies != {}:
            proxies = proxies
        elif not len(proxylist):
            if self.Db.db:
                echo(
                    "0|critical",
                    "Proxy pool empty!!! Please check the db conn & db dataset!!!",
                )
            proxies = {}
        else:
            index = random.randint(0, len(proxylist) - 1)
            proxies_url = proxylist[index]
            proxies = {type_map[httptype]: proxies_url}

        try:
            result = basic_req(
                url,
                types=types,
                proxies=proxies,
                data=data,
                header=header,
                need_cookie=need_cookie,
                config=config,
            )
            if test_func is not None:
                if not test_func(result):
                    if self.check_retry(url):
                        return self.proxy_req(
                            url,
                            types=types + 1000 * ss_type,
                            data=data,
                            header=header,
                            test_func=test_func,
                            need_cookie=need_cookie,
                            config=config,
                            proxies=proxies,
                        )
                    else:
                        self.failured_time[url] = 0
                        return
                return result
            return result

        except:
            self.cannot_use_ip[random.randint(0, MAXN)] = proxies_url

            if proxies_url in proxylist:
                proxylist.remove(proxylist.index(proxies_url))

            if not len(self.cannot_use_ip.keys()) % 10:
                self.clean_cannot_use()

            if self.check_retry(url):
                return self.proxy_req(
                    url,
                    types=types + 1000 * ss_type,
                    data=data,
                    test_func=test_func,
                    header=header,
                    need_cookie=need_cookie,
                    config=config,
                    proxies=proxies,
                )

    def check_retry(self, url: str) -> bool:
        """ check try time """
        if url not in self.failured_time:
            self.failured_time[url] = 0
            return True
        elif self.failured_time[url] < 3:
            self.failured_time[url] += 1
            return True
        else:
            self.log_write(url)
            self.failured_time[url] = 0
            return False

    def log_write(self, url: str):
        """ failure log """
        echo("0|warning", "url {} retry max time".format(url))

    def insert_proxy(self, insert_list: list):
        """ insert data to db """
        results = self.Db.insert_db(self.insert_sql % str(insert_list)[1:-1])
        if results:
            echo("2|info", "Insert " + str(len(insert_list)) + " items Success!")

    def update_proxy(self, update_list: list, types: int):
        """ update data to db"""
        results = self.Db.update_db(self.replace_ip % str(update_list)[1:-1])
        typemap = {0: "can use ", 1: "can not use "}
        if results:
            echo(
                "2|info",
                "Update",
                typemap[types],
                str(len(update_list)),
                " items Success!",
            )

    def select_proxy(self, target_list: list) -> list:
        """ select ip proxy by ids """
        if not len(target_list):
            return []
        elif len(target_list) == 1:
            waitlist = "('" + target_list[0] + "')"
        else:
            waitlist = tuple(target_list)
        return self.Db.select_db(self.select_sql % str(waitlist))

    def db_can_use_proxy(self):
        """ test db have or not this data """

        results = self.select_proxy([ii[0] for ii in self.can_use_ip.values()])
        ss_len = len([1 for ii in self.can_use_ip.values() if ii[1] > 1])
        echo("2|info", "SS proxies", ss_len)

        insert_list = []
        update_list = []
        ip_map = {}
        if results != False:
            for ip_info in results:
                ip_map[ip_info[1]] = [ip_info[0], ip_info[2]]

            for ip_now in self.can_use_ip.values():
                http_type = ip_now[1]
                ip_now = ip_now[0]
                if ip_now in ip_map:
                    if ip_map[ip_now][1]:
                        update_list.append((ip_map[ip_now][0], ip_now, http_type, 0))
                else:
                    insert_list.append((ip_now, http_type))
            if len(insert_list):
                self.insert_proxy(insert_list)
            if len(update_list):
                self.update_proxy(update_list, 0)
        else:
            pass
        self.can_use_ip = {}

    def clean_cannot_use(self):
        """ update db proxy cannot use """
        results = self.select_proxy(self.cannot_use_ip.values())
        update_list = []
        ip_map = {}
        if results:
            for ip_info in results:
                ip_map[ip_info[1]] = [ip_info[0], ip_info[2]]

            for ip_now in self.cannot_use_ip.values():
                http_type = ip_now[4] == "s"
                if ip_now in ip_map:
                    update_list.append(
                        (ip_map[ip_now][0], ip_now, http_type, ip_map[ip_now][1] + 1)
                    )

            if len(update_list):
                self.update_proxy(update_list, 1)
        self.cannot_use_ip = {}

    def init_proxy(self):
        """ init proxy list """

        results = self.Db.select_db(self.select_list)
        self.proxylist = []
        self.proxylists = []
        self.proxylist_ss = []
        self.proxylists_ss = []
        if not results:
            echo(
                "0|error", "Please check db configure!!! The proxy pool cant use!!!>>>"
            )
            return
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
        echo("2|info", len(self.proxylist), " http proxy can use.")
        echo("2|info", len(self.proxylists), " https proxy can use.")
        echo("2|info", len(self.proxylist_ss), " ss http proxy can use.")
        echo("2|info", len(self.proxylists_ss), " ss https proxy can use.")

    def judge_url(self, urls: str, index: int, times: int, ss_test: bool = False):
        """
        use /api/playlist to judge http; use /discover/playlist judge https
        1. don't timeout = 5
        2. response.result.tracks.size() != 1
        """

        http_type = "https" in urls
        proxies = {type_map[http_type]: urls}

        test_url = (
            type_map[http_type] + "://music.163.com/api/song/lyric?os=pc&id=548556492"
        )
        ss_url = "https://www.google.com/?gws_rd=ssl"
        data = basic_req(test_url, 1, proxies)
        if (
            data is None
            or not isinstance(data, dict)
            or list(data.keys())
            != ["sgc", "sfy", "qfy", "transUser", "lyricUser", "code"]
            or data["code"] != 200
        ):
            echo("0|debug", urls, proxies, "return error ^--<^>--^ ")
            self.cannot_use_ip[index] = urls
            return
        if times < 0:
            self.judge_url(urls, index, times + 1)
        else:
            echo("1|debug", urls, proxies, "Proxies can use.")
            self.canuse_proxies.append(urls)
            self.can_use_ip[index] = [urls, int(http_type)]
            if ss_test:
                data = basic_req(ss_url, 0)
                if len(str(data)) > 5000:
                    self.can_use_ip[index] = [urls, int(http_type) + 2]

    def thread_judge(self, batch_size: int = 500):
        """ threading to judge proxy """
        changeJsonTimeout(2)
        changeHtmlTimeout(3)

        proxy_exec = ThreadPoolExecutor(max_workers=batch_size // 2)
        text = self.waitjudge
        num = len(text)
        for block in range(num // batch_size + 1):
            proxy_th = [
                proxy_exec.submit(self.judge_url, jj, ii, 0)
                for ii, jj in enumerate(
                    text[block * batch_size : batch_size * (block + 1)]
                )
            ]
            list(as_completed(proxy_th))
            self.db_can_use_proxy()
            self.clean_cannot_use()
        self.waitjudge = []

    def test_db(self, types: int):
        """ test proxy in db can use """

        version = begin_time()
        typestr = ""
        if types == 2:
            typestr = "(0,1,2,3)"
        elif types == 1:
            typestr = "(1,3)"
        else:
            typestr = "(0,2)"
        results = self.Db.select_db(self.select_all % typestr)
        random_select = self.Db.select_db(self.random_select % typestr)
        if not results:
            results = []
        if not random_select:
            random_select = []
        for index in results + random_select:
            self.waitjudge.append(index[0])
        self.thread_judge()
        self.init_proxy()
        end_time(version, 2)

    def xici_proxy(self, page: int):
        """
        xici proxy http://www.xicidaili.com/nn/{page}
        The first proxy I use, but now it can not use it mostly.
        """

        if not str(page).isdigit():
            echo("0|warning", "Please input num!")
            return []

        version = begin_time()
        url = "http://www.xicidaili.com/nn/%d"
        for index in range(1, page + 1):
            html = basic_req(url % index, 0)
            tem = html.find_all("tr")
            for index in range(1, len(tem)):
                tds = tem[index].find_all("td")
                ip = tds[5].text.lower()
                self.waitjudge.append("{}://{}:{}".format(ip, tds[1].text, tds[2].text))
        self.thread_judge()
        end_time(version, 2)

    def gatherproxy(self, types: int):
        """
        :100: very nice website
        first of all you should download proxy ip txt from:
        http://www.gatherproxy.com/zh/proxylist/country/?c=China
        """
        if not os.path.exists("{}gatherproxy".format(data_dir)):
            echo("0|warning", "Gather file not exist!!!")
            return
        file_d = read_file("{}gatherproxy".format(data_dir))
        waitjudge_http = ["http://" + ii for ii in file_d]
        waitjudge_https = ["https://" + ii for ii in file_d]
        if not types:
            self.waitjudge += waitjudge_http
        elif types == 1:
            self.waitjudge += waitjudge_https
        elif types == 2:
            self.waitjudge += waitjudge_http + waitjudge_https
        else:
            self.waitjudge += file_d
        echo("2|warning", "load gather over!")

    def goubanjia(self):
        """
        :-1: html tag mixed with invalid data
        :100:And the most important thing is the port writed in 'class' rather in text.
        The website is difficult to spider, but the proxys are very goog
        goubanjia proxy http://www.goubanjia.com
        """

        version = begin_time()
        host = "http://www.goubanjia.com"
        html = self.proxy_req(host, 0)

        if not html:
            return []
        trs = html.find_all("tr", class_=["warning", "success"])
        for tr in trs:
            tds = tr.find_all("td")
            ip = tds[2].find_all("a")[0].text + "://"
            iplist = tds[0].find_all(["div", "span", not "p"], class_=not "port")
            for index in iplist:
                ip += index.text
            encode = tds[0].find_all(["div", "span", "p"], class_="port")[0]["class"][1]
            uncode = functools.reduce(
                lambda x, y: x * 10 + (ord(y) - ord("A")), map(lambda x: x, encode), 0
            )
            self.waitjudge.append(ip + ":" + str(int(uncode / 8)))
        self.thread_judge()
        end_time(version, 2)

    def schedulegou(self):
        sched = BlockingScheduler()
        sched.add_job(self.goubanjia, "interval", seconds=100)
        sched.start()

    def data5u(self):
        """
        data5u proxy http://www.data5u.com/
        no one can use
        """

        version = begin_time()
        url_list = ["", "free/gngn/index.shtml", "free/gwgn/index.shtml"]
        host = "http://www.data5u.com/"
        for uri in url_list:
            html = self.proxy_req(host + uri, 0)
            if not html:
                continue
            table = html.find_all("ul", class_="l2")
            for index in table:
                tds = index.find_all("li")
                ip = tds[3].text
                self.waitjudge.append("{}://{}:{}".format(ip, tds[1].text, tds[2].text))
        self.thread_judge()
        end_time(version, 2)

    def sixsixip(self, area: int, page: int):
        """
        66ip proxy http://www.66ip.cn/areaindex_{area}/{page}.html
        """

        version = begin_time()
        threadings = []
        for index in range(1, area + 1):
            for pageindex in range(1, page + 1):
                echo("2|debug", "{} {}".format(index, pageindex))
                work = threading.Thread(
                    target=self.sixsixthread, args=(index, pageindex)
                )
                threadings.append(work)
        for work in threadings:
            work.start()
        for work in threadings:
            work.join()
        self.thread_judge()
        end_time(version, 2)

    def sixsixthread(self, index: int, pageindex: int):
        host = """http://www.66ip.cn/areaindex_%d/%d.html"""
        html = self.proxy_req(host % (index, pageindex), 0)
        if not html:
            return []
        trs = html.find_all("table")[2].find_all("tr")
        for test in range(1, len(trs) - 1):
            tds = trs[test].find_all("td")
            self.waitjudge.append("http://{}:{}".format(tds[0].text, tds[1].text))
            self.waitjudge.append("https://{}:{}".format(tds[0].text, tds[1].text))

    def kuaidaili(self, page: int):
        """
        kuaidaili https://www.kuaidaili.com/free/
        """

        version = begin_time()
        threadings = []
        for index in range(1, page + 1):
            work = threading.Thread(target=self.kuaidailithread, args=(index,))
            threadings.append(work)
        for work in threadings:
            work.start()
        for work in threadings:
            work.join()
        self.thread_judge()
        end_time(version, 2)

    def kuaidailithread(self, index: int):
        host = """https://www.kuaidaili.com/free/inha/%d/"""
        html = self.proxy_req(host % index, 0)
        if not html:
            return []
        trs = html.find_all("tr")
        for index in range(1, len(trs)):
            tds = trs[index].find_all("td")
            ip = tds[3].text.lower() + "://" + tds[0].text + ":" + tds[1].text
            self.waitjudge.append(ip)

    def get_cookie(self):
        """
        make cookie login
        PS: Though cookie expired time is more than 1 year,
            but It will be break when the connect close.
            So you need reactive the cookie by this function.
        """
        headers = {
            "Cookie": "_lang=en-US; _ga=GA1.2.1084455496.1548351129; _gid=GA1.2.1515017701.1552361687; ASP.NET_SessionId=ckin3pzyqyoyt3zg54zrtrct; _gat=1; arp_scroll_position=57",
            "Accept": get_accept("html") + ";q=0.9",
        }
        login_url = "http://www.gatherproxy.com/subscribe/login"

        cookie_html = basic_req(login_url, 3, header=headers)
        try:
            verify_text = re.findall('<span class="blue">(.*?)</span>', cookie_html)[0]
        except:
            return
        verify_list = verify_text.replace("= ", "").strip().split()
        num_map = {
            "Zero": 0,
            "One": 1,
            "Two": 2,
            "Three": 3,
            "Four": 4,
            "Five": 5,
            "Six": 6,
            "Seven": 7,
            "Eight": 8,
            "Nine": 9,
            "Ten": 10,
        }
        verify_num = [verify_list[0], verify_list[2]]
        for index, num in enumerate(verify_num):
            if num.isdigit():
                verify_num[index] = int(num)
            elif num in num_map:
                verify_num[index] = num_map[num]
            else:
                echo("0|error", "Error", num)
                # return False
        verify_code = 0
        error = True

        operation = verify_list[1]
        if (
            operation == "+"
            or operation == "plus"
            or operation == "add"
            or operation == "multiplied"
        ):
            verify_code = verify_num[0] + verify_num[1]
            error = False
        if operation == "-" or operation == "minus":
            verify_code = verify_num[0] - verify_num[1]
            error = False
        if operation == "X" or operation == "multiplication":
            verify_code = verify_num[0] * verify_num[1]
            error = False
        if error:
            echo("0|error", "Error", operation)
        if not os.path.exists("%spassage" % data_dir):
            echo("0|warning", "gather passage not exist!!!")
            return
        with codecs.open("%spassage" % data_dir, "r", encoding="utf-8") as f:
            passage = [index[:-1] for index in f.readlines()]
        data = {
            "Username": passage[0],
            "Password": passage[1],
            "Captcha": str(verify_code),
        }
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
            "Cookie": "_lang=en-US; _ga=GA1.2.1084455496.1548351129; _gid=GA1.2.1515017701.1552361687; ASP.NET_SessionId=ckin3pzyqyoyt3zg54zrtrct; _gat=1; arp_scroll_position=57",
            "Accept": get_accept("html") + ";q=0.9",
        }
        url = "http://www.gatherproxy.com/subscribe/infos"
        try:
            sid_url_req = requests.get(url, headers=headers, verify=False, timeout=10)
        except:
            return
        sid_url_html = BeautifulSoup(sid_url_req.text, "html.parser")
        sid_url = sid_url_html.find_all("div", class_="wrapper")[1].find_all("a")[0][
            "href"
        ]
        if len(sid_url.split("sid=")) < 2:
            echo("0|warning", "cookie error")
            self.get_cookie()
            self.load_gather()
            return
        sid = sid_url.split("sid=")[1]
        sid_url = "http://www.gatherproxy.com" + sid_url

        data = {"ID": sid, "C": "", "P": "", "T": "", "U": "0"}
        gatherproxy = requests.post(sid_url, headers=headers, data=data, verify=False)
        with codecs.open(data_dir + "gatherproxy", "w", encoding="utf-8") as f:
            f.write(gatherproxy.text)

    def load_proxies_list(self, types: int = 2):
        """ load proxies """
        SITES = ["http://www.proxyserverlist24.top/", "http://www.live-socks.net/"]
        spider_pool = []
        self.waitjudge = []
        for site in SITES:
            self.get_other_proxies(site)
        self.gatherproxy(3)
        waitjudge = list(set(self.waitjudge))
        waitjudge_http = ["http://" + ii for ii in waitjudge]
        waitjudge_https = ["https://" + ii for ii in waitjudge]
        if not types:
            self.waitjudge = waitjudge_http
        elif types == 1:
            self.waitjudge = waitjudge_https
        else:
            self.waitjudge = waitjudge_http + waitjudge_https
        echo(
            "1|info",
            "-_-_-_-_-_-_-",
            len(waitjudge),
            "Proxies wait to judge -_-_-_-_-_-_-",
        )

    def request_text(self, url: str) -> str:
        """ requests text """
        req = basic_req(url, 2)
        if req is None:
            echo("0|debug", url)
            if can_retry(url):
                return self.request_text(url)
            else:
                return ""
        echo("1|debug", url)
        text = req.text
        if type(text) == str:
            return text
        elif type(text) == bytes:
            return text.decode()
        else:
            return ""

    def get_free_proxy(self, url: str):
        req = basic_req(url, 2)
        if req is None:
            return []
        tt = req.text
        t_list = re.findall("<tr><td>(\d*\.\d*\.\d*\.\d*)</td><td>(\d*?)</td>", tt)
        echo(1, "Get Free proxy List", url, len(t_list))
        return ["{}:{}".format(ii, jj) for ii, jj in t_list]

    def get_proxy_free(self):
        urls = [
            "https://www.sslproxies.org",
            "https://free-proxy-list.net",
            "https://www.us-proxy.org",
            "https://free-proxy-list.net/uk-proxy.html",
            "https://free-proxy-list.net/anonymous-proxy.html",
            "http://www.google-proxy.net",
        ]
        t_list = []
        for url in urls:
            t_list.extend(self.get_free_proxy(url))
        t_list.extend(self.get_api())
        for ii in ["http", "https"]:
            t_list.extend(self.get_download(ii))
        for ii in range(15):
            t_list.extend(self.get_hideme(ii))
        t_list = list(set(t_list))
        with open(data_dir + "gatherproxy", "w") as f:
            f.write("\n".join(t_list))

    def ip_decoder(self, data: str):
        data = re.sub("\+", "\x20", data)
        data = re.sub(
            "%([a-fA-F0-9][a-fA-F0-9])",
            lambda i: chr(int("0x" + i.group()[1:], 16)),
            data,
        )
        return re.findall(">(.*?)</a", data)

    def get_api(self):
        API_KEY = self.scraper_key
        url = "http://api.scraperapi.com/?api_key={}&url=http://httpbin.org/ip".format(
            API_KEY
        )
        t_list = []
        for ii in range(7):
            tt = basic_req(url, 1)
            if not isinstance(tt, dict) or "origin" not in tt:
                continue
            t_list.append(tt["origin"])
        echo(1, "Get scraperapi", len(t_list))
        return t_list

    def get_download(self, types: str):
        url = "https://www.proxy-list.download/api/v0/get?l=en&t=" + types
        t = int(time_str(time_format="%d"))
        if t % 3 == 0:
            tt = basic_req(url, 1)
        else:
            tt = self.proxy_req(url, 1)
        if not isinstance(tt, list) or len(tt) < 1:
            return []
        tt_list = tt[0]["LISTA"]
        echo(1, "Get download", types, len(tt_list))
        return ["{}:{}".format(ii["IP"], ii["PORT"]) for ii in tt_list]

    def get_freeproxylists_net(self, pn: int):
        url = "http://www.freeproxylists.net/?page={}".format(pn)
        header = {
            "Host": "www.freeproxylists.net",
            "Proxy-Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_16_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4185.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "Accept-Language": "en-US,en;q=0.9",
        }

    def get_hideme(self, pn: int):
        url = "https://hidemy.name/en/proxy-list/"
        if pn:
            url += "?start={}".format((pn + 1) * 64)
        tt = basic_req(url, 3)
        res = re.findall("<tr><td>([0-9\.]*?)</td><td>([0-9\.]*?)</td>", tt)
        echo(1, "Get Hideme page: No.{} {} items.".format(pn + 1, len(res)))
        return ["{}:{}".format(ii, jj) for ii, jj in res]

    def get_other_proxies(self, url: str):
        """ get other proxies """
        pages = re.findall(
            r"<h3[\s\S]*?<a.*?(http.*?\.html).*?</a>", self.request_text(url)
        )
        if not len(pages):
            echo("0|warning", "Please do not frequently request {}!!!".format(url))
        else:
            proxies = [
                re.findall(
                    r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,5}", self.request_text(ii)
                )
                for ii in pages
            ]
            self.waitjudge = [*self.waitjudge, *sum(proxies, [])]

    def load_proxies_test(self):
        """ load mode & test proxies """
        version = begin_time()
        self.load_proxies_list()
        proxies_len = len(self.waitjudge)
        self.thread_judge()
        canuse_len = len(self.canuse_proxies)
        echo(
            "1|info",
            "\nTotal Proxies num: {}\nCan use num: {}\nTime spend: {}\n".format(
                proxies_len, canuse_len, end_time(version)
            ),
        )
        with open("{}canuse_proxies.txt".format(data_dir), "w") as f:
            f.write("\n".join(self.canuse_proxies))

    def load_configure(self):
        cfg = load_cfg(ASSIGN_PATH)
        self.scraper_key = cfg["PROXY"].get("scraper_key", "")


if __name__ == "__main__":
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    parser = create_argparser("Proxy Pool")
    parser.add_argument(
        "--model", type=int, default=0, metavar="model", help="model 0/1"
    )
    parser.add_argument(
        "--test_time", type=int, default=1, metavar="test_time", help="test_time"
    )
    args = set_args(parser)
    model = args.model
    proxy = GetFreeProxy()
    if model == 1:
        proxy.get_proxy_free()
    elif model == 0:
        proxy.load_proxies_test()
        proxy.test_db(2)
    else:
        proxy.test_db(2)
