# -*- coding: utf-8 -*-
# @Author: gunjianpan
# @Date:   2018-10-19 15:33:46
# @Last Modified by:   gunjianpan
# @Last Modified time: 2020-03-23 23:46:48

from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
    with_statement,
)

import codecs
import datetime
import json
import logging
import os
import pickle
import platform
import random
import re
import smtplib
import threading
import time
import urllib
from email.mime.text import MIMEText

import numpy as np
import requests
import urllib3
from bs4 import BeautifulSoup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def basic_req(
    url: str,
    types: int,
    proxies=None,
    data=None,
    header=None,
    need_cookie: bool = False,
    config: dict = {},
):
    """
    requests
    @types XY: X=0.->get;   =1.->post;
               Y=0.->html;  =1.->json; =2.->basic; =3.->text;
    """
    header = req_set(url, header)
    if "http" not in url:
        echo(
            "0|warning",
            "You should assign the type of [http]/[https] before the url str!!! The default is [http].",
        )
    if types not in [0, 1, 2, 3, 11, 12, 13]:
        echo("0|warning", types, " type is not supported!!!")
        return

    if types < 10:
        req_func = requests.get
    else:
        req_func = requests.post
    mode = types % 10
    if mode == 0:
        timeout = html_timeout
    else:
        timeout = json_timeout
    return get_basic(
        req_func, url, proxies, data, header, need_cookie, config, mode, timeout
    )


def req_set(url: str, header):
    """ req headers set """
    global headers
    headers["Host"] = url.split("/")[2]
    index = random.randint(0, agent_len)
    headers["User-Agent"] = agent_lists[index]
    if not header is None and "User-Agent" not in header:
        header["User-Agent"] = agent_lists[index]
    return header


def get_basic(
    req_func,
    url: str,
    proxies,
    data,
    header,
    need_cookie: bool,
    config: dict,
    mode: int = 0,
    timeouts: int = 5,
):
    """ basic get requests"""
    if header is None:
        header = headers
    allow_redirects = config.get("allow_redirects", True)
    timeout = config.get("timeout", timeouts)
    return_proxy = config.get("return_proxy", False)
    try:
        req = req_func(
            url,
            headers=header,
            verify=False,
            timeout=timeout,
            proxies=proxies,
            data=data,
            allow_redirects=allow_redirects,
        )
        if mode == 2:
            if return_proxy:
                return req, proxies
            return req
        elif mode == 0:
            if req.apparent_encoding == "utf-8" or "gbk" in req.apparent_encoding:
                req.encoding = req.apparent_encoding
            result = BeautifulSoup(req.text, "html.parser")
        elif mode == 1:
            result = req.json()
        elif mode == 3:
            result = req.text
        if need_cookie:
            return result, req.cookies.get_dict()
        if return_proxy:
            return result, proxies
        return result
    except:
        if mode == 3:
            result = ""
        elif mode == 0:
            result = BeautifulSoup("<html></html>", "html.parser")
        else:
            result = None
        if need_cookie:
            return result, {}
        return result


def changeCookie(cookie: str):
    """ change cookie """
    global headers
    headers["Cookie"] = cookie


def changeHeaders(header: dict):
    """ change Headers """
    global headers
    headers = {**headers, **header}


def changeHtmlTimeout(timeout: int):
    """ change html timeout """
    global html_timeout
    html_timeout = timeout


def changeJsonTimeout(timeout: int):
    """ change json timeout """
    global json_timeout
    json_timeout = timeout


def begin_time() -> int:
    """ multi-version time manage """
    global start
    start.append(time_stamp())
    return len(start) - 1


def end_time_aver(version: int):
    time_spend = time_stamp() - start[version]
    spend_list.append(time_spend)
    echo(
        "2|info",
        "Last spend: {:.3f}s, Average spend: {:.3f}s.".format(
            time_spend, sum(spend_list) / len(spend_list)
        ),
    )


def end_time(version: int, mode: int = 1):
    time_spend = time_stamp() - start[version]
    if not mode:
        return time_spend
    time_spend = get_time_str(time_spend)
    if mode == 2:
        echo("2|info", time_spend)
    return time_spend


def empty():
    global spend_list
    spend_list = []


def can_retry(url: str, time: int = 3) -> bool:
    """ judge can retry once """
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


def send_email(context: str, subject: str, add_rec=None, assign_rec=None) -> bool:
    """ send email """

    if not os.path.exists("{}emailSend".format(data_dir)) or not os.path.exists(
        "{}emailRec".format(data_dir)
    ):
        echo("0|warning", "email send/Rec list not exist!!!")
        return
    origin_file = [ii.split(",") for ii in read_file("{}emailRec".format(data_dir))]
    email_rec = [ii for ii, jj in origin_file if jj == "0"]
    email_cc = [ii for ii, jj in origin_file if jj == "1"]
    if assign_rec is not None:
        email_rec = assign_rec
    send_email_once(email_rec, email_cc, context, subject)
    if not add_rec is None:
        send_email_once(add_rec, [], context, subject)


def send_email_once(email_rec: list, email_cc: list, context: str, subject: str):
    email_send = [ii.split(",") for ii in read_file("{}emailSend".format(data_dir))]
    send_index = random.randint(0, len(email_send) - 1)
    mail_host = "smtp.163.com"
    mail_user = email_send[send_index][0]
    mail_pass = email_send[send_index][1]
    sender = "{}@163.com".format(mail_user)

    sign = EMAIL_SIGN % time_str(time_format="%B %d")
    message = MIMEText("{}{}".format(context, sign), "plain", "utf-8")
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = ", ".join(email_rec)
    message["Cc"] = ", ".join(email_cc)

    try:
        smtpObj = smtplib.SMTP_SSL(mail_host)
        smtpObj.connect(mail_host, 465)
        smtpObj.login(mail_user, mail_pass)
        smtpObj.sendmail(sender, email_rec + email_cc, message.as_string())
        smtpObj.quit()
        echo("1|warning", "Send email success!!")
        return True
    except smtplib.SMTPException as e:
        echo("0|warning", "Send email error", e)
        return False


def dump_bigger(data, output_file: str):
    """ pickle.dump big file which size more than 4GB """
    max_bytes = 2 ** 31 - 1
    bytes_out = pickle.dumps(data, protocol=4)
    with open(output_file, "wb") as f_out:
        for idx in range(0, len(bytes_out), max_bytes):
            f_out.write(bytes_out[idx : idx + max_bytes])


def load_bigger(input_file: str):
    """ pickle.load big file which size more than 4GB """
    max_bytes = 2 ** 31 - 1
    bytes_in = bytearray(0)
    input_size = os.path.getsize(input_file)
    with open(input_file, "rb") as f_in:
        for _ in range(0, input_size, max_bytes):
            bytes_in += f_in.read(max_bytes)
    return pickle.loads(bytes_in)


def time_str(time_s: int = -1, time_format: str = "%Y-%m-%d %H:%M:%S"):
    """ time stamp -> time str """
    if time_s > 0:
        return time.strftime(time_format, time.localtime(time_s))
    return time.strftime(time_format, time.localtime(time_stamp()))


def time_stamp(time_str: str = "", time_format: str = "%Y-%m-%d %H:%M:%S") -> float:
    """ time str -> time stamp """
    if not len(time_str):
        return time.time()
    return time.mktime(time.strptime(time_str, time_format))


def echo(types, *args):
    """
    echo log -> stdout / log file
        @param: color: 0 -> red, 1 -> green, 2 -> yellow, 3 -> blue, 4 -> gray
        @param: log_type: info, warning, debug, error
        @param: is_service: bool
    """
    args = " ".join([str(ii) for ii in args])
    types = str(types)
    re_num = re.findall("\d", types)
    re_word = re.findall("[a-zA-Z]+", types)
    color = int(re_num[0]) if len(re_num) else 4
    log_type = re_word[0] if len(re_word) else "info"

    if is_service:
        log(log_type, args)
        return
    colors = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "gray": "\033[90m",
    }
    if not color in list(range(len(colors.keys()))):
        color = 4
    if platform.system() == "Windows":
        print(args)
    else:
        print(list(colors.values())[color], args, "\033[0m")


def shuffle_batch_run_thread(
    threading_list: list, batch_size: int = 24, is_await: bool = False
):
    """ shuffle batch run thread """
    thread_num = len(threading_list)
    np.random.shuffle(threading_list)  # shuffle thread
    total_block = thread_num // batch_size + 1
    for block in range(total_block):
        for ii in threading_list[
            block * batch_size : min(thread_num, batch_size * (block + 1))
        ]:
            if threading.active_count() > batch_size:
                time.sleep(random.randint(2, 4) * (random.random() + 1))
            ii.start()

        if not is_await or block % 10 == 1:
            for ii in threading_list[
                block * batch_size : min(thread_num, batch_size * (block + 1))
            ]:
                ii.join()
        else:
            time.sleep(min(max(5, batch_size * 2 / 210), 10))
        echo(
            "1|info",
            time_str(),
            "{}/{}".format(total_block, block),
            "epochs finish.",
            "One Block {} Thread ".format(batch_size),
        )


def mkdir(origin_dir: str):
    """ mkdir file dir"""
    if not os.path.exists(origin_dir):
        os.mkdir(origin_dir)


def read_file(read_path: str, mode: int = 0):
    """ read file """
    if not os.path.exists(read_path):
        return [] if not mode else ""
    with open(read_path, "r", encoding="utf-8", newline="\n") as f:
        if not mode:
            data = [ii.strip() for ii in f.readlines()]
        elif mode == 1:
            data = f.read()
        elif mode == 2:
            data = list(f.readlines())
    return data


def log(types: str, *log_args: list):
    """ log record @param: type: {'critical', 'error', 'warning', 'info', 'debug'} """
    mkdir(LOG_DIR)
    LOG_PATH = "{}{}.log".format(LOG_DIR, time_str(time_format="%Y%m%d"))
    logging.basicConfig(
        level=logging.DEBUG,
        filename=LOG_PATH,
        filemode="a",
        format="[%(asctime)s] [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("chardet").setLevel(logging.WARNING)
    log_str = " ".join([str(ii) for ii in log_args])
    if types == "critical":
        logging.critical(log_str)
    elif types == "error":
        logging.error(log_str)
    elif types == "warning":
        logging.warning(log_str)
    elif types == "info":
        logging.info(log_str)
    elif types == "debug":
        logging.debug(log_str)
    else:
        logging.info("{} {}".format(types, log_str))


def decoder_url(url: str, do_decoder: bool = False) -> dict:
    if "?" not in url:
        return {}
    decoder_dict = {
        ii.split("=", 1)[0]: ii.split("=", 1)[1]
        for ii in url.split("?", 1)[1].split("&")
        if ii != ""
    }
    if do_decoder:
        decoder_dict = {
            key: urllib.parse.unquote(value) for key, value in decoder_dict.items()
        }
    return decoder_dict


def encoder_url(url_dict: {}, origin_url: str) -> str:
    return "{}?{}".format(
        origin_url,
        "&".join(
            [
                "{}={}".format(ii, urllib.parse.quote(str(jj)))
                for ii, jj in url_dict.items()
            ]
        ),
    )


def json_str(data: dict):
    """ equal to JSON.stringify in javascript """
    return json.dumps(data, separators=(",", ":"))


def decoder_cookie(cookie: str) -> dict:
    return {ii.split("=", 1)[0]: ii.split("=", 1)[1] for ii in cookie.split("; ")}


def encoder_cookie(cookie_dict: {}) -> str:
    return "; ".join(["{}={}".format(ii, jj) for ii, jj in cookie_dict.items()])


def get_time_str(time_gap: int, is_gap: bool = True) -> str:
    if not is_gap:
        time_gap = int(time_gap // 60)
    day = int(time_gap // 1440)
    hour = int(time_gap / 60) % 24
    minute = int(time_gap % 60)
    result = ""
    if day:
        result += "{}Day ".format(day)
    if hour:
        result += "{:02d}h ".format(hour)
    if minute:
        if day and not hour:
            result += "{:02d}h ".format(hour)
        result += "{:02d}min".format(minute)
    return result.strip()


def get_min_s(t: str) -> str:
    t = float(t)
    m = int(t // 60)
    s = int(t % 60)
    return "{:02d}:{:02d}".format(m, s)


def replace_params(origin_str: str, reg: str) -> str:
    """ replace params """
    params_re = re.findall(reg, origin_str)
    params = {}
    for ii in params_re:
        if not ii in params:
            params[ii] = len(params)
    for ii in sorted(list(params.keys()), key=lambda i: -len(i)):
        origin_str = origin_str.replace(ii, f"a{params[ii]}")
    return origin_str


def decoder_fuzz(reg: str, file_path: str, replace_func=replace_params):
    """ simple decoder of fuzz file """
    file_dir, file_name = os.path.split(file_path)
    origin_str = read_file(file_path, mode=1)
    origin_str = codecs.unicode_escape_decode(origin_str)[0]
    origin_str = replace_func(origin_str, reg)
    name1, name2 = file_name.split(".", 1)
    output_path = f"{file_dir}/{name1}_decoder.{name2}"
    echo(
        1,
        "decoder fuzz file {} -> {}, total {} line.".format(
            file_name, output_path, origin_str.count("\n")
        ),
    )
    with open(output_path, "w") as f:
        f.write(origin_str)


def get_accept(types: str) -> str:
    """ @param: types => html, json, xhr """
    if types == "html":
        return "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9"
    elif types == "json":
        return "application/json, text/javascript, */*; q=0.01"
    elif types == "xhr":
        return "application/json, text/plain, */*"
    return "*/*"


def get_use_agent(types: str = "pc") -> str:
    """ @param: types => pc, mobile"""
    if types == "pc":
        return "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3682.0 Safari/537.36"
    return "Mozilla/5.0 (iPhone; CPU iPhone OS 11_0 like Mac OS X) AppleWebKit/604.1.38 (KHTML, like Gecko) Version/11.0 Mobile/15A372 Safari/604.1"


def get_content_type(types: str = "utf8") -> str:
    return "application/x-www-form-urlencoded{}".format(
        ";charset=UTF-8" if types == "utf8" else ""
    )


def change_pic_size(picture_path: str, resize: tuple = (600, 600)):
    import cv2
    if not os.path.exists(picture_path):
        echo(0, "picture not found in", picture_path)
        return
    pic = cv2.imread(picture_path)
    pic = cv2.resize(pic, resize)
    split_text = os.path.splitext(picture_path)
    output_path = "{}_resize{}".format(*split_text)
    cv2.imwrite(output_path, pic)


headers = {
    "Cookie": "",
    "Accept": get_accept("html"),
    "Content-Type": get_content_type(),
    "User-Agent": get_use_agent(),
}
data_dir = "util/data/"
log_path = "service.log"
mkdir(data_dir)
agent_lists = [
    " ".join(index.split()[1:])[1:-1] for index in read_file("{}agent".format(data_dir))
]
if not len(agent_lists):
    agent_lists = [headers["User-Agent"]]

agent_len = len(agent_lists) - 1
html_timeout = 5
json_timeout = 4
start = []
spend_list = []
failure_map = {}
is_service = False
LOG_DIR = "log/"
EMAIL_SIGN = "\n\n\nBest wish!!\n%s\n\n————————————————————\n• Send from script designed by gunjianpan."
