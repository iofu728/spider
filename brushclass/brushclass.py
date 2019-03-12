# -*- coding: utf-8 -*-
# @Author: gunjianpan
# @Date:   2019-02-25 21:13:45
# @Last Modified by:   gunjianpan
# @Last Modified time: 2019-02-26 20:34:01

import codecs
import threading
import time
import pandas as pd
import re
import requests
import random
import smtplib


from email.mime.text import MIMEText
from bs4 import BeautifulSoup
from proxy.getproxy import GetFreeProxy
from utils.utils import begin_time, get_html, end_time, changeCookie, changeHeaders, changeHtmlTimeout
from urllib.request import urlopen


class Brush(object):
    """
    brush class in http://elective.pku.edu.cn
    """

    def __init__(self, ):
        self.proxyclass = GetFreeProxy()
        self.failured_map = {}
        self.laster_timestamp = 0

    def send_email(self, context, subject):

        with open('brushclass/data/email', 'r') as f:
            email = f.readlines()
        mail_host = 'smtp.163.com'
        # 163用户名
        mail_user = email[0][:-1]
        # 密码(部分邮箱为授权码)
        mail_pass = email[1][:-1]
        # 邮件发送方邮箱地址
        sender = email[0][:-1] + '@163.com'
        # 邮件接受方邮箱地址，注意需要[]包裹，这意味着你可以写多个邮件地址群发
        receivers = [email[2][:-1] + '@163.com']

        # 设置email信息
        # 邮件内容设置
        message = MIMEText(context, 'plain', 'utf-8')
        # 邮件主题
        message['Subject'] = subject
        # 发送方信息
        message['From'] = sender
        # 接受方信息
        message['To'] = receivers[0]

        # 登录并发送邮件
        try:
            smtpObj = smtplib.SMTP_SSL()
            # 连接到服务器
            smtpObj.connect(mail_host, 465)
            # 登录到服务器
            smtpObj.login(mail_user, mail_pass)
            # 发送
            smtpObj.sendmail(
                sender, receivers, message.as_string())
            # 退出
            smtpObj.quit()
            print('success')
        except smtplib.SMTPException as e:
            print('error', e)  # 打印错误

    def have_places(self):
        """
        brush class
        """
        version = begin_time()
        have_places = False

        while not have_places:
            if self.have_places_once():
                self.send_email('大数据专题', '大数据专题 有名额啦 有名额啦')
                self.send_email('大数据专题', '大数据专题 有名额啦 有名额啦')
                self.send_email('大数据专题', '大数据专题 有名额啦 有名额啦')
                have_places = True
            time.sleep(random.randint(10, 20))
        end_time = ()

    def have_places_once(self):
        """
        have places
        """
        url = 'http://elective.pku.edu.cn/elective2008/edu/pku/stu/elective/controller/supplement/refreshLimit.do'
        with open('brushclass/data/cookie', 'r') as f:
            cookie = f.readlines()
        headers = {
            'pragma': 'no-cache',
            # 'sec-fetch-dest': 'empty',
            # 'sec-fetch-site': 'same-origin',
            # 'sec-fetch-user': '?F',
            # 'sec-origin-policy': '0',
            # 'upgrade-insecure-requests': '1',
            'X-Requested-With': 'XMLHttpRequest',
            'cache-control': 'no-cache',
            'Cookie': '',
            # 'Upgrade-Insecure-Requests': '1',
            'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            "Accept-Encoding": "",
            "Accept-Language": "zh-CN,zh;q=0.9",
            # :todo: change user-agent
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3682.0 Safari/537.36",
            "Origin": "http://elective.pku.edu.cn",
            "Referer": "http://elective.pku.edu.cn/elective2008/edu/pku/stu/elective/controller/supplement/SupplyCancel.do",
        }
        changeHeaders(headers)
        changeCookie(cookie[0][:-1])

        data = {
            "index": '10',
            "seq": 'yjkc20141100016542',
        }

        ca = self.proxyclass.get_request_proxy(url, 3, data)

        if not ca:
            if round(time.time()) - self.laster_timestamp > 60:
                self.send_email("Cookie failure", "Cookie failure")
            return False
        print(ca['electedNum'])
        self.laster_timestamp = round(time.time())
        return int(ca['electedNum']) < 120


if __name__ == '__main__':
    brush = Brush()
    brush.have_places()
