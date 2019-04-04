# -*- coding: utf-8 -*-
# @Author: gunjianpan
# @Date:   2019-03-29 10:35:27
# @Last Modified by:   gunjianpan
# @Last Modified time: 2019-03-29 12:38:54

import requests
import json
import time
import os

from fontTools.ttLib import TTFont

"""
  * data.eastmoney.com/bbsj/201806/lrb.html 
    .data/
    └── base.woff  // base woff load from data.eastmonet.com
"""
data_dir = 'eastmoney/data/'
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


req = requests.get(url, headers=header, timeout=30)


def analysis_font(font_url: str):
    ''' analysis font '''
    if not os.path.exists('%sbase.woff' % data_dir):
        print('base.woff not exist!!!')
        return
    suffix = font_url.split('.')[-1]
    font = requests.get(font_url, headers=header, timeout=30)
    font_name = '%sfont.%s' % (data_dir, suffix)
    with open('%sfont.%s' % (data_dir, suffix), 'wb') as f:
        f.write(font.content)
    font_map = TTFont(font_name).getBestCmap()
    base_map = TTFont('%sbase.woff' % data_dir).getBestCmap()

    font_dict = {jj: ii+1 for ii,
                 jj in enumerate(list(base_map.values())[1:])}
    font_dict[list(base_map.values())[0]] = '.'
    num_dict = {hex(ii).upper().replace('0x', '&#x'): font_dict[jj]
                for ii, jj in font_map.items()}
    return num_dict


try:
    origin_str = req.text
    begin_index = origin_str.index('defjson')
    end_index = origin_str.index(']}},\r\n')
    json_str = origin_str[begin_index + 9:end_index + 3]
    json_str = json_str.replace('data:', '"data":').replace(
        'pages:', '"pages":').replace('font:', '"font":')
    json_req = json.loads(json_str)
    # font_map = json_req['font']['FontMapping']
    font_url = json_req['font']['WoffUrl']
    font_map = analysis_font(font_url)
    origin_data = json.dumps(json_req['data'])
    font_map = {ii['code']: str(ii['value']) for ii in font_map}
    for ii, jj in font_map.items():
        origin_data = origin_data.replace(ii, jj)
    replace_data = json.loads(origin_data)
    need_info = ['scode', 'sname', 'parentnetprofit', 'sjltz', 'totaloperatereve', 'tystz', 'operateexp',
                 'saleexp', 'manageexp', 'financeexp', 'totaloperateexp', 'operateprofit', 'sumprofit', 'noticedate']
    data = [ii[jj] for ii in replace_data for jj in need_info]
    result_data = [','.join(data[ii * 14:(ii + 1) * 14])
                   for ii in range(len(replace_data))]
    now_time = time.strftime("%Y-%m-%d_%H:%M:%S", time.localtime(time.time()))
    with open('%seastmony%s.csv' % (data_dir, now_time), 'w') as f:
        f.write('\n'.join(result_data))


except Exception as e:
    raise
