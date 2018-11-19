# -*- coding: utf-8 -*-
# @Author: gunjianpan
# @Date:   2018-11-10 11:17:16
# @Last Modified by:   gunjianpan
# @Last Modified time: 2018-11-19 10:40:56
import codecs
import threading

from proxy.getproxy import GetFreeProxy
from utils.db import Db
from utils.utils import begin_time, get_html, end_time


class Press_test():
    """
    give press in short time
    """

    def __init__(self):
        self.proxyclass = GetFreeProxy()

    def basic_press(self, url, host, times, types):
        """
        press have no data input
        """
        if types == 1:
            html = self.proxyclass.get_request_proxy(url, host, 0)
        else:
            html = get_html(url, {}, host)

        if html == False and times < 5:
            self.basic_press(url, host, times + 1, types)

    def press_threading(self, url, host, qps, types):
        """
        press url at constant qps
        """
        begin_time()
        threadings = []
        for index in range(qps):
            work = threading.Thread(
                target=self.basic_press, args=(url, host, 0, types))
            threadings.append(work)
        for work in threadings:
            work.start()
        for work in threadings:
            work.join()
        end_time()

    def one_press_attack(self, url, host, qps, types, total):
        """
        press url from a long time
        """
        for index in range(total):
            self.press_threading(url, host, qps, types)
        print('Over')
