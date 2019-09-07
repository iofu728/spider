# -*- coding: utf-8 -*-
# @Author: gunjianpan
# @Date:   2018-10-19 15:33:46
# @Last Modified by:   gunjianpan
# @Last Modified time: 2019-09-07 19:20:05

from __future__ import with_statement
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import codecs
import datetime
import json
import logging
import os
import pickle
import platform
import random
import re
import urllib
import smtplib
import threading
import time
from email.mime.text import MIMEText

import numpy as np
import requests
import urllib3
from bs4 import BeautifulSoup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

headers = {
    'pragma': 'no-cache',
    'cache-control': 'no-cache',
    'Cookie': '',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3',
    "Accept-Encoding": "",
    "Accept-Language": "zh-CN,zh;q=0.9",
    'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3682.0 Safari/537.36"}
data_dir = 'util/data/'
log_path = 'service.log'
if not os.path.exists(data_dir):
    os.makedirs(data_dir)
try:
    with codecs.open('%sagent' % data_dir, 'r', encoding='utf-8') as f:
        file = f.readlines()
    agent_lists = [" ".join(index.split()[1:])[1:-1] for index in file]
except:
    agent_lists = [headers['User-Agent']]
agent_len = len(agent_lists) - 1
html_timeout = 5
json_timeout = 4
start = []
spend_list = []
failure_map = {}
is_service = False
LOG_DIR = 'log/'
EMAIL_SIGN = '\n\n\nBest wish!!\n%s\n\n————————————————————\n• Send from script designed by gunjianpan.'


def basic_req(url: str, types: int, proxies=None, data=None, header=None, need_cookie: bool = False):
    """
    requests
    @types XY: X=0.->get;   =1.->post;
               Y=0.->html;  =1.->json; =2.->basic; =3.->text;
    """
    header = req_set(url, header)
    result = None
    if not types:
        result = get_html(url, proxies, header, need_cookie)
    elif types == 1:
        result = get_json(url, proxies, header, need_cookie)
    elif types == 2:
        result = get_basic(url, proxies, header)
    elif types == 3:
        result = get_text(url, proxies, header, need_cookie)
    elif types == 11:
        result = post_json(url, proxies, data, header, need_cookie)
    elif types == 12:
        result = post_basic(url, proxies, data, header)
    elif types == 13:
        result = post_text(url, proxies, data, header, need_cookie)
    else:
        echo('0|warning', types, ' type is not supported!!!')
    if need_cookie and result is None:
        return None, {}
    return result


def req_set(url: str, header):
    ''' req headers set '''
    global headers
    headers['Host'] = url.split('/')[2]
    index = random.randint(0, agent_len)
    headers['User-Agent'] = agent_lists[index]
    if not header is None and 'User-Agent' not in header:
        header['User-Agent'] = agent_lists[index]
    return header


def get_html(url: str, proxies=None, header=None, need_cookie: bool = False):
    ''' get html @return BeautifulSoup '''
    if header is None:
        header = headers
    try:
        html = requests.get(url, headers=header, verify=False,
                            timeout=html_timeout, proxies=proxies, allow_redirects=False)
        if html.status_code == 301 or html.status_code == 302:
            url = BeautifulSoup(html.text, 'html.parser').a['href']
            print('Redirect: ', url)
            headers['Host'] = url.split('/')[2]
            html = requests.get(url, headers=header, verify=False,
                                timeout=html_timeout, proxies=proxies, allow_redirects=False)
        if html.apparent_encoding == 'utf-8' or 'gbk' in html.apparent_encoding:
            html.encoding = html.apparent_encoding
        cookies = html.cookie.get_dict()
        html = html.text
    except:
        cookies = {}
        html = '<html></html>'
    if need_cookie:
        return BeautifulSoup(html, 'html.parser'), cookies
    return BeautifulSoup(html, 'html.parser')


def get_json(url: str, proxies=None, header=None, need_cookie: bool = False):
    ''' get json @return dict '''
    if header is None:
        header = headers
    try:
        json_req = requests.get(url, headers=header, verify=False,
                                timeout=json_timeout, proxies=proxies)
        if need_cookie:
            return json_req.json(), json_req.cookies.get_dict()
        return json_req.json()
    except:
        return


def post_json(url: str, proxies=None, data=None, header=None, need_cookie: bool = False):
    ''' post json @return dict '''
    if header is None:
        header = headers
    try:
        json_req = requests.post(url, headers=header, verify=False, data=data,
                                 timeout=json_timeout, proxies=proxies)
        if need_cookie:
            return json_req.json(), json_req.cookies.get_dict()
        return json_req.json()
    except Exception as e:
        return


def post_basic(url: str, proxies=None, data=None, header=None):
    ''' post basic @return requests '''
    if header is None:
        header = headers
    try:
        return requests.post(url, headers=header, verify=False, data=data,
                             timeout=json_timeout, proxies=proxies)
    except:
        return


def get_basic(url: str, proxies=None, header=None):
    ''' get basic '''
    if header is None:
        header = headers
    try:
        return requests.get(url, headers=header, verify=False,
                            timeout=html_timeout, proxies=proxies)
    except:
        return


def get_text(url: str, proxies=None, header=None, need_cookie: bool = False) -> str:
    ''' get text '''
    if header is None:
        header = headers
    try:
        req = requests.get(url, headers=header, verify=False,
                           timeout=html_timeout, proxies=proxies)
        ''' change encoding '''
        req.encoding = req.apparent_encoding
        if need_cookie:
            return req.text, req.cookies.get_dict()
        return req.text
    except:
        if need_cookie:
            return '', {}
        return ''


def post_text(url: str, proxies=None, header=None, data=None, need_cookie: bool = False) -> str:
    ''' post text '''
    if header is None:
        header = headers
    try:
        req = requests.post(url, headers=header, verify=False, data=data,
                            timeout=html_timeout, proxies=proxies)
        if need_cookie:
            return req.text, req.cookies.get_dict()
        return req.text
    except:
        if need_cookie:
            return '', {}
        return ''


def changeCookie(cookie: str):
    ''' change cookie '''
    global headers
    headers['Cookie'] = cookie


def changeHeaders(header: dict):
    ''' change Headers '''
    global headers
    headers = {**headers, **header}


def changeHtmlTimeout(timeout: int):
    ''' change html timeout '''
    global html_timeout
    html_timeout = timeout


def changeJsonTimeout(timeout: int):
    ''' change json timeout '''
    global json_timeout
    json_timeout = timeout


def begin_time() -> int:
    ''' multi-version time manage '''
    global start
    start.append(time.time())
    return len(start) - 1


def end_time_aver(version: int):
    time_spend = time.time() - start[version]
    spend_list.append(time_spend)
    echo('2|info', 'Last spend: {:.3f}s, Average spend: {:.3f}s.'.format(
        time_spend, sum(spend_list) / len(spend_list)))


def end_time(version: int, mode: int = 1):
    time_spend = time.time() - start[version]
    if mode:
        echo('2|info', '{:.3f}s'.format(time_spend))
    else:
        return time_spend


def empty():
    global spend_list
    spend_list = []


def can_retry(url: str, time: int = 3) -> bool:
    ''' judge can retry once '''
    global failure_map
    if url not in failure_map:
        failure_map[url] = 0
        return True
    elif failure_map[url] < time:
        failure_map[url] += 1
        return True
    else:
        failure_map[url] = 0
        return False


def send_email(context: str, subject: str, add_rec=None) -> bool:
    ''' send email '''

    if not os.path.exists('{}emailSend'.format(data_dir)) or not os.path.exists('{}emailRec'.format(data_dir)):
        echo('0|warning', 'email send/Rec list not exist!!!')
        return
    origin_file = [ii.split(',')
                   for ii in read_file('{}emailRec'.format(data_dir))]
    email_rec = [ii for ii, jj in origin_file if jj == '0']
    email_cc = [ii for ii, jj in origin_file if jj == '1']
    send_email_once(email_rec, email_cc, context, subject)
    if not add_rec is None:
        send_email_once(add_rec, [], context, subject)


def send_email_once(email_rec: list, email_cc: list, context: str, subject: str):
    email_send = [ii.split(',')
                  for ii in read_file('{}emailSend'.format(data_dir))]
    send_index = random.randint(0, len(email_send) - 1)
    mail_host = 'smtp.163.com'
    mail_user = email_send[send_index][0]
    mail_pass = email_send[send_index][1]
    sender = '{}@163.com'.format(mail_user)

    sign = EMAIL_SIGN % time_str(time_format='%B %d')
    message = MIMEText('{}{}'.format(context, sign), 'plain', 'utf-8')
    message['Subject'] = subject
    message['From'] = sender
    message['To'] = ', '.join(email_rec)
    message['Cc'] = ', '.join(email_cc)

    try:
        smtpObj = smtplib.SMTP_SSL(mail_host)
        smtpObj.connect(mail_host, 465)
        smtpObj.login(mail_user, mail_pass)
        smtpObj.sendmail(sender, email_rec + email_cc, message.as_string())
        smtpObj.quit()
        echo('1|warning', 'Send email success!!')
        return True
    except smtplib.SMTPException as e:
        echo('0|warning', 'Send email error', e)
        return False


def dump_bigger(data, output_file: str):
    ''' pickle.dump big file which size more than 4GB '''
    max_bytes = 2**31 - 1
    bytes_out = pickle.dumps(data, protocol=4)
    with open(output_file, 'wb') as f_out:
        for idx in range(0, len(bytes_out), max_bytes):
            f_out.write(bytes_out[idx:idx + max_bytes])


def load_bigger(input_file: str):
    ''' pickle.load big file which size more than 4GB '''
    max_bytes = 2**31 - 1
    bytes_in = bytearray(0)
    input_size = os.path.getsize(input_file)
    with open(input_file, 'rb') as f_in:
        for _ in range(0, input_size, max_bytes):
            bytes_in += f_in.read(max_bytes)
    return pickle.loads(bytes_in)


def time_str(time_stamp: int = -1, time_format: str = '%Y-%m-%d %H:%M:%S'):
    ''' time stamp -> time str '''
    if time_stamp > 0:
        return time.strftime(time_format, time.localtime(time_stamp))
    return time.strftime(time_format, time.localtime(time.time()))


def time_stamp(time_str: str, time_format: str = '%Y-%m-%d %H:%M:%S'):
    ''' time str -> time stamp '''
    return time.mktime(time.strptime(time_str, time_format))


def echo(types, *args):
    '''
    echo log -> stdout / log file
        @param: color: 0 -> red, 1 -> green, 2 -> yellow, 3 -> blue, 4 -> gray
        @param: log_type: info, warning, debug, error
        @param: is_service: bool
    '''
    args = ' '.join([str(ii) for ii in args])
    types = str(types)
    re_num = re.findall('\d', types)
    re_word = re.findall('[a-zA-Z]+', types)
    color = int(re_num[0]) if len(re_num) else 4
    log_type = re_word[0] if len(re_word) else 'info'

    if is_service:
        log(log_type, args)
        return
    colors = {'red': '\033[91m', 'green': '\033[92m',
              'yellow': '\033[93m', 'blue': '\033[94m', 'gray': '\033[90m'}
    if not color in list(range(len(colors.keys()))):
        color = 4
    if platform.system() == 'Windows':
        print(args)
    else:
        print(list(colors.values())[color], args, '\033[0m')


def shuffle_batch_run_thread(threading_list: list, batch_size: int = 24, is_await: bool = False):
    ''' shuffle batch run thread '''
    thread_num = len(threading_list)
    np.random.shuffle(threading_list)  # shuffle thread
    total_block = thread_num // batch_size + 1
    for block in range(total_block):
        for ii in threading_list[block * batch_size:min(thread_num, batch_size * (block + 1))]:
            if threading.active_count() > batch_size:
                time.sleep(random.randint(2, 4) * (random.random() + 1))
            ii.start()

        if not is_await or block % 10 == 1:
            for ii in threading_list[block * batch_size:min(thread_num, batch_size * (block + 1))]:
                ii.join()
        else:
            time.sleep(min(max(5, batch_size * 2 / 210), 10))
        echo('1|info', time_str(), '{}/{}'.format(total_block, block), 'epochs finish.',
             'One Block {} Thread '.format(batch_size))


def mkdir(origin_dir: str):
    ''' mkdir file dir'''
    if not os.path.exists(origin_dir):
        os.mkdir(origin_dir)


def read_file(read_path: str) -> list:
    ''' read file '''
    if not os.path.exists(read_path):
        return []
    with open(read_path, 'r', encoding='utf-8') as f:
        data = [ii.strip() for ii in f.readlines()]
    return data


def log(types: str, *log_args: list):
    ''' log record @param: type: {'critical', 'error', 'warning', 'info', 'debug'} '''
    mkdir(LOG_DIR)
    LOG_PATH = '{}{}.log'.format(LOG_DIR, time_str(time_format='%Y%m%d'))
    logging.basicConfig(level=logging.DEBUG,
                        filename=LOG_PATH,
                        filemode='a',
                        format='[%(asctime)s] [%(levelname)s] %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("chardet").setLevel(logging.WARNING)
    log_str = ' '.join([str(ii) for ii in log_args])
    if types == 'critical':
        logging.critical(log_str)
    elif types == 'error':
        logging.error(log_str)
    elif types == 'warning':
        logging.warning(log_str)
    elif types == 'info':
        logging.info(log_str)
    elif types == 'debug':
        logging.debug(log_str)
    else:
        logging.info("{} {}".format(types, log_str))


def decoder_url(url: str) -> dict:
    if '?' not in url:
        return {}
    return {ii.split('=', 1)[0]: ii.split('=', 1)[1] for ii in url.split('?', 1)[1].split('&') if ii != ''}


def encoder_url(url_dict: {}, origin_url: str) -> str:
    return '{}?{}'.format(origin_url, '&'.join(['{}={}'.format(ii, urllib.parse.quote(str(jj))) for ii, jj in url_dict.items()]))


def json_str(data: dict):
    ''' equal to JSON.stringify in javascript '''
    return json.dumps(data, separators=(',', ':'))


def decoder_cookie(cookie: str) -> dict:
    return {ii.split('=', 1)[0]: ii.split('=', 1)[1] for ii in cookie.split('; ')}


def encoder_cookie(cookie_dict: {}) -> str:
    return '; '.join(['{}={}'.format(ii, jj)for ii, jj in cookie_dict.items()])
