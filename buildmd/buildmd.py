# -*- coding: utf-8 -*-
# @Author: gunjianpan
# @Date:   2019-01-31 17:08:32
# @Last Modified by:   gunjianpan
# @Last Modified time: 2019-01-31 20:33:09

import codecs
import threading
import time
import pandas as pd
import re

from bs4 import BeautifulSoup
from proxy.getproxy import GetFreeProxy
from utils.utils import begin_time, get_html, end_time
from urllib.request import urlopen


class Buildmd(object):
    """docstring for buildmd"""

    def __init__(self, ):
        self.request_list = []
        self.proxyclass = GetFreeProxy()
        self.failured_map = {}
        self.get_lists()
        self.img_map = {}

    def joint_url(self, tid):
        """
        joint url
        """
        return 'http://note.youdao.com/yws/public/note/' + str(tid) + '?editorType=0&cstk=S0RcfVHi'

    def find_title(self, index):
        if int(index) < 5:
            return 'winter18/' + str(index + 1) + '.md'
        if int(index) < 9:
            return 'autumn18/' + str(index - 4) + '.md'
        if int(index) < 19:
            return 'summer18/' + str(index - 8) + '.md'
        if int(index) < 23:
            return 'spring18/' + str(index - 18) + '.md'
        if int(index) < 25:
            return 'winter17/' + str(index - 22) + '.md'

    def get_lists(self):
        """
        get title lists
        """
        url = self.joint_url('3bb0c25eca85e764b6d55a281faf7195')
        title_json = self.proxyclass.get_request_proxy(url, 1)
        if not title_json:
            if self.can_retry(url):
                self.get_lists()
            return
        content = BeautifulSoup(
            title_json['content'], 'html.parser').find_all('a')
        self.request_list = [
            re.split(r'/|=', index.text)[-1] for index in content]

    def build_md(self):
        """
        build md
        """
        version = begin_time()

        threadings = []
        for index, tid in enumerate(self.request_list):
            work = threading.Thread(
                target=self.build_md_once, args=(index, tid,))
            threadings.append(work)

        for work in threadings:
            work.start()
        for work in threadings:
            work.join()
        img_map = {k: self.img_map[k] for k in sorted(self.img_map.keys())}
        img_threadings = []
        for index in img_map.keys():
            for img_id, img_url in enumerate(img_map[index]):
                work = threading.Thread(
                    target=self.load_img, args=(index, img_id, img_url,))
                img_threadings.append(work)
        for work in img_threadings:
            work.start()
        for work in img_threadings:
            work.join()

        end_time(version)

    def build_md_once(self, index, tid):
        """
        build md in one
        """
        url = self.joint_url(tid)
        title_json = self.proxyclass.get_request_proxy(url, 1)
        if not title_json:
            if self.can_retry(url, index):
                self.build_md_once(index, tid)
            return
        content = BeautifulSoup(
            title_json['content'], 'html.parser').find_all('div')
        text = []
        img_href = []
        img_id = 1
        ttid = 1
        img_title = self.find_title(index).split('/')[1][:-3]
        for word in content:
            temp_text = ''
            if word.span and len(word.span.text) and not word.span.text[0].isdigit:
                temp_text = '## ' + word.span.text
                ttid = 1
            if word.img:
                temp_text = '![image](../' + img_title + str(img_id) + '.jpg)'
                img_href.append(word.img['src'].replace('https', 'http'))
                img_id += 1

            if not len(temp_text):
                temp_text = word.text
                if len(temp_text) and temp_text[0].isdigit():
                    temp_text = str(ttid) + '. **' + \
                        ' '.join(temp_text.split('\xa0')[1:]).strip() + '**'
                    ttid += 1
                if len(temp_text) and (temp_text[0] == '￥' or temp_text[0] == '€'):
                    temp_text = '<a>' + temp_text + '</a>'
            text.append(temp_text)
        with open('buildmd/' + self.find_title(index), 'w') as f:
            f.write('\n'.join(text))
        self.img_map[index] = img_href
        print(index, len(img_href))

    def load_img(self, index, img_id, img_url):
        """
        load img
        """
        img = self.proxyclass.get_request_proxy(img_url, 2)
        if img == True or img == False:
            if self.can_retry(img_url):
                self.load_img(index, img_id, img_url)
            return
        with open('buildmd/' + self.find_title(index).split('/')[0] + '/img/' + self.find_title(index).split('/')[1][:-3] + str(img_id + 1) + '.jpg', 'wb') as f:
            f.write(img.content)

    def can_retry(self, url, index=None):
        """
        judge can retry once
        """

        if url not in self.failured_map:
            self.failured_map[url] = 0
            # print("Retry " + str(self.failured_map[url]) + ' ' + url)
            return True
        elif self.failured_map[url] < 2:
            self.failured_map[url] += 1
            # print("Retry " + str(self.failured_map[url]) + ' ' + url)
            return True
        else:
            if index:
                index = str(index)
            print("Failured " + url + index)
            self.proxyclass.log_write(url)
            self.failured_map[url] = 0
            return False
