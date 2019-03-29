'''
@Author: gunjianpan
@Date:   2018-10-19 15:33:46
@Last Modified by:   gunjianpan
@Last Modified time: 2019-03-30 00:59:48
'''

import os
import pickle
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

with open('utils/data/agent', 'r') as f:
    file = f.readlines()
agent_lists = [" ".join(index.split()[1:])[1:-1] for index in file]
agent_len = len(agent_lists) - 1
html_timeout = 5
json_timeout = 5
start = []
spendList = []
failured_map = {}


def basic_req(url, types, proxies=None, data=None, header=None):
    """
    requests
    @types XY: X=0.->get;   =1.->post;
               Y=0.->html;  =1.->json; =2.->basic
    """
    req_set(url)
    result = None
    if not types:
        result = get_html(url, proxies, header)
    elif types == 1:
        result = get_json(url, proxies, header)
    elif types == 2:
        result = get_basic(url, proxies, header)
    elif types == 11:
        result = post_json(url, proxies, data, header)
    elif types == 12:
        result = post_basic(url, proxies, data, header)
    else:
        print(types, ' type is not supported!!!')
    return result


def req_set(url):
    """
    req set
    """
    global headers
    headers['Host'] = url.split('/')[2]
    index = random.randint(0, agent_len)
    headers['User-Agent'] = agent_lists[index]


def get_html(url, proxies=None, header=None):
    """
    get html
    @url requests.url
    @proxies requests.proxies
    @return beautifulSoup analysis result
    """
    # print(proxies, header)
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
    except Exception as e:
        # print('Error')
        html = '<html></html>'
    return BeautifulSoup(html, 'html.parser')


def get_json(url, proxies=None, header=None):
    """
    get json
    @url requests.url
    @proxys requests.proxys
    @return json
    """
    if header is None:
        header = headers
    try:
        return requests.get(url, headers=header, verify=False,
                            timeout=json_timeout, proxies=proxies).json()
    except Exception as e:
        return


def post_json(url, proxies=None, data=None, header=None):
    """
    post json
    @url requests.url
    @proxies requests.proxys
    @data form-data
    @return json
    """
    if header is None:
        header = headers
    try:
        return requests.post(url, headers=header, verify=False, data=data,
                             timeout=json_timeout, proxies=proxies).json()
    except Exception as e:
        return


def post_basic(url, proxies=None, data=None, header=None):
    """
    post json
    @url requests.url
    @proxies requests.proxys
    @data form-data
    @return json
    """
    if header is None:
        header = headers
    try:
        return requests.post(url, headers=header, verify=False, data=data,
                             timeout=json_timeout, proxies=proxies)
    except Exception as e:
        return


def get_basic(url, proxies=None, header=None):
    """
    get img
    @url requests.url
    @proxys requests.proxys
    @return basic
    """
    if header is None:
        header = headers
    try:
        return requests.get(url, headers=header, verify=False,
                            timeout=html_timeout, proxies=proxies)
    except Exception as e:
        return


def changeCookie(cookie):
    """
    change cookie
    """
    global headers
    headers['Cookie'] = cookie


def changeHeaders(header):
    """
    change Headers
    """
    global headers
    headers = {**headers, **header}


def changeHtmlTimeout(timeout):
    """
    change html timeout
    """
    global html_timeout
    html_timeout = timeout


def changeJsonTimeout(timeout):
    """
    change json timeout
    """
    global json_timeout
    json_timeout = timeout


def begin_time():
    """
    multi-version time manage
    """
    global start
    start.append(time.time())
    return len(start) - 1


def end_time_avage(version):
    termSpend = time.time() - start[version]
    spendList.append(termSpend)
    print(str(termSpend)[0:5] + ' ' +
          str(sum(spendList) / len(spendList))[0:5])


def end_time(version):
    termSpend = time.time() - start[version]
    print(str(termSpend)[0:5])


def spend_time(version):
    return str(time.time() - start[version])[0:5]


def empty():
    spendList = []


def can_retry(url, index=None):
    """
    judge can retry once
    """

    global failured_map

    if url not in failured_map:
        failured_map[url] = 0
        return True
    elif failured_map[url] < 2:
        failured_map[url] += 1
        return True
    else:
        failured_map[url] = 0
        return False


def send_email(context, subject):
    """
    send email
    """
    data_path = 'utils/data/'

    with open(data_path + 'emailSend', 'r') as f:
        email_send = [ii.strip().split(',') for ii in f.readlines()]
    with open(data_path + 'emailRec', 'r') as f:
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

        print('Send email success!!')
        return True
    except smtplib.SMTPException as e:
        print('Send email error', e)
        return False


def dump_bigger(data, output_file):
    """
    pickle.dump big file which size more than 4GB
    """
    max_bytes = 2**31 - 1
    bytes_out = pickle.dumps(data, protocol=4)
    with open(output_file, 'wb') as f_out:
        for idx in range(0, len(bytes_out), max_bytes):
            f_out.write(bytes_out[idx:idx + max_bytes])


def load_bigger(input_file):
    """
    pickle.load big file which size more than 4GB
    """
    max_bytes = 2**31 - 1
    bytes_in = bytearray(0)
    input_size = os.path.getsize(input_file)
    with open(input_file, 'rb') as f_in:
        for _ in range(0, input_size, max_bytes):
            bytes_in += f_in.read(max_bytes)
    return pickle.loads(bytes_in)
