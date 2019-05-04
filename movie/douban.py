# -*- coding: utf-8 -*-
# @Author: gunjianpan
# @Date:   2019-04-29 20:04:28
# @Last Modified by:   gunjianpan
# @Last Modified time: 2019-05-04 15:29:53

import json
import os
import random
import re
import string
import threading
import time
import urllib
from collections import Counter

import numpy as np

from proxy.getproxy import GetFreeProxy
from util.util import (basic_req, begin_time, can_retry, changeHeaders,
                       changeHtmlTimeout, changeJsonTimeout, dump_bigger, echo,
                       end_time, load_bigger, shuffle_batch_run_thread)

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
        self.get_movie_tag()

    def generate_cookie(self, type: str = 'explore'):
        ''' generate bid '''
        bid = "".join(random.sample(string.ascii_letters + string.digits, 11))
        changeHeaders({"Cookie": "bid={}".format(bid),
                       'Referer': '{}{}'.format(self.BASIC_URL, type)})

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
        tag = basic_req(self.SEARCH_TAG_URL % 'movie', 1)
        self.tag_movie = tag['tags']
        tag = basic_req(self.SEARCH_TAG_URL % 'tv', 1)
        self.tag_tv = tag['tags']
        basic_text = basic_req(self.TAG_URL, 3)
        EXPLORE_APP_URL = re.findall(r'https.*explore/app.js', basic_text)[0]
        app_js_text = basic_req(EXPLORE_APP_URL, 3)
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
        if os.path.exists(comment_path):
            self.comment = load_bigger(comment_path)
        else:
            self.comment = {ii: {} for ii in self.movie_id2name.keys()}
        if os.path.exists(user_path):
            self.user_info = load_bigger(user_path)
        else:
            self.user_info = {}
        self.finish_list = []
        self.again_list = []
        self.more_user = []
        comment_thread = []
        for ii in self.movie_id2name.keys():
            for jj in range(0, 100, 20):
                comment_thread.append(threading.Thread(
                    target=self.load_user_id, args=(ii, jj)))
        shuffle_batch_run_thread(comment_thread, 600, True)
        time.sleep(20)
        while len(self.more_user):
            more_user = [threading.Thread(
                target=self.load_user_id, args=(ii[0], ii[1],)) for ii in self.more_user]
            self.more_user = []
            again_list = [threading.Thread(
                target=self.load_user_id, args=(ii[0], ii[1],)) for ii in self.again_list]
            self.again_list = []
            shuffle_batch_run_thread([*more_user, again_list], 600, True)
            time.sleep(20)
        time.sleep(360)
        dump_bigger(self.comment, comment_path)
        dump_bigger(self.user_info, user_path)
        comment_num = sum([len(ii.keys()) for ii in self.comment.values()])
        echo(1, 'Comment num: {}\nSpend time: {:.2f}s\n'.format(
            comment_num, end_time(version, 0)))

    def load_user_id(self, movie_id: int, start: int):
        ''' load comment '''
        url = self.COMMENT_URL % (movie_id, start)
        comment_json = proxy_req(url, 1)
        if comment_json is None or not 'html' in comment_json:
            if can_retry(url, 5):
                time.sleep(random.random() * 3.14)
                self.load_user_id(movie_id, start)
            else:
                self.again_list.append([movie_id, start])
                echo(0, url, 'Failed')
            return
        comment_html = comment_json['html']
        user_list = re.findall(
            r'title="(.*?)" href="https://www.douban.com/people/([\s\S]{1,30}?)/"\>', comment_html)

        if not len(user_list):
            return
        votes = re.findall(r'votes"\>(\w{1,7}?)<', comment_html)
        comment_time = re.findall(r'-time " title="(.*?)">\n', comment_html)
        short = re.findall(r'class="short">([\s\S]*?)</span>', comment_html)
        if len(user_list) != len(comment_time) or len(user_list) != len(short):
            echo(0, url, 'Comment reg error!!!')
        comment = {jj[1]: [jj[0], jj[1], comment_time[ii], short[ii], votes[ii] if ii < len(votes) else '']
                   for ii, jj in enumerate(user_list)}
        user_list = {ii[1] for ii in user_list}
        self.user_info = {*self.user_info, *user_list}
        self.comment[movie_id] = {**self.comment[movie_id], **comment}
        if len(user_list) == 20 and not (start + 20) % 100:
            self.more_user.append([movie_id, start])
        self.finish_list.append(1)
        if not len(self.finish_list) % 100:
            echo(2, len(self.finish_list), 'Finish...')
            dump_bigger(self.comment, '{}douban_comment.pkl'.format(data_dir))
            dump_bigger(self.user_info, '{}douban_user.pkl'.format(data_dir))

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
    mv.get_comment_v1()
