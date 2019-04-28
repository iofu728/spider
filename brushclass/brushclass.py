# -*- coding: utf-8 -*-
# @Author: gunjianpan
# @Date:   2019-02-25 21:13:45
# @Last Modified by:   gunjianpan
# @Last Modified time: 2019-03-27 23:44:02

import time
import random
import os

from proxy.getproxy import GetFreeProxy
from util.util import begin_time, end_time, send_email

get_request_proxy = GetFreeProxy().get_request_proxy
data_path = 'brushclass/data/'

"""
  * brush @http
  * www.zhihu.com/api/v4/creator/content_statistics
  * www.jianshu.com/u/
  * blog.csdn.net
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
            'pragma': 'no-cache',
            'X-Requested-With': 'XMLHttpRequest',
            'cache-control': 'no-cache',
            'Cookie': '',
            'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            "Accept-Encoding": "",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3682.0 Safari/537.36",
            "Origin": "http://elective.pku.edu.cn",
            "Referer": "http://elective.pku.edu.cn/elective2008/edu/pku/stu/elective/controller/supplement/SupplyCancel.do",
        }
        headers['Cookie'] = cookie[0][:-1]

        data = {
            "index": '10',
            "seq": 'yjkc20141100016542',
        }

        ca = get_request_proxy(url, 11, data, header=headers)

        if not ca:
            if round(time.time()) - self.laster_timestamp > 60:
                send_email("Cookie failure", "Cookie failure")
            return False
        print(ca['electedNum'])
        self.laster_timestamp = round(time.time())
        return int(ca['electedNum']) < 120


if __name__ == '__main__':
    if not os.path.exists(data_path):
        os.makedirs(data_path)
    brush = Brush()
    brush.have_places()
