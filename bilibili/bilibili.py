# -*- coding: utf-8 -*-
# @Author: gunjianpan
# @Date:   2019-04-07 20:25:45
# @Last Modified by:   gunjianpan
# @Last Modified time: 2019-09-13 18:11:02


import base64
import codecs
import json
import os
import pickle
import random
import rsa
import shutil
import sys
import threading
import time
import urllib
from concurrent.futures import ThreadPoolExecutor, as_completed
from configparser import ConfigParser
from typing import List

import numpy as np
import regex

sys.path.append(os.getcwd())
from proxy.getproxy import GetFreeProxy
from util.util import (basic_req, begin_time, can_retry, changeHeaders, echo,
                       encoder_cookie, end_time, get_min_s, get_time_str,
                       headers, mkdir, read_file, send_email, time_stamp,
                       time_str)


proxy_req = GetFreeProxy().proxy_req
one_day = 86400
root_dir = os.path.abspath('bilibili')
data_dir = os.path.join(root_dir, 'data/')
history_data_dir = os.path.join(data_dir, 'history_data/')
history_dir = os.path.join(data_dir, 'history/')
comment_dir = os.path.join(data_dir, 'comment/')
dm_dir = os.path.join(data_dir, 'dm/')
assign_path = os.path.join(root_dir, 'assign_up.ini')

"""
  * bilibili @http
  * www.bilibili.com/video/av{av_id}
  * www.bilibili.com/ranking/all/155/{0/1}/{day}
  * space.bilibili.com/ajax/member/getSubmitVideos?mid={mid}&page=1&pagesize=50
  * api.bilibili.com/x/v2/reply?jsonp=jsonp&pn=%d&type=1&oid=%d&sort=0
    api.bilibili.com/x/report/click/now?jsonp=jsonp
    api.bilibili.com/x/report/click/web/h5
    api.bilibili.com/x/report/web/heartbeat
    api.bilibili.com/x/web-interface/archive/stat?aid={av_id}
    api.bilibili.com/x/relation/stat?jsonp=jsonp&callback=__jp11&vmid={mid}
"""


class Up():
    ''' some spider application in bilibili '''
    BILIBILI_URL = 'https://www.bilibili.com'
    BASIC_AV_URL = 'http://www.bilibili.com/video/av%d'
    ARCHIVE_STAT_URL = 'http://api.bilibili.com/x/web-interface/archive/stat?aid=%d'
    VIEW_URL = 'http://api.bilibili.com/x/web-interface/view?aid=%d'
    RELATION_STAT_URL = 'http://api.bilibili.com/x/relation/stat?jsonp=jsonp&callback=__jp11&vmid=%d'
    BASIC_RANKING_URL = 'https://www.bilibili.com/ranking/all/%d/'
    MEMBER_SUBMIT_URL = 'http://space.bilibili.com/ajax/member/getSubmitVideos?mid=%s&page=1&pagesize=50'
    REPLY_V2_URL = 'http://api.bilibili.com/x/v2/reply?jsonp=jsonp&pn=%d&type=1&oid=%d&sort=2'
    PLAYLIST_URL = 'https://api.bilibili.com/x/player/pagelist?aid=%d&jsonp=jsonp'
    DM_URL = 'https://api.bilibili.com/x/v1/dm/list.so?oid=%d'
    GET_KEY_URL = 'http://passport.bilibili.com/login?act=getkey&r=%f'
    LOGIN_URL = 'https://passport.bilibili.com/login'
    LOGIN_V2_URL = 'https://passport.bilibili.com/web/login/v2'
    LOGIN_OAUTH_URL = 'https://passport.bilibili.com/api/v2/oauth2/login'
    CAPTCHA_URL = 'https://passport.bilibili.com/web/captcha/combine?plat=11'
    NO_RANK_CONSTANT = 'No rank.....No Rank......No Rank.....'
    JSON_KEYS = ['code', 'message', 'ttl', 'data']

    def __init__(self):
        self.rank = {}
        self.rank_type = {}
        self.public = {}
        self.public_list = []
        self.star = {}
        self.data_v2 = {}
        self.have_assign = []
        self.have_assign_now = {1: [], 3: []}
        self.last_rank = {}
        self.last_check = {}
        self.last_view = {}
        self.last_star = {}
        self.rank_map = {}
        self.comment = {}
        self.email_send_time = {}
        self.begin_timestamp = int(time.time())
        self.av_id_list = []
        self.ac_id_map = {}
        self.del_map = {}
        self.history_check_finish = {}
        self.dm_map = {}
        self.dm_exec = ThreadPoolExecutor(max_workers=100)
        self.access_key = ''
        self.load_configure()
        self.load_history_data()

    def load_configure(self):
        ''' load assign configure '''
        cfg = ConfigParser()
        cfg.read(assign_path, 'utf-8')
        self.assign_up_name = cfg.get('basic', 'up_name')
        mid = cfg['basic']['up_mid'] 
        self.assign_up_mid = int(mid) if len(mid) else -1
        self.assign_rank_id = cfg.getint('basic', 'rank_id')
        self.assign_tid = cfg.getint('basic', 'tid')
        self.basic_av_id = cfg.getint('basic', 'basic_av_id')
        self.view_abnormal = cfg.getint('basic', 'view_abnormal')
        assign_id = cfg.get('assign', 'av_ids').split(',')
        self.assign_ids = [int(ii) for ii in assign_id]
        rank_map = {ii: [] for ii in self.assign_ids if ii not in self.del_map}
        self.rank_map = {**rank_map, **self.rank_map}
        self.keyword = cfg.get('comment', 'keyword')
        self.ignore_rpid = json.loads(cfg.get('comment', 'ignore_rpid'))
        self.ignore_list = cfg.get('comment', 'ignore_list')
        self.ignore_start = cfg.getfloat('comment', 'ignore_start')
        self.ignore_end = cfg.getfloat('comment', 'ignore_end')
        self.email_limit = cfg.getint('comment', 'email_limit')
        self.AV_URL = self.BASIC_AV_URL % self.basic_av_id
        self.RANKING_URL = self.BASIC_RANKING_URL % self.assign_rank_id + '%d/%d'
        self.history_check_list = [int(ii) for ii in cfg.get('basic', 'history_check_list').split(',')]
        self.special_info_email = cfg.get('basic', 'special_info_email').split(',')
        self.username = urllib.parse.quote_plus(cfg.get('login', 'username'))
        self.password = cfg.get('login', 'password')
        
    def load_av_lists(self):
        url = self.MEMBER_SUBMIT_URL % self.assign_up_mid
        av_list = basic_req(url, 1)
        if av_list is None or list(av_list.keys()) != ['status', 'data']:
            if can_retry(url):
                self.load_av_lists()
            return
        av_id_map = {ii['aid']: ii for ii in av_list['data']['vlist']}
        if self.basic_av_id not in av_id_map:
            if can_retry(url):
                self.load_av_lists()
            return
        self.av_id_map = av_id_map

    def load_history_file(self, av_id: int, av_info: dict):
        data_path = '{}{}_new.csv'.format(history_data_dir, av_id)
        history_list = read_file(data_path)[:3660]
        if not len(history_list):
            return
        created, title = av_info['created'], av_info['title']
        history_list = [ii.split(',') for ii in history_list]
        time_map = {round((time_stamp(ii[0]) - created) / 120) * 2: ii for ii in history_list if ii[0] != ''}
        last_data = [0] * 8
        for ii in self.history_map.keys():
            if ii in time_map:
                self.history_map[ii][av_id] = time_map[ii]
                last_data = time_map[ii] + last_data[len(time_map[ii]):]
            else:
                self.history_map[ii][av_id] = last_data

    def load_history_data(self):
        self.load_av_lists()
        self.public = {**{ii: [jj['created'], jj['mid']]  for ii, jj in self.av_id_map.items()}, **self.public}
        self.history_map = {ii * 2: {} for ii in range(0, 3660)}
        for av_id, av_info in self.av_id_map.items():
            self.load_history_file(av_id, av_info)

    def delay_load_history_data(self):
        time.sleep(60)
        self.load_history_data()

    def check_rank(self, av_id: int):
        rank_list = self.rank_map[av_id] if av_id in self.rank_map else []
        stat = self.get_stat_info(av_id)
        if stat is None:
            return
        need = ['view', 'like', 'coin', 'favorite', 'reply', 'share', 'danmaku']
        data = [stat[index] for index in need]
        if not self.check_view(av_id, data[0]):
            if can_retry(av_id):
                self.check_rank(av_id)
            return
        data = [time_str(), *data]
        if len(rank_list):
            data = [*data, *rank_list[:2], *rank_list[-2:]]

        with codecs.open('{}{}.csv'.format(history_dir, av_id), 'a', encoding='utf-8') as f:
            f.write(','.join([str(index) for index in data]) + '\n')

        if av_id in self.last_check and int(time.time()) - self.last_check[av_id] > one_day:
            self.del_map[av_id] = 1
            del self.rank_map[av_id]
            if av_id == self.basic_av_id:
                clean_csv(av_id)
        elif av_id not in self.last_check and int(time.time()) > one_day + self.begin_timestamp:
            self.del_map[av_id] = 1
            del self.rank_map[av_id]
            if av_id == self.basic_av_id:
                clean_csv(av_id)
        self.last_view[av_id] = data[1]
        now_time = time.time()
        if not av_id in self.public or av_id not in self.av_id_list:
            return
        time_gap = (now_time - self.public[av_id][0]) / 60
        echo('0|debug', av_id, time_gap < (4.5 * one_day / 60), self.public[av_id])
        if time_gap >= (4.5 * one_day / 60):
            return
        if not av_id in self.history_check_finish:
            self.history_check_finish[av_id] = []
        echo('3|info', 'Time Gap:', int(time_gap / 10))
        if int(time_gap / 10) in self.history_check_list and int(time_gap / 10) not in self.history_check_finish[av_id]:
            self.history_rank(time_gap, data, av_id)

    def history_rank(self, time_gap: int, now_info: list, av_id: int):
        echo('0|info', 'send history rank')
        time_gap = int(time_gap / 10) * 10
        history_map = {ii: jj for ii, jj in self.history_map[time_gap].items() if jj[1]}
        if len(history_map) < 5:
            self.load_history_data()
        other_views = [int(ii[1]) for ii in history_map.values()]
        other_views_len = len(other_views)
        other_views.append(now_info[1])
        ov_sort_idx = np.argsort(-np.array(other_views))
        av_ids = list(history_map.keys())
        now_sorted = [jj for jj, ii in enumerate(ov_sort_idx) if ii == other_views_len][0] + 1
        other_result = [(jj + 1, av_ids[ii]) for jj, ii in enumerate(ov_sort_idx[:4]) if ii != other_views_len]
        time_tt = get_time_str(time_gap * 60)
        email_title = 'av{}发布{}, 本年度排名No.{}/{}, 播放量: {}, 点赞: {}, 硬币: {}, 收藏: {}, 弹幕: {}'.format(av_id, time_tt, now_sorted, len(other_views), now_info[1], now_info[2], now_info[3], now_info[4], now_info[7])
        email_title += self.get_history_rank(now_info)
        context = '{}\n\n'.format(email_title)
        for no, av in other_result[:3]:
            data_info = history_map[av]
            context += '{}, av{}, 本年度No.{}, 播放量: {}, 点赞: {}, 硬币: {}, 收藏: {}, 弹幕: {}{}, 发布时间: {}\n'.format(self.av_id_map[av]['title'].split('|', 1)[0], av, no, data_info[1], data_info[2], data_info[3], data_info[4], data_info[7], self.get_history_rank(data_info), time_str(self.av_id_map[av]['created']))
        send_email(context, email_title)
        self.history_check_finish[av_id].append(round(time_gap / 10))

    def get_history_rank(self, data_info: list) -> str:
        if len(data_info) <= 8:
            return ''
        return ', Rank: {}, Score: {}'.format(data_info[8], data_info[9])

    def check_view(self, av_id: int, view: int) -> bool:
        ''' check view '''
        if not av_id in self.last_view:
            return True
        last_view = self.last_view[av_id]
        if last_view > view:
            return False
        if last_view + self.view_abnormal < view:
            return False
        return True

    def check_rank_list(self, av_id: int, rank_list: list) -> bool:
        ''' check rank list '''
        if not len(rank_list) or rank_list[2] != self.assign_up_name:
            return False
        av_id_id = int(av_id) * 10 + int(rank_list[-1])
        if av_id_id not in self.rank:
            return True
        first_rank = rank_list[0] // 10
        if first_rank not in self.rank[av_id_id] or first_rank == 0 or (first_rank == 1 and not rank_list[0] % 3):
            if self.last_rank[av_id_id] != rank_list[0]:
                return True
        return False

    def check_rank_v2(self, av_id: int):
        rank_list = self.rank_map[av_id] if av_id in self.rank_map else []
        stat = self.get_star_info(av_id)
        if stat is None:
            return
        need = ['view', 'like', 'coin', 'favorite', 'reply', 'share', 'danmaku']
        data = [stat[index] for index in need]
        data = [time_str(), *data]
        if len(rank_list):
            data = [*data, *rank_list[:2], *rank_list[-2:]]
        self.data_v2[av_id] = data

    def check_type(self, av_id: int):
        ''' check type '''
        if av_id in self.rank_type:
            return self.rank_type[av_id]
        if av_id in self.rank_map and not len(self.rank_map[av_id]):
            self.rank_type[av_id] = True
            return True
        return 2

    def check_type_req(self, av_id: int):
        view_data = self.get_view_detail(av_id)
        if view_data is None:
            return
        self.rank_type[av_id] = view_data['tid'] == self.assign_tid

    def add_av(self, av_id: int, rank: int, score: int) -> bool:
        ''' decide add av '''
        if av_id not in self.rank_map:
            return rank < 95 or score > 5000
        else:
            if not len(self.rank_map[av_id]):
                return True
            else:
                if self.rank_map[av_id][0] - rank > 5:
                    return True
                return score - self.rank_map[av_id][1] > 200

    def public_monitor(self, av_id: int):
        ''' a monitor '''
        self.public_list.append(av_id)
        data_time, mid = self.public[av_id]
        self.get_star_num(mid)
        self.check_rank_v2(av_id)
        time.sleep(5)
        follower = self.star[mid] if mid in self.star else 0
        origin_data = self.data_v2[av_id] if av_id in self.data_v2 else []
        sleep_time = data_time + one_day - int(time.time())
        if sleep_time < 0:
            return
        echo('4|debug', 'Monitor Begin %d' % (av_id))
        time.sleep(sleep_time)
        self.get_star_num(mid)
        self.check_rank_v2(av_id)

        time.sleep(5)
        follower_2 = self.star[mid] if mid in self.star else 0
        one_day_data = self.data_v2[av_id] if av_id in self.data_v2 else []

        data = [time_str(data_time), av_id, follower,
                follower_2, *origin_data, *one_day_data]
        with codecs.open(data_dir + 'public.csv', 'a', encoding='utf-8') as f:
            f.write(','.join([str(ii) for ii in data]) + '\n')

    def public_data(self, av_id: int):
        ''' get public basic data '''
        view_data = self.get_view_detail(av_id)
        if view_data is None:
            return
        data_time = view_data['pubdate']
        mid = view_data['owner']['mid']
        self.get_star_num(mid)
        self.public[av_id] = [data_time, mid]

    def get_star_num(self, mid: int, load_disk: bool = False):
        ''' get star num'''
        url = self.RELATION_STAT_URL % mid
        star = proxy_req(url, 2, header=self.get_api_headers(self.basic_av_id))
        if star is None or star.status_code != 200 or len(star.text) < 8 or not '{' in star.text:
            if can_retry(url):
                self.get_star_num(mid, load_disk)
            return
        try:
            star = star.text
            star_begin = star.find('{')
            star_json = star[star_begin:-1]
            star_json = json.loads(star_json)
            self.star[mid] = star_json['data']['follower']
            if not load_disk or not self.check_star(mid, self.star[mid]):
                return
            self.last_star[mid] = self.star[mid]
            with open('{}star.csv'.format(data_dir), 'a') as f:
                f.write('{},{}\n'.format(time_str(), self.star[mid]))
        except:
            pass

    def check_rank_rose(self, av_id: int, rank_list: list):
        ''' check rank rose '''
        if not self.check_rank_list(av_id, rank_list):
            return
        rank, score = rank_list[:2]
        av_id_id = int(av_id) * 10 + int(rank_list[-1])
        if av_id_id not in self.rank:
            self.rank[av_id_id] = [rank_list[0] // 10]
        else:
            self.rank[av_id_id].append(rank_list[0] // 10)
        self.last_rank[av_id_id] = rank_list[0]
        rank_str = 'Av: {} {} day List || Rank: {} Score: {}'.format(av_id, rank_list[-1], rank, score)
        if av_id in self.public:
            time_gap = (time.time() - self.public[av_id][0])
            rank_str += ', Public: {}'.format(get_time_str(time_gap))
            rank_context ='{}, Public Time: {}'.format(rank_str, time_str(self.public[av_id][0]))
        else:
            rank_context = rank_str
        send_email(rank_context, rank_str)

    def check_star(self, mid: int, star: int) -> bool:
        ''' check star '''
        if not mid in self.last_star:
            return True
        last_star = self.last_star[mid]
        if last_star > star:
            return False
        if last_star + self.view_abnormal < star:
            return False
        return True

    def load_rank_index(self, index: int, day_index: int):
        ''' load rank '''
        self.have_assign_now[day_index] = []
        url = self.RANKING_URL % (index, day_index)
        text = proxy_req(url, 3, header=self.get_api_headers(self.basic_av_id))
        rank_str = regex.findall('window.__INITIAL_STATE__=(.*?);', text)
        if not len(rank_str):
            if can_retry(url):
                self.load_rank_index(index, day_index)
            return
        rank_map = json.loads(rank_str[0])
        rank_list = rank_map['rankList']

        now_av_id = []
        wait_check_public = []
        rank_map = {}

        for ii, rank in enumerate(rank_list):
            av_id = int(rank['aid'])
            need_params = ['pts','author','mid','play','video_review', 'coins', 'duration', 'title']
            temp_rank_list = [ii, *[rank[ii] for ii in need_params], index, day_index]
            now_av_id.append(av_id)
            if not self.check_type(av_id):
                continue
            if day_index < 5:
                self.check_rank_rose(av_id, temp_rank_list)
            if self.add_av(av_id, ii, temp_rank_list[1]):
                rank_map[av_id] = temp_rank_list

        ''' check assign av rank '''
        for ii in self.assign_ids:
            if not ii in self.public:
                wait_check_public.append(ii)
            if not ii in self.last_view and not ii in self.rank_map:
                self.rank_map[ii] = []
        have_assign = [ii for ii in self.assign_ids if ii in now_av_id]

        ''' check tid type '''
        threading_public = []
        for ii in rank_map.keys():
            work = threading.Thread(target=self.check_type_req, args=(ii,))
            threading_public.append(work)
        for work in threading_public:
            work.start()
        for work in threading_public:
            work.join()

        for ii, jj in rank_map.items():
            if self.check_type(ii) != True:
                continue
            if not ii in self.public:
                wait_check_public.append(ii)
            self.last_check[ii] = int(time.time())
            self.rank_map[ii] = jj

        ''' load public basic data '''
        threading_public = []
        for ii in wait_check_public:
            work = threading.Thread(target=self.public_data, args=(ii,))
            threading_public.append(work)
        for work in threading_public:
            work.start()
        for work in threading_public:
            work.join()

        ''' begin monitor '''
        threading_list = []
        for ii, jj in self.public.items():
            if not ii in self.public_list and jj[0] + one_day > int(time.time()):
                work = threading.Thread(target=self.public_monitor, args=(ii,))
                threading_list.append(work)
        for work in threading_list:
            work.start()
        self.have_assign_now[day_index] = have_assign

    def load_rank(self):
        ''' load rank '''
        self.load_rank_index(1, 1)
        self.load_rank_index(1, 3)
        assign_1, assign_2 = self.have_assign_now[1], self.have_assign_now[3]
        have_assign = assign_1 + assign_2
        echo('4|debug', assign_1, assign_2, have_assign)
        not_rank_list = [ii for ii in self.have_assign if not ii in have_assign]

        if len(not_rank_list):
            for not_rank_av_id in not_rank_list:
                no_rank_warning = 'Time: {}, Av: {}, {}'.format(time_str(), not_rank_av_id, self.NO_RANK_CONSTANT)
                send_email(no_rank_warning, no_rank_warning, self.special_info_email)
                time.sleep(pow(np.pi, 2))
                send_email(no_rank_warning, no_rank_warning, self.special_info_email)
                echo('4|error', no_rank_warning)
        self.have_assign = have_assign

        echo('4|debug', 'Rank_map_len:', len(self.rank_map.keys()), 'Empty:',
              len([1 for ii in self.rank_map.values() if not len(ii)]))
        youshan = [','.join([str(kk) for kk in [ii, *jj]])
                   for ii, jj in self.rank_map.items()]
        with codecs.open(data_dir + 'youshang', 'w', encoding='utf-8') as f:
            f.write('\n'.join(youshan))

    def load_click(self, num=1000000):
        ''' schedule click '''
        self.rank_map = {ii: [] for ii in self.assign_ids}

        for index in range(num):
            threading_list = []
            if not index % 5:
                threading_list.append(threading.Thread(target=self.load_rank, args=()))
            if index % 7 == 3:
                threading_list.append(threading.Thread(target=self.delay_load_history_data, args=()))
            if index % 15 == 2:
                threading_list.append(threading.Thread(target=self.get_star_num, args=(self.assign_up_mid, True)))
                threading_list.append(threading.Thread(target=self.update_proxy, args=()))
            threading_list.append(threading.Thread(target=self.load_configure, args=()))
            threading_list.append(threading.Thread(target=self.get_check, args=()))
            for av_id in self.rank_map:
                if av_id in self.av_id_list or av_id in self.assign_ids:
                    threading_list.append(threading.Thread(target=self.check_rank, args=(av_id,)))
                elif index % 5 == 2:
                    threading_list.append(threading.Thread(target=self.check_rank, args=(av_id,)))
            for work in threading_list:
                work.start()
            time.sleep(120)

    def update_proxy(self):
        global proxy_req
        proxy_req = GetFreeProxy().proxy_req

    def update_ini(self, av_id: int):
        cfg = ConfigParser()
        cfg.read(assign_path, 'utf-8')
        cfg.set('basic', 'basic_av_id', str(av_id))
        history_av_ids = cfg.get('assign', 'av_ids')
        cfg.set('assign', 'av_ids', '{},{}'.format(history_av_ids, av_id))
        cfg.write(open(assign_path, 'w'))

    def get_check(self):
        ''' check comment '''
        self.load_av_lists()
        av_id_list = [[ii['aid'], ii['comment']] for ii in self.av_id_map.values() if not regex.findall(self.ignore_list, str(ii['aid']))]
        av_map = {ii['aid']: ii for ii in self.av_id_map.values()}
        self.comment_next = {ii: True for (ii, _) in av_id_list}
        if self.av_id_list and len(self.av_id_list) and len(self.av_id_list) != len(av_id_list):
            new_av_id = [ii for (ii, _) in av_id_list if not ii in self.av_id_list and not ii in self.del_map]
            self.rank_map = {**self.rank_map, **{ii:[] for ii in new_av_id}}
            echo('1|error','New Av id:', new_av_id)
            for ii in new_av_id:
                shell_str = 'nohup python3 bilibili/bsocket.py {} %d >> log.txt 2>&1 &'.format(ii)
                echo('0|error', 'Shell str:', shell_str)
                os.system(shell_str % 1)
                os.system(shell_str % 2)
                email_str = '{} av:{} was releasing at {}!!! Please check the auto pipeline.'.format(av_map[ii]['title'], ii, time_str(av_map[ii]['created']))
                email_str2 = '{} {} is release at {}.\nPlease check the online & common program.'.format(av_map[ii]['title'], time_str(av_map[ii]['created']), self.BASIC_AV_URL % ii)
                send_email(email_str2, email_str, self.special_info_email)
                self.update_ini(ii)
                self.public[ii] = [av_map[ii]['created'], av_map[ii]['mid']]
                self.last_check[ii] = int(time.time())

        self.av_id_list = [ii for (ii,_) in av_id_list]
        now_hour = int(time_str(time_format='%H'))
        now_min = int(time_str(time_format='%M'))
        now_time = now_hour + now_min / 60
        if now_time > self.ignore_start and now_time < self.ignore_end:
            return
        if os.path.exists('{}comment.pkl'.format(comment_dir)):
            with codecs.open('{}comment.pkl'.format(comment_dir), 'rb') as f:
                self.comment = pickle.load(f)
        if self.assign_up_mid == -1:
            return

        threading_list = []
        for (ii, jj) in av_id_list:
            if ii not in self.comment:
                self.comment[ii] = {}
            work = threading.Thread(
                target=self.comment_check_schedule, args=(ii, jj,))
            threading_list.append(work)
        for work in threading_list:
            work.start()
        for work in threading_list:
            work.join()
        with codecs.open('{}comment.pkl'.format(comment_dir), 'wb') as f:
            pickle.dump(self.comment, f)
        return av_id_list

    def comment_check_schedule(self, av_id: int, comment: int):
        ''' schedule comment check thread '''

        for pn in range(1, (comment - 1) // 20 + 2):
            if not self.comment_next[av_id]:
                return
            echo('2|debug', 'Comment check, av_id:', av_id, 'pn:', pn)
            self.check_comment_once(av_id, pn)
        comment = [self.comment[av_id][k] for k in sorted(self.comment[av_id].keys())]
        basic = [','.join([str(jj) for jj in ii['basic']])
                 for ii in comment if 'basic' in ii]
        replies = []
        for ii in comment:
            if not 'replies' in ii:
                continue
            parent_rpid = ii['basic'][0]
            replies_t = ii['replies']
            for jj in replies_t:
                jj[0] = '%s-%s' % (str(parent_rpid), str(jj[0]))
                replies.append(','.join([str(kk) for kk in jj]))
        with codecs.open('%s%d_comment.csv' % (comment_dir, av_id), 'w', encoding='utf-8') as f:
            f.write('\n'.join(basic) + '\n')
            f.write('\n'.join(replies) + '\n')

    def check_comment_once(self, av_id: int, pn: int):
        ''' check comment once '''
        comment = self.get_comment_info(av_id, pn)
        if comment is None:
            return
        hots = comment['hots']
        replies = comment['replies']
        if pn > 1:
            wait_check = replies
        else:
            wait_check = replies if hots is None else [*hots, *replies]
        wait_check = [{**jj, 'idx': ii + 1} for ii, jj in enumerate(wait_check)]

        for ii in wait_check:
            info = {'basic': self.get_comment_detail(ii, av_id, pn)}
            rpid = info['basic'][0]
            crep = ii['replies']
            idx = ii['idx']

            if not crep is None:
                info['replies'] = [self.get_comment_detail({**ii, 'idx': idx}, av_id, pn, rpid) for ii in crep]
            self.comment[av_id][rpid] = info
        wait_check = [ii for ii in wait_check if not ii['rpid'] in self.comment[av_id]]
        self.comment_next[av_id] = len(wait_check) >= 20
        echo('1|debug', int(self.comment_next[av_id]), 'av_id:', av_id,'len of wait_check:', len(wait_check))


    def get_comment_detail(self, comment: dict, av_id: int, pn: int, parent_rpid=None) -> List:
        ''' get comment detail '''
        ctime = time_str(comment['ctime'])
        wait_list = ['rpid', 'member', 'content', 'like', 'idx']
        wait_list_mem = ['uname', 'sex', 'sign', 'level_info']
        wait_list_content = ['message', 'plat']
        rpid, member, content, like, idx = [comment[ii] for ii in wait_list]
        uname, sex, sign, level = [member[ii] for ii in wait_list_mem]
        current_level = level['current_level']
        content, plat = [content[ii] for ii in wait_list_content]
        req_list = [rpid, ctime, like, plat, current_level, uname, sex, content, sign, idx]
        self.have_bad_comment(req_list, av_id, pn, parent_rpid)
        req_list[-2] = req_list[-2].replace(',', ' ').replace('\n', ' ')
        req_list[-3] = req_list[-3].replace(',', ' ').replace('\n', ' ')
        return req_list

    def have_bad_comment(self, req_list: list, av_id: int, pn: int, parent_rpid=None):
        ''' check comment and send warning email if error '''
        rpid, ctime, like, _, _, uname, sex, content, sign, idx = req_list

        if not len(regex.findall(self.keyword, content)):
            return True
        rpid = '{}{}'.format(rpid, '' if not parent_rpid else '-{}'.format(rpid))

        url = self.BASIC_AV_URL % av_id
        rpid_str = '{}-{}'.format(av_id, rpid)
        if rpid in [kk for ii in self.ignore_rpid.values() for kk in ii]:
            return True
        if self.email_limit < 1 or (rpid_str in self.email_send_time and self.email_send_time[rpid_str] >= self.email_limit):
            return True

        email_content = '{}\nUrl: {} Page: {} #{}@{},\nUser: {},\nSex: {},\nconetnt: {},\nsign: {}\nlike: {}'.format(ctime, url, pn, idx, rpid, uname, sex, content, sign, like)
        email_subject = '({})av_id: {} || #{} Comment Warning !!!'.format(ctime, av_id, rpid)
        echo('4|warning', email_content, email_subject)
        send_email_time = 0
        send_email_result = False
        while not send_email_result and send_email_time < 4:
            send_email_result = send_email(email_content, email_subject)
            send_email_time += 1
        if rpid_str in self.email_send_time:
            self.email_send_time[rpid_str] += 1
        else:
            self.email_send_time[rpid_str] = 1

    def get_cid(self, av_id: int):
        playlist_url = self.PLAYLIST_URL % av_id
        return self.get_api_req(playlist_url, av_id)

    def get_danmaku_once(self, oid: int):
        dm_url = self.DM_URL % oid
        req = proxy_req(dm_url, 2)
        if req is None:
            if can_retry(dm_url):
                return self.get_danmaku_once(oid)
            else:
                return
        req.encoding = 'utf-8'
        dm = regex.findall('p="(.*?)">(.*?)</d>', req.text)
        echo(3, 'oid {} have {} dm'.format(oid, len(dm)))
        return dm, oid

    def get_view_detail(self, av_id: int, cid: int = -1):
        view_url = self.VIEW_URL % av_id
        if cid >= 0:
            view_url += '&cid={}'.format(cid)
        return self.get_api_req(view_url, av_id)

    def get_stat_info(self, av_id: int):
        stat_url = self.ARCHIVE_STAT_URL % av_id
        return self.get_api_req(stat_url, av_id)

    def get_comment_info(self, av_id: int, pn: int):
        comment_url = self.REPLY_V2_URL % (pn, av_id)
        return self.get_api_req(comment_url, av_id)

    def get_api_req(self, url: str, av_id:int):
        req = proxy_req(url, 1, header=self.get_api_headers(av_id))
        if req is None or list(req.keys()) != self.JSON_KEYS:
            if can_retry(url):
                return self.get_api_req(url, av_id)
            else:
                return
        return req['data']
    
    def get_api_headers(self, av_id: int) -> dict:
        return {
            'Accept': '*/*',
            'Referer': self.BASIC_AV_URL % av_id
        }

    def get_danmaku(self, av_id: int):
        mkdir(dm_dir)
        output_path = '{}{}_dm.csv'.format(dm_dir, av_id)

        view_data = self.get_view_detail(av_id)
        if view_data is None:
            return

        cid_list = [ii['cid'] for ii in view_data['pages']]
        dm_map = self.dm_map[av_id] if av_id in self.dm_map else {}
        cid_list = [ii for ii in cid_list if ii not in dm_map or len(dm_map[ii]) == 0]
        dm_thread = [self.dm_exec.submit(self.get_danmaku_once, ii) for ii in cid_list]
        need_dm = view_data['stat']['danmaku']
        need_p = len(view_data['pages'])
        echo(2, 'Begin {} p thread, need {} dm'.format(need_p, need_dm))

        dm_list = list(as_completed(dm_thread))
        dm_list = [ii.result() for ii in as_completed(dm_thread)]
        dm_list = [ii for ii in dm_list if ii is not None]
        dm_map = {**dm_map, **{jj: ii for ii, jj in dm_list}}
        dm_num = sum([len(ii) for ii in dm_map.values()])
        p_num = len(dm_map)
        self.dm_map[av_id] = dm_map

        title = '{} {} Total {} p {} dm, Actual {} p {} dm'.format(view_data['title'], self.BASIC_AV_URL % av_id, need_p, need_dm, p_num, dm_num)
        result = [title, '']
        for cid in view_data['pages']:
            if cid['cid'] not in dm_map:
                continue
            dm = dm_map[cid['cid']]
            dm = [[float(ii.split(',')[0]), time_str(time_stamp=int(ii.split(',')[4])), jj] for ii, jj in dm]
            dm = sorted(dm, key=lambda i: i[0])
            dm = [','.join([get_min_s(str(ii)), jj, kk]) for ii, jj, kk in dm]
            p_title = 'p{} {} Total {} dm'.format(cid['page'], cid['part'], len(dm))
            result.extend([p_title, *dm, ''])
        
        with open(output_path, 'w') as f:
            f.write('\n'.join(result))
        print_str = 'Load {} p {} dm to {}, except {} p {} m'.format(output_path, len(dm_list), dm_num, need_p, need_dm)
        if need_dm == dm_num:
            echo(1, print_str, 'success')
        else:
            echo(0, print_str, 'error')

    def get_access_key(self):
        captcha, cookie = self.get_captcha()
        hash_salt, key, cookie = self.get_hash_salt(cookie)


    def get_hash_salt(self, cookie: dict = {}):
        url = self.GET_KEY_URL % np.random.random()
        headers = {
            'Accept': '*/*',
            'Referer': self.LOGIN_URL,
            'X-Requested-With': 'XMLHttpRequest'
        }
        if len(cookie):
            headers['Cookie'] = encoder_cookie(cookie)
        hash_salt, cookies = proxy_req(url, 1, header=headers, need_cookie=True)
        if hash_salt is None or list(hash_salt.keys()) != ['hash', 'key']:
            if can_retry(url):
                return self.get_hash_salt()
            else:
                return
        return hash_salt['hash'], hash_salt['key'], cookies

    def get_captcha(self, cookie: dict = {}):
        url = self.CAPTCHA_URL
        headers = {
            'Accept': 'application/json, text/plain, */*',
            'Referer': self.LOGIN_URL,
        }
        if len(cookie):
            headers['Cookie'] = encoder_cookie(cookie)
        captcha, cookies = proxy_req(url, 1, header=headers, need_cookie=True)
        if captcha is None or list(captcha.keys()) != ['data', 'code']:
            if can_retry(url):
                return self.get_captcha()
            else:
                return
        return captcha['data']['result'], cookies
        

    def get_access_key_req(self, hash_salt: str, key: str, challenge: str, validate: str, cookie: dict = {}):
        data = {
            'captchaType': 11,
            'username': self.username,
            'password': self.encoder_login_info(hash_salt, key),
            'keep': True,
            'key': key,
            'goUrl': self.AV_URL,
            'challenge': challenge,
            'validate': validate,
            'seccode': f'{validate}|jordan'
        }
        headers = {
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Referer': self.LOGIN_URL
        }
        if len(cookie):
            headers['Cookie'] = encoder_cookie(cookie)
        login = proxy_req(self.LOGIN_V2_URL, 12, header=headers)

    def encode_login_info(self, hash_salt: str, key: str):
        public_key = rsa.PublicKey.load_pkcs1_openssl_pem(key.encode())
        concate = rsa.encrypt(hash_salt + self.password).encode('utf-8')
        s = base64.b64encode(concate, public_key)
        s = urllib.parse.quote_plus(s)
        return s


def clean_csv(av_id: int):
    ''' clean csv '''
    csv_path = os.path.join(history_dir, '{}.csv'.format(av_id))
    output_path = os.path.join(history_data_dir, '{}_new.csv'.format(av_id))
    csv = read_file(csv_path)
    last_time, last_view = csv[0].split(',')[:2]
    result = [csv[0]]
    last_time = time_stamp(last_time)
    last_view = int(last_view)
    empty_line = ','.join([' '] * (len(csv[0].split(',')) + 1))
    for line in csv[1:]:
        now_time, now_view = line.split(',')[:2]
        now_time = time_stamp(now_time)
        now_view = int(now_view)
        time_gap = now_time - last_time

        if now_view < last_view or now_view - last_view > 5000:
            continue
        if abs(time_gap) > 150:
            for ii in range(int((time_gap - 30) // 120)):
                result.append(empty_line)
        if abs(time_gap) > 90:
            result.append(line)
            last_view, last_time = now_view, now_time
    with open(output_path, 'w') as f:
        f.write('\n'.join(result))


if __name__ == '__main__':
    mkdir(data_dir)
    mkdir(comment_dir)
    mkdir(history_dir)
    mkdir(history_data_dir)
    if not os.path.exists(assign_path):
        shutil.copy(assign_path + '.tmp', assign_path)
    bb = Up()
    bb.load_click()
