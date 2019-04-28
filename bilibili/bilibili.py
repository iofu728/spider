'''
@Author: gunjianpan
@Date:   2019-04-07 20:25:45
@Last Modified by:   gunjianpan
@Last Modified time: 2019-04-24 01:36:04
'''

import codecs
import threading
import time
import os
import random
import re
import json
import pickle
import shutil

from configparser import ConfigParser
from proxy.getproxy import GetFreeProxy
from util.util import begin_time, end_time, changeHeaders, basic_req, can_retry, send_email, headers, time_str

get_request_proxy = GetFreeProxy().get_request_proxy
one_day = 86400
data_dir = 'bilibili/data/'
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
    REPLY_V2_URL = 'http://api.bilibili.com/x/v2/reply?jsonp=jsonp&pn=%d&type=1&oid=%d&sort=0'

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
        self.comment_max = {}
        self.email_send_time = {}
        self.begin_timestamp = int(time.time())
        self.load_configure()

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
        rank_map = {ii: [] for ii in self.assign_ids}
        self.rank_map = {**rank_map, **self.rank_map}
        self.keyword = cfg.get('comment', 'keyword')
        self.ignore_floor = json.loads(cfg.get('comment', 'ignore_floor'))
        self.ignore_list = cfg.get('comment', 'ignore_list')
        self.ignore_start = cfg.getfloat('comment', 'ignore_start')
        self.ignore_end = cfg.getfloat('comment', 'ignore_end')
        self.email_limit = cfg.getint('comment', 'email_limit')
        self.AV_URL = self.BASIC_AV_URL % self.basic_av_id
        self.RANKING_URL = self.BASIC_RANKING_URL % self.assign_rank_id + '%d/%d'

    def basic_view(self, url: str, times: int, types: int):
        ''' press have no data input '''
        url = self.AV_URL
        if types == 1:
            html = get_request_proxy(url, 0)
        else:
            html = basic_req(url, 0)

        if html == False and times < 5:
            self.basic_view(url, times + 1, types)

    def one_click_bilibili(self, url: str, times: int, types: int):
        ''' press have no data input '''
        url = self.AV_URL
        if types == 1:
            html = get_request_proxy(url, 0)
        else:
            html = basic_req(url, 0)

        if html == False:
            if times < 5:
                self.basic_view(url, times + 1, types)
            return
        times = 0
        url_1 = self.CLICK_NOW_URL
        if types == 1:
            json_1 = get_request_proxy(url_1, 1)
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
            json_req = get_request_proxy(url, 11, data)
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
            json_3 = get_request_proxy(url_3, 11, data_3)
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
        json_req = get_request_proxy(url, 1)

        if not self.have_error(json_req):
            if times < 3:
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
            del self.rank_map[av_id]
        elif av_id not in self.last_check and int(time.time()) > one_day + self.begin_timestamp:
            del self.rank_map[av_id]
        self.last_view[av_id] = data[1]

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
        json_req = get_request_proxy(url, 1)

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

        json_req = get_request_proxy(url, 1)

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
        json_req = get_request_proxy(url, 1)
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
        req = get_request_proxy(url, 2, header=header)
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

    def check_rank_rose(self, av_id, rank_list):
        ''' check rank rose '''
        if self.check_rank_list(av_id, rank_list):
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
                work = threading.Thread(target=self.load_rank, args=())
                threading_list.append(work)
                check = threading.Thread(target=self.get_check, args=())
                threading_list.append(check)
            if not index % 15:
                work = threading.Thread(
                    target=self.get_star_num, args=(self.assign_up_mid, 0, True))
                threading_list.append(work)
            for av_id in self.rank_map:
                work = threading.Thread(target=self.check_rank, args=(av_id,))
                threading_list.append(work)
            for work in threading_list:
                work.start()
            time.sleep(120)
            self.load_configure()

    def get_check(self):
        ''' check comment '''
        now_hour = int(time_str(format='%H'))
        now_min = int(time_str(format='%M'))
        now_time = now_hour + now_min / 60
        if now_time > self.ignore_start and now_time < self.ignore_end:
            return
        if os.path.exists('{}comment.pkl'.format(comment_dir)):
            with codecs.open('{}comment.pkl'.format(comment_dir), 'rb') as f:
                self.comment = pickle.load(f)
        if self.assign_up_mid == -1:
            return
        url = self.MEMBER_SUBMIT_URL % self.assign_up_mid
        json_req = get_request_proxy(url, 1)
        if json_req is None or not 'data' in json_req or not 'vlist' in json_req['data']:
            if can_retry(url):
                self.get_check()
            return
        av_id_list = [[ii['aid'], ii['comment']]
                      for ii in json_req['data']['vlist'] if not re.findall(self.ignore_list, str(ii['aid']))]
        if self.basic_av_id not in [ii[0] for ii in av_id_list]:
            if can_retry(url):
                self.get_check()
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
        check_index = comment
        for pn in range(1, (comment - 1) // 20 + 2):
            need_check = False
            for ii in range(20):
                if check_index < 1:
                    return
                if not check_index in self.comment[av_id]:
                    print(pn, av_id, check_index)
                    need_check = True
                    check_index -= (20 - ii)
                    break
                check_index -= 1
            if not need_check:
                continue

            self.check_comment_once(av_id, pn)
            if av_id in self.comment_max:
                check_index = self.comment_max[av_id] - 1
        comment = [self.comment[av_id][k]
                   for k in sorted(self.comment[av_id].keys())]
        basic = [','.join([str(jj) for jj in ii['basic']])
                 for ii in comment if 'basic' in ii]
        replies = []
        for ii in comment:
            if not 'replies' in ii:
                continue
            parent_floor = ii['basic'][0]
            replies_t = ii['replies']
            for jj in replies_t:
                jj[0] = '%s-%s' % (str(parent_floor), str(jj[0]))
                replies.append(','.join([str(kk) for kk in jj]))
        with codecs.open('%s%d_comment.csv' % (comment_dir, av_id), 'w', encoding='utf-8') as f:
            f.write('\n'.join(basic) + '\n')
            f.write('\n'.join(replies) + '\n')

    def check_comment_once(self, av_id: int, pn: int):
        ''' check comment once '''
        url = self.REPLY_V2_URL % (pn, av_id)
        json_req = get_request_proxy(url, 1)
        if json_req is None or not 'data' in json_req or not 'hots' in json_req['data']:
            if can_retry(url):
                self.check_comment_once(av_id, pn)
            return

        hots = json_req['data']['hots']
        replies = json_req['data']['replies']
        temp_floor = [] if replies is None else [ii['floor'] for ii in replies]
        if replies is None:
            wait_check = [] if hots is None else hots
        else:
            wait_check = replies if hots is None else [*hots, *replies]

        for ii in wait_check:
            info = {'basic': self.get_comment_detail(ii, av_id, pn)}
            floor = info['basic'][0]
            crep = ii['replies']

            if not crep is None:
                info['replies'] = [self.get_comment_detail(
                    ii, av_id, pn, floor) for ii in crep]
            self.comment[av_id][floor] = info
        if len(temp_floor):
            for ii in range(min(temp_floor), max(temp_floor) + 1):
                if not ii in self.comment[av_id]:
                    self.comment[av_id][ii] = {}
            self.comment_max[av_id] = min(temp_floor)

    def get_comment_detail(self, comment: dict, av_id: int, pn: int, parent_floor=None):
        ''' get comment detail '''
        ctime = time_str(comment['ctime'])
        wait_list = ['floor', 'member', 'content', 'like']
        wait_list_mem = ['uname', 'sex', 'sign', 'level_info']
        wait_list_content = ['message', 'plat']
        floor, member, content, like = [comment[ii] for ii in wait_list]
        uname, sex, sign, level = [member[ii] for ii in wait_list_mem]
        current_level = level['current_level']
        content, plat = [content[ii] for ii in wait_list_content]
        req_list = [floor, ctime, like, plat,
                    current_level, uname, sex, content, sign]
        self.have_bad_comment(req_list, av_id, pn, parent_floor)
        req_list[-1] = req_list[-1].replace(',', ' ').replace('\n', ' ')
        req_list[-2] = req_list[-2].replace(',', ' ').replace('\n', ' ')
        return req_list

    def have_bad_comment(self, req_list: list, av_id: int, pn: int, parent_floor=None):
        ''' check comment and send warning email if error '''
        floor, ctime, like, _, _, uname, sex, content, sign = req_list

        if not len(re.findall(self.keyword, content)):
            return True
        floor = '{}{}'.format(floor, '' if not parent_floor else '-{}'.format(floor))

        url = self.BASIC_AV_URL % av_id
        floor_str = '{}-{}'.format(av_id, floor)
        if str(av_id) in self.ignore_floor and floor in self.ignore_floor[str(av_id)]:
            return True
        if self.email_limit < 1 or (floor_str in self.email_send_time and self.email_send_time[floor_str] > self.email_limit):
            return True 

        email_content = '%s\nUrl: %s Page: %d #%s,\nUser: %s,\nSex: %s,\nconetnt: %s,\nsign: %s\nlike: %d' % (
            ctime, url, pn, floor, uname, sex, content, sign, like)
        email_subject = '(%s)av_id: %s || #%s Comment Warning !!!' % (
            ctime, av_id, floor)
        print(email_content, email_subject)
        send_email_time = 0
        send_email_result = False
        while not send_email_result and send_email_time < 4:
            send_email_result = send_email(email_content, email_subject)
            send_email_time += 1
        if floor_str in self.email_send_time:
            self.email_send_time[floor_str] += 1
        else:
            self.email_send_time[floor_str] = 0


if __name__ == '__main__':
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    if not os.path.exists(comment_dir):
        os.makedirs(comment_dir)
    if not os.path.exists(history_dir):
        os.makedirs(history_dir)
    if not os.path.exists(assign_path):
        shutil.copy(assign_path + '.tmp', assign_path)
    bb = Up()
    bb.load_click()
