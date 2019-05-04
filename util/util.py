'''
@Author: gunjianpan
@Date:   2018-10-19 15:33:46
@Last Modified by:   gunjianpan
@Last Modified time: 2019-05-03 00:18:03
'''

import codecs
import numpy as np
import os
import pickle
import platform
import random
import requests
import smtplib
import time
import urllib3

from bs4 import BeautifulSoup
from email.mime.text import MIMEText

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
json_timeout = 5
start = []
spend_list = []
failure_map = {}
is_service = False


def basic_req(url: str, types: int, proxies=None, data=None, header=None, need_cookie: bool = False):
    """
    requests
    @types XY: X=0.->get;   =1.->post;
               Y=0.->html;  =1.->json; =2.->basic; =3.->text;
    """
    req_set(url)
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
        echo(0, types, ' type is not supported!!!')
    if need_cookie and result is None:
        return None, {}
    return result


def req_set(url: str):
    ''' req headers set '''
    global headers
    headers['Host'] = url.split('/')[2]
    index = random.randint(0, agent_len)
    headers['User-Agent'] = agent_lists[index]


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
    except:
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
    echo(2, 'Last spend: {:.3f}s, Average spend: {:.3f}s.'.format(
        time_spend, sum(spend_list) / len(spend_list)))


def end_time(version: int, mode: int = 1):
    time_spend = time.time() - start[version]
    if mode:
        echo(2, '{:.3f}s'.format(time_spend))
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


def send_email(context: str, subject: str) -> bool:
    ''' send email '''

    if not os.path.exists('{}emailSend'.format(data_dir)) or not os.path.exists('{}emailRec'.format(data_dir)):
        echo(0, 'email send/Rec list not exist!!!')
        return
    with codecs.open('{}emailSend'.format(data_dir), 'r', encoding='utf-8') as f:
        email_send = [ii.strip().split(',') for ii in f.readlines()]
    with codecs.open(data_dir + 'emailRec', 'r', encoding='utf-8') as f:
        origin_file = f.readlines()
        email_rec = [ii.strip().split(',')[0]
                     for ii in origin_file if ii.strip().split(',')[1] == '0']
        email_cc = [ii.strip().split(',')[0]
                    for ii in origin_file if ii.strip().split(',')[1] == '1']
    send_len = len(email_send)
    send_index = random.randint(0, send_len - 1)
    mail_host = 'smtp.163.com'
    mail_user = email_send[send_index][0]
    mail_pass = email_send[send_index][1]
    sender = mail_user + '@163.com'

    message = MIMEText(context, 'plain', 'utf-8')
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

        echo(1, 'Send email success!!')
        return True
    except smtplib.SMTPException as e:
        echo(0, 'Send email error', e)
        return False


def dump_bigger(data, output_file: str):
    ''' pickle.dump big file which size more than 4GB '''
    max_bytes = 2**31 - 1
    bytes_out = pickle.dumps(data, protocol=4)
    with codecs.open(output_file, 'wb') as f_out:
        for idx in range(0, len(bytes_out), max_bytes):
            f_out.write(bytes_out[idx:idx + max_bytes])


def load_bigger(input_file: str):
    ''' pickle.load big file which size more than 4GB '''
    max_bytes = 2**31 - 1
    bytes_in = bytearray(0)
    input_size = os.path.getsize(input_file)
    with codecs.open(input_file, 'rb') as f_in:
        for _ in range(0, input_size, max_bytes):
            bytes_in += f_in.read(max_bytes)
    return pickle.loads(bytes_in)


def time_str(timestamp: int = -1, format: str = '%Y-%m-%d %H:%M:%S'):
    ''' time str '''
    if timestamp > 0:
        return time.strftime(format, time.localtime(timestamp))
    return time.strftime(format, time.localtime(time.time()))


def echo(color, *args):
    ''' echo log @param: color: 0 -> error, 1 -> success, 2 -> info '''
    args = ' '.join([str(ii) for ii in args])
    if is_service:
        with open(log_path, 'a') as f:
            f.write('{}\n'.format(args))
        return
    colors = {'error': '\033[91m', 'success': '\033[94m', 'info': '\033[93m'}
    if type(color) != int or not color in list(range(len(colors.keys()))) or platform.system() == 'Windows':
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
            ii.start()
        if not is_await:
            for ii in threading_list[block * batch_size:min(thread_num, batch_size * (block + 1))]:
                ii.join()
        else:
            time.sleep(min(max(5, batch_size * 2 / 210), 10))
        echo(1, time_str(), '{}/{}'.format(total_block, block), 'epochs finish.',
             'One Block {} Thread '.format(batch_size))
