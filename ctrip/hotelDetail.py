'''
@Author: gunjianpan
@Date:   2019-04-20 10:57:55
@Last Modified by:   gunjianpan
@Last Modified time: 2019-04-21 10:40:11
'''
import codecs
import numpy as np
import os
import re
import time
import js2py

from bs4 import BeautifulSoup
from utils.utils import basic_req, changeHeaders, echo, begin_time, end_time, time_str

data_dir = 'ctrip/data/'
one_day = 86400


def decoder_confusion():
    ''' decoder confusion '''
    with open('ctrip/fingerprint.js', 'r') as f:
        origin_js = [codecs.unicode_escape_decode(
            ii.strip())[0] for ii in f.readlines()]
    __0x3717e_begin = origin_js[1].index('[') + 1
    __0x3717e_end = origin_js[1].index(']')
    __0x3717e = origin_js[1][__0x3717e_begin:__0x3717e_end].split(',')
    __0x3717e = [ii.strip() for ii in __0x3717e]
    origin_str = '|||||'.join(origin_js)
    for ii, jj in enumerate(__0x3717e):
        origin_str = origin_str.replace('__0x3717e[{}]'.format(ii), jj)
    with open('ctrip/fingerprint_confusion.js', 'w') as f:
        f.write('\n'.join(origin_str.split('|||||')))


def load_ocean():
    ''' load ocean '''
    with open('ctrip/oceanball_origin.js', 'r') as f:
        origin_js = [ii.strip() for ii in f.readlines()]
    origin_str = '|||'.join(origin_js)
    params = re.findall(r'var (.*?) =', origin_str)
    params_another = re.findall(r'function\((.*?)\)', origin_str)
    params_another = sum([ii.replace('||||', '').split(',')
                          for ii in params_another], [])
    params += params_another

    params = sorted(list(set([ii for ii in params if len(
        ii) > 6])), key=lambda ii: len(ii), reverse=True)
    for ii, jj in enumerate(params):
        origin_str = origin_str.replace(jj, 'a{}'.format(ii))
    with open('ctrip/oceanball_origin_decoder.js', 'w') as f:
        f.write(origin_str.replace('|||', '\n'))


HOTELS_URL = 'https://hotels.ctrip.com/'
HOTEL_ROOMLIST_FOR_DETAIL_URL = '%sDomestic/tool/AjaxHote1RoomListForDetai1.aspx' % HOTELS_URL
OCEANBALL_URL = '{}domestic/cas/oceanball'.format(HOTELS_URL)
HOTEL_DETAIL_URL = '{}hotel/%d.html'.format(HOTELS_URL)


class HotelDetail:
    ''' generate params for https://hotels.ctrip.com/Domestic/tool/AjaxHote1RoomListForDetai1.aspx '''

    def __init__(self):
        self.default_hotel_id = 4889292

    def generate_callback(self, e):
        ''' generate callback params e '''
        char_list = [chr(ii)
                     for ii in range(65, 123) if ii > 96 or ii < 91]
        o = ''.join(["CAS", *[char_list[ii]
                              for ii in np.random.randint(0, 51, e)]])
        return o

    def generate_eleven(self):
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
        #   6. finsh, return, and joint params;
        #
        ################################################################

        callback = self.generate_callback(15)
        now_time = int(time.time() * 1000)
        url = '{}?callback={}&_={}'.format(OCEANBALL_URL, callback, now_time)
        referer_url = HOTEL_DETAIL_URL % self.default_hotel_id
        changeHeaders({'Referer': referer_url})
        oceanball_js = basic_req(url, 3)
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
        function(){let href='https://hotels.ctrip.com/hotel/4889292.html';
            a={'documentElement': {'attributes':{}}};
            b={};
            function c(){};
            userAgent ='Chrome/73.0.3682.0';
            geolocation = 0;
        '''

        ''' replace document & windown & navigator '''
        oe = oe.replace('document.body.innerHTML.length', '888').replace(
            'document.body.innerHTML', '""')
        oe = oe.replace('document.createElement("div")', '{}')
        oe = oe.replace('window.HTMLSpanElement', 'c').replace(
            'document.createElement("span")', '1')
        oe = oe.replace('window.location.href', 'href').replace(
            'location.href', 'href')
        oe = oe.replace('navigator.', '')
        oe = oe.replace('new Image().', '')
        oe = oe.replace('document.all', '0').replace('document.referrer', '""')
        oe = oe.replace('this || ', '')
        oe = oe.replace('window["document"]', 'a')

        oe = oe.replace('document', 'a').replace('window', 'b')
        oe = oe.replace('function(){', replace, 1)

        ''' eval script '''
        eleven = js2py.eval_js(oe)
        echo(1, 'eleven', eleven)
        return eleven

    def generate_other_params(self, hotel_id: int = 4889292, city_id: int=2,
                              startDate: str=time_str(-1, '%Y-%m-%d'),
                              depDate: str=time_str(int(time.time() + one_day), '%Y-%m-%d')):
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
            'RoomGuestCount': '1,1,0'
        }
        return params

    def get_hotel_detail(self):
        ''' get hotel detail '''
        params = {
            **self.generate_other_params(),
            'callback': self.generate_callback(16),
            'eleven': self.generate_eleven(),
            '_': int(time.time() * 1000)
        }
        params_list = ['{}={}'.format(
            ii, (jj if not jj is None else '')) for ii, jj in params.items()]
        url = '{}?{}'.format(HOTEL_ROOMLIST_FOR_DETAIL_URL,
                             '&'.join(params_list))
        echo(2, 'XHR url', url)
        text = basic_req(url, 1)
        return text

    def parse_detail(self):
        ''' parse hotel detail '''

        version = begin_time()
        text = self.get_hotel_detail()
        html = BeautifulSoup(text['html'], 'html.parser')
        trs = html.findAll('tr')[2:]
        hotel_detail = []

        for tr in trs:
            room_name = re.findall('baseroomname="(.*?)"', str(tr))
            if not len(room_name):
                room_name = re.findall(
                    'rel="nofollow">\n(.*?)\n', str(tr))
            room_name = room_name[0].strip() if len(
                room_name) else hotel_detail[-1][0]
            price = re.findall(r'</dfn>(\d{4,5}?)</span>', str(tr))
            if not len(price):
                continue
            else:
                price = price[0]
            price_type = re.findall('room_type_name">(.*?)</span>', str(tr))[0]
            if 'em' in price_type:
                price_type = ','.join([*re.findall(
                    '(.*?)<em', price_type), *re.findall('（(.*?)）', price_type)])
            hotel_detail.append([room_name, price_type, price])
        output_dir = '{}hotelDetail.txt'.format(data_dir)
        with open(output_dir, 'w') as f:
            f.write('\n'.join([','.join(ii) for ii in hotel_detail]))
        echo(1, 'Load {} price\nOutput path: {}\nSpend time: {:.2f}s'.format(
            len(hotel_detail), output_dir, end_time(version, 0)))
        return hotel_detail


if __name__ == '__main__':
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    ch = HotelDetail()
    ch.parse_detail()
