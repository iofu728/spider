'''
@Author: gunjianpan
@Date:   2019-03-21 17:34:15
@Last Modified by:   gunjianpan
@Last Modified time: 2019-04-18 19:33:44
'''

import execjs
import requests
import time
import re
import threading

from bs4 import BeautifulSoup

"""
  * shaoq @http
  * shaoq.com:7777
    (single spider not use basic_req)
"""


class Shaoq(object):
    """
    shao q exam
    """

    def __init__(self):
        self.test = 0

    def test_req(self):
        basic_url = 'http://shaoq.com:7777/'
        url = '%sexam' % basic_url
        headers = {
            'pragma': 'no-cache',
            'cache-control': 'no-cache',
            'Host': 'shaoq.com:7777',
            'Referer': 'http://shaoq.com:7777/exam',
            'Cookie': '',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3',
            "Accept-Encoding": "",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3682.0 Safari/537.36",
        }

        '''get cookie'''
        first_req = requests.get(url, headers=headers, verify=False)
        cookies_map = first_req.cookies.get_dict()
        cookies_list = ['%s=%s' % (ii, jj)for ii, jj in cookies_map.items()]
        self.cookie = ','.join(cookies_list)
        headers['Cookie'] = self.cookie

        ''' load img '''
        html = BeautifulSoup(first_req.text, 'html.parser')
        img_list = re.findall('<img src=.*', str(html))
        img_url_list = [index.split('"')[1] for index in img_list]

        threading_list = []
        for index in img_url_list:
            work = threading.Thread(
                target=self.load_img, args=(basic_url + index, headers,))
            threading_list.append(work)
        for work in threading_list:
            work.start()

        ''' wait 5.5s !important'''
        time.sleep(5.5)

        second_req = requests.get(url, headers=headers, verify=False).text
        second_html = BeautifulSoup(second_req, 'html.parser')
        js_compile = execjs.compile(open('exam/shaoq.js').read())
        css_result = js_compile.call('get_css', second_req)
        css_dict = self.load_css(css_result)

        ''' remove script & head & meta & br'''
        remove_html = [ii.extract()for ii in second_html.find_all(
            re.compile('script|meta|head|br'))]

        result_list = second_html.find_all('span')
        for ii in result_list:
            ii.string = css_dict[ii['class'][0]]
        result = second_html.text.replace('\n\n ', '|||').replace('\n', '').replace(
            '\xa0'*8, '\n').replace(' ', '').replace('|||', '\n')
        print(result)

    def load_img(self, img_url, headers):
        '''load img for no wait'''
        headers['Accept'] = 'image/webp,image/apng,image/*,*/*;q=0.8'
        requests.get(img_url, headers=headers, verify=False)

    def load_css(self, css_result: str) -> dict:
        return dict(re.findall(r'\.(.+)::before {content: "(.+)";}', css_result))


if __name__ == '__main__':
    es = Shaoq()
    es.test_req()
