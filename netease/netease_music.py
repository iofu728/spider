# -*- coding: utf-8 -*-
# @Author: gunjianpan
# @Date:   2018-10-12 20:00:17
# @Last Modified by:   gunjianpan
# @Last Modified time: 2018-10-14 21:53:46
# coding:utf-8

import requests
from bs4 import BeautifulSoup
import sqlite3
import threading
import json
import urllib.parse
import time


class Get_list_id():
    def __init__(self):
        self.urlslist = ["全部", "华语", "欧美", "日语", "韩语", "粤语", "小语种", "流行", "摇滚", "民谣", "电子", "舞曲", "说唱", "轻音乐", "爵士", "乡村", "R&B/Soul", "古典", "民族", "英伦", "金属", "朋克", "蓝调", "雷鬼", "世界音乐", "拉丁", "另类/独立", "New Age", "古风", "后摇", "Bossa Nova", "清晨", "夜晚", "学习",
                         "工作", "午休", "下午茶", "地铁", "驾车", "运动", "旅行", "散步", "酒吧", "怀旧", "清新", "浪漫", "性感", "伤感", "治愈", "放松", "孤独", "感动", "兴奋", "快乐", "安静", "思念", "影视原声", "ACG", "儿童", "校园", "游戏", "70后", "80后", "90后", "网络歌曲", "KTV", "经典", "翻唱", "吉他", "钢琴", "器乐", "榜单", "00后"]
        self.headers = {
            'Host': "music.163.com",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Connection": "keep-alive",
            'Referer': "http://music.163.com/",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.0 Safari/537.36"}
        self.time = 0

    def run_list(self):
        start = time.time()
        threadings = []
        for id in self.urlslist:
            work = threading.Thread(target=self.get_lists, args=(id,))
            threadings.append(work)
        for work in threadings:
            work.start()
        for work in threadings:
            work.join()
        end = time.time()
        print(end - start)

    def get_lists(self, id):
        if "/" in id or "&" in id:
            f = open(id.split("/" or "&")[0] + '.txt', 'a')
        else:
            f = open(id + '.txt', 'a')

        count = 0
        while True:
            url = "http://music.163.com/discover/playlist/?order=hot&cat=" + \
                urllib.parse.quote_plus(id) + "&limit=35&offset=" + str(count)
            html = requests.get(url, headers=self.headers, verify=False).text
            try:
                table = BeautifulSoup(html, 'html.parser').find(
                    'ul', id='m-pl-container').find_all('li')
            except:
                break
            ids = []
            for item in table:
                ids.append(item.find('div', attrs={'class': 'bottom'}).find(
                    'a').get('data-res-id'))
            count += 35
            f.write(str(ids) + '\n')

    def get_id(self, list_id, file_d):
        url = 'http://music.163.com/api/playlist/detail?id=' + str(list_id)
        data = requests.get(url, headers=self.headers, verify=False).json()
        if data['code'] != 200:
            return []
        result = data['result']
        musiclist = ""
        tracks = result['tracks']
        for track in tracks:
            musiclist += (track['name'] + '\n')
        file_d.write(musiclist)
        self.time = self.time + 1

    def get_detail(self, id):
        threadings = []
        if "/" in id or "&" in id:
            f = open(id.split("/" or "&")[0] + ".txt", 'r')
        else:
            f = open(id + ".txt", 'r')
        if "/" in id or "&" in id:
            file_d = open(id.split("/" or "&")[0] + "data.txt", 'a')
        else:
            file_d = open(id + "data.txt", 'a')
        for line in f.readlines():
            for id in eval(line.replace('\n', '')):
                work = threading.Thread(
                    target=self.get_id, args=(id, file_d))
                threadings.append(work)
        for work in threadings:
            work.start()
        for work in threadings:
            work.join()
        print(self.time)

    def run_detail(self):
        self.time = 0
        start = time.time()
        threadings = []
        for id in self.urlslist:
            work = threading.Thread(target=self.get_detail, args=(id,))
            threadings.append(work)
        for work in threadings:
            work.start()
        for work in threadings:
            work.join()
        # for index in range(0, len(threadings), 10):
        #     i = 0
        #     while(i + index < len(threadings)):
        #         threadings[index + i].start()
        #         i = i + 1
        # for index in range(0, len(threadings), 10):
        #     i = 0
        #     while(i + index < len(threadings)):
        #         threadings[index + i].join()
        #         i = i + 1
        end = time.time()
        print(end - start)
        print(self.time)


# def get_id(list_id):
#     url = 'http://music.163.com/api/playlist/detail?id=' + str(list_id)
#     headers = {
#         'Host': "music.163.com",
#         "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
#         "Accept-Encoding": "gzip, deflate, br",
#         "Accept-Language": "zh-CN,zh;q=0.9",
#         "Connection": "keep-alive",
#         'Referer': "http://music.163.com/",
#         "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.0 Safari/537.36"}
#     data = requests.get(url, headers=headers, verify=False).json()
#     if data['code'] != 200:
#         return []
#     result = data['result']
#     musiclist = ''
#     tracks = result['tracks']
#     for track in tracks:
#         musiclist += (track['name'] + '\n')
#     print(musiclist)
#

# Traceback (most recent call last):
#   File "/usr/lib/python3.4/threading.py", line 920, in _bootstrap_inner
#     self.run()
#   File "/usr/lib/python3.4/threading.py", line 868, in run
#     self._target(*self._args, **self._kwargs)
#   File "/notebooks/music.py", line 69, in get_id
#     data = requests.get(url, headers=self.headers, verify=False).json()
#   File "/usr/local/lib/python3.4/dist-packages/requests/models.py", line 800, in json
#     self.content.decode(encoding), **kwargs
#   File "/usr/lib/python3.4/json/__init__.py", line 318, in loads
#     return _default_decoder.decode(s)
#   File "/usr/lib/python3.4/json/decoder.py", line 343, in decode
#     obj, end = self.raw_decode(s, idx=_w(s, 0).end())
#   File "/usr/lib/python3.4/json/decoder.py", line 361, in raw_decode
#     raise ValueError(errmsg("Expecting value", s, err.value)) from None
# ValueError: Expecting value: line 1 column 1 (char 0)
