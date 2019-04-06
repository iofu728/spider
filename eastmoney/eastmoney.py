# -*- coding: utf-8 -*-
# @Author: gunjianpan
# @Date:   2019-03-29 10:35:27
# @Last Modified by:   gunjianpan
# @Last Modified time: 2019-03-29 12:38:54

import codecs
import json
import os
import pickle
import requests
import time

from fontTools.ttLib import TTFont

"""
  * data.eastmoney.com/bbsj/201806/lrb.html 
    .data/
    ├── base.pkl                       // base_unicode list
    ├── base.woff                      // base font file (autoload)
    ├── eastmony%Y-%m-%d_%H:%M:%S.csv  // result .csv
    └── font.woff                      // last time font file
"""
data_dir = 'eastmoney/data/'
base_dir = '%sbase.' % data_dir
base_pkl = '%spkl' % base_dir
base_font = '%swoff' % base_dir
url = 'http://data.eastmoney.com/bbsj/201806/lrb.html'

header = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3',
    'Accept-Encoding': '',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
    'Host': 'data.eastmoney.com',
    'Pragma': 'no-cache',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3747.0 Safari/537.36'
}


def analysis_font(font_url: str, mode=None) -> dict:
    ''' analysis font '''
    if (not os.path.exists(base_font) or not os.path.exists(base_pkl)) and not mode:
        print('base file not exist!!!')
        return

    suffix = font_url.split('.')[-1]
    font = requests.get(font_url, headers=header, timeout=30)
    font_name = '%sfont.%s' % (data_dir, suffix)
    with codecs.open(font_name, 'wb') as f:
        f.write(font.content)
    font_map = TTFont(font_name).getBestCmap()
    ''' prepare base '''
    if not mode is None:
        char_list = [hex(ii).upper().replace('0X', '&#x') +
                     ';' for ii in font_map.keys()]
        base_unicode = [
            int(mode[ii]) if ii in mode else '.' for ii in char_list]
        pickle.dump(base_unicode, codecs.open(base_pkl, 'wb'))
        with codecs.open(base_font, 'wb') as f:
            f.write(font.content)
        return {}

    base_unicode = pickle.load(open(base_pkl, 'rb'))

    base_map = TTFont(base_font).getBestCmap()
    font_dict = {jj: base_unicode[ii]
                 for ii, jj in enumerate(base_map.values())}
    num_dict = {hex(ii).upper().replace('0X', '&#x') + ';': str(font_dict[jj])
                for ii, jj in font_map.items()}
    return num_dict


def load_eastmoney():
    ''' load detail from eastmoney '''
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    req = requests.get(url, headers=header, timeout=30)
    origin_str = req.text

    ''' parse json '''
    begin_index = origin_str.index('defjson')
    end_index = origin_str.index(']}},\r\n')
    json_str = origin_str[begin_index + 9:end_index + 3]
    json_str = json_str.replace('data:', '"data":').replace(
        'pages:', '"pages":').replace('font:', '"font":')
    json_req = json.loads(json_str)
    font_url = json_req['font']['WoffUrl']

    ''' prepare base '''
    if not os.path.exists(base_pkl) or not os.path.exists(base_font):
        print('Prepare base<<<<<<<')
        font_map = json_req['font']['FontMapping']
        font_map = {ii['code']: str(ii['value']) for ii in font_map}
        analysis_font(font_url, font_map)

    ''' load font '''
    font_map = analysis_font(font_url)
    origin_data = json.dumps(json_req['data'])

    ''' load data '''
    for ii, jj in font_map.items():
        origin_data = origin_data.replace(ii, jj)
    replace_data = json.loads(origin_data)
    need_info = ['scode', 'sname', 'parentnetprofit', 'sjltz', 'totaloperatereve', 'tystz', 'operateexp',
                 'saleexp', 'manageexp', 'financeexp', 'totaloperateexp', 'operateprofit', 'sumprofit', 'noticedate']
    data = [ii[jj] for ii in replace_data for jj in need_info]
    result_data = [','.join(data[ii * 14:(ii + 1) * 14])
                   for ii in range(len(replace_data))]

    ''' store data '''
    now_time = time.strftime("%Y-%m-%d_%H:%M:%S", time.localtime(time.time()))
    print(now_time, 'eastmoney data load Success!!!')
    with codecs.open('%seastmony%s.csv' % (data_dir, now_time), 'w', encoding='utf-8') as f:
        f.write('\n'.join(result_data))


if __name__ == '__main__':
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    load_eastmoney()
