# -*- coding: utf-8 -*-
# @Author: gunjianpan
# @Date:   2019-04-20 10:57:55
# @Last Modified by:   gunjianpan
# @Last Modified time: 2019-09-13 17:59:26

import codecs
import datetime
import json
import os
import random
import re
import shutil
import sys
import threading
import time

import numpy as np
import tzlocal
from bs4 import BeautifulSoup

import execjs
import js2py

sys.path.append(os.getcwd())
from util.util import (basic_req, begin_time, changeHeaders, decoder_fuzz,
                       echo, end_time, time_str)


data_dir = 'ctrip/data/'
cookie_path = 'ctrip/cookie.txt'
compress_path = 'ctrip/compress.js'
one_day = 86400


def decoder_confusion():
    ''' decoder confusion '''
    with open(f'{data_dir}fingerprint.js', 'r') as f:
        origin_js = [codecs.unicode_escape_decode(
            ii.strip())[0] for ii in f.readlines()]
    __0x3717e_begin = origin_js[1].index('[') + 1
    __0x3717e_end = origin_js[1].index(']')
    __0x3717e = origin_js[1][__0x3717e_begin:__0x3717e_end].split(',')
    __0x3717e = [ii.strip() for ii in __0x3717e]
    origin_str = '|||||'.join(origin_js)
    params = re.findall(r'var (.*?) =', origin_str)
    params_another = re.findall(r'function\((.*?)\)', origin_str)
    params_another = sum([ii.replace('|||||', '').split(',')
                          for ii in params_another], [])
    params += params_another

    params = sorted(list(set([ii for ii in params if len(
        ii) > 6])), key=lambda ii: len(ii), reverse=True)
    for ii, jj in enumerate(__0x3717e):
        origin_str = origin_str.replace(f'__0x3717e[{ii}]', jj)
    for ii, jj in enumerate(params):
        origin_str = origin_str.replace(jj, f'a{ii}')
    with open(f'{data_dir}fingerprint_confusion.js', 'w') as f:
        f.write('\n'.join(origin_str.split('|||||')))


def load_ocean():
    ''' load ocean '''
    with open(f'{data_dir}oceanball_origin.js', 'r') as f:
        origin_js = [ii.strip() for ii in f.readlines()]
    origin_str = '|||'.join(origin_js)
    params = [*re.findall(r'var ([a-zA-Z]*?) =', origin_str),
              re.findall(r'var ([a-zA-Z]*?);', origin_str)]
    params_another = re.findall(r'function\((.*?)\)', origin_str)
    params_another = sum([ii.replace('|||', '').split(',')
                          for ii in params_another], [])
    params += params_another
    params += re.findall(r', ([a-zA-Z]*?)\)', origin_str)
    params += re.findall(r'\(([a-zA-Z]*?),', origin_str)

    params = sorted(list(set([ii for ii in params if len(
        ii) > 6])), key=lambda ii: len(ii), reverse=True)
    for ii, jj in enumerate(params):
        origin_str = origin_str.replace(jj, f'a{ii}')
    with open(f'{data_dir}oceanball_origin_decoder.js', 'w') as f:
        f.write(origin_str.replace('|||', '\n'))


def load_ocean_v2():
    ''' load ocean ball v2 @2019.6.9 '''
    decoder_fuzz('(_\w{3,7}_\w{5})',
                 '{}oceanballv2_july.js'.format(data_dir),
                 replace_func=replace_params)


def replace_params(origin_str: str, reg: str) -> str:
    ''' replace params '''
    params_re = re.findall(reg, origin_str)
    echo(1, "You're", re.findall('_(.*?)_', params_re[0])[0])
    params = {}
    for ii in params_re:
        if not ii in params:
            params[ii] = len(params)
    for ii in sorted(list(params.keys()), key=lambda i: -len(i)):
        origin_str = origin_str.replace(ii, f'a{params[ii]}')
    return origin_str


def load_html_js():
    with open(f'{data_dir}html_js.js', 'r') as f:
        origin_js = [ii.strip() for ii in f.readlines()]
    origin_str = '|||'.join(origin_js)

    ''' long params name replace '''
    params = re.findall(r'_0x\w{6}?', origin_str)
    params += re.findall(r'_0x\w{5}?', origin_str)
    params += re.findall(r'_0x\w{4}?', origin_str)
    params = sorted(list(set(params)), key=lambda ii: len(ii), reverse=True)

    ''' __0x33920 '''
    __0x33920_begin = origin_js[35].index('[') + 1
    __0x33920_end = origin_js[35].index(']')
    __0x33920 = origin_js[35][__0x33920_begin:__0x33920_end].split(',')
    __0x33920 = [ii.strip() for ii in __0x33920]
    for ii, jj in enumerate(__0x33920):
        origin_str = origin_str.replace('__0x33920[{}]'.format(ii), jj)

    ''' _0x4f05 '''
    _0x4f05_dict = {2: "prototype", 3: "hashCode", 4: "length", 5: "pmqAv", 6: "charCodeAt", 11: "EcTAI", 12: "bTlKh", 13: "prototype", 14: "toString", 15: ";expires=", 16: ";path=/", 17: "getDate", 18: "xxxxt", 19: "xxxxt", 20: "ymGjh", 21: "DjPmX", 22: "cookie", 23: "cookie",
                    24: "split", 25: "length", 26: "webdriver", 27: "random", 28: "abs", 29: "userAgent", 30: "replace", 31: "abs", 32: "hashCode", 33: "substr", 34: "host", 35: "indexOf", 36: "m.ctrip", 45: "fcerror", 46: "_zQdjfing", 47: "_RGUID", 48: "replace", 49: "fromCharCode", 50: "QVALA"}
    _0x4f05_origin = {ii: hex(ii) for ii in _0x4f05_dict.keys()}
    _0x4f05_replace = {ii: re.findall(
        r'_0x4f05\("%s",.{7}\)' % jj, origin_str) for ii, jj in _0x4f05_origin.items()}
    print(_0x4f05_replace)
    for ii, jj in _0x4f05_replace.items():
        for kk in jj:
            origin_str = origin_str.replace(
                kk, '"{}"'.format(_0x4f05_dict[ii]))

    ''' _0x1bf9 '''
    _0x1bf9_dict = {1: "eit", 2: "NMs", 3: "FMx", 4: "utc", 5: "sign", 6: "sign", 22: "mMa", 23: ";path=/", 24: "KWcVI", 25: "KWcVI", 33: "setDate", 34: "getDate", 35: "cookie", 36: "dnvrD", 37: "dnvrD", 38: "dnvrD", 39: "ceIER", 40: "toGMTString", 41: "jXvnT", 42: "abs", 43: "hashCode", 47: "DkDiA", 48: "btRpY", 49: "sign", 50: "href", 51: "length", 52: "OZJLY", 53: "HWzfY", 54: "btRpY", 55: "ZQRZh", 56: "rSeVr", 57: "pow", 58: "pop", 59: "ZQRZh", 60: "KEEqN", 61: "xmTXV", 62: "abs", 63: "mytJr", 64: "btRpY", 65: "hashCode", 66: "abs", 67: "xbNid", 68: "evWhs", 69: "log",
                    70: "tStBb", 71: "toFixed", 72: "sign", 73: "wBNtc", 74: "abs", 75: "wyibM", 76: "bSvQq", 77: "dHSnF", 78: "random", 79: "getTimezoneOffset", 80: "BzPEC", 81: "dHSnF", 82: "WYJFv", 83: "WYJFv", 84: "split", 85: "length", 86: "QTDGI", 89: "BzPEC", 90: "AceIM", 91: "wOQ", 93: "TGIHa", 94: "join", 95: "join", 96: "join", 97: "HTF", 98: "ioW", 99: "HfzNS", 100: "MIA", 101: "FNbOm", 102: "HfzNS", 103: "OCGEJ", 104: "HfzNS", 105: "aYQhD", 107: "push", 108: "length", 109: "call", 110: "call", 111: "call", 112: "split", 113: "call", 114: "WYJFv", 115: "ZmtWg", 116: "zYC", 119: "join"}
    _0x1bf9_origin = {ii: hex(ii) for ii in _0x1bf9_dict.keys()}
    _0x1bf9_replace = {ii: re.findall(
        r'_0x1bf9\("%s",.{7}\)' % jj, origin_str) for ii, jj in _0x1bf9_origin.items()}
    print(_0x1bf9_replace)
    for ii, jj in _0x1bf9_replace.items():
        for kk in jj:
            origin_str = origin_str.replace(
                kk, '"{}"'.format(_0x1bf9_dict[ii]))

    for ii, jj in enumerate(params):
        origin_str = origin_str.replace(jj, 'a{}'.format(ii))
    with open('{}html_js_decoder.js'.format(data_dir), 'w') as f:
        f.write(origin_str.replace('|||', '\n'))


HOTELS_URL = 'https://hotels.ctrip.com/'
HOTEL_ROOMLIST_DETAIL_URL = '%sDomestic/tool/AjaxHote1RoomListForDetai1.aspx' % HOTELS_URL
OCEANBALL_URL = '{}domestic/cas/oceanball'.format(HOTELS_URL)
HOTEL_DETAIL_URL = '{}hotel/%d.html'.format(HOTELS_URL)
AJAX_PROMOTION_URL = '{}Domestic/Tool/AjaxGetPromotionFilterList.aspx'.format(
    HOTELS_URL)


class HotelDetail:
    ''' generate params for https://hotels.ctrip.com/Domestic/tool/AjaxHote1RoomListForDetai1.aspx '''

    def __init__(self):
        self.default_hotel_id = 4889292
        self.header = {
            'pragma': 'no-cache',
            'cache-control': 'no-cache',
            'Cookie': '',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3',
            "Accept-Encoding": "",
            "Accept-Language": "zh-CN,zh;q=0.9",
            'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3682.0 Safari/537.36"
        }

    def generate_callback(self, e):
        ''' generate callback params e '''
        cl = [chr(ii) for ii in range(65, 123) if ii > 96 or ii < 91]
        o = ''.join(["CAS", *[cl[ii] for ii in np.random.randint(0, 51, e)]])
        return o

    def generate_eleven_v2(self, hotel_id: int):
        ################################################################
        #
        #   [generate eleven] version 19.7.28(Test ✔️) write by gunjianpan
        #
        #   1. random generate 15 bit param `callback`;
        #   2. use callback request OCEANBALL -> get origin js;
        #   3. decoder params to union param;
        #   4. find where the code eval;
        #      'h=a3.pop(),i=a11(h);return a18(i.apply(h.o,g),ud,ud,0),'
        #   5. compare the env of chrome with node.
        #      'https://github.com/iofu728/spider/tree/develop#oceannballv2'
        #   5. you will get `爬虫前进的道路上还是会有各种各样想不到的事情会发生`
        #   6. final, return, and joint params;
        #
        ################################################################

        referer_url = HOTEL_DETAIL_URL % hotel_id
        self.header['Referer'] = referer_url
        callback = self.generate_callback(15)
        now_time = int(time.time() * 1000)
        url = f'{OCEANBALL_URL}?callback={callback}&_={now_time}'
        oj, cookie = basic_req(url, 3, need_cookie=True, header=self.header)
        print(cookie)
        oj = replace_params(oj, '(_\w{3,7}_\w{5,6})')
        oj = oj.replace('"this"', 'this').replace('\'', '"').replace('\n', '')
        ooj = oj

        ''' replace window '''
        oj = oj.replace('Window', 'window')
        oj = oj.replace('window', 'windows')

        ''' return answer '''
        echo(0, 'Num of a6[h][i]', oj.count('a19[0])}}return a18(a6[h][i]'))
        echo(0, 'Num 0f end', oj.count('});; })();'))
        oj = oj.replace('});; })();', '});;return aa;})();')
        ooj = ooj.replace('});; })();', '});;return aa;})();')

        ''' windows setting '''
        windows_str = 'function(){ var windows = {"navigator":{"userAgent":"Mozilla/5.0"}};aa=[];windows["' + \
            callback + \
            '"] = function(e) {temp = e();console.log(temp);return temp};'
        oj = oj.replace('function(){ ', windows_str)

        oj = "function aabb(){tt=" + oj + ";return tt;}"

        ''' replace param undefine replace'''
        oj = oj.replace('env.define;', 'windows.define;')
        oj = oj.replace('env.module;', 'windows.module;')
        oj = oj.replace('env.global;', 'windows.global;')
        oj = oj.replace('env.require;', 'windows.require;')
        oj = oj.replace('env.', '')

        ''' synchronous node & chrome v8 param'''
        oj = oj.replace(
            'var a2=', 'require=undefined;module=undefined;global=undefined;var a2=')
        oj = oj.replace('process:process,', 'process:NO,')
        oj = oj.replace('process,', 'NO, ')
        oj = oj.replace(
            'return a19[p];', 'var last = a19[p];if (last.k == 0 && last.o == 0 && last.r == 0 && last.v != 0) {last.v = TypeError();}return last;')

        oj = oj.replace('h=a3.pop(),i=a11(h);return a18(i.apply(h.o,g),ud,ud,0),',
                        'h=a3.pop(),i=a11(h);var test = h.k!="getOwnPropertyNames" ? i.apply(h.o,g) :[];if(h.o=="function tostring() { [python code] }"){test=23};if(g=="object window"){test=21};if(h.k=="keys"){test=["TEMPORARY", "PERSISTENT"];}aa=test;return a18(test, ud, ud, 0),')

        ''' eval script '''
        eleven = js2py.eval_js(oj + ';aabb()')
        echo(1, 'eleven', eleven)
        return eleven

    def generate_eleven(self, hotel_id: int):
        ################################################################
        #
        #   [generate eleven] version 19.4.21(Test ✔️) write by gunjianpan
        #
        #   1. random generate 15 bit param `callback`;
        #   2. use callback request OCEANBALL -> get origin js;
        #   3. eval once -> (match array, and then chr() it) -> decoder js;
        #   4. replace document and windows(you also can use execjs & jsdom);
        #   5. warning you should replace `this` to some params,
        #      Otherwise, you will get `老板给小三买了包， 却没有给你钱买房`
        #   6. final, return, and joint params;
        #
        ################################################################

        callback = self.generate_callback(15)
        now_time = int(time.time() * 1000)
        url = '{}?callback={}&_={}'.format(OCEANBALL_URL, callback, now_time)
        referer_url = HOTEL_DETAIL_URL % hotel_id
        changeHeaders(
            {'Referer': referer_url, 'if-modified-since': 'Thu, 01 Jan 1970 00:00:00 GMT'})
        oceanball_js, cookie = basic_req(url, 3, need_cookie=True)
        print(cookie)

        array = re.findall(r'\(\[(.*)\],', oceanball_js)[0].split(',')
        array = [int(ii) for ii in array]
        offset = int(re.findall(r'item-(\d*?)\)', oceanball_js)[0])

        ''' String.fromCharCode '''
        oe = ''.join([chr(ii - offset) for ii in array])

        ''' replace window[callback] callback function '''
        replace_str = re.findall(r'{}\(new.*\)\);'.format(callback), oe)[0]
        eleven_params = re.findall(
            r'{}\(new.*\+ (.*?) \+.*\)\);'.format(callback), oe)[0]
        replaced_str = 'return {};'.format(eleven_params)
        oe = oe.replace(replace_str, replaced_str)
        oe = oe.replace('\'', '"').replace('\r', '')
        oe = oe.replace(';!', 'let aaa = ', 1)

        replace = '''
        function(){let href="https://hotels.ctrip.com/hotel/%d.html";
            a={"documentElement": {"attributes":{}}};
            b={};
            function c(){};
            userAgent ="Chrome/73.0.3682.0";
            geolocation = 1;
        ''' % hotel_id

        ''' replace document & windown & navigator '''
        oe = oe.replace('document.body.innerHTML.length', '888').replace(
            'document.body.innerHTML', '""')
        oe = oe.replace('document.createElement("div")', '{}')
        oe = oe.replace('window.HTMLSpanElement', 'c').replace(
            'document.createElement("span")', 'new c')
        oe = oe.replace('window.location.href', 'href').replace(
            'location.href', 'href')
        oe = oe.replace('navigator.', '')
        oe = oe.replace('new Image().', '').replace('new Image();', '')
        oe = oe.replace('document.all', '0').replace('document.referrer', '""')
        oe = oe.replace('this || ', '')
        oe = oe.replace('window["document"]', 'a')

        oe = oe.replace('document', 'a').replace('window', 'b')
        oe = oe.replace('function(){', replace, 1)

        ''' eval script '''
        eleven = js2py.eval_js(oe)
        echo(1, 'eleven', eleven)

        return eleven

    def generate_other_params(self, hotel_id: int = 4889292, city_id: int = 2,
                              startDate: str = time_str(-1, '%Y-%m-%d'),
                              depDate: str = time_str(int(time.time() + one_day), '%Y-%m-%d')):
        ''' generate other params '''
        params = {
            'psid': None,
            'MasterHotelID': hotel_id,
            'hotel': hotel_id,
            'EDM': 'F',
            'roomId': None,
            'IncludeRoom': None,
            'city': city_id,
            'showspothotel': 'T',
            'supplier': None,
            'IsDecoupleSpotHotelAndGroup': 'F',
            'contrast': 0,
            'brand': 776,
            'startDate': startDate,
            'depDate': depDate,
            'IsFlash': 'F',
            'RequestTravelMoney': 'F',
            'hsids': None,
            'IsJustConfirm': None,
            'contyped': 0,
            'priceInfo': -1,
            'equip': None,
            'filter': None,
            'productcode': None,
            'couponList': None,
            'abForHuaZhu': None,
            'defaultLoad': 'T',
            'esfiltertag': None,
            'estagid': None,
            'Currency': None,
            'Exchange': None,
            'minRoomId': 0,
            'maskDiscount': 0,
            'TmFromList': 'F',
            'th': 119,
            'RoomGuestCount': '1,1,0',
            'promotionf': None,
            'allpoint': None,
        }
        return params

    def get_hotel_detail(self, hotel_id: int):
        ''' get hotel detail '''
        params = {
            **self.generate_other_params(hotel_id),
            'eleven': self.generate_eleven_v2(hotel_id),
            'callback': self.generate_callback(16),
            '_': int(time.time() * 1000)
        }
        params_list = ['{}={}'.format(
            ii, (jj if not jj is None else '')) for ii, jj in params.items()]
        url = '{}?{}'.format(HOTEL_ROOMLIST_DETAIL_URL, '&'.join(params_list))
        echo(2, 'XHR url', url)
        req, _ = basic_req(url, 1, need_cookie=True, header=self.header)
        return req

    def parse_detail(self, hotel_id: int = 4889292):
        ''' parse hotel detail '''

        version = begin_time()
        # self.user_action(hotel_id)
        # self.generate_cookie(hotel_id)
        # self.prepare_req()
        text = self.get_hotel_detail(hotel_id)
        html = BeautifulSoup(text['html'], 'html.parser')
        trs = html.findAll('tr')[2:]
        hotel_detail = []

        for tr in trs:
            room_name = re.findall('baseroomname="(.*?)"', str(tr))
            if not len(room_name):
                room_name = re.findall('l="nofollow">\n(.*?)\n', str(tr))
            room_name = room_name[0].strip() if len(
                room_name) else (hotel_detail[-1][0] if len(hotel_detail) else '')
            price = re.findall(r'</dfn>(\d{4,5}?)</span>', str(tr))
            if not len(price):
                continue
            sales_price_list = re.findall(r'促销优惠减(.*?)</span>', str(tr))
            sales_price = sales_price_list[0] if len(sales_price_list) else ''
            price_type = re.findall('room_type_name">(.*?)</span>', str(tr))[0]
            if 'em' in price_type:
                price_type = ','.join([*re.findall(
                    '(.*?)<em', price_type), *re.findall('（(.*?)）', price_type)])
            hotel_detail.append([room_name, price_type, price[0], sales_price])
        output_dir = '{}hotelDetail.txt'.format(data_dir)
        with open(output_dir, 'w') as f:
            f.write('\n'.join([','.join(ii) for ii in hotel_detail]))
        echo(1, 'Hotel: {}\nLoad {} price\nOutput path: {}\nSpend time: {:.2f}s'.format(
            hotel_id, len(hotel_detail), output_dir, end_time(version, 0)))
        return hotel_detail

    def generate_cookie(self, hotel_id: int):
        ''' generate cookie '''

        # url = '{}hotel/{}.html'.format(HOTELS_URL, hotel_id)
        # _, cookie = basic_req(url, 3, need_cookie=True)
        cookie = {**self.login_cookie(), **self.generate_v1()}
        print(self.encoder_cookie(cookie))
        changeHeaders({'Cookie': self.encoder_cookie(cookie)})

    def decoder_cookie(self, cookie: str) -> dict:
        return {ii.split('=', 1)[0]: ii.split('=', 1)[1] for ii in cookie.split('; ')}

    def encoder_cookie(self, cookie_dict: {}) -> str:
        return '; '.join(['{}={}'.format(ii, jj)for ii, jj in cookie_dict.items()])

    def get_timezone_offset(self):
        local_tz = tzlocal.get_localzone()
        return -int(local_tz.utcoffset(datetime.datetime.today()).total_seconds() / 60)

    def a312(self, a312_value):
        a323_list = [0, 36, 5, 5, 5, 5, 137, 137, 36, 171]
        a199 = 0 if a312_value > len(a323_list) - 1 else a323_list[a312_value]
        return '{}{}'.format('0' if a199 < 16 else '', str(hex(a199)).split('0x', 1)[1])

    def generate_v1(self, time_stamp: int = 0):
        a241, a166, a144 = self.get_timezone_offset(), int(time.time() * 1000), 10
        a166 += sum([np.int32((int('0x2ede', 16) + ii) * a241)
                     for ii in range(6)])
        a166 = a166 if not time_stamp else time_stamp
        a33 = [int(ii) for ii in list(str(a166))]
        for ii in range(len(a33)):
            a33[ii] ^= a144
            a144 = a33[ii]

        a34 = [int(ii) for ii in list(str(a166))]
        a167 = [a34[len(a34) - ii - 1] for ii, _ in enumerate(a34)]
        a13 = [0x3, 0x1, 0x2, 0x6, 0xb, 0x5, 0xa, 0x4, 0x8, 0x0, 0x9, 0x7, 0xc]
        a217 = [self.a312(a167[ii if ii > len(a167) else a13[ii]])
                for ii in range(len(a167))]
        cookie = {'htltmp': ''.join(
            [hex(ii)[-1] for ii in a33]), 'utc': str(a166), 'htlstmp': ''.join(a217), 'MKT_Pagesource': 'PC'}
        return cookie

    def login_cookie(self):
        if not os.path.exists(cookie_path):
            shutil.copy(cookie_path + '.tmp', cookie_path)
        with open(cookie_path) as f:
            cookie = self.decoder_cookie(f.read().strip())
        return cookie

    def user_action(self, hotel_id: int = 4889292):

        url = '{}hotel/{}.html'.format(HOTELS_URL, hotel_id)
        text = basic_req(url, 3)
        page_id = int(re.findall(r'id="page_id" value="(\d*?)" />', text)[0])
        correlation_id = re.findall(r'relationId" value="(\d*?)"/>', text)[0]

        e = self.login_cookie()['_bfa'].split('.')
        common = [page_id, e[1] + '.' + e[2], int(e[6]), int(e[7]), correlation_id,
                  "M:70,181023_hod_fxtj:B;", '', '2.6.9', "vq5tkk-ufpyck-qsxbg3", "", "", "", "", "", "online"]
        _queue = [{
            'action': 'click',
            'xpath': "HTML/BODY[@id='mainbody']/FORM[@id='aspnetForm']/DIV[3][@id='base_bd']/DIV[4]/DIV[@id='divDetailMain']/DIV[9][@id='id_room_select_box']/DIV[2]/DIV/DIV/A[@id='changeBtn'][@x='{}'][@y='{}'][@rx='{}'][@ry='{}']".format(random.randint(50, 80), random.randint(650, 750), random.randint(20, 40), random.randint(5, 20)),
            'ts': int(time.time() * 1000),
        }]
        ee = [[2, "useraction"], common, _queue]
        eee = json.dumps(ee, separators=(',', ':'))
        print(eee)
        compress = execjs.compile(open(compress_path).read())
        eeee = compress.call('compress', eee)
        echo(2, eeee)
        cookie = {'uid': 'Yn17vOkRm2gW+jCNwT8jPg=='}
        header = {
            'Referer': 'https://hotels.ctrip.com/hotel/4889292.html',
            'Cookie': self.encoder_cookie(cookie),
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3777.0 Safari/537.36',
        }
        url = 'https://s.c-ctrip.com/bf.gif?ac=a&d={}&jv=1.0.0'.format(eeee)
        req = basic_req(url, 2, header=header)
        echo(0, req.cookies.get_dict())

    def prepare_req(self, hotel_id: int = 4889292, city_id: int = 2,
                    startDate: str = time_str(-1, '%Y-%m-%d'),
                    depDate: str = time_str(int(time.time() + one_day), '%Y-%m-%d')):
        referer_url = HOTEL_DETAIL_URL % hotel_id

        changeHeaders({'Referer': referer_url})
        data = {'city': city_id, 'checkin': startDate,
                'cjeckout': depDate, 'defalutVal': None}
        return basic_req(AJAX_PROMOTION_URL, 11, data=data)


if __name__ == '__main__':
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    ch = HotelDetail()
    ch.parse_detail()
