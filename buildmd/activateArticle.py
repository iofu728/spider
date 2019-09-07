# -*- coding: utf-8 -*-
# @Author: gunjianpan
# @Date:   2019-08-26 20:46:29
# @Last Modified by:   gunjianpan
# @Last Modified time: 2019-09-08 02:12:13

import hashlib
import json
import os
import sys
import threading
import time
import urllib
from concurrent.futures import ThreadPoolExecutor, as_completed
from configparser import ConfigParser

import regex
sys.path.append(os.getcwd())
from proxy.getproxy import GetFreeProxy
from util.util import (basic_req, begin_time, can_retry, changeHeaders,
                       changeJsonTimeout, decoder_url, echo, encoder_cookie,
                       encoder_url, end_time, headers, json_str, mkdir,
                       read_file, send_email, time_stamp, time_str)

proxy_req = GetFreeProxy().proxy_req
root_dir = os.path.abspath('buildmd')
assign_path = os.path.join(root_dir, 'tbk.ini')


class ActivateArticle(object):
    ''' activate article in youdao Cloud'''
    HOME_ID = '3bb0c25eca85e764b6d55a281faf7195'
    UNLOGGED_ID = '8ce21d52-5f01-a247-bb7e-3263ecd8c272'
    Y_URL = 'https://note.youdao.com/'
    SHARE_URL = '{}ynoteshare1/index.html?id=%s&type=note'.format(Y_URL)
    NOTE_URL = '{}yws/public/note/%s?editorType=0&unloginId={}'.format(
        Y_URL, UNLOGGED_ID)
    ULAND_URL = 'https://uland.taobao.com/coupon/edetail?e=07BoqTjt6FoGQASttHIRqReJUgbXBbJr2j5o6AqsuM5Um%2Fg8xRLmNu9y76MhKVDMLu9BHulqqhbAiOpWRpNCvQeVsp3llNhDDfqEFBOhTcw%2BMyFk2I2hI7MVuRZAQ2GQ6KS1OlRFp695PSSvs%2FN10Z%2FOC1D%2Bu8PCBJnqsdjteNeeSq6h8MKodLCSyLFw4qsuJ47rYvIjaE20%2Bc5Gzwi6gW5us6IkMHWUriP63lKgYyrom9kMiklcP%2FMgbS%2F5f07N&scm=20140618.1.01010001.s101c6'
    DECODER_TPWD_URL = 'http://www.taokouling.com/index/taobao_tkljm'
    MTOP_URL = 'https://h5api.m.taobao.com/h5/mtop.alimama.union.xt.en.api.entry/1.0/'
    JSON_KEYS = ['p', 'ct', 'su', 'pr', 'au', 'pv',
                 'mt', 'sz', 'domain', 'tl', 'content']
    URL_DOMAIN = {5: 'uland.taobao.com',
                  0: 's.click.taobao.com',
                  10: 'taoquan.taobao.com',
                  1: 'item.taobao.com'}
    NEED_KEY = ['content', 'url', 'validDate']
    ONE_HOURS = 3600
    ONE_DAY = 24
    M = '_m_h5_tk'
    BASIC_STAMP = time_stamp(time_format='%d天%H小时%M分%S秒',
                             time_str='1天0小时0分0秒') - ONE_DAY * ONE_HOURS

    def __init__(self):
        self.tpwd_map = {}
        self.tpwds = {}
        self.cookies = {}
        self.tpwd_exec = ThreadPoolExecutor(max_workers=10)
        self.load_configure()
        self.load_ids()
        self.get_m_h5_tk()

    def load_configure(self):
        cfg = ConfigParser()
        cfg.read(assign_path, 'utf-8')
        self.appkey = cfg.get('basic', 'appkey')
        self.secret = cfg.get('basic', 'secret')
        self.user_id = cfg.get('basic', 'user_id')
        self.site_id = cfg.get('basic', 'site_id')
        self.adzone_id = cfg.get('basic', 'adzone_id')

    def load_ids(self):
        changeJsonTimeout(5)
        req = self.basic_youdao(self.HOME_ID)
        if req is None:
            echo('0|error', 'Get The Home Page Info Error!!! Please retry->->->')
            return
        self.idx = regex.findall('id=(\w*?)<', req)
        if len(self.idx) < 30:
            echo('0|error', 'The Num of id is error!! Please check it.')
            return

    def basic_youdao(self, idx: str, use_proxy: bool = True):
        url = self.NOTE_URL % idx
        refer_url = self.SHARE_URL % idx
        headers = {
            'Accept': '*/*',
            'Referer': refer_url,
            'X-Requested-With': 'XMLHttpRequest',
        }
        if use_proxy:
            req = proxy_req(url, 1, header=headers)
        else:
            req = basic_req(url, 1, header=headers)
        if req is None or list(req.keys()) != self.JSON_KEYS:
            if can_retry(url):
                echo(2, 'retry')
                return self.basic_youdao(idx)
            else:
                echo(1, 'retry upper time')
                return ''
        else:
            echo(3, 'return result')
            return req['content']

    def load_article(self, article_id: int):
        article = self.basic_youdao(article_id)
        tpwds = list(set(regex.findall('\p{Sc}(\w{8,12}?)\p{Sc}', article)))
        self.tpwds[article_id] = tpwds
        if not article_id in self.tpwd_map:
            self.tpwd_map[article_id] = {}
        time = 0
        while len(self.tpwd_map[article_id]) < len(tpwds) and time < 5:
            thread_list = [ii for ii in tpwds
                           if not ii in self.tpwd_map[article_id]]
            echo(1, article_id, 'tpwds len:', len(tpwds),
                 'need load', len(thread_list))
            thread_list = [self.tpwd_exec.submit(self.decoder_tpwd_once,
                                                 article_id, ii) for ii in thread_list]
            list(as_completed(thread_list))
            time += 1

    def decoder_tpwd_once(self, article_id: str, tpwd: str):
        req = self.decoder_tpwd(tpwd)
        if req is None or not 'data' in req or '!DOCTYPE html' in req:
            return
        req = req['data']
        temp_map = {ii: req[ii] for ii in self.NEED_KEY}
        temp_map['validDate'] = time_stamp(time_format='%d天%H小时%M分%S秒',
                                           time_str=req['validDate']) - self.BASIC_STAMP + time.time()
        self.tpwd_map[article_id][tpwd] = temp_map
        tpwd_type, item_id = self.analysis_tpwd_url(temp_map['url'])
        temp_map['type'] = tpwd_type
        temp_map['item_id'] = item_id
        if tpwd_type < 20:
            echo(2, 'Domain:', self.URL_DOMAINR[tpwd_type],
                 'item id:', item_id)
        self.tpwd_map[article_id][tpwd] = temp_map

    def analysis_tpwd_url(self, url: str):
        if self.URL_DOMAIN[0] in url:
            return 5, self.get_uland_url(url)
        elif self.URL_DOMAIN[1] in url:
            return 0, self.get_s_click_url(url)
        elif self.URL_DOMAIN[2] in url:
            return 10, 0
        elif self.URL_DOMAIN[3] in url:
            return 1, self.get_item_detail(url)
        echo('0|warning', 'New Domain:',
             regex.findall('https://(.*?)/', url), url)
        return 20, 0

    def decoder_tpwd(self, tpwd: str):
        ''' decoder the tpwd from taokouling '''
        headers = {
            'Referer': 'http://www.taokouling.com/index/taobao_tkljm',
            'X-Requested-With': 'XMLHttpRequest'
        }
        text = {'text': '￥{}￥'.format(tpwd)}
        req = proxy_req(self.DECODER_TPWD_URL, 11, data=text, header=headers)
        if req is None or not '!DOCTYPE html' in req:
            print(req)
        if req is None or not 'data' in req or '!DOCTYPE html' in req:
            if can_retry(tpwd):
                return self.decoder_tpwd(tpwd)
            else:
                return {}
        return req

    def get_s_click_url(self, s_click_url: str):
        ''' decoder s.click real jump url @validation time: 2019.08.31'''
        req = proxy_req(s_click_url, 2)
        if req is None:
            if can_retry(s_click_url):
                return self.get_s_click_url(s_click_url)
            else:
                return
        tu_url = req.url
        qso = decoder_url(tu_url)
        redirect_url = urllib.parse.unquote(qso['tu'])
        return self.get_s_click_detail(redirect_url, tu_url)

    def get_s_click_detail(self, redirect_url: str, tu_url: str):
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3',
            'referer': tu_url
        }
        req = proxy_req(redirect_url, 2, header=headers)
        if req is None:
            if can_retry(redirect_url):
                return self.get_s_click_detail(redirect_url, tu_url)
            else:
                return
        return self.get_item_detail(req.url)

    def get_item_detail(self, item_url: str):
        item = decoder_url(item_url)
        return item['id']

    def get_uland_url(self, uland_url: str):
        if not self.M in self.cookies or time.time() - self.m_time > self.ONE_HOURS / 2:
            self.get_m_h5_tk()
        s_req = self.get_uland_url_once(uland_url, self.cookies)
        req_text = s_req.text
        re_json = json.loads(req_text[req_text.find('{'): -1])
        return re_json['data']['resultList'][0]['itemId']

    def get_m_h5_tk(self):
        self.m_time = time.time()
        req = self.get_uland_url_once(self.ULAND_URL)
        self.cookies = req.cookies.get_dict()

    def get_uland_url_once(self, uland_url: str, cookies: dict = {}):
        ''' tb h5 api @2019.9.7 ✔️Tested'''
        step = self.M in cookies
        uland_params = decoder_url(uland_url)
        headers = {'referer': uland_url}
        if step:
            headers['Cookie'] = encoder_cookie(cookies)
        tt = json_str({
            'floorId': '13193' if step else '13052',
            'variableMap': json_str({
                'taoAppEnv': '0',
                'e': uland_params['e'],
                'scm': uland_params['scm']
            })})
        appkey = '12574478'

        token = cookies[self.M].split('_')[0] if step else ''
        t = int(time.time() * 1000)
        data = {
            'jsv': '2.4.0',
            'appKey': appkey,
            't': t,
            'sign': self.get_tb_h5_token(token, appkey, tt, t),
            'api': 'mtop.alimama.union.xt.en.api.entry',
            'v': 1.0,
            'timeout': 20000,
            'AntiCreep': True,
            'AntiFlood': True,
            'type': 'jsonp',
            'dataType': 'jsonp',
            'callback': 'mtopjsonp{}'.format(int(step) + 1),
            'data': tt
        }
        mtop_url = encoder_url(data, self.MTOP_URL)
        req = proxy_req(mtop_url, 2, header=headers)
        if req is None:
            if can_retry(mtop_url):
                return self.get_uland_url_once(uland_url, cookies)
            else:
                return
        return req

    def get_tb_h5_token(self, token: str, appkey: str, data: str, t: int):
        md5 = hashlib.md5()
        wait_enc = '&'.join([token, str(t), appkey, data])
        md5.update(wait_enc.encode())
        return md5.hexdigest()
