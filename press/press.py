# -*- coding: utf-8 -*-
# @Author: gunjianpan
# @Date:   2018-11-10 11:17:16
# @Last Modified by:   gunjianpan
# @Last Modified time: 2019-03-25 21:18:30
import threading
import time

from proxy.getproxy import GetFreeProxy
from util.db import Db
from util.util import begin_time, end_time, basic_req

get_request_proxy = GetFreeProxy().get_request_proxy


class Press_test():
    """
    give press in short time
    """

    def basic_press(self, url, times, types):
        """
        press have no data input
        """
        url = url + str(int(round(time.time() * 1000)))
        if types == 1:
            html = get_request_proxy(url, 1)
        else:
            html = basic_req(url, 1)

        if html == False and times < 5:
            self.basic_press(url, times + 1, types)

    def press_threading(self, url, qps, types):
        """
        press url at constant qps
        """
        version = begin_time()
        threadings = []
        for index in range(qps):
            work = threading.Thread(
                target=self.basic_press, args=(url, 0, types))
            threadings.append(work)
        for work in threadings:
            work.start()
        for work in threadings:
            work.join()
        end_time(version)

    def one_press_attack(self, url, qps, types, total):
        """
        press url from a long time
        """
        for index in range(total):
            self.press_threading(url, qps, types)
        print('Over')
