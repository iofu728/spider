# -*- coding: utf-8 -*-
# @Author: gunjianpan
# @Date:   2019-08-26 20:46:29
# @Last Modified by:   gunjianpan
# @Last Modified time: 2019-09-22 22:18:33

import hashlib
import json
import os
import sys
import threading
import time
import urllib
from concurrent.futures import ThreadPoolExecutor, as_completed
from configparser import ConfigParser

import numpy as np
import regex

sys.path.append(os.getcwd())
import top
from proxy.getproxy import GetFreeProxy
from util.db import Db
from util.util import (basic_req, begin_time, can_retry, changeHeaders,
                       changeJsonTimeout, decoder_cookie, decoder_url, echo,
                       encoder_cookie, encoder_url, end_time, headers,
                       json_str, mkdir, read_file, send_email, time_stamp,
                       time_str)


proxy_req = GetFreeProxy().proxy_req
root_dir = os.path.abspath('buildmd')
assign_path = os.path.join(root_dir, 'tbk.ini')


class TBK(object):
    ''' tbk info class '''
    CSTK_KEY = 'YNOTE_CSTK'

    def __init__(self):
        super(TBK, self).__init__()
        self.items = {}
        self.load_configure()
        self.load_tbk_info()

    def load_configure(self):
        cfg = ConfigParser()
        cfg.read(assign_path, 'utf-8')
        self.appkey = cfg.get('TBK', 'appkey')
        self.secret = cfg.get('TBK', 'secret')
        self.user_id = cfg.getint('TBK', 'user_id')
        self.site_id = cfg.getint('TBK', 'site_id')
        self.adzone_id = cfg.getint('TBK', 'adzone_id')
        self.home_id = cfg.get('YNOTE', 'home_id')
        self.uland_url = cfg.get('TBK', 'uland_url')
        self.unlogin_id = cfg.get('YNOTE', 'unlogin_id')
        self.cookie = cfg.get('YNOTE', 'cookie')[1:-1]
        cookie_de = decoder_cookie(self.cookie)
        self.cstk = cookie_de[self.CSTK_KEY] if self.CSTK_KEY in cookie_de else ''
        top.setDefaultAppInfo(self.appkey, self.secret)

    def load_tbk_info(self):
        favorites = self.get_uatm_favor()
        for ii in favorites:
            self.get_uatm_detail(ii)

    def get_uatm_favor(self):
        req = top.api.TbkUatmFavoritesGetRequest()
        req.page_no = 1
        req.page_size = 30
        req.fields = 'favorites_id'
        uatm_favor = req.getResponse()
        favorites = uatm_favor['tbk_uatm_favorites_get_response']['results']['tbk_favorites']
        favorites = [ii['favorites_id'] for ii in favorites]
        return favorites

    def get_uatm_detail(self, favorites_id: int):
        req = top.api.TbkUatmFavoritesItemGetRequest()
        req.adzone_id = self.adzone_id
        req.favorites_id = favorites_id
        req.page_size = 200
        req.fields = 'num_iid, title, reserve_price, zk_final_price, user_type, provcity, item_url, click_url, volume, tk_rate, zk_final_price_wap, shop_title, event_start_time, event_end_time, type, status, coupon_click_url, coupon_end_time, coupon_info, coupon_start_time, coupon_total_count, coupon_remain_count'
        try:
            item = req.getResponse()
            item = item['tbk_uatm_favorites_item_get_response']['results']['uatm_tbk_item']
            items = {ii['num_iid']: ii for ii in item}
            self.items = {**self.items, **items}
        except Exception as e:
            echo(0, favorites_id, 'favorite error', e)


class ActivateArticle(TBK):
    ''' activate article in youdao Cloud'''
    Y_URL = 'https://note.youdao.com/'
    WEB_URL = f'{Y_URL}web/'
    SYNC_URL = f'{Y_URL}yws/api/personal/sync?method=%s&keyfrom=web&cstk=%s'
    NOTE_URL = f'{Y_URL}yws/public/note/%s?editorType=0&unloginId=%s'
    SHARE_URL = f'{Y_URL}ynoteshare1/index.html?id=%s&type=note'
    LISTRECENT_URL = f'{Y_URL}yws/api/personal/file?method=listRecent&offset=%d&limit=30&keyfrom=web&cstk=%s'
    DECODER_TPWD_URL = 'http://www.taokouling.com/index/taobao_tkljm'
    Y_DOC_JS_URL = 'https://shared-https.ydstatic.com/ynote/ydoc/index-6f5231c139.js'
    MTOP_URL = 'https://h5api.m.taobao.com/h5/mtop.alimama.union.xt.en.api.entry/1.0/'
    S_LIST_SQL = 'SELECT `id`, article_id, title, q, created_at from article;'
    I_LIST_SQL = 'INSERT INTO article (article_id, title, q) VALUES %s;'
    R_LIST_SQL = 'REPLACE INTO article (`id`, article_id, title, q, is_deleted, created_at) VALUES %s;'
    S_ARTICLE_SQL = 'SELECT `id`, article_id, tpwd_id, item_id, tpwd, domain, content, url, expire_at, created_at from article_tpwd WHERE `article_id` = "%s";'
    I_ARTICLE_SQL = 'INSERT INTO article_tpwd (article_id, tpwd_id, item_id, tpwd, domain, content, url, expire_at) VALUES %s;'
    R_ARTICLE_SQL = 'REPLACE INTO article_tpwd (`id`, article_id, tpwd_id, item_id, tpwd, domain, content, url, expire_at, created_at, is_deleted) VALUES %s;'
    END_TEXT = '</text><inline-styles/><styles/></para></body></note>'
    JSON_KEYS = ['p', 'ct', 'su', 'pr', 'au', 'pv',
                 'mt', 'sz', 'domain', 'tl', 'content']
    URL_DOMAIN = {0: 's.click.taobao.com',
                  1: 'item.taobao.com',
                  5: 'uland.taobao.com',
                  10: 'taoquan.taobao.com',
                  15: 'empty'}
    NEED_KEY = ['content', 'url', 'validDate']
    ONE_HOURS = 3600
    ONE_DAY = 24
    M = '_m_h5_tk'
    ZERO_STAMP = '0天0小时0分0秒'
    BASIC_STAMP = time_stamp(time_format='%d天%H小时%M分%S秒',
                             time_str='1天0小时0分0秒') - ONE_DAY * ONE_HOURS

    def __init__(self):
        super(ActivateArticle, self).__init__()
        self.Db = Db('tbk')
        self.Db.create_table(os.path.join(root_dir, 'tpwd.sql'))
        self.Db.create_table(os.path.join(root_dir, 'article.sql'))
        self.tpwd_map = {}
        self.tpwd_db_map = {}
        self.tpwds = {}
        self.cookies = {}
        self.article = {}
        self.list_recent = {}
        self.empty_content = ''
        self.tpwd_exec = ThreadPoolExecutor(max_workers=50)

    def load_process(self):
        self.load_ids()
        self.get_m_h5_tk()
        self.get_ynote_file()
        self.get_ynote_file(1)

    def load_ids(self):
        changeJsonTimeout(5)
        req, _, _ = self.basic_youdao(self.home_id)
        if req is None:
            echo('0|error', 'Get The Home Page Info Error!!! Please retry->->->')
            return
        self.idx = regex.findall('id=(\w*?)<', req)
        if len(self.idx) < 30:
            echo('0|error', 'The Num of id is error!! Please check it.')
        else:
            echo(1, 'Load Article List {} items.'.format(len(self.idx)))

    def basic_youdao(self, idx: str, use_proxy: bool = True):
        url = self.NOTE_URL % (idx, self.unlogin_id)
        refer_url = self.SHARE_URL % idx
        headers = {
            'Accept': '*/*',
            'Referer': refer_url,
            'X-Requested-With': 'XMLHttpRequest',
        }
        req_req = proxy_req if use_proxy else basic_req
        req = req_req(url, 1, header=headers)
        if req is None or list(req.keys()) != self.JSON_KEYS:
            if can_retry(url):
                echo(2, 'retry')
                return self.basic_youdao(idx)
            else:
                echo(1, 'retry upper time')
                return '', '', ''
        return req['content'], req['tl'], req['p']

    def load_article_pipeline(self):
        article_exec = ThreadPoolExecutor(max_workers=5)
        a_list = [article_exec.submit(self.load_article, ii)
                  for ii in self.idx]
        list(as_completed(a_list))
        self.load_list2db()

    def load_article(self, article_id: str):
        article, tl, q = self.basic_youdao(article_id)
        if article_id not in self.tpwds:
            tpwds = list(set(regex.findall('\p{Sc}(\w{8,12}?)\p{Sc}', article)))
            self.tpwds[article_id] = tpwds
        else:
            tpwds = self.tpwds[article_id]
        if article_id not in self.tpwd_map:
            self.tpwd_map[article_id] = {}
        time = 0
        au_list = []
        if len(q):
            self.article[article_id] = (tl, q)
        while len(self.tpwd_map[article_id]) < len(tpwds) and time < 5:
            thread_list = [ii for ii in tpwds
                           if not ii in self.tpwd_map[article_id]]
            echo(1, article_id, 'tpwds len:', len(tpwds),
                 'need load', len(thread_list))
            thread_list = [self.tpwd_exec.submit(self.decoder_tpwd_once,
                                                 article_id, ii) for ii in thread_list]
            list(as_completed(thread_list))
            au_list.extend([self.tpwd_exec.submit(self.decoder_tpwd_url,
                                                  article_id, ii) for ii, jj in self.tpwd_map[article_id].items()
                            if not 'type' in jj or jj['item_id'] is None])
            time += 1
        list(as_completed(au_list))
        self.load_article2db(article_id)

    def load_list2db(self):
        exist_map = self.get_exist_list()
        insert_list, update_list = [], []
        for ii, jj in self.article.items():
            if ii in exist_map:
                t = exist_map[ii]
                update_list.append((t[0], ii, jj[0], jj[1], 0, t[-1]))
            else:
                insert_list.append((ii, jj[0], jj[1]))
        self.update_db(insert_list, 'Insert Article List', 1)
        self.update_db(update_list, 'Update Article List', 1)

    def get_exist_list(self):
        exist_list = self.Db.select_db(self.S_LIST_SQL)
        exist_map = {}
        for ii, jj in enumerate(exist_list):
            t = jj[-1].strftime('%Y-%m-%d %H:%M:%S')
            exist_map[ii[1]] = (*jj[:-1], t)
        self.exist_map = exist_map
        return exist_map

    def load_article2db(self, article_id: str):
        m = self.tpwd_map[article_id]
        exist_list = self.get_article_db(article_id)
        for ii, jj in enumerate(exist_list):
            t = jj[-1].strftime('%Y-%m-%d %H:%M:%S')
            exist_list[ii] = (*jj[:-1], t)
        self.tpwd_db_map[article_id] = {ii[2]: ii for ii in exist_list}
        data = [(article_id, ii, m[jj]['item_id'], jj, m[jj]['type'], m[jj]['content'], m[jj]['url'], str(int(m[jj]['validDate'])))
                for ii, jj in enumerate(self.tpwds[article_id]) if jj in m and 'item_id' in m[jj] and m[jj]['type'] != 15]
        data_map = {ii[1]: ii for ii in data}
        update_list, insert_list = [], []
        for ii in data:
            if ii[1] in self.tpwd_db_map[article_id]:
                t = self.tpwd_db_map[article_id][ii[1]]
                update_list.append((t[0], *ii, t[-1], 0))
            else:
                insert_list.append(ii)
        for ii, jj in self.tpwd_db_map[article_id].items():
            if ii not in data_map:
                update_list.append((*jj, 1))
        self.update_db(insert_list, f'article_id {article_id} Insert')
        self.update_db(update_list, f'article_id {article_id} Update')

    def get_article_db(self, article_id: str):
        return [ii for ii in self.Db.select_db(self.S_ARTICLE_SQL % article_id)]

    def update_db(self, data: list, types: str, mode: int = 0):
        if not len(data):
            return
        if 'insert' in types.lower():
            basic_sql = self.I_LIST_SQL if mode else self.I_ARTICLE_SQL
        else:
            basic_sql = self.R_LIST_SQL if mode else self.R_ARTICLE_SQL

        i_sql = basic_sql % str(data)[1:-1]
        insert_re = self.Db.insert_db(i_sql)
        if insert_re:
            echo(3, '{} {} info Success'.format(types, len(data)))
        else:
            echo(0, '{} failed'.format(types))

    def decoder_tpwd_once(self, article_id: str, tpwd: str):
        req = self.decoder_tpwd(tpwd)
        if req is None or not 'data' in req or '!DOCTYPE html' in req:
            return
        req = req['data']
        temp_map = {ii: req[ii] for ii in self.NEED_KEY}
        if temp_map['validDate'] == self.ZERO_STAMP or '-' in temp_map['validDate']:
            temp_map['validDate'] = time_stamp()
        else:
            temp_map['validDate'] = time_stamp(time_format='%d天%H小时%M分%S秒',
                                               time_str=req['validDate']) - self.BASIC_STAMP + time_stamp()
        self.tpwd_map[article_id][tpwd] = temp_map
        self.decoder_tpwd_url(article_id, tpwd)

    def decoder_tpwd_url(self, article_id: str, tpwd: str):
        temp_map = self.tpwd_map[article_id][tpwd]
        tpwd_type, item_id = self.analysis_tpwd_url(temp_map['url'])
        if item_id is None:
            return
        temp_map['type'] = tpwd_type
        temp_map['item_id'] = item_id
        if tpwd_type < 20:
            echo(2, 'Domain:', self.URL_DOMAIN[tpwd_type],
                 'item id:', item_id)
        self.tpwd_map[article_id][tpwd] = temp_map

    def analysis_tpwd_url(self, url: str):
        if self.URL_DOMAIN[5] in url:
            return 5, self.get_uland_url(url)
        elif self.URL_DOMAIN[0] in url:
            return 0, self.get_s_click_url(url)
        elif self.URL_DOMAIN[10] in url:
            return 10, 0
        elif self.URL_DOMAIN[1] in url:
            return 1, self.get_item_detail(url)
        elif url == '':
            return 15, 0
        echo('0|warning', 'New Domain:',
             regex.findall('https://(.*?)/', url), url)
        return 20, 0

    def decoder_tpwd(self, tpwd: str):
        ''' decoder the tpwd from taokouling '''
        headers = {
            'Referer': self.DECODER_TPWD_URL,
            'X-Requested-With': 'XMLHttpRequest'
        }
        text = {'text': '￥{}￥'.format(tpwd)}
        req = proxy_req(self.DECODER_TPWD_URL, 11, data=text, header=headers)
        if req is None or not 'data' in req or '!DOCTYPE html' in req:
            if can_retry(tpwd):
                return self.decoder_tpwd(tpwd)
            else:
                return {}
        return req

    def get_s_click_url(self, s_click_url: str):
        ''' decoder s.click real jump url @validation time: 2019.08.31'''
        if 'tu=' not in s_click_url:
            tu_url = self.get_s_click_tu(s_click_url)
        else:
            tu_url = s_click_url
        if tu_url is None or 'tu=' not in tu_url:
            echo(3, 's_click_url tu url ENd Retry..', tu_url)
            return
        qso = decoder_url(tu_url)
        if 'tu' not in qso:
            if 'alisec' in tu_url:
                echo('0|debug', 'Request Too Fast')
                time.sleep(np.random.randint(10) * np.random.rand())
            else:
                echo(0, s_click_url, tu_url)
            return
        redirect_url = urllib.parse.unquote(qso['tu'])
        return self.get_s_click_detail(redirect_url, tu_url)

    def get_s_click_tu(self, s_click_url: str):
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3',
            'Host': 's.click.taobao.com'
        }
        req = proxy_req(s_click_url, 2, header=headers)
        if req is None or 'tu=' not in req.url:
            if can_retry(s_click_url):
                return self.get_s_click_tu(s_click_url)
            else:
                return
        return req.url

    def get_s_click_detail(self, redirect_url: str, tu_url: str):
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3',
            'referer': tu_url
        }
        req = proxy_req(redirect_url, 2, header=headers)
        if req is None or 'id=' not in req.url:
            if can_retry(redirect_url):
                return self.get_s_click_detail(redirect_url, tu_url)
            else:
                return
        return self.get_item_detail(req.url)

    def get_item_detail(self, item_url: str) -> str:
        item = decoder_url(item_url)
        if not 'id' in item:
            echo(0, 'id not found:', item_url)
            return ''
        return item['id']

    def get_uland_url(self, uland_url: str):
        if not self.M in self.cookies or time_stamp() - self.m_time > self.ONE_HOURS / 2:
            self.get_m_h5_tk()
        s_req = self.get_uland_url_once(uland_url, self.cookies)
        req_text = s_req.text
        re_json = json.loads(req_text[req_text.find('{'): -1])
        return re_json['data']['resultList'][0]['itemId']

    def get_m_h5_tk(self):
        self.m_time = time_stamp()
        req = self.get_uland_url_once(self.uland_url)
        self.cookies = req.cookies.get_dict()
        echo(1, 'get m h5 tk cookie:', self.cookies)

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
        t = int(time_stamp() * 1000)
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

    def get_ynote_file(self, offset: int = 0):
        url = self.LISTRECENT_URL % (offset, self.cstk)
        data = {'cstk': self.cstk}
        req = proxy_req(url, 11, data=data,
                        header=self.get_ynote_web_header(1))
        if req is None or type(req) != list:
            if can_retry(url):
                return self.get_ynote_file(offset)
            else:
                return None
        list_recent = {ii['fileEntry']['id']: ii['fileEntry'] for ii in req}
        self.list_recent = {**self.list_recent, **list_recent}
        echo(1, 'Load ynote file {} items.'.format(len(self.list_recent)))
        return req

    def get_ynote_web_header(self, mode: int = 0):
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
            'Cookie': self.cookie,
            'Host': self.Y_URL.split('/')[2],
            'Origin': self.Y_URL,
            'Referer': self.WEB_URL
        }
        if mode:
            headers['Accept'] = 'application/json, text/plain, */*'
        else:
            headers['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3'
        return headers

    def get_empty_content(self):
        headers = {'Referer': self.WEB_URL}
        req = proxy_req(self.Y_DOC_JS_URL, 3, header=headers)
        if len(req) < 1000:
            if can_retry(self.Y_DOC_JS_URL):
                return self.get_empty_content()
            else:
                return
        empty_content = regex.findall('t.EMPTY_NOTE_CONTENT=\'(.*?)\'', req)[0]
        empty_content = empty_content.split(self.END_TEXT)[0]
        self.empty_content = empty_content
        echo(1, 'Load empty content', empty_content)
        return empty_content

    def get_web_content(self):
        req = proxy_req(self.WEB_URL, 3, header=self.get_ynote_web_header())
        if len(req) < 1000:
            if can_retry(self.WEB_URL):
                return self.get_web_content()
            else:
                return
        return req

    def get_xml(self, article_id: str):

        url = self.SYNC_URL % ('download', self.cstk)
        data = {
            'fileId': self.exist_map[article_id][-1].split('/')[-1],
            'version': -1,
            'convert': True,
            'editorType': 1,
            'cstk': self.cstk
        }
        req = proxy_req(url, 11, data=data,
                        headers=self.get_ynote_web_header())
        return req

    def update_article(self, article_id: str, article_body: str):
        p = self.exist_map[article_id][-1].split('/')[-1]
        article_info = self.list_recent[p]
        data = {
            'fileId': p,
            'parentId': article_info['parentId'],
            'domain': article_info['domain'],
            'rootVersion': -1,
            'sessionId': '',
            'modifyTime': int(time_stamp()),
            'bodyString': article_body,
            'transactionId': p,
            'transactionTime': int(time_stamp()),
            'orgEditorType': article_info['orgEditorType'],
            'tags': article_info['tags'],
            'cstk': self.cstk
        }
        url = self.SYNC_URL % ('push', self.cstk) 
        req = proxy_req(url, 11, data=data, headers=self.get_ynote_web_header())
        return req
