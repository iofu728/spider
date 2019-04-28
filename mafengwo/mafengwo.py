'''
@Author: gunjianpan
@Date:   2019-04-16 16:50:45
@Last Modified by:   gunjianpan
@Last Modified time: 2019-04-20 01:33:26
'''
import codecs
import execjs
import numpy as np
import os
import re
import time
import threading

from bs4 import BeautifulSoup
from proxy.getproxy import GetFreeProxy
from util.util import basic_req, echo, time_str, can_retry, begin_time, end_time, shuffle_batch_run_thread

data_dir = 'mafengwo/data/'
hotel_js_path = 'mafengwo/hotel.js'
decoder_js_path = '{}decoder.js'.format(data_dir)
origin_js_path = '{}origin.js'.format(data_dir)
get_request_proxy = GetFreeProxy().get_request_proxy


class Mafengwo:
    ''' some js confusion applications in mafengwo '''

    JD_URL = 'http://www.mafengwo.cn/jd/10186/gonglve.html'
    AJAX_ROUTER_URL = 'http://www.mafengwo.cn/ajax/router.php'
    MDD_URL = 'http://www.mafengwo.cn/mdd/'

    def __init__(self):
        self.spot_result = {}
        self.spot_pn = {}
        self.prepare_js()

    def decode_js_test(self):
        ''' decode js for test '''
        with open(decoder_js_path, 'r') as f:
            decoder_js = [codecs.unicode_escape_decode(
                ii.strip())[0] for ii in f.readlines()]
        __Ox2133f = [ii.strip()
                     for ii in decoder_js[4][17:-2].replace('\"', '\'').split(',')]
        decoder_str = '|||'.join(decoder_js)
        params = re.findall(r'(\_0x\w{6,8}?)=|,|\)', decoder_str)
        params = sorted(list(set([ii for ii in params if len(
            ii) > 6])), key=lambda ii: len(ii), reverse=True)
        for ii, jj in enumerate(__Ox2133f):
            decoder_str = decoder_str.replace('__Ox2133f[{}]'.format(ii), jj)
        for ii, jj in enumerate(params):
            decoder_str = decoder_str.replace(jj, 'a{}'.format(ii))
        decoder_js = decoder_str.split('|||')
        with open(origin_js_path, 'w') as f:
            f.write('\n'.join(decoder_js))
        return decoder_js

    def prepare_js(self):
        ''' prepare js '''
        pre_text = basic_req(self.JD_URL, 3)
        INDEX_JS_URL = re.findall(
            r'src=.*index\.js.*" t', pre_text)[0].split('"')[1]
        origin_js = basic_req(INDEX_JS_URL, 3)

        ''' decoder js '''
        decode_js = codecs.unicode_escape_decode(origin_js)[0]

        ''' params replace '''
        replace_list_str = decode_js.split(';')[2]
        empty_index = replace_list_str.index(' ') + 1
        begin_index = replace_list_str.index('=[') + 2
        end_index = replace_list_str.index(']')
        replace_list = replace_list_str[begin_index:end_index].split(',')
        rp = replace_list_str[empty_index:begin_index - 2]
        for ii, jj in enumerate(replace_list):
            decode_js = decode_js.replace('{}[{}]'.format(rp, ii), jj)
        self.slat = replace_list[46].replace('"', '')
        echo(2, 'salt', self.slat)

        ''' load to local '''
        with open(decoder_js_path, 'w') as f:
            f.write(';\n'.join(decode_js.split(';')))

        ''' del function about ajax '''
        del_str = re.findall(r'_.{6,10}\["ajaxPrefilter.*\)\}\}\)', decode_js)
        del_begin_index = decode_js.index(del_str[0])

        result_js = decode_js[:del_begin_index] + \
            decode_js[del_begin_index + len(del_str[0]):]

        result_js = decode_js[:del_begin_index] + \
            decode_js[del_begin_index + len(del_str[0]):]
        self.result_js = result_js
        self.js_compile = execjs.compile(open(hotel_js_path).read())
        echo(1, 'Load hotel index js success!!!')

    def js_compile_sn(self, prepare_map):
        ''' js compile sn '''
        wait_js = '<script>' + self.result_js + '</script>'
        sn = self.js_compile.call(
            'analysis_js', wait_js, self.slat, prepare_map)
        echo(2, '_sn', sn)
        return sn

    def load_sn(self, data: dict, now_time=0) -> dict:
        ''' load sn '''

        if not now_time:
            now_time = int(time.time() * 1000)
        prepare_map = {**data, '_ts': now_time}

        ''' _0xe7fex37 sorted & str num '''
        prepare_map = {ii: str(prepare_map[ii]) for ii in sorted(prepare_map)}

        ''' js compile sn '''
        sn = self.js_compile_sn(prepare_map)

        data = {
            **data,
            '_sn': sn,
            '_ts': now_time
        }
        return data

    def load_spot_once(self, pn=1, city_id=10186):
        ''' load spot once '''
        data = {
            'sAct': 'KMdd_StructWebAjax|GetPoisByTag',
            'iMddid': city_id,
            'iTagId': 0,
            'iPage': pn,
        }
        data = self.load_sn(data)
        print(data)
        req = get_request_proxy(self.AJAX_ROUTER_URL, 11, data=data)
        if req is None or not 'data' in req or not 'list' in req['data']:
            if can_retry('{}{}{}'.format(self.AJAX_ROUTER_URL, city_id, pn)):
                self.load_spot_once(pn, city_id)
            return
        spot_list = req['data']['list']
        spot_pn = req['data']['page']
        spot_tmp = re.findall('<h3>.*?(.*?)</h3>', spot_list)
        try:
            total_pn = int(re.findall('共<span>(.*?)</span>', spot_pn)[0])
        except Exception as e:
            total_pn = 1
            echo(0, 'City id:', city_id, 'Page:', pn, spot_pn, e)

        if city_id not in self.spot_result:
            self.spot_result[city_id] = spot_tmp
        else:
            self.spot_result[city_id] += spot_tmp
        self.spot_pn[city_id] = total_pn

    def load_spot(self, batch_size=50):
        ''' load spot '''
        version = begin_time()
        self.load_city_list()
        # self.city_list = [10186]
        city_threading = [threading.Thread(
            target=self.load_spot_once, args=(1, ii,))for ii in self.city_list]
        shuffle_batch_run_thread(city_threading, 150)

        spot_continue = []
        for ii, jj in self.spot_pn.items():
            spot_continue += [threading.Thread(
                target=self.load_spot_once, args=(pn, ii,)) for pn in range(2, jj + 1)]

        shuffle_batch_run_thread(spot_continue, 150)
        output = ['{},{}'.format(self.id2map[ii], ','.join(jj))
                  for ii, jj in self.spot_result.items()]
        output_path = '{}spot.txt'.format(data_dir)
        with open(output_path, 'w') as f:
            f.write('\n'.join(output))
        city_num = len(self.city_list)
        spot_num = sum([len(ii) for ii in self.spot_result.values()])
        echo(1, 'City num: {}\nSpot num: {}\nOutput path: {}\nSpend time: {:.2f}s\n'.format(
            city_num, spot_num, output_path, end_time(version, 0)))

    def load_city_list(self):
        ''' load city list '''
        text = basic_req(self.MDD_URL, 3)
        city_list = re.findall(
            '/travel-scenic-spot/mafengwo/(.*?).html" target="_blank">(.*?)(</a>|<span)', text)
        id2map = {int(ii[0]): ii[1].strip()
                  for ii in city_list if ii[0].isdigit()}
        city_list = id2map.keys()
        self.city_list = city_list
        self.id2map = id2map


if __name__ == '__main__':
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    mm = Mafengwo()
    mm.load_spot()
