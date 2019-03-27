# -*- coding: utf-8 -*-
# @Author: gunjianpan
# @Date:   2019-03-16 15:18:10
# @Last Modified by:   gunjianpan
# @Last Modified time: 2019-03-28 00:09:51
import threading
import time
import random
import re
import json as js
import pickle

from proxy.getproxy import GetFreeProxy
from utils.utils import begin_time, end_time, changeHeaders, basic_req, can_retry, send_email

one_day = 86400
data_path = 'bilibili/data/'
yybzz_path = 'bilibili/yybzz/'
get_request_proxy = GetFreeProxy().get_request_proxy


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
    """
    some development in bilibili
    """

    def __init__(self):
        self.finish = 0
        self.rank = {}
        self.rank_map = {}
        self.rank_type = {}
        self.public = {}
        self.public_list = []
        self.star = {}
        self.origin_data_v2 = {}
        self.have_yybzz = False
        self.last_rank = {}
        self.exec_map = {}
        self.last_check = {}
        self.last_view = {}
        self.comment = {}
        self.comment_max = {}
        self.begin_timestamp = int(time.time())

    def basic_view(self, url, times, types):
        """
        press have no data input
        """
        # url = url + str(int(round(time.time() * 1000)))
        url = 'http://www.bilibili.com/video/av46317059'
        if types == 1:
            html = get_request_proxy(url, 0)
        else:
            html = basic_req(url, 0)

        if html == False and times < 5:
            self.basic_view(url, times + 1, types)

    def view_threading(self, url, qps, types):
        """
        press url at constant qps
        """
        version = begin_time()
        changeHeaders({'Referer': 'https://www.bilibili.com/video/av46317059'})
        threadings = []
        for index in range(qps):
            # work = threading.Thread(
            #     target=self.basic_press, args=(url, 0, types))
            # threadings.append(work)
            work = threading.Thread(
                target=self.basic_press_bilibili, args=(url, 0, types))
            threadings.append(work)
        for work in threadings:
            work.start()
        for work in threadings:
            work.join()
        print('Finish', self.finish)
        self.finish = 0
        self.check_click()
        end_time(version)

    def basic_press_bilibili(self, url, times, types):
        """
        press have no data input
        """

        url = 'https://www.bilibili.com/video/av46317059'
        if types == 1:
            html = get_request_proxy(url, 0)
        else:
            html = basic_req(url, 0)

        if html == False:
            if times < 5:
                self.basic_view(url, times + 1, types)
            return
        time = 0
        url_1 = 'http://api.bilibili.com/x/report/click/now?jsonp=jsonp'

        if types == 1:
            json_1 = get_request_proxy(url_1, 1)
            # json_1 = get_request_proxy(url_1, 1)
        else:
            json_1 = basic_req(url_1, 1)
        if not json_1 is None:
            print(json_1)

        if not self.have_error(json_1, 1):
            if times < 2:
                self.basic_press_bilibili(url, times + 1, types)
            return
        time = 0
        url = 'http://api.bilibili.com/x/report/click/web/h5'
        data = {
            'aid': '46317059',
            'cid': '81149626',
            'part': '1',
            'mid': str(random.randint(10000000, 19999999)),
            'lv': '2',
            'ftime': '1539774474',
            'stime': json_1['data']['now'],
            'jsonp': 'jsonp',
            'type': '3',
            'sub_type': '0'
        }
        # url = url + str(int(round(time.time() * 1000)))
        if types == 1:
            json = get_request_proxy(url, 11, data)
            # json = get_request_proxy(url, 3, data)
        else:
            json = basic_req(url, 11, data=data)
        if not json is None:
            print(json)

        if not self.have_error(json):
            if times < 2:
                self.basic_press_bilibili(url, times + 1, types)
            return
        time = 0
        url_3 = 'http://api.bilibili.com/x/report/web/heartbeat'
        data_3 = {
            'aid': '46317059',
            'cid': '81149626',
            'mid': data['mid'],
            'csrf': '48a5a9fdd754d5ed21cd360be83b75b5',
            'played_time': '0',
            'realtime': '0',
            'start_ts': json_1['data']['now'],
            'type': '3',
            'dt': '2',
            'play_type': '1'
        }

        if types == 1:
            json_3 = get_request_proxy(url_3, 11, data_3)
            # json_3 = get_request_proxy(url_3, 11, data_3)
        else:
            json_3 = basic_req(url_3, 11, data=data_3)
        if not json_3 is None:
            print(json_3)

        if not self.have_error(json_3) and times < 2:
            self.basic_press_bilibili(url, times + 1, types)
        print('finish.')
        self.finish = self.finish + 1

    def check_click(self):
        changeHeaders({'Referer': 'https://www.bilibili.com/video/av46412322'})
        url = 'http://api.bilibili.com/x/web-interface/archive/stat?aid=46412322'
        json = basic_req(url, 1)
        if 'data' not in json:
            self.check_click()
            return
        json = json['data']
        need = ['view', 'like', 'coin', 'favorite',
                'reply', 'share', 'danmaku']
        data = [json[index] for index in need]
        data = [time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time())), *data]
        with open('press/data/yybzz', 'a') as f:
            f.write(','.join([str(index) for index in data]) + '\n')
        print(','.join([str(index) for index in data]))

    def check_rank_yybzz(self):
        changeHeaders({'Referer': 'https://www.bilibili.com/video/av46412322'})
        url = 'https://www.bilibili.com/ranking/all/155/1/1'
        html = basic_req(url, 0)
        li_list = html.find_all('li', class_='rank-item')
        yybzz = [index for index in li_list if '野原白之助' in index.text]
        if not len(yybzz):
            return
        yybzz = yybzz[0]
        score = int(yybzz.find_all('div', class_='pts')
                    [0].find_all('div')[0].text)
        rank = int(yybzz.find_all('div', class_='num')[0].text)

        url = 'http://api.bilibili.com/x/web-interface/archive/stat?aid=46412322'
        json = basic_req(url, 1)
        if 'data' not in json:
            self.check_rank()
            return
        json = json['data']
        need = ['view', 'like', 'coin', 'favorite',
                'reply', 'share', 'danmaku']
        data = [json[index] for index in need]
        data = [time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time())), *data]
        data.append(rank)
        data.append(score)
        if not rank % 10 and rank not in self.rank:
            self.rank.append(rank)
            send_email('Rank: %d Score: %d' % (rank, score),
                       'Rank: %d Score: %d' % (rank, score))
        with open('press/data/yybzz', 'a') as f:
            f.write(','.join([str(index) for index in data]) + '\n')
        print(','.join([str(index) for index in data]))

    def check_rank(self, av_id, times=0):
        rank_list = self.rank_map[av_id] if av_id in self.rank_map else []
        changeHeaders(
            {'Referer': 'https://www.bilibili.com/video/av%d' % (av_id)})
        if len(rank_list):
            score = int(rank_list[1])
            rank = int(rank_list[0])

        url = 'http://api.bilibili.com/x/web-interface/archive/stat?aid=%d' % (
            av_id)
        json = get_request_proxy(url, 1)

        if not self.have_error(json):
            if times < 3:
                self.check_rank(av_id, times + 1)
            return
        json = json['data']
        need = ['view', 'like', 'coin', 'favorite',
                'reply', 'share', 'danmaku']
        data = [json[index] for index in need]
        if not self.check_view(av_id, data[0]):
            if times < 3:
                self.check_rank(av_id, times + 1)
            return
        if len(rank_list):
            data = [time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time())), *data, *rank_list[:2], *rank_list[3:5]]
        else:
            data = [time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time())), *data]

        with open(data_path + '%d.csv' % (av_id), 'a') as f:
            f.write(','.join([str(index) for index in data]) + '\n')
        # print(','.join([str(index) for index in data]))

        if self.check_rank_list(av_id, rank_list):
            av_id_id = int(av_id) * 10 + int(rank_list[-1])
            if av_id_id not in self.rank:
                self.rank[av_id_id] = [rank_list[0] // 10]
            else:
                self.rank[av_id_id].append(rank_list[0] // 10)
            self.last_rank[av_id_id] = rank_list[0]
            send_email('%dday List || Rank: %d Score: %d' % (int(
                rank_list[-1]), rank, score), '%dday List || Rank: %d Score: %d' % (int(rank_list[-1]), rank, score))
        if av_id in self.last_check and self.last_check[av_id] - int(time.time()) > one_day:
            del self.rank_map[av_id]
        elif av_id not in self.last_check and int(time.time()) > one_day + self.begin_timestamp:
            del self.rank_map[av_id]

    def check_view(self, av_id, view):
        """
        check view
        """
        if not av_id in self.last_view:
            return True
        last_view = self.last_view[av_id]
        if last_view < view:
            return False
        if last_view + 2000 < view:
            return False
        return True

    def check_rank_list(self, av_id, rank_list):
        if not len(rank_list) or rank_list[2] != '野原白之助3':
            return False
        av_id_id = int(av_id) * 10 + int(rank_list[-1])
        if av_id_id not in self.rank:
            return True
        first_rank = rank_list[0] // 10
        if first_rank not in self.rank[av_id_id] or first_rank == 0 or first_rank == 1:
            if self.last_rank[av_id_id] != rank_list[0]:
                return True
        return False

    def check_rank_v2(self, av_id, times=0):
        vId = str(av_id)
        rank_list = self.rank_map[av_id] if av_id in self.rank_map else []
        changeHeaders(
            {'Referer': 'https://www.bilibili.com/video/av%d' % (av_id)})
        if len(rank_list):
            score = rank_list[1]
            rank = rank_list[0]

        url = 'http://api.bilibili.com/x/web-interface/archive/stat?aid=%d' % (
            av_id)
        json = get_request_proxy(url, 1)

        if not self.have_error(json):
            if times < 3:
                self.check_rank_v2(av_id, times + 1)
            return
        json = json['data']
        need = ['view', 'like', 'coin', 'favorite',
                'reply', 'share', 'danmaku']
        data = [json[index] for index in need]
        if len(rank_list):
            data = [time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time())), *data, *rank_list[:2], *rank_list[3:5]]
        else:
            data = [time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time())), *data]
        self.origin_data_v2[av_id] = data

    def have_error(self, json, types=None):
        '''
        have error json
        '''
        if json is None:
            return
        if 'code' not in json or json['code'] != 0:
            return False
        if 'message' not in json or json['message'] != '0':
            return False
        if 'ttl' not in json or json['ttl'] != 1:
            return False
        if not types is None:
            if 'data' not in json or 'now' not in json['data']:
                return False
        return True

    def check_type(self, av_id):
        """
        check type
        """
        if av_id in self.rank_type:
            return self.rank_type[av_id]
        if av_id in self.rank_map and not len(self.rank_map[av_id]):
            self.rank_type[av_id] = True
            return True
        changeHeaders(
            {'Referer': 'https://www.bilibili.com/video/av%d' % (av_id)})
        url = 'https://api.bilibili.com/x/web-interface/view?aid=%d' % (av_id)

        json = get_request_proxy(url, 1)

        if json is None:
            return False
        if 'data' not in json:
            return False
        if 'tid' not in json['data']:
            return False
        self.rank_type[av_id] = json['data']['tid'] == 158
        return json['data']['tid'] == 158

    def add_av(self, av_id, rank, score):
        """
        if or not add av
        """
        if av_id not in self.rank_map:
            return rank < 95 or score > 5000
        else:
            if not len(self.rank_map[av_id]):
                return True
            else:
                if self.rank_map[av_id][0] - rank > 5:
                    return True
                return score - self.rank_map[av_id][1] > 200

    def public_monitor(self, av_id, times):
        self.public_list.append(av_id)
        print('Monitor Begin %d' % (av_id))
        data_time, mid = self.public[av_id]
        self.get_star_num(mid, 0)
        self.check_rank_v2(av_id, 0)

        time.sleep(5)

        follower = self.star[mid] if mid in self.star else 0
        origin_data = self.origin_data_v2[av_id] if av_id in self.origin_data_v2 else [
        ]
        sleep_time = data_time + one_day - int(time.time())
        if sleep_time < 0:
            return
        time.sleep(sleep_time)
        self.get_star_num(mid, 0)
        self.check_rank_v2(av_id, 0)

        time.sleep(5)
        follower_2 = self.star[mid] if mid in self.star else 0
        one_day_data = self.origin_data_v2[av_id] if av_id in self.origin_data_v2 else [
        ]

        data = [time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(data_time)), av_id, follower, follower_2, *origin_data, *one_day_data]
        with open(data_path + 'public.csv', 'a') as f:
            f.write(','.join([str(ii) for ii in data]) + '\n')

    def public_data(self, av_id, times):
        changeHeaders(
            {'Referer': 'https://www.bilibili.com/video/av%d' % (av_id)})
        url = 'http://api.bilibili.com/x/web-interface/view?aid=%d' % (av_id)
        json = get_request_proxy(url, 1)
        if json is None:
            if times < 3:
                self.public_data(av_id, times + 1)
            return
        data_time = json['data']['pubdate']
        mid = json['data']['owner']['mid']
        self.get_star_num(mid, 0)
        self.public[av_id] = [data_time, mid]

    def get_star_num(self, mid, times):

        url = 'http://api.bilibili.com/x/relation/stat?jsonp=jsonp&callback=__jp11&vmid=%d' % (
            mid)
        changeHeaders({
            'Origin': 'https://www.bilibili.com',
            'Referer': 'https://www.bilibili.com/video/av46317059'
        })
        req = get_request_proxy(url, 2)
        if req is None or req.status_code != 200 or len(req.text) < 8 or not '{' in req.text:
            if times < 3:
                self.get_star_num(mid, times + 1)
            return
        try:
            json = js.loads(req.text[7:-1])
            self.star[mid] = json['data']['follower']
        except Exception as e:
            pass

    def load_rank_index(self, index, day_index):
        """
        load rank
        """
        index = str(index)
        day_index = str(day_index)
        changeHeaders(
            {'Referer': 'https://www.bilibili.com/ranking/all/155/' + index + '/' + day_index})
        url = 'https://www.bilibili.com/ranking/all/155/' + index + '/' + day_index
        html = basic_req(url, 0)
        rank_list = html.find_all('li', class_='rank-item')

        now_av_id = []
        wait_check_public = []

        for av in rank_list:
            av_href = av.find_all('a')[0]['href']
            av_id = int(re.findall('av.*', av_href)[0][2:-1])
            now_av_id.append(av_id)
            if not self.check_type(av_id):
                continue
            rank = int(av.find_all('div', class_='num')[0].text)
            score = int(av.find_all('div', class_='pts')
                        [0].find_all('div')[0].text)
            name = av.find_all('span')[2].text
            if self.add_av(av_id, rank, score):
                if not av_id in self.public:
                    wait_check_public.append(av_id)
                self.last_check[av_id] = int(time.time())
                self.rank_map[av_id] = [rank, score, name, index, day_index]

        with open(data_path + 'yybzz.csv') as f:
            yybzz = [int(index.replace('\n', '')) for index in f.readlines()]

        for ii in yybzz:
            if not ii in self.public:
                wait_check_public.append(ii)

        have_yybzz = False
        for index in yybzz:
            if index in now_av_id:
                have_yybzz = True
        if self.have_yybzz and not have_yybzz:
            send_email('No rank.....No Rank......No Rank.....',
                       'No rank.....No Rank......No Rank.....')

        threading_public = []
        for ii in wait_check_public:
            work = threading.Thread(target=self.public_data, args=(ii, 0,))
            threading_public.append(work)
        for work in threading_public:
            work.start()
        for work in threading_public:
            work.join()

        threadings = []
        for ii, jj in self.public.items():
            if not ii in self.public_list and jj[0] + one_day > int(time.time()):
                work = threading.Thread(
                    target=self.public_monitor, args=(ii, 0,))
                threadings.append(work)
        for work in threadings:
            work.start()

    def load_rank(self):
        """
        load rank
        """
        self.load_rank_index(1, 1)
        self.load_rank_index(1, 3)

        print(self.rank_map)
        with open(data_path + 'youshang', 'w') as f:
            f.write('\n'.join([str(index) for index in self.rank_map.keys()]))

    def load_click(self, num=1000000):
        with open(data_path + 'youshang', 'r') as f:
            self.rank_map = {int(index): [] for index in f.readlines()}

        for index in range(num):
            threadings = []
            if not index % 5:
                work = threading.Thread(target=self.load_rank, args=())
                threadings.append(work)
                check = threading.Thread(target=self.get_check, args=())
                threadings.append(check)
            for av_id in self.rank_map:
                work = threading.Thread(target=self.check_rank, args=(av_id,))
                threadings.append(work)
            for work in threadings:
                work.start()
            time.sleep(120)

    def get_check(self):
        with open('%scomment.pkl' % yybzz_path, 'rb') as f:
            self.comment = pickle.load(f)

        url = 'https://space.bilibili.com/ajax/member/getSubmitVideos?mid=282849687&page=1&pagesize=50'
        json = get_request_proxy(url, 1)
        if json is None or not 'data' in json or not 'vlist' in json['data']:
            if can_retry(url):
                self.get_check()
            return
        av_id_list = [[ii['aid'], ii['comment']]
                      for ii in json['data']['vlist']]

        threadings = []
        for (ii, jj) in av_id_list:
            if ii not in self.comment:
                self.comment[ii] = {}
            work = threading.Thread(
                target=self.comment_check_schedule, args=(ii, jj,))
            threadings.append(work)
        for work in threadings:
            work.start()
        for work in threadings:
            work.join()
        with open('%scomment.pkl' % yybzz_path, 'wb') as f:
            pickle.dump(self.comment, f)

        return av_id_list

    def comment_check_schedule(self, av_id, comment):
        """
        schedule comment check thread
        """
        check_index = comment
        for pn in range(1, (comment - 1) // 20 + 2):
            need_check = False
            for ii in range(20):
                if check_index < 1:
                    return
                if not check_index in self.comment[av_id]:
                    print(pn, av_id, check_index)
                    need_check = True
                    check_index -= (ii + 1)
                    break
                check_index -= 1
            if not need_check:
                continue

            self.check_comment_once(av_id, pn)
            if av_id in self.comment_max:
                check_index = self.comment_max[av_id] - 1
            # time.sleep(random.uniform(5, 10))
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
        with open('%s%d_comment.csv' % (yybzz_path, av_id), 'w') as f:
            f.write('\n'.join(basic) + '\n')
            f.write('\n'.join(replies) + '\n')

    def check_comment_once(self, av_id, pn):
        """
        check comment once
        """
        url = 'https://api.bilibili.com/x/v2/reply?jsonp=jsonp&pn=%d&type=1&oid=%d&sort=0' % (
            pn, av_id)
        json = get_request_proxy(url, 1)
        if json is None or not 'data' in json or not 'hots' in json['data']:
            if can_retry(url):
                self.check_comment_once(av_id, pn)
            return

        hots = json['data']['hots']
        replies = json['data']['replies']
        temp_floor = [] if replies is None else [ii['floor'] for ii in replies]
        if replies is None:
            wait_check = [] if hots is None else hots
        else:
            wait_check = replies if hots is None else [*hots, *replies]
        comment = []

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

    def get_comment_detail(self, comment, av_id, pn, parent_floor=None):
        """
        get comment detail
        """
        ctime = time.strftime("%Y-%m-%d %H:%M:%S",
                              time.localtime(comment['ctime']))
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

    def have_bad_comment(self, req_list, av_id, pn, parent_floor=None):
        """
        check comment and send warining email if error
        """
        floor, ctime, like, _, _, uname, sex, content, sign = req_list
        if not '在售价' in content and not '券后价' in content:
            return True

        floor = str(
            floor) if parent_floor is None else '%d-%d' % (parent_floor, floor)
        url = 'https://www.bilibili.com/video/av%d' % av_id

        email_content = '%s\nUrl: %s Page: %d #%s,\nUser: %s,\nSex: %s,\nconetnt: %s,\nsign: %s' % (
            ctime, url, pn, floor, uname, sex, content, sign)
        email_subject = '(%s)av_id: %s || #%s Comment Warning !!!' % (
            ctime, av_id, floor)
        print(email_content, email_subject)
        send_email_time = 0
        send_email_result = False
        while not send_email_result and send_email_time < 4:
            send_email_result = send_email(email_content, email_subject)
            send_email_time += 1


if __name__ == '__main__':
    bb = Up()
    bb.load_click()
