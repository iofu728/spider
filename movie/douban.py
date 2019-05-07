# -*- coding: utf-8 -*-
# @Author: gunjianpan
# @Date:   2019-04-29 20:04:28
# @Last Modified by:   gunjianpan
# @Last Modified time: 2019-05-07 19:55:29

import json
import os
import random
import re
import string
import sys
import shutil
import threading
import time
import urllib
from collections import Counter
import pickle

import numpy as np
from bs4 import BeautifulSoup

from proxy.getproxy import GetFreeProxy
from util.util import (basic_req, begin_time, can_retry, changeHeaders,
                       changeHtmlTimeout, changeJsonTimeout, dump_bigger, echo,
                       end_time, load_bigger, shuffle_batch_run_thread)

sys.setrecursionlimit(10000)
proxy_req = GetFreeProxy().proxy_req
data_dir = 'movie/data/'


class DouBan:
    ''' get douban movie info '''

    API_BASIC_URL = 'http://api.douban.com/v2/movie/'
    API_PROXY_URL = 'http://douban.uieee.com/v2/movie/'
    BASIC_URL = 'https://movie.douban.com/'
    SEARCH_TAG_URL = '{}j/search_tags?type=%s&source='.format(BASIC_URL)
    SEARCH_SUBJECT_URL = '{}j/search_subjects?'.format(BASIC_URL)
    NEW_SEARCH_SUBJECT_URL = '{}j/new_search_subjects?'.format(BASIC_URL)
    TAG_URL = '{}tag/#/'.format(BASIC_URL)
    COMMENT_URL = '{}subject/%d/comments?start=%d&limit=20&sort=new_score&status=P&comments_only=1'.format(
        BASIC_URL)
    COMMENT_PROXY_URL = '{}subject/%d/comments?start=%d&count=100'.format(
        API_PROXY_URL)
    USER_COLLECT_URL = '{}people/%s/collect?start=%d&sort=time&rating=all&filter=all&mode=list'.format(
        BASIC_URL)

    def __init__(self):
        self.movie_id_dict = {}
        self.movie_id2name = {}
        self.user_list = []
        self.again_list = []
        self.page_size = 100
        self.page_limit = 1000
        self.proxy_can_use = False
        self.sort_list = ['time', 'recommend', 'rank']
        self.rank_list = ['top250', 'us_box',
                          'weekly', 'in_theaters', 'coming_soon']
        # self.get_movie_tag()

    def generate_cookie(self, types: str = 'explore'):
        ''' generate bid '''
        bid = "".join(random.sample(string.ascii_letters + string.digits, 11))
        changeHeaders({"Cookie": "bid={}".format(bid),
                       'Referer': '{}{}'.format(self.BASIC_URL, types)})

    def get_movie_lists(self):
        ''' get movie list '''

        version = begin_time()
        movie_get = []
        for kk in range(0, 1100, 100):
            for jj in self.sort_list:
                for ii in self.tag_movie:
                    movie_get.append(threading.Thread(
                        target=self.get_movie_lists_once, args=('movie', ii, jj, kk,)))
                for ii in self.tag_tv:
                    movie_get.append(threading.Thread(
                        target=self.get_movie_lists_once, args=('tv', ii, jj, kk,)))
        shuffle_batch_run_thread(movie_get, 500, True)
        again_list = [threading.Thread(target=self.get_movie_lists_once, args=(
            ii[0], ii[1], ii[2], ii[3],)) for ii in self.again_list]
        shuffle_batch_run_thread(again_list, 500, True)
        self.again_list = []
        echo(1, len(self.movie_id2name.keys()))

        changeHtmlTimeout(40)
        movie_get = []
        tag_categories = self.tag_categories
        for mm in range(0, 10000, 1000):
            for tags in tag_categories[0][1:]:
                for genres in tag_categories[1][1:]:
                    for ii, jj in self.yearMap.values():
                        year_range = '{},{}'.format(ii, jj)
                        for sorts in self.tabs:
                            movie_get.append(threading.Thread(
                                target=self.get_movie_list_from_tabs, args=(sorts, tags, genres, year_range, mm,)))
        echo(2, 'Thread Num:', len(movie_get))
        shuffle_batch_run_thread(movie_get, 900, True)
        again_list = [threading.Thread(target=self.get_movie_list_from_tabs, args=(
            ii[0], ii[1], ii[2], ii[3], ii[4],)) if len(ii) == 5 else threading.Thread(target=self.get_movie_lists_once, args=(
                ii[0], ii[1], ii[2], ii[3],)) for ii in self.again_list]
        shuffle_batch_run_thread(again_list, 900, True)
        time.sleep(120)
        changeJsonTimeout(10)
        for ii in self.rank_list:
            self.get_movie_rank(ii, 0)
            if ii == 'top250':
                self.get_movie_rank(ii, 100)
                self.get_movie_rank(ii, 200)

        movie_list = self.movie_id2name.keys()
        output_path = '{}douban_movie_id'.format(data_dir)
        with open(output_path + '.txt', 'w') as f:
            f.write('\n'.join([str(ii) for ii in movie_list]))
        dump_bigger(self.movie_id2name, output_path + '.pkl')

        movie_num = len(movie_list)
        echo(1, 'Movie num: {}\nOutput path: {}\nSpend time: {:.2f}s\n'.format(
            movie_num, output_path, end_time(version, 0)))

    def get_movie_lists_once(self, types: str, tag: str, sorts: str, page_start: int):
        ''' get movie lists once '''
        params_dict = {'type': types, 'tag': urllib.parse.quote(tag), 'sort': sorts,
                       'page_limit': self.page_size, 'page_start': page_start}
        params = ['{}={}'.format(ii, jj) for ii, jj in params_dict.items()]
        url = '{}{}'.format(self.SEARCH_SUBJECT_URL, '&'.join(params))
        self.generate_cookie()
        movie_json = proxy_req(url, 1)
        if movie_json is None or not 'subjects' in movie_json:
            if can_retry(url):
                self.get_movie_lists_once(types, tag, sorts, page_start)
            else:
                self.again_list.append([types, tag, sorts, page_start])
                echo(0, url, 'Failed')
            return
        echo(2, url, 'loaded')
        id2name = {int(ii['id']): ii['title'] for ii in movie_json['subjects']}
        self.movie_id2name = {**self.movie_id2name, **id2name}

    def get_movie_list_from_tabs(self, sorts: str, tags: str, genres: str, year_range: str, star: int = 0):
        ''' get info from movie list '''
        params_dict = {'sort': sorts, 'range': '0,10', 'tags': urllib.parse.quote(tags),
                       'genres': urllib.parse.quote(genres), 'star': star, 'limit': 1000 if star < 9000 else 9999 - star, 'year_range': year_range}
        params = ['{}={}'.format(ii, jj)
                  for ii, jj in params_dict.items() if jj != '']
        url = '{}{}'.format(self.NEW_SEARCH_SUBJECT_URL, '&'.join(params))
        self.generate_cookie()
        movie_req = proxy_req(url, 2)
        if movie_req is None:
            if can_retry(url):
                self.get_movie_list_from_tabs(
                    sorts, tags, genres, year_range, star)
            else:
                self.again_list.append([sorts, tags, genres, year_range, star])
                echo(0, url, 'Failed')
            return
        if movie_req.status_code != 200:
            return
        try:
            movie_json = movie_req.json()
            echo(2, url, 'loaded')
            id2name = {int(ii['id']): ii['title'] for ii in movie_json['data']}
            self.movie_id2name = {**self.movie_id2name, **id2name}
        except:
            echo(0, url, 'Except!')

    def get_movie_tag(self):
        ''' get movie tag '''
        tag = proxy_req(self.SEARCH_TAG_URL % 'movie', 1)
        self.tag_movie = tag['tags']
        tag = proxy_req(self.SEARCH_TAG_URL % 'tv', 1)
        self.tag_tv = tag['tags']
        basic_text = proxy_req(self.TAG_URL, 3)
        EXPLORE_APP_URL = re.findall(r'https.*explore/app.js', basic_text)[0]
        app_js_text = proxy_req(EXPLORE_APP_URL, 3)
        json_list = re.findall(r'ion\(\){return(.*?})}}', app_js_text)[2]
        params = [*re.findall(r',(\w*?):', json_list), 'tag_items']
        for ii in params:
            json_list = json_list.replace('{}:'.format(ii), '"{}":'.format(ii))
        json_list = json_list.replace('!', '').replace(
            'document.documentElement.clientHeight', '"document.documentElement.clientHeight"')
        json_map = json.loads(json_list + '}')
        self.tag_categories = json_map['tag_categories']
        self.yearMap = json_map['yearMap']
        self.tabs = [ii[0] for ii in json_map['tabs']]

    def get_movie_rank(self, types: str, start: int):
        url = '{}{}?start={}&count=100'.format(
            self.API_PROXY_URL, types, start)
        rank_json = proxy_req(url, 1)
        if rank_json is None or not 'subjects' in rank_json:
            if can_retry(url):
                self.get_movie_rank(types, start)
            else:
                self.again_list.append([types, start])
                echo(0, url, 'Failed')
            return
        echo(2, url, 'loaded')

        id2name = {int(ii['id']) if 'id' in ii else int(ii['subject']['id']): ii['title']
                   if 'title' in ii else ii['subject']['title'] for ii in rank_json['subjects']}
        self.movie_id2name = {**self.movie_id2name, **id2name}

    def load_list(self):
        version = begin_time()
        self.movie_id2name = load_bigger(
            '{}douban_movie_id.pkl'.format(data_dir))
        with open('{}movie_list.txt'.format(data_dir), 'r') as f:
            external_list = [ii.strip() for ii in f.readlines()]
        total_list = list(self.movie_id2name.values()) + external_list
        word_map = Counter(total_list)
        wait_list = [ii for ii in external_list if word_map[ii] == 1]
        self.finish_list = []
        changeJsonTimeout(10)
        wait_queue = [threading.Thread(
            target=self.get_search_list, args=(ii,)) for ii in wait_list]
        shuffle_batch_run_thread(wait_queue, 600, True)
        again_list = [threading.Thread(
            target=self.get_search_list, args=(ii,)) for ii in self.again_list]
        shuffle_batch_run_thread(again_list, 600, True)
        time.sleep(660)
        output_path = '{}movie_id.pkl'.format(data_dir)
        dump_bigger(self.movie_id2name, output_path)
        movie_num = len(self.movie_id2name.keys())
        echo(1, 'Movie num: {}\nOutput path: {}\nSpend time: {:.2f}s\n'.format(
            movie_num, output_path, end_time(version, 0)))

    def find_no_exist(self):
        with open('{}movie_list.txt'.format(data_dir), 'r') as f:
            external_list = [ii.strip() for ii in f.readlines()]
        exist_names = list(self.movie_id2name.values())
        wait_list = []
        for ii in external_list:
            if not ii in exist_names:
                wait_list.append(ii)
        dump_bigger(wait_list, '{}wait_list.pkl'.format(data_dir))

    def get_search_list(self, q: str):
        if self.proxy_can_use:
            base_url = self.API_PROXY_URL if random.random() * 10 > 7 else self.API_BASIC_URL
        else:
            base_url = self.API_BASIC_URL
        url = '{}search?q={}&count=66'.format(base_url, urllib.parse.quote(q))
        search_json = proxy_req(url, 1)
        if search_json is None or not 'subjects' in search_json:
            if search_json and 'code' in search_json:
                if search_json['code'] == 112:
                    self.proxy_can_use = False
            if can_retry(url, 6):
                time.sleep(random.random() *
                           (3.14 + random.randint(4, 10)) + 3.14)
                self.get_search_list(q)
            else:
                self.again_list.append(q)
                echo(0, url, 'Failed')
            return
        # echo(2, url, 'loaded')
        id2name = {int(ii['id']): ii['title']
                   for ii in search_json['subjects']}
        self.movie_id2name = {**self.movie_id2name, **id2name}
        self.finish_list.append(q)
        if not len(self.finish_list) % 600:
            echo(2, len(self.finish_list), 'Finish...')
            dump_bigger(self.movie_id2name,
                        '{}douban_movie_id.pkl'.format(data_dir))

    def get_comment_v1(self):
        ''' get comment info & user info '''
        version = begin_time()
        self.movie_id2name = load_bigger(
            '{}douban_movie_id.pkl'.format(data_dir))

        comment_path = '{}douban_comment.pkl'.format(data_dir)
        user_path = '{}douban_user.pkl'.format(data_dir)
        finish_path = '{}douban_cf.pkl'.format(data_dir)
        more_path = '{}douban_more.pkl'.format(data_dir)
        again_path = '{}douban_again.pkl'.format(data_dir)
        # if os.path.exists(comment_path):
        #     self.comment = load_bigger(comment_path)
        # else:
        #     self.comment = {ii: {} for ii in self.movie_id2name.keys()}
        if os.path.exists(user_path):
            self.user_info = load_bigger(user_path)
        else:
            self.user_info = {}
        if os.path.exists(finish_path):
            self.finish_list = load_bigger(finish_path)
        else:
            self.finish_list = {}
        if os.path.exists(more_path):
            self.more_user = load_bigger(more_path)
        else:
            self.more_user = []
        if os.path.exists(again_path):
            self.again_list = load_bigger(again_path)
        comment_thread = []
        echo(0, 'Begin generate Thread')

        for ii in self.movie_id2name.keys():
            if (ii, 0) in self.finish_list:
                continue
            comment_thread.append(threading.Thread(
                target=self.load_user_id, args=(ii, 0)))
        again_thread = [threading.Thread(
            target=self.load_user_id, args=(ii[0], ii[1])) for ii in self.again_list if tuple(ii) not in self.finish_list]
        comment_thread = [*comment_thread, *again_thread]
        echo(0, 'End of Generate Thread.')
        self.pre_shuffle_batch_run_thread(comment_thread)
        time.sleep(20)
        while len(self.more_user):
            echo(2, 'len of more', len(self.more_user))
            again_list = [threading.Thread(
                target=self.load_user_id, args=(ii[0], ii[1],)) for ii in self.again_list if tuple(ii) not in self.finish_list]
            self.again_list = []
            for ii in self.more_user:
                if tuple(ii) in self.finish_list:
                    continue
                again_list.append(threading.Thread(
                    target=self.load_user_id, args=(ii[0], ii[1],)))
            self.more_user = []
            echo(2, 'len of thread', len(again_list))
            self.pre_shuffle_batch_run_thread(again_list)
            time.sleep(20)
        time.sleep(360)
        # dump_bigger(self.comment, comment_path)
        dump_bigger(self.user_info, user_path)
        dump_bigger(self.finish_list, finish_path)
        comment_num = sum([len(ii.keys()) for ii in self.comment.values()])
        echo(1, 'Comment num: {}\nSpend time: {:.2f}s\n'.format(
            comment_num, end_time(version, 0)))

    def pre_shuffle_batch_run_thread(self, comment_thread: list):
        ''' pre shuffle batch '''
        index = 0
        total_num = len(comment_thread)
        while index < total_num:
            self.test_proxy()
            if self.proxy_can_use:
                next_index = min(total_num, index +
                                 400 if self.proxy_can_use else index + 2000)
                bath_size = 40 if self.proxy_can_use else 200
                json_timeout = 20 if self.proxy_can_use else 10
                changeJsonTimeout(json_timeout)
                shuffle_batch_run_thread(
                    comment_thread[index:next_index], bath_size, not self.proxy_can_use)
                index = next_index
            else:
                time.sleep(60)

    def test_proxy(self) -> bool:
        url = '{}search?q=%E5%A5%87%E5%BC%82%E5%8D%9A%E5%A3%AB&count=66'.format(
            self.API_PROXY_URL)
        test = basic_req(url, 1)
        if test is None:
            return False
        if 'code' in test:
            self.proxy_can_use = False
            return False
        if 'subjects' not in test:
            return False
        if len(test['subjects']) == 4:
            self.proxy_can_use = True
            return True
        return False

    def load_comment_v1(self, movie_id: int, start: int):
        ''' load comment '''
        url = self.COMMENT_URL % (movie_id, start)
        self.generate_cookie()
        comment_json = proxy_req(url, 1)
        if comment_json is None or not 'html' in comment_json:
            if can_retry(url):
                time.sleep(random.random() * random.randint(0, 4))
                self.load_user_id(movie_id, start)
            else:
                self.again_list.append([movie_id, start])
                echo(0, url, 'Failed')
            return
        comment_html = comment_json['html']
        # comment_bs4 = BeautifulSoup(comment_html, 'html.parser')
        # comment = {}
        # for ii in comment_bs4.find_all('div', class_='comment-item'):
        #     user_id = ii.a['href'].split('/')[-2]
        #     user_name = ii.a['title']
        #     votes = ii.find_all('span', class_='votes')
        #     votes = votes[0].text if len(votes) else ''
        #     comment_time = ii.find_all(
        #         'span', class_='comment-time')[0]['title']
        #     rate = ii.find_all('span', class_='rating')
        #     rate = rate[0]['class'][0].split('allstar')[1] if len(rate) else ''
        #     short = ii.find_all('span', class_='short')
        #     short = short[0] if len(short) else ''
        #     comment[user_id] = [user_name, user_id,
        #                         comment_time, short, votes, rate]
        # user_list = set(comment)

        user_list = re.findall(
            r'title="(.*?)" href="https://www.douban.com/people/([\s\S]{1,30}?)/"\>', comment_html)

        if not len(user_list):
            self.finish_list[(movie_id, start)] = 0
            self.checkpoint()
            return
        votes = re.findall(r'votes"\>(\w{1,7}?)<', comment_html)
        comment_time = re.findall(r'-time " title="(.*?)">\n', comment_html)
        short = re.findall(r'class="short">([\s\S]*?)</span>', comment_html)
        rate = re.findall('allstar(\w{1,2}?) rat', comment_html)
        if len(user_list) != len(comment_time) or len(user_list) != len(short):
            echo(0, url, 'Comment reg error!!!')
        comment = {jj[1]: [jj[0], jj[1], comment_time[ii], short[ii] if ii < len(short) else '', votes[ii] if ii < len(votes) else '', rate[ii] if ii < len(rate) else '']
                   for ii, jj in enumerate(user_list)}
        user_list = {ii[1] for ii in user_list}
        self.user_info = {*self.user_info, *user_list}
        self.comment[movie_id] = {**self.comment[movie_id], **comment}
        if len(user_list) == 20 and (not (start + 20) % 100 or start < 100):
            self.more_user.append([movie_id, start + 20])
        self.finish_list[(movie_id, start)] = 0
        self.checkpoint()

    def load_user_id(self, movie_id: int, start: int):
        ''' load user id schedule '''
        if self.proxy_can_use:
            self.load_comment_v2(movie_id, start)
        # else:
        #     self.load_comment_v1(movie_id, start)

    def load_comment_v2(self, movie_id: int, start: int):
        ''' load comment by proxy'''
        url = self.COMMENT_PROXY_URL % (movie_id, start)
        self.generate_cookie()
        comment_json = basic_req(url, 1)
        if comment_json is None or not 'comments' in comment_json:
            if not comment_json is None and 'code' in comment_json:
                if comment_json['code'] == 5000:
                    self.finish_list[(movie_id, start)] = 0
                    self.checkpoint()
                else:
                    comment_json['code'] == 112
                    self.proxy_can_use = False
                    echo(2, url, 'Failed')
                    self.again_list.append([movie_id, start])
            else:
                self.again_list.append([movie_id, start])
                echo(0, url, 'Failed')
            return
        comment_html = comment_json['comments']
        comment = {(movie_id, ii['author']['id']): [ii['author']['name'], ii['author']['id'],
                                                    ii['created_at'], ii['content'], '', ii['rating']['value']] for ii in comment_html}
        user_list = {ii['author']['id'] for ii in comment_html}
        self.user_info = {*self.user_info, *user_list}
        self.comment = {**self.comment, **comment}
        if len(user_list) == 100:
            self.more_user.append([movie_id, start + 100])
        self.finish_list[(movie_id, start)] = 0
        self.finish_list[(movie_id, start + 20)] = 0
        self.finish_list[(movie_id, start + 40)] = 0
        self.finish_list[(movie_id, start + 60)] = 0
        self.finish_list[(movie_id, start + 80)] = 0
        self.checkpoint()

    def checkpoint(self):
        checkpoint_num = 32 if self.proxy_can_use else 200
        if not len(self.finish_list.keys()) % checkpoint_num:
            echo(2, len(self.finish_list), 'Finish...')
            # dump_bigger(self.comment, '{}douban_comment.pkl'.format(data_dir))
            dump_bigger(self.user_info, '{}douban_user.pkl'.format(data_dir))
            dump_bigger(self.finish_list, '{}douban_cf.pkl'.format(data_dir))
            dump_bigger(self.more_user, '{}douban_more.pkl'.format(data_dir))
            dump_bigger(self.again_list, '{}douban_again.pkl'.format(data_dir))

    def load_user_comment(self):
        self.movie_id2name = load_bigger(
            '{}douban_movie_id.pkl'.format(data_dir))

        comment_path = '{}douban_12.pkl'.format(data_dir)
        user_path = '{}douban_user.pkl'.format(data_dir)
        finish_path = '{}douban_uf.pkl'.format(data_dir)
        user_detail_path = '{}douban_ud.pkl'.format(data_dir)
        if os.path.exists(comment_path):
            self.comment = load_bigger(comment_path)
        else:
            self.comment = {}

        if os.path.exists(user_detail_path):
            self.user_detail = load_bigger(user_detail_path)
        else:
            self.user_detail = {}
        if os.path.exists(finish_path):
            self.finish_list_user = load_bigger(finish_path)
        else:
            self.finish_list_user = {}
        threading.Thread(target=self.get_comment_v1, args=()).start()
        while True:
            if os.path.exists(user_path):
                self.user_info = load_bigger(user_path)
            else:
                self.user_info = {}
            echo(1, 'Begin New loop...')
            wait_user = []
            user_info = self.user_info.copy()
            user_info = sorted(
                user_info, key=lambda ii: self.user_detail[ii][0] if ii in self.user_detail else 0, reverse=True)
            for ii in user_info:
                if not ii in self.user_detail:
                    wait_user.append([ii, 0])
                else:
                    temp_pn = 0
                    max_pn = self.user_detail[ii][0]
                    while(temp_pn <= max_pn and (ii, temp_pn) in self.finish_list_user):
                        temp_pn += 1
                    if temp_pn > max_pn:
                        continue
                    wait_user.append([ii, temp_pn])

                if len(wait_user) > 9999:
                    break
            wait_thread = [threading.Thread(
                target=self.get_user_comment, args=(ii, jj,)) for ii, jj in wait_user]
            echo(2, 'len of thread', len(wait_thread))
            self.pre_shuffle(wait_thread)

    def pre_shuffle(self, comment_thread: list):
        ''' pre shuffle batch '''
        index = 0
        total_num = len(comment_thread)
        while index < total_num:
            self.test_proxy()
            next_index = min(total_num, index + 2000)
            bath_size = 200
            json_timeout = 20
            changeJsonTimeout(json_timeout)
            shuffle_batch_run_thread(
                comment_thread[index:next_index], bath_size, True)
            index = next_index

    def get_user_comment(self, user_id: str, pn: int):
        ''' get user comment '''
        url = self.USER_COLLECT_URL % (user_id, pn * 30)
        self.generate_cookie()
        collect_text = proxy_req(url, 3).replace(
            ' ', '').replace('\n', '').replace('&nbsp;', '')
        if collect_text is '':
            if can_retry(url, 1):
                self.get_user_comment(user_id, pn)
            return
        try:
            if not user_id in self.user_detail:

                total = int(re.findall('\((\d{1,7}?)\)', collect_text)[0])
                page = total // 30 + (1 if total % 20 else 0) - 1
                tag = re.findall(
                    'title="\w{1,20}">(.*?)</a><span>(\d{1,6})', collect_text)
                self.user_detail[user_id] = [page, tag]
                # echo(0, 'tag len', len(tag))
            user_name = re.findall('<h1>([\s\S]{0,20}?)看过', collect_text)[0]
            movie_ids = re.findall('/subject/(\d.*?)/">', collect_text)
            date = re.findall(
                '<divclass="date">(.{0,35})(\d{4}-\d{2}-\d{2})</div>', collect_text)
            rating = [re.findall('spanclass="rating(\d)-t', ii[0])[0]
                      if len(ii[0]) else '' for ii in date]
            for ii, jj in enumerate(movie_ids):
                movie_id = int(jj)
                temp_comment = [user_id, user_name,
                                date[ii][1], '', '', rating[ii]]

                if (movie_id, user_id) in self.comment:
                    temp_comment[3] = self.comment[(movie_id, user_id)][3]
                    temp_comment[4] = self.comment[(movie_id, user_id)][4]
                self.comment[(movie_id, user_id)] = temp_comment
        except:
            pass
        self.finish_list_user[(user_id, pn)] = 0
        if not len(self.finish_list_user.keys()) % 4000:
            echo(2, len(self.finish_list_user), 'Finish...')
            dump_bigger(self.finish_list_user,
                        '{}douban_uf.pkl'.format(data_dir))
            dump_bigger(self.user_detail,
                        '{}douban_ud.pkl'.format(data_dir))
            comment_loader = self.comment.copy()
            dump_bigger(comment_loader, '{}douban_12.pkl'.format(data_dir))
            echo(0, 'Dumps Over')
        if len(self.finish_list_user.keys()) % 30000 == 100:
            comment_loader = self.comment.copy()
            dump_bigger(comment_loader, '{}douban_comment_{}.pkl'.format(
                data_dir, len(self.finish_list_user.keys())))

    def shuffle_movie_list(self):
        ''' prepare distribution spider '''
        movie_id2name = load_bigger('movie/data/douban_movie_id.pkl')
        ids = list(movie_id2name.keys())
        np.random.shuffle(ids)
        one_bath_size = len(ids) // 3
        first_map = {ii: 0 for ii in ids[:one_bath_size]}
        second_map = {ii: 0 for ii in ids[one_bath_size:one_bath_size * 2]}
        third_map = {ii: 0 for ii in ids[one_bath_size*2:]}
        dump_bigger(first_map, 'movie/data/douban_movie_id1.pkl')
        dump_bigger(second_map, 'movie/data/douban_movie_id2.pkl')
        dump_bigger(third_map, 'movie/data/douban_movie_id3.pkl')


if __name__ == "__main__":
    mv = DouBan()
    # mv.get_movie_lists()
    # mv.load_list()
    mv.load_user_comment()
