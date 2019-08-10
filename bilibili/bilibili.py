# -*- coding: utf-8 -*-
# @Author: gunjianpan
# @Date:   2019-04-07 20:25:45
# @Last Modified by:   gunjianpan
# @Last Modified time: 2019-08-10 17:09:17


import codecs
import json
import os
import pickle
import random
import re
import shutil
import sys
import threading
import time
from configparser import ConfigParser
from typing import List

import numpy as np

sys.path.append(os.getcwd())
from proxy.getproxy import GetFreeProxy
from util.util import (basic_req, begin_time, can_retry, changeHeaders, echo,
                       end_time, headers, mkdir, read_file, send_email,
                       time_stamp, time_str)

proxy_req = GetFreeProxy().proxy_req
one_day = 86400
data_dir = 'bilibili/data/'
history_data_dir = '{}history_data/'.format(data_dir)
history_dir = '{}history/'.format(data_dir)
comment_dir = '{}comment/'.format(data_dir)
assign_path = 'bilibili/assign_up.ini'

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
    CLICK_NOW_URL = 'http://api.bilibili.com/x/report/click/now?jsonp=jsonp'
    CLICK_WEB_URL = 'http://api.bilibili.com/x/report/click/web/h5'
    REPORT_HEARTBEAT_URL = 'http://api.bilibili.com/x/report/web/heartbeat'
    ARCHIVE_STAT_URL = 'http://api.bilibili.com/x/web-interface/archive/stat?aid=%d'
    VIEW_URL = 'http://api.bilibili.com/x/web-interface/view?aid=%d'
    RELATION_STAT_URL = 'http://api.bilibili.com/x/relation/stat?jsonp=jsonp&callback=__jp11&vmid=%d'
    BASIC_RANKING_URL = 'https://www.bilibili.com/ranking/all/%d/'
    MEMBER_SUBMIT_URL = 'http://space.bilibili.com/ajax/member/getSubmitVideos?mid=%s&page=1&pagesize=50'
    REPLY_V2_URL = 'http://api.bilibili.com/x/v2/reply?jsonp=jsonp&pn=%d&type=1&oid=%d&sort=2'

    def __init__(self):
        self.finish = 0
        self.rank = {}
        self.rank_type = {}
        self.public = {}
        self.public_list = []
        self.star = {}
        self.data_v2 = {}
        self.have_assign = False
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
        self.load_configure()
        self.load_history_data()

    def load_configure(self):
        ''' load assign configure '''
        cfg = ConfigParser()
        cfg.read(assign_path, 'utf-8')
        self.assign_up_name = cfg.get('basic', 'up_name')
        self.assign_up_mid = cfg.getint('basic', 'up_mid') if len(
            cfg['basic']['up_mid']) else -1
        self.assign_rank_id = cfg.getint('basic', 'rank_id')
        self.assign_tid = cfg.getint('basic', 'tid')
        self.basic_av_id = cfg.getint('basic', 'basic_av_id')
        self.view_abnormal = cfg.getint('basic', 'view_abnormal')
        self.assign_ids = [int(ii)
                           for ii in cfg.get('assign', 'av_ids').split(',')]
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

    def load_av_lists(self):
        url = self.MEMBER_SUBMIT_URL % self.assign_up_mid
        json_req = basic_req(url, 1)
        if json_req is None or not 'data' in json_req or not 'vlist' in json_req['data']:
            if can_retry(url):
                self.load_av_lists()
            return
        av_id_map = {ii['aid']: ii for ii in json_req['data']['vlist']}
        if self.basic_av_id not in av_id_map:
            if can_retry(url):
                self.load_av_lists()
            return
        self.av_id_map = av_id_map

    def load_history_file(self, av_id: int, av_info: dict):
        data_path = '{}{}_new.csv'.format(history_data_dir, av_id)
        history_list = read_file(data_path)[:2880]
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
        self.history_map = {ii * 2: {} for ii in range(0, 2880)}
        self.history_check_finish = []
        for av_id, av_info in self.av_id_map.items():
            self.load_history_file(av_id, av_info)

    def basic_view(self, url: str, times: int, types: int):
        ''' press have no data input '''
        url = self.AV_URL
        if types == 1:
            html = proxy_req(url, 0)
        else:
            html = basic_req(url, 0)

        if html == False and times < 5:
            self.basic_view(url, times + 1, types)

    def one_click_bilibili(self, url: str, times: int, types: int):
        ''' press have no data input '''
        url = self.AV_URL
        if types == 1:
            html = proxy_req(url, 0)
        else:
            html = basic_req(url, 0)

        if html == False:
            if times < 5:
                self.basic_view(url, times + 1, types)
            return
        times = 0
        url_1 = self.CLICK_NOW_URL
        if types == 1:
            json_1 = proxy_req(url_1, 1)
        else:
            json_1 = basic_req(url_1, 1)
        if not json_1 is None:
            print(json_1)

        if not self.have_error(json_1, 1):
            if times < 2:
                self.one_click_bilibili(url, times + 1, types)
            return
        times = 0
        url = self.CLICK_WEB_URL
        data = {
            'aid': self.basic_av_id,
            'cid': '',
            'part': '1',
            'mid': str(random.randint(10000000, 19999999)),
            'lv': '2',
            'ftime': '',
            'stime': json_1['data']['now'],
            'jsonp': 'jsonp',
            'type': '3',
            'sub_type': '0'
        }
        if types == 1:
            json_req = proxy_req(url, 11, data)
        else:
            json_req = basic_req(url, 11, data=data)
        if not json_req is None:
            print(json_req)

        if not self.have_error(json_req):
            if times < 2:
                self.one_click_bilibili(url, times + 1, types)
            return
        times = 0
        url_3 = self.REPORT_HEARTBEAT_URL
        data_3 = {
            'aid': self.basic_av_id,
            'cid': '',
            'mid': data['mid'],
            'csrf': '',
            'played_time': '0',
            'realtime': '0',
            'start_ts': json_1['data']['now'],
            'type': '3',
            'dt': '2',
            'play_type': '1'
        }

        if types == 1:
            json_3 = proxy_req(url_3, 11, data_3)
        else:
            json_3 = basic_req(url_3, 11, data=data_3)
        if not json_3 is None:
            print(json_3)

        if not self.have_error(json_3) and times < 2:
            self.one_click_bilibili(url, times + 1, types)
        print('finish.')
        self.finish += 1

    def check_rank(self, av_id: int, times=0):
        rank_list = self.rank_map[av_id] if av_id in self.rank_map else []
        changeHeaders({'Referer': self.BASIC_AV_URL % av_id})

        url = self.ARCHIVE_STAT_URL % av_id
        json_req = proxy_req(url, 1)

        if not self.have_error(json_req):
            if (av_id not in self.av_id_list and times < 3) or (av_id in self.av_id_list and times < 6):
                self.check_rank(av_id, times + 1)
            return
        json_req = json_req['data']
        need = ['view', 'like', 'coin', 'favorite',
                'reply', 'share', 'danmaku']
        data = [json_req[index] for index in need]
        if not self.check_view(av_id, data[0]):
            if times < 3:
                self.check_rank(av_id, times + 1)
            return
        if len(rank_list):
            data = [time_str(), *data, *rank_list[:2], *rank_list[-2:]]
        else:
            data = [time_str(), *data]

        with codecs.open('%s%d.csv' % (history_dir, av_id), 'a', encoding='utf-8') as f:
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
        echo(0, av_id, av_id == self.basic_av_id, av_id in self.public, (now_time - self.public[av_id][0]) < 3.1 * one_day * 60, self.public[av_id])
        if av_id == self.basic_av_id and av_id in self.public and (now_time - self.public[av_id][0]) < 3.1 * one_day * 60:
            time_gap = (now_time - self.public[av_id][0]) / 60
            echo(3, 'Time Gap:', round(time_gap / 10))
            if round(time_gap / 10) in self.history_check_list and round(time_gap / 10) not in self.history_check_finish:
                self.history_rank(time_gap, data, av_id)

    def history_rank(self, time_gap: int, now_info: list, av_id: int):
        echo(0, 'send history rank') 
        time_gap = round(time_gap / 10) * 10 
        history_map = {ii: jj for ii, jj in self.history_map[time_gap].items() if jj[1]}
        other_views = [int(ii[1]) for ii in history_map.values()]
        other_views_len = len(other_views)
        other_views.append(now_info[1])
        ov_sort_idx = np.argsort(-np.array(other_views))
        av_ids = list(history_map.keys())
        now_sorted = [jj for jj, ii in enumerate(ov_sort_idx) if ii == other_views_len][0] + 1
        other_result = [(jj + 1, av_ids[ii]) for jj, ii in enumerate(ov_sort_idx[:4]) if ii != other_views_len]
        time_tt = self.get_time_str(time_gap)
        email_title = 'av{}发布{}, 本年度排名No.{}/{}, 播放量: {}, 点赞: {}, 硬币: {}, 收藏: {}, 弹幕: {}'.format(av_id, time_tt, now_sorted, len(other_views), now_info[1], now_info[2], now_info[3], now_info[4], now_info[7])
        email_title += self.get_history_rank(now_info)
        context = '{}\n\n'.format(email_title)
        for no, av in other_result[:3]:
            data_info = history_map[av]
            context += '{}, av{}, 本年度No.{}, 播放量: {}, 点赞: {}, 硬币: {}, 收藏: {}, 弹幕: {}{}, 发布时间: {}\n'.format(self.av_id_map[av]['title'].split('|', 1)[0], av, no, data_info[1], data_info[2], data_info[3], data_info[4], data_info[7], self.get_history_rank(data_info), time_str(self.av_id_map[av]['created']))
        context += '\nBest wish for you\n--------\nSend from script by gunjianpan.'
        send_email(context, email_title)
        self.history_check_finish.append(round(time_gap / 10))

    def get_history_rank(self, data_info: list):
        if len(data_info) <= 8:
            return ''
        return ', Rank: {}, Score: {}'.format(data_info[8], data_info[9])

    def get_time_str(self, time_gap:int):
        if time_gap < 60:
            return '{}min'.format(time_gap)
        if time_gap < 1440:
            return '{}h'.format(round(time_gap / 60))
        return '{}天'.format(round(time_gap / 1440))

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
        if first_rank not in self.rank[av_id_id] or first_rank == 0 or first_rank == 1:
            if self.last_rank[av_id_id] != rank_list[0]:
                return True
        return False

    def check_rank_v2(self, av_id: int, times=0):
        rank_list = self.rank_map[av_id] if av_id in self.rank_map else []
        changeHeaders({'Referer': self.BASIC_AV_URL % av_id})

        url = self.ARCHIVE_STAT_URL % av_id
        json_req = proxy_req(url, 1)

        if not self.have_error(json_req):
            if times < 3:
                self.check_rank_v2(av_id, times + 1)
            return
        json_req = json_req['data']
        need = ['view', 'like', 'coin', 'favorite',
                'reply', 'share', 'danmaku']
        data = [json_req[index] for index in need]
        if len(rank_list):
            data = [time_str(), *data, *rank_list[:2], *rank_list[-2:]]
        else:
            data = [time_str(), *data]
        self.data_v2[av_id] = data

    def have_error(self, json_req: dict, types=None) -> bool:
        ''' check json_req'''
        if json_req is None:
            return False
        if 'code' not in json_req or json_req['code'] != 0:
            return False
        if 'message' not in json_req or json_req['message'] != '0':
            return False
        if 'ttl' not in json_req or json_req['ttl'] != 1:
            return False
        if not types is None:
            if 'data' not in json_req or 'now' not in json_req['data']:
                return False
        return True

    def check_type(self, av_id: int):
        ''' check type '''
        if av_id in self.rank_type:
            return self.rank_type[av_id]
        if av_id in self.rank_map and not len(self.rank_map[av_id]):
            self.rank_type[av_id] = True
            return True
        return 2

    def check_type_req(self, av_id: int):
        changeHeaders({'Referer': self.BASIC_AV_URL % av_id})
        url = self.VIEW_URL % av_id

        json_req = proxy_req(url, 1)

        if json_req is None or 'data' not in json_req or 'tid' not in json_req['data']:
            if can_retry(url):
                self.check_type_req(av_id)
            return
        self.rank_type[av_id] = json_req['data']['tid'] == self.assign_tid

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

    def public_monitor(self, av_id: int, times: int):
        ''' a monitor '''
        self.public_list.append(av_id)
        data_time, mid = self.public[av_id]
        self.get_star_num(mid, 0)
        self.check_rank_v2(av_id, 0)
        time.sleep(5)
        follower = self.star[mid] if mid in self.star else 0
        origin_data = self.data_v2[av_id] if av_id in self.data_v2 else []
        sleep_time = data_time + one_day - int(time.time())
        if sleep_time < 0:
            return
        print('Monitor Begin %d' % (av_id))
        time.sleep(sleep_time)
        self.get_star_num(mid, 0)
        self.check_rank_v2(av_id, 0)

        time.sleep(5)
        follower_2 = self.star[mid] if mid in self.star else 0
        one_day_data = self.data_v2[av_id] if av_id in self.data_v2 else []

        data = [time_str(data_time), av_id, follower,
                follower_2, *origin_data, *one_day_data]
        with codecs.open(data_dir + 'public.csv', 'a', encoding='utf-8') as f:
            f.write(','.join([str(ii) for ii in data]) + '\n')

    def public_data(self, av_id: int, times: int):
        ''' get public basic data '''
        changeHeaders({'Referer': self.BASIC_AV_URL % av_id})
        url = self.VIEW_URL % av_id
        json_req = proxy_req(url, 1)
        if json_req is None or not 'data' in json_req or not 'pubdate' in json_req['data']:
            if times < 3:
                self.public_data(av_id, times + 1)
            return
        data_time = json_req['data']['pubdate']
        mid = json_req['data']['owner']['mid']
        self.get_star_num(mid, 0)
        self.public[av_id] = [data_time, mid]

    def get_star_num(self, mid: int, times: int, load_disk=False):
        ''' get star num'''
        url = self.RELATION_STAT_URL % mid
        header = {**headers, **
                  {'Origin': self.BILIBILI_URL, 'Referer': self.AV_URL}}
        if 'Host' in header:
            del header['Host']
        req = proxy_req(url, 2, header=header)
        if req is None or req.status_code != 200 or len(req.text) < 8 or not '{' in req.text:
            if times < 3:
                self.get_star_num(mid, times + 1, load_disk)
            return
        try:
            json_req = json.loads(req.text[7:-1])
            self.star[mid] = json_req['data']['follower']
            if load_disk and self.check_star(mid, self.star[mid]):
                self.last_star[mid] = self.star[mid]
                with open('{}star.csv'.format(data_dir), 'a') as f:
                    f.write('%s,%d\n' % (time_str(), self.star[mid]))
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
        send_email('%d day List || Rank: %d Score: %d' % (int(
            rank_list[-1]), rank, score), '%d day List || Rank: %d Score: %d' % (int(rank_list[-1]), rank, score))

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
        changeHeaders({'Referer': self.AV_URL})
        url = self.RANKING_URL % (index, day_index)
        text = basic_req(url, 3)
        rank_str = re.findall('window.__INITIAL_STATE__=(.*?);', text)
        if not len(rank_str):
            if can_retry(url):
                self.load_rank_index(index, day_index)
            return False
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
            self.check_rank_rose(av_id, temp_rank_list)
            if self.add_av(av_id, ii, temp_rank_list[1]):
                rank_map[av_id] = temp_rank_list

        ''' check assign av rank '''
        for ii in self.assign_ids:
            if not ii in self.public:
                wait_check_public.append(ii)
            if not ii in self.last_view and not ii in self.rank_map:
                self.rank_map[ii] = []
        have_assign = len([0 for ii in self.assign_ids if ii in now_av_id]) > 0

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
            work = threading.Thread(target=self.public_data, args=(ii, 0,))
            threading_public.append(work)
        for work in threading_public:
            work.start()
        for work in threading_public:
            work.join()

        ''' begin monitor '''
        threading_list = []
        for ii, jj in self.public.items():
            if not ii in self.public_list and jj[0] + one_day > int(time.time()):
                work = threading.Thread(
                    target=self.public_monitor, args=(ii, 0,))
                threading_list.append(work)
        for work in threading_list:
            work.start()
        return have_assign

    def load_rank(self):
        ''' load rank '''
        assign_1 = self.load_rank_index(1, 1)
        assign_2 = self.load_rank_index(1, 3)
        have_assign = assign_1 or assign_2
        print(assign_1, assign_2, have_assign)

        if self.have_assign and not have_assign:
            send_email('No rank.....No Rank......No Rank.....',
                       'No rank.....No Rank......No Rank.....')
        self.have_assign = have_assign

        print('Rank_map_len:', len(self.rank_map.keys()), 'Empty:',
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
                threading_list.append(threading.Thread(target=self.load_history_data, args=()))         
            if not index % 15:
                threading_list.append(threading.Thread(target=self.get_star_num, args=(self.assign_up_mid, 0, True)))
                threading_list.append(threading.Thread(target=self.update_proxy, args=()))
            threading_list.append(threading.Thread(target=self.load_configure, args=()))
            threading_list.append(threading.Thread(target=self.get_check, args=()))
            for av_id in self.rank_map:
                if av_id in self.av_id_list or av_id in self.assign_ids:
                    threading_list.append(threading.Thread(target=self.check_rank, args=(av_id,)))
                elif index % 3 == 2:
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
        av_id_list = [[ii['aid'], ii['comment']] for ii in self.av_id_map.values() if not re.findall(self.ignore_list, str(ii['aid']))]
        av_map = {ii['aid']: ii for ii in self.av_id_map.values()}
        self.comment_next = {ii: True for (ii, _) in av_id_list}
        if self.av_id_list and len(self.av_id_list) and len(self.av_id_list) != len(av_id_list):
            new_av_id = [ii for (ii, _) in av_id_list if not ii in self.av_id_list and not ii in self.del_map]
            self.rank_map = {**self.rank_map, **{ii:[] for ii in new_av_id}}
            echo(1, new_av_id)
            for ii in new_av_id:
                shell_str = 'nohup ipython3 bilibili/bsocket.py {} %d >> log.txt 2>&1 &'.format(ii)
                echo(0, shell_str)
                os.system(shell_str % 1)
                os.system(shell_str % 2)
                email_str = '{} av:{} was releasing at {}!!! Please check the auto pipeline.'.format(av_map[ii]['title'], ii, time_str(av_map[ii]['created']))
                email_str2 = '{} {} is release at {}.\nPlease check the online & common program.\n\nBest wish for you\n--------\nSend from script by gunjianpan.'.format(av_map[ii]['title'], time_str(av_map[ii]['created']), self.BASIC_AV_URL % ii) 
                send_email(email_str2, email_str)
                self.update_ini(ii)
                self.public[ii] = [av_map[ii]['created'], av_map[ii]['mid']]

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
            echo(2, 'Comment check, av_id:', av_id, 'pn:', pn)
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
        url = self.REPLY_V2_URL % (pn, av_id)
        json_req = proxy_req(url, 1)
        if json_req is None or not 'data' in json_req or not 'hots' in json_req['data']:
            if can_retry(url):
                self.check_comment_once(av_id, pn)
            return

        hots = json_req['data']['hots']
        replies = json_req['data']['replies']
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
        echo(3, int(self.comment_next[av_id]), 'av_id:', av_id,'len of wait_check:', len(wait_check))


    def get_comment_detail(self, comment: dict, av_id: int, pn: int, parent_rpid=None) -> List:
        ''' get comment detail '''
        # print(comment)
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

        if not len(re.findall(self.keyword, content)):
            return True
        rpid = '{}{}'.format(rpid, '' if not parent_rpid else '-{}'.format(rpid))

        url = self.BASIC_AV_URL % av_id
        rpid_str = '{}-{}'.format(av_id, rpid)
        if str(av_id) in self.ignore_rpid and rpid in self.ignore_rpid[str(av_id)]:
            return True
        if self.email_limit < 1 or (rpid_str in self.email_send_time and self.email_send_time[rpid_str] > self.email_limit):
            return True 

        email_content = '%s\nUrl: %s Page: %d #%d@%s,\nUser: %s,\nSex: %s,\nconetnt: %s,\nsign: %s\nlike: %d' % (ctime, url, pn, idx, rpid, uname, sex, content, sign, like)
        email_subject = '(%s)av_id: %s || #%s Comment Warning !!!' % (ctime, av_id, rpid)
        print(email_content, email_subject)
        send_email_time = 0
        send_email_result = False
        while not send_email_result and send_email_time < 4:
            send_email_result = send_email(email_content, email_subject)
            send_email_time += 1
        if rpid_str in self.email_send_time:
            self.email_send_time[rpid_str] += 1
        else:
            self.email_send_time[rpid_str] = 0

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
            # echo(1, last_view, last_time, now_view, now_time)
            continue
        if abs(time_gap) > 150:
            for ii in range(int((time_gap - 30) // 120)):
                result.append(empty_line)
        if abs(time_gap) > 90:
            # echo(0, last_view, last_time, now_view, now_time)
            result.append(line)
            last_view, last_time = now_view, now_time
        # else:
        #     echo(2, last_view, last_time, now_view, now_time)
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
