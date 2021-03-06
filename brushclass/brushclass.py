# -*- coding: utf-8 -*-
# @Author: gunjianpan
# @Date:   2019-02-25 21:13:45
# @Last Modified by:   gunjianpan
# @Last Modified time: 2019-10-11 02:03:24

import argparse
import time
import random
import os
import sys

sys.path.append(os.getcwd())
from collections import Counter
from proxy.getproxy import GetFreeProxy
from util.util import begin_time, end_time, send_email, can_retry, echo, basic_req, get_accept, get_content_type

proxy_req = GetFreeProxy().proxy_req
data_path = 'brushclass/data/'

"""
  * brush @http
  * http://elective.pku.edu.cn
  * https://portal.w.pku.edu.cn/portal2017/bizcenter/score/retrScores.do  
    .data/
    └── cookie    // elective.pku.edu.cn cookie
"""


class Brush(object):
    """
    brush class in http://elective.pku.edu.cn
    """

    def __init__(self, ):
        self.failured_map = {}
        self.laster_timestamp = 0

    def have_places(self):
        """
        brush class
        """
        version = begin_time()
        have_places = False

        while not have_places:
            if self.have_places_once():
                send_email('大数据专题', '大数据专题 有名额啦 有名额啦')
                send_email('大数据专题', '大数据专题 有名额啦 有名额啦')
                send_email('大数据专题', '大数据专题 有名额啦 有名额啦')
                have_places = True
            time.sleep(random.randint(10, 20))
        end_time(version)

    def have_places_once(self):
        """
        have places
        """
        url = 'http://elective.pku.edu.cn/elective2008/edu/pku/stu/elective/controller/supplement/refreshLimit.do'
        if not os.path.exists('%scookie' % data_path):
            print('Brush Cookie not exist!!!')
            return
        with open('%scookie' % data_path, 'r') as f:
            cookie = f.readlines()
        headers = {
            'X-Requested-With': 'XMLHttpRequest',
            'Cookie': '',
            'Content-Type': get_content_type(),
            'Accept': get_accept('xhr'),
            "Origin": "http://elective.pku.edu.cn",
            "Referer": "http://elective.pku.edu.cn/elective2008/edu/pku/stu/elective/controller/supplement/SupplyCancel.do",
        }
        headers['Cookie'] = cookie[0][:-1]

        data = {
            "index": '10',
            "seq": 'yjkc20141100016542',
        }

        ca = proxy_req(url, 11, data, header=headers)

        if not ca:
            if round(time.time()) - self.laster_timestamp > 60:
                send_email("Cookie failure", "Cookie failure")
            return False
        print(ca['electedNum'])
        self.laster_timestamp = round(time.time())
        return int(ca['electedNum']) < 120


def get_score(cookie: str):
    SCORE_URL = 'https://portal.w.pku.edu.cn/portal2017/bizcenter/score/retrScores.do'
    headers = {
        'Accept': get_accept('xhr'),
        'Host': 'portal.w.pku.edu.cn',
        'Origin': 'https://portal.w.pku.edu.cn',
        'Referer': 'https://portal.w.pku.edu.cn/portal2017/',
        'Cookie': cookie,

    }
    req = basic_req(SCORE_URL, 11, header=headers)
    if req is None or list(req.keys()) != ['success', 'xslb', 'xh', 'xm', 'scoreLists']:
        if can_retry(SCORE_URL):
            return get_score(cookie)
        else:
            return
    return req


def get_gpa(cookie: str):
    score = get_score(cookie)
    if score is None:
        return
    need_cj = ['A', 'B', 'C', 'D', 'F']
    name = score['xm']
    student_id = score['xh']
    score_list = score['scoreLists']
    score_list = [(int(ii['xf']), ii['cj'])
                  for ii in score_list if ii['cj'][0] in need_cj]
    grade_list = [(ii, get_grade_point(jj)) for ii, jj in score_list]
    TG = sum([ii * jj for ii, jj in grade_list])
    TC = sum([ii for ii, _ in grade_list])
    level = [ii[0] for _, ii in score_list]
    level_count = Counter(level)
    gpa = TG / TC
    echo(1, f'{name}, Congratulations u get {TC} credits and {gpa:.3f} gpa in this university.')
    for ii in need_cj:
        if ii not in level_count:
            continue
        count = level_count[ii]
        echo(2, f'U have {count} class get {ii}.')


def get_grade_point(score: str):
    score_map = {'A': 4, 'B': 3, 'C': 2, 'D': 1, 'F': 0}
    grade_point = score_map[score[0]]
    if len(score) == 2 and score[0] != 'F':
        flag = 1 if score[1] == '+' else -1
        grade_point += 0.3 * flag
    grade_point = min(4, grade_point)
    return grade_point


if __name__ == '__main__':
    if not os.path.exists(data_path):
        os.makedirs(data_path)
    parser = argparse.ArgumentParser(description='pku student helper')
    parser.add_argument('--mode', type=int, default=1, metavar='mode',help='0->bruchclass,1->get_gpa')
    parser.add_argument('--cookie', type=str, default='', metavar='cookie',help='portal cookie')
    mode = parser.parse_args().mode
    if mode == 0:
        brush = Brush()
        brush.have_places()
    else:
        cookie = parser.parse_args().cookie.replace('\'', '').replace('"', '')
        get_gpa(cookie)
