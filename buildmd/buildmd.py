# -*- coding: utf-8 -*-
# @Author: gunjianpan
# @Date:   2019-01-31 17:08:32
# @Last Modified by:   gunjianpan
# @Last Modified time: 2019-03-27 23:47:55

import codecs
import threading
import time
import os
import re
import random

from bs4 import BeautifulSoup
from proxy.getproxy import GetFreeProxy
from utils.utils import begin_time, end_time, changeCookie, changeHtmlTimeout, basic_req, can_retry
from urllib.request import urlopen

"""
  * youdao & alimama & taobao @http
  * note.youdao.com/yws/public/note/
  * shoucang.taobao.com/item_collect_n.htm?t={}
  * note.youdao.com/yws/api/personal/sync?method=push&keyfrom=web&cstk=E3CF_lx8
  * pub.alimama.com/favorites/item/batchAdd.json
  * pub.alimama.com/favorites/group/newList.json?toPage=1&perPageSize=40&keyword=&t=
  * note.youdao.com/yws/api/personal/file?method=listRecent&offset=0&limit=30&keyfrom=web&cstk=E3CF_lx8
  * pub.alimama.com/items/search.json?auctionTag=&perPageSize=50&shopTag=&_tb_token_={}
    .data/
    ├── collect        // tb collect file
    ├── cookie         // youdao note cookie
    ├── cookie_alimama // alimama cookie
    └── cookie_collect // tb cookie
"""

get_request_proxy = GetFreeProxy().get_request_proxy
data_dir = 'buildmd/data/'


class Buildmd(object):
    """docstring for buildmd"""

    def __init__(self, ):
        self.request_list = []
        self.failured_map = {}
        # self.get_lists()
        self.img_map = {}
        self.goods = {}
        self.collect = {}
        self.special_list = ['620买长款双面羊绒大衣已经很划算了。',
                             '\xa0\xa0\xa0\xa0版型好看又百搭', '\xa0质量很好', '\xa0\xa0fromlala瘦竹竿', '\xa0mylittlebanana']
        self.title_list = ['衣服', '下装', '包包', '配饰', '鞋子', '鞋子：', '饰品：',
                           '鞋', '包', '鞋包', '鞋包：', '配饰：', '衣服：', '下装：', '包包：', '袜子：']
        self.goods_candidate = []
        self.headers = {}
        self.goods_map = {}
        self.title2map = {}
        self.url2goods = {}
        self.goods_name = {}

    def joint_url(self, tid):
        """
        joint url
        """
        return 'http://note.youdao.com/yws/public/note/' + str(tid) + '?editorType=0&cstk=S0RcfVHi'

    def find_title(self, index: int):
        if int(index) < 5:
            return 'winter18/' + str(index + 1) + '.md'
        if int(index) < 9:
            return 'autumn18/' + str(index - 4) + '.md'
        if int(index) < 19:
            return 'summer18/' + str(index - 8) + '.md'
        if int(index) < 23:
            return 'spring18/' + str(index - 18) + '.md'
        if int(index) < 25:
            return 'winter17/' + str(index - 22) + '.md'

    def get_lists(self):
        """
        get title lists
        """
        url = self.joint_url('3bb0c25eca85e764b6d55a281faf7195')
        title_json = get_request_proxy(url, 1)
        if not title_json:
            if can_retry(url):
                self.get_lists()
            return
        content = BeautifulSoup(
            title_json['content'], 'html.parser').find_all('a')
        self.request_list = [
            re.split(r'/|=', index.text)[-1] for index in content]

    def build_md(self, load_img=False):
        """
        build md
        """
        version = begin_time()

        threadings = []
        for index, tid in enumerate(self.request_list):
            work = threading.Thread(
                target=self.build_md_once, args=(index, tid,))
            threadings.append(work)

        for work in threadings:
            work.start()
        for work in threadings:
            work.join()
        if not load_img:
            return
        img_map = {k: self.img_map[k] for k in sorted(self.img_map.keys())}
        img_threadings = []
        for index in img_map.keys():
            for img_id, img_url in enumerate(img_map[index]):
                work = threading.Thread(
                    target=self.load_img, args=(index, img_id, img_url,))
                img_threadings.append(work)
        for work in img_threadings:
            work.start()
        for work in img_threadings:
            work.join()

        end_time(version)

    def build_md_once(self, index, tid):
        """
        build md in one
        """
        url = self.joint_url(tid)
        title_json = get_request_proxy(url, 1)
        if not title_json:
            if can_retry(url, index):
                self.build_md_once(index, tid)
            return
        content = BeautifulSoup(
            title_json['content'], 'html.parser').find_all('div')
        text = []
        img_href = []
        img_id = 1
        ttid = 1
        img_title = self.find_title(index).split('/')[1][:-3]
        for word in content:
            temp_text = ''
            if word.span and len(word.span.text) and not word.span.text[0].isdigit:
                temp_text = '## ' + word.span.text
                ttid = 1
            if word.img:
                temp_text = '![image](img/' + img_title + str(img_id) + '.jpg)'
                img_href.append(word.img['src'].replace('https', 'http'))
                img_id += 1

            if not len(temp_text):
                temp_text = word.text
                if len(temp_text) and temp_text[0].isdigit():
                    temp_text = str(ttid) + '. **' + \
                        ' '.join(temp_text.split('\xa0')[1:]).strip() + '**'
                    ttid += 1
                if len(temp_text) and temp_text[0:2] == '//':
                    temp_text = str(ttid) + '. **' + \
                        ' '.join(temp_text.split('\xa0')[2:]).strip() + '**'
                    ttid += 1
                if len(temp_text) and (temp_text[0] == '￥' or temp_text[0] == '€'):
                    temp_text = '<a>' + temp_text + '</a>'
            text.append(temp_text)
        with codecs.open(data_dir + self.find_title(index), 'w', encoding='utf-8') as f:
            f.write('\n'.join(text))
        self.img_map[index] = img_href
        print(index, len(img_href))

    def load_img(self, index, img_id, img_url):
        """
        load img
        """
        img = get_request_proxy(img_url, 2)
        if img == True or img == False:
            if can_retry(img_url):
                self.load_img(index, img_id, img_url)
            return
        with codecs.open('buildmd/' + self.find_title(index).split('/')[0] + '/img/' + self.find_title(index).split('/')[1][:-3] + str(img_id + 1) + '.jpg', 'wb') as f:
            f.write(img.content)

    def load_goods(self):
        """
        load goods
        """
        version = begin_time()
        if not os.path.exists('%scookie' % data_dir):
            print('Youdao Note cookie not exist!!!')
            return
        with codecs.open('%scookie' % data_dir, 'r', encoding='utf-8') as f:
            cookie = f.readline()
        changeCookie(cookie[:-1])

        threadings = []
        for index, tid in enumerate(self.request_list):
            work = threading.Thread(
                target=self.load_goods_once, args=(index, tid,))
            threadings.append(work)

        for work in threadings:
            work.start()
        for work in threadings:
            work.join()

        goods = [self.goods[k] for k in sorted(self.goods.keys())]
        goods = sum(goods, [])
        with codecs.open('%sgoods' % data_dir, 'w', encoding='utf-8') as f:
            f.write("\n".join(goods))
        end_time(version)

    def load_goods_once(self, index, tid):
        """
        build md in one
        """
        url = self.joint_url(tid)
        title_json = get_request_proxy(url, 1)
        if not title_json:
            if can_retry(url, index):
                self.load_goods_once(index, tid)
            return
        content = BeautifulSoup(
            title_json['content'], 'html.parser')
        # return content
        content = content.find_all('div')
        if not len(content):
            if can_retry(url, index):
                self.load_goods_once(index, tid)
            return
        # print(len(content))
        text = []
        ttid = 0
        text.append(self.find_title(index))
        good_text = []
        describe = []
        title = ''
        url = ''
        tpud = ''

        for word in content:
            temp_text = ''
            temp_text = word.text
            if not len(temp_text):
                continue
            if len(temp_text) and temp_text not in self.special_list and not '€' in temp_text and ((temp_text[0].isdigit() and (not '【' in temp_text or '【已下架】'in temp_text)) or (temp_text[0] == '\xa0' and not 'http' in temp_text and not '￥' in temp_text and not '微信' in temp_text and not '(' in temp_text) or (word.span and len(word.span.text.replace('\xa0', '')) and (word.span['style'] == 'font-size:16px;color:#fc9db1;font-weight:bold;' or word.span['style'] == 'font-size:16px;color:#1e6792;background-color:#ffffff;font-weight:bold;'))):
                temp_text = temp_text.replace('\xa0', ' ').replace('|', '')
                temp_text = temp_text.replace(
                    '//', '').replace('￥', '').strip()
                if not re.search(r'\d\.\d', temp_text):
                    temp_text = temp_text.replace('.', ' ')
                elif temp_text.count('.') > 1:
                    temp_text = temp_text.replace('.', ' ', 1)
                temp_list = temp_text.split()
                print(temp_list)
                if not len(temp_list):
                    continue
                if ttid:
                    text.append(' '.join([*good_text, *[url, tpud]]))
                url = ''
                tpud = ''
                ttid += 1
                describe = []
                good_text = []
                if len(title):
                    text.append(title)
                    title = ''
                if temp_list[0].isdigit():
                    good_text.append(str(int(temp_list[0])))
                else:
                    good_text.append(str(ttid))
                    good_text.append(temp_list[0])
                if len(temp_list) == 1:
                    continue
                if len(good_text) == 1:
                    good_text.append(temp_list[1])
                elif temp_list[1].isdigit():
                    good_text.append(str(int(temp_list[1])))
                    if len(temp_list) > 2:
                        describe = temp_list[2:]
                if len(temp_list) > 2 and temp_list[2].isdigit():
                    good_text.append(str(int(temp_list[2])))
                elif len(temp_list) > 3 and temp_list[3].isdigit():
                    good_text.append(str(int(temp_list[3])))
                    describe = temp_list[2]
                    if len(temp_list) > 4:
                        describe = [*describe, *temp_list[4:]]
                elif len(temp_list) > 3 and len(temp_list[2]) > 3 and temp_list[2][2:].isdigit():
                    if len(temp_list[3]) > 3 and temp_list[3][2:].isdigit():
                        good_text.append(temp_list[2] + '/' + temp_list[3])
                    else:
                        good_text.append(str(int(temp_list[2][2:])))
                    continue
                elif len(temp_list) > 2 and re.search(r'\d', temp_list[2]):
                    digit_list = re.findall(r"\d+\.?\d*", temp_list[2])
                    good_text.append(digit_list[0])
                    if len(temp_list) > 3:
                        describe = [*describe, *temp_list[3:]]
                elif len(temp_list) > 2:
                    describe.append(temp_list[2])
                if len(temp_list) > 3:
                    describe = temp_list[3:]
            elif 'http' in temp_text:
                temp_text = temp_text.replace('\xa0', '').strip()
                print('http', temp_text)
                url = temp_text
            elif temp_text.count('€') == 2 or temp_text.count('￥') == 2:
                temp_text = temp_text.replace('\xa0', '').strip()
                print('￥', temp_text)
                tpud = temp_text
            elif '【店铺链接】' in temp_text:
                temp_text = temp_text.replace('\xa0', '').strip()
                print('【店铺链接】', temp_text)
                url += temp_text
            elif temp_text in self.title_list:
                print(2, temp_text)
                temp_text = temp_text.replace('\xa0', '')
                title = temp_text
            elif len(good_text) == 1:
                temp_text = temp_text.replace('\xa0', ' ').replace(
                    '.', ' ').replace('￥', '').replace('|', '')
                temp_list = temp_text.split()
                print(3, temp_list)
                if not len(temp_list):
                    continue
                elif len(temp_list) > 1 and temp_list[1].isdigit():
                    good_text.append(temp_list[0])
                    good_text.append(str(int(temp_list[1])))
                    describe = temp_list[2:]
                else:
                    describe.append(temp_text)
            elif temp_text.count('￥') == 1:
                temp_text = temp_text.replace('￥', '').replace(
                    '\xa0', '').replace('|', '').strip()
                digit_list = re.findall(r"\d+\.?\d*", temp_text)
                print('$', digit_list)
                if len(digit_list):
                    good_text.append(digit_list[0])
            else:
                temp_text = temp_text.replace('\xa0', '')
                print(4, temp_text)
                describe.append(temp_text)
        if len(good_text):
            text.append(' '.join([*good_text, *[url, tpud]]))

        text.append(' ')
        self.goods[index] = text
        print(len(text))

    def load_collect(self, page):
        """
        load collect
        """
        version = begin_time()
        if not os.path.exists('%scookie_collect' % data_dir):
            print('TB cookie not exist!!!')
            return
        with codecs.open('%scookie_collect' % data_dir, 'r', encoding='utf-8') as f:
            cookie = f.readline()
        changeCookie(cookie[:-1])
        changeHtmlTimeout(30)
        for block in range(page // 10 + 1):
            begin = block * 10
            end = min(page, (block + 1) * 10)
            threadings = []
            for index in range(begin, end):
                work = threading.Thread(
                    target=self.load_collect_once, args=(index,))
                threadings.append(work)
            for work in threadings:
                work.start()
            for work in threadings:
                work.join()

        collect = [self.collect[k] for k in sorted(self.collect.keys())]
        collect = sum(collect, [])
        with codecs.open('%scollect_wyy' % data_dir, 'w', encoding='utf-8') as f:
            f.write("\n".join(collect))
        end_time(version)

    def load_collect_once(self, index):
        """
        load taobao collect
        """
        baseurl = 'https://shoucang.taobao.com/item_collect_n.htm?t='
        url = baseurl + str(int(round(time.time() * 1000)))
        if index:
            url += 'ifAllTag=0&tab=0&tagId=&categoryCount=0&type=0&tagName=&categoryName=&needNav=false&startRow=' + \
                str(30 * index)

        collect_html = basic_req(url, 0)
        if collect_html != True and collect_html != False:
            collect_list = collect_html.find_all('li', class_=["J_FavListItem g-i-item fav-item ", "J_FavListItem g-i-item fav-item isinvalid",
                                                               "J_FavListItem g-i-item fav-item istmall ", "J_FavListItem g-i-item fav-item istmall isinvalid"])
            print(len(collect_list))
        if collect_html == True or collect_html == False or not len(collect_list):
            if can_retry(baseurl + str(index), index):
                self.load_collect_once(index)
            return
        text = []
        for collect in collect_list:
            data_id = collect['data-id']
            # data_ownerid = collect['data-ownerid']
            title = collect.find_all('a', class_='img-item-title-link')[0].text

            price = collect.find_all('div', class_='g_price')[0].strong.text if len(
                collect.find_all('div', class_='g_price')) else '0'
            text.append("||".join([data_id, title, price]))

        self.collect[index] = text

    def test_change_youdaoyun(self, atricle_id, body, article_name):
        """
        change youdaoyun article demo
        @param 'buildmd/data/cookie': cookie in youdaoyun web
        @param            article_id: change article No.
        @param:                 body: change article body
        @param:         article_name: change article name
        """
        url = 'https://note.youdao.com/yws/api/personal/sync?method=push&keyfrom=web&cstk=E3CF_lx8'
        headers = {
            'pragma': 'no-cache',
            'cache-control': 'no-cache',
            'Cookie': '',
            'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
            'Accept': 'application/json, text/plain, */*',
            "Accept-Encoding": "",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3682.0 Safari/537.36",
            'Origin': 'https://note.youdao.com',
            'Referer': 'https://note.youdao.com/web'
        }
        if not os.path.exists('%scookie' % data_dir):
            print('Youdao Note cookie not exist!!!')
            return

        with codecs.open('%scookie' % data_dir, 'r', encoding='utf-8') as f:
            cookie = f.readline()
        headers['cookie'] = cookie[:-1]
        headers['Host'] = url.split('/')[2]

        file_list_url = 'https://note.youdao.com/yws/api/personal/file?method=listRecent&offset=0&limit=30&keyfrom=web&cstk=E3CF_lx8'
        file_data = {
            'cstk': 'E3CF_lx8'
        }
        ca = basic_req(file_list_url, 11, data=file_data, header=headers)
        if not len(ca):
            print('List Error')
            return
        change_data_origin = ca[atricle_id]['fileEntry']
        body_string = ['<?xml version="1.0"?><note xmlns="http://note.youdao.com" schema-version="1.0.3" file-version="0"><head/><body><para><coId>12-1550424181958</coId><text>',
                       body, '</text><inline-styles/><styles/></para></body></note>']
        change_data = {
            'name': article_name,
            'fileId': change_data_origin['id'],
            'parentId': change_data_origin['parentId'],
            'domain': change_data_origin['domain'],
            'rootVersion': -1,
            'sessionId': '',
            'modifyTime': int(round(time.time())),
            'bodyString': "".join(body_string),
            'transactionId': change_data_origin['id'],
            'transactionTime': int(round(time.time())),
            'orgEditorType': change_data_origin['orgEditorType'],
            'tags': change_data_origin['tags'],
            'cstk': 'E3CF_lx8'
        }
        print(change_data)
        cb = basic_req(url, 12, data=change_data, header=headers)
        return cb

    def bulk_import_alimama(self):
        """
        bulk import alimama
        """

        version = begin_time()
        if not os.path.exists('%scollect_wyy' % data_dir):
            print('Collect File not exist!!!')
            return
        with codecs.open('%scollect_wyy' % data_dir, 'r', encoding='utf-8') as f:
            goods = f.readlines()
        self.goods_candidate = [index.split('||')[0] for index in goods]
        goods_len = len(self.goods_candidate)

        self.headers = {
            'pragma': 'no-cache',
            'X-Requested-With': 'XMLHttpRequest',
            'cache-control': 'no-cache',
            'Cookie': '',
            'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            "Accept-Encoding": "",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3682.0 Safari/537.36",
            'Origin': 'http://pub.alimama.com',
            'Referer': 'http://pub.alimama.com/promo/search/index.htm?q=%E7%AC%AC%E5%9B%9B%E5%8D%81%E4%B9%9D%E5%A4%A9%2019%E6%98%A5%E5%AD%A3&_t=1550891362391'
        }
        if not os.path.exists('%scookie_alimama' % data_dir):
            print('alimama cookie not exist!!!')
            return
        with codecs.open('%scookie_alimama' % data_dir, 'r', encoding='utf-8') as f:
            cookie = f.readlines()
        url_list = [
            'https://pub.alimama.com/favorites/group/newList.json?toPage=1&perPageSize=40&keyword=&t=',
            str(int(round(time.time() * 1000))),
            '&_tb_token_=',
            cookie[1][:-1],
            '&pvid=',
            cookie[2][:-1]
        ]
        url = ''.join(url_list)
        self.headers['Cookie'] = cookie[0][:-1]
        self.headers['Host'] = url.split('/')[2]

        group_list = basic_req(url, 2, header=self.headers)

        if group_list.status_code != 200 or group_list.json()['info']['message'] == 'nologin':
            print('group_list error')
            return
        group_list = group_list.json()['data']['result']
        group_list = [index['id'] for index in group_list]

        print(group_list)

        assert len(group_list) > (goods_len - 1) // 200

        threadings = []
        for index in range((goods_len - 1) // 200 + 1):
            work = threading.Thread(
                target=self.bulk_import_alimama_once, args=(index, group_list[index], ))
            threadings.append(work)
        for work in threadings:
            work.start()
        for work in threadings:
            work.join()
        end_time(version)

    def bulk_import_alimama_once(self, index, group_id):
        """
        bulk import alimama
        """

        url = 'http://pub.alimama.com/favorites/item/batchAdd.json'
        if not os.path.exists('%scookie_alimama' % data_dir):
            print('alimama cookie not exist!!!')
            return
        with codecs.open('%scookie_alimama' % data_dir, 'r', encoding='utf-8') as f:
            cookie = f.readlines()

        goods_len = len(self.goods_candidate)
        begin_id = index * 200
        end_id = min(goods_len, (index + 1) * 200)

        goods_ids = self.goods_candidate[begin_id:end_id]
        update_data = {
            'groupId': group_id,
            'itemListStr': ','.join(goods_ids),
            't': str(int(round(time.time() * 1000))),
            '_tb_token_': cookie[1][:-1],
            'pvid': cookie[2][:-1]
        }
        print(update_data)
        cb = basic_req(url, 12, data=update_data, header=headers)
        if cb.status_code == 200 and cb.json()['info']['message'] != 'nologin':
            print(cb.json()['data'])

    def match_goods(self):

        self.headers = {
            'pragma': 'no-cache',
            'X-Requested-With': 'XMLHttpRequest',
            'cache-control': 'no-cache',
            'Cookie': '',
            'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            "Accept-Encoding": "",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3682.0 Safari/537.36",
        }

        version = begin_time()
        changeHtmlTimeout(30)
        block_size = 10
        if not os.path.exists('%sgoods' % data_dir):
            print('goods file not exist!!!')
            return
        with codecs.open('%sgoods' % data_dir, 'r', encoding='utf-8') as f:
            wait_goods = f.readlines()
        goods_url = [re.findall('http.* ', index)[0].strip(
        ).replace('https', 'http') if 'http' in index and not '【' in index else False for index in wait_goods]

        if not os.path.exists('%scollect_wyy' % data_dir):
            print('collect file not exist!!!')
            return
        with codecs.open('%scollect_wyy' % data_dir, 'r', encoding='utf-8') as f:
            collect = f.readlines()
        self.title2map = {
            index.split("||")[1]: index.split("||")[0] for index in collect}

        threadings = []
        for index, url in enumerate(goods_url):
            if url == False:
                continue
            work = threading.Thread(
                target=self.get_goods_id_first, args=(url, index,))
            threadings.append(work)
        url_len = len(threadings)
        for index in range((url_len - 1) // block_size + 1):
            begin_id = index * block_size
            end_id = min(url_len, (index + 1) * block_size)
            threadings_block = threadings[begin_id: end_id]

            for work in threadings_block:
                work.start()
            for work in threadings_block:
                work.join()

            time.sleep(random.randint(0, 9))

        write_body = [' '.join([self.goods_map[index], body])
                      if index in self.goods_map else (' '.join([self.url2goods[goods_url[index]], body]) if goods_url[index] in self.url2goods else body) for index, body in enumerate(wait_goods)]
        with codecs.open('%sgoods_one' % data_dir, 'w', encoding='utf-8') as f:
            f.write(''.join(write_body))
        end_time(version)

    def get_goods_id_first(self, origin_url, index):
        """
        get goods id first
        """

        origin_url = origin_url.replace('https', 'http')
        # first_result = get_request_proxy(origin_url, 0)
        first_result = basic_req(origin_url, 0, header=self.headers)

        if not first_result or len(first_result.find_all('script')) < 2:
            if can_retry(origin_url):
                self.get_goods_id_first(origin_url, index)
            return

        wait = first_result.find_all('script')[1].text
        if not '"title":"' in wait:
            return
        title = re.findall(
            '"title":".*","', wait)[0].split('","')[0].split('":"')[1]
        if title in self.title2map:
            self.goods_map[index] = self.title2map[title]
            self.url2goods[origin_url] = self.title2map[title]

            print(self.title2map[title])
        else:
            print(title)
        # url = re.findall('var url = .*\'', wait)[0].split('\'')[1]
        # self.get_goods_second(url, index)

    def get_goods_second(self, url, index):

        second_result = basic_req(url, 0, header=self.headers)
        # second_result = get_request_proxy(url, 0)

        if not second_result or not len(second_result.find_all('input')):
            if can_retry(url):
                self.get_goods_second(url, index)
            return
        goods_id = second_result.find_all('input')[6]['value']
        print(goods_id)
        self.goods_map[index] = goods_id

    def search_goods(self):
        version = begin_time()
        if not os.path.exists('%swait' % data_dir):
            print('wait file not exist!!!')
            return
        with codecs.open('%swait' % data_dir, 'r', encoding='utf-8') as f:
            wait = f.readlines()
        threadings = []
        for index, goods_name in enumerate(wait):
            work = threading.Thread(
                target=self.search_goods_once, args=(goods_name[:-1], index, ))
            threadings.append(work)
        for work in threadings:
            work.start()
            time.sleep(random.randint(5, 9))
        for work in threadings:
            work.join()
        goods_name = [self.goods_name[k]
                      for k in sorted(self.goods_name.keys())]
        with codecs.open('%swait_goods' % data_dir, 'w', encoding='utf-8') as f:
            f.write('\n'.join(goods_name))
        end_time(version)

    def search_goods_once(self, goods_name, index):
        if not os.path.exists('%scookie_alimama' % data_dir):
            print('alimama cookie not exist!!!')
            return
        with codecs.open('%scookie_alimama' % data_dir, 'r', encoding='utf-8') as f:
            cookie = f.readlines()
        url_list = [
            'https://pub.alimama.com/items/search.json?auctionTag=&perPageSize=50&shopTag=&_tb_token_=',
            cookie[1][:-1],
            '&pvid=',
            cookie[2][:-1],
            '&t=',
            str(int(round(time.time() * 1000))),
            '&_t=',
            str(int(round(time.time() * 1000))),
            '&q=',
            goods_name
        ]
        headers = {
            'pragma': 'no-cache',
            'X-Requested-With': 'XMLHttpRequest',
            'cache-control': 'no-cache',
            'Cookie': '',
            'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            "Accept-Encoding": "",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3682.0 Safari/537.36",
        }
        headers['Cookie'] = cookie[0][:-1]
        ca = basic_req(''.join(url_list), 2, header=headers)
        if ca.status_code != 200 or not 'data' in ca.json():
            if can_retry(''.join(url_list)):
                self.search_goods_once(goods_name, index)
            return
        page_list = ca.json()['data']['pageList']
        title = ['||'.join([str(index['auctionId']), goods_name, str(
            index['zkPrice'])]) for index in page_list][0]
        self.goods_name[index] = title
        print(title)
