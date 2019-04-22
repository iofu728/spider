'''
@Author: gunjianpan
@Date:   2018-10-19 15:33:46
@Last Modified by:   gunjianpan
@Last Modified time: 2019-04-20 16:37:26
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
data_dir = 'utils/data/'
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


def basic_req(url: str, types: int, proxies=None, data=None, header=None):
    """
    requests
    @types XY: X=0.->get;   =1.->post;
               Y=0.->html;  =1.->json; =2.->basic; =3.->text;
    """
    req_set(url)
    result = None
    if not types:
        result = get_html(url, proxies, header)
    elif types == 1:
        result = get_json(url, proxies, header)
    elif types == 2:
        result = get_basic(url, proxies, header)
    elif types == 3:
        result = get_text(url, proxies, header)
    elif types == 11:
        result = post_json(url, proxies, data, header)
    elif types == 12:
        result = post_basic(url, proxies, data, header)
    elif types == 13:
        result = post_text(url, proxies, data, header)
    else:
        echo(0, types, ' type is not supported!!!')
    return result


def req_set(url: str):
    ''' req headers set '''
    global headers
    headers['Host'] = url.split('/')[2]
    index = random.randint(0, agent_len)
    headers['User-Agent'] = agent_lists[index]


def get_html(url: str, proxies=None, header=None):
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
        html = html.text
    except:
        html = '<html></html>'
    return BeautifulSoup(html, 'html.parser')


def get_json(url: str, proxies=None, header=None):
    ''' get json @return dict '''
    if header is None:
        header = headers
    try:
        return requests.get(url, headers=header, verify=False,
                            timeout=json_timeout, proxies=proxies).json()
    except:
        return


def post_json(url: str, proxies=None, data=None, header=None):
    ''' post json @return dict '''
    if header is None:
        header = headers
    try:
        return requests.post(url, headers=header, verify=False, data=data,
                             timeout=json_timeout, proxies=proxies).json()
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


def get_text(url: str, proxies=None, header=None) -> str:
    ''' get text '''
    if header is None:
        header = headers
    try:
        req = requests.get(url, headers=header, verify=False,
                           timeout=html_timeout, proxies=proxies)
        ''' change encoding '''
        req.encoding = req.apparent_encoding
        return req.text
    except:
        return ''


def post_text(url: str, proxies=None, header=None, data=None) -> str:
    ''' post text '''
    if header is None:
        header = headers
    try:
        return requests.post(url, headers=header, verify=False, data=data,
                             timeout=html_timeout, proxies=proxies).text
    except:
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


def can_retry(url: str, index=None) -> bool:
    ''' judge can retry once '''
    global failure_map
    if url not in failure_map:
        failure_map[url] = 0
        return True
    elif failure_map[url] < 2:
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


def echo(color, *args, is_service=False):
    ''' echo log @param: color: 0 -> error, 1 -> success, 2 -> info '''
    if is_service:
        return
    colors = {'error': '\033[91m', 'success': '\033[94m', 'info': '\033[93m'}
    args = ' '.join([str(ii) for ii in args])
    if type(color) != int or not color in list(range(len(colors.keys()))) or platform.system() == 'Windows':
        print(args)
    else:
        print(list(colors.values())[color], args, '\033[0m')


def shuffle_batch_run_thread(threading_list: list, batch_size=24):
    ''' shuffle batch run thread '''
    thread_num = len(threading_list)
    np.random.shuffle(threading_list)  # shuffle thread
    for block in range(thread_num // batch_size + 1):
        for ii in threading_list[block * batch_size:min(thread_num, batch_size * (block + 1))]:
            ii.start()
        for ii in threading_list[block * batch_size:min(thread_num, batch_size * (block + 1))]:
            ii.join()
