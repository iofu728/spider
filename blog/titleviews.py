# -*- coding: utf-8 -*-
# @Author: gunjianpan
# @Date:   2019-02-09 11:10:52
# @Last Modified by:   gunjianpan
# @Last Modified time: 2020-01-04 14:41:30

import argparse
import codecs
import datetime
import re
import os
import threading

from bs4 import BeautifulSoup
from proxy.getproxy import GetFreeProxy
from util.db import Db
from util.util import begin_time, end_time, changeCookie, basic_req, can_retry, changeHtmlTimeout, echo, mkdir, read_file, echo, get_accept

"""
  * blog @http
  * www.zhihu.com/api/v4/creator/content_statistics
  * www.jianshu.com/u/
  * blog.csdn.net
    .data/
    ├── cookie   // zhihu cookie
    ├── google   // google analysis data
    ├── slug     // blog title slug
    └── title    // blog title list
"""
proxy_req = GetFreeProxy().proxy_req
data_dir = 'blog/data/'


class TitleViews(object):
    ''' script of load my blog data -> analysis '''
    CSDN_URL = 'https://blog.csdn.net/iofu728'
    JIANSHU_URL = 'https://www.jianshu.com/u/2e0f69e4a4f0'
    ZHIHU_URL = 'https://www.zhihu.com/api/v4/creator/content_statistics/'

    def __init__(self):
        self.Db = Db("blog")
        self.local_views = {}
        self.title_map = {}
        self.title2slug = {}
        self.zhihu_views = {}
        self.zhihu_id = {}
        self.jianshu_views = {}
        self.jianshu_id = {}
        self.csdn_views = {}
        self.csdn_id = {}
        self.exist_data = {}
        self.getTitleMap()
        self.insert_sql = '''INSERT INTO title_views(`title_name`, `local_views`, `zhihu_views`, `csdn_views`, `jianshu_views`, `zhihu_id`, `csdn_id`, `jianshu_id`) VALUES %s'''
        self.update_sql = '''REPLACE INTO title_views(`id`, `title_name`, `local_views`, `zhihu_views`, `csdn_views`, `jianshu_views`, `zhihu_id`, `csdn_id`, `jianshu_id`, `created_at`) VALUES %s'''
        self.new_day_sql = '''INSERT INTO page_views(`date`, `existed_views`, `existed_spider`) VALUES %s'''

    def loadLocalView(self):
        '''  load local view '''
        test = read_file('{}google'.format(data_dir))[7:]
        for index in test:
            arr = index.split(',')
            slug = self.matchSlug(arr[0])
            if slug is None or slug not in self.title_map:
                continue
            print(slug + ' ' + str(arr[1]) + ' ' + arr[0])
            if slug in self.local_views:
                self.local_views[slug] += int(arr[1])
            else:
                self.local_views[slug] = int(arr[1])

    def getTitleMap(self):
        ''' get title map '''
        slug = read_file('{}slug'.format(data_dir))
        title = read_file('{}title'.format(data_dir))
        self.title_map = {tempslug.split(
            '"')[1]: title[num].split('"')[1] for num, tempslug in enumerate(slug)}
        title2slug = {
            self.title_map[index]: index for index in self.title_map.keys()}
        noemoji_title = {self.filter_emoji(
            self.title_map[index]).replace('\u200d', ''): index for index in self.title_map.keys()}
        self.title2slug = {**noemoji_title, **title2slug}

    def matchSlug(self, pattern: str):
        ''' match slug '''
        arr = re.search(r'\/([^\/]+).html', pattern)
        return None if arr is None else arr.group(1)

    def getZhihuView(self):
        cookie = ''.join(read_file('{}cookie'.format(data_dir)))
        changeCookie(cookie)
        url_basic = [
            self.ZHIHU_URL,
            'articles?order_field=object_created&order_sort=descend&begin_date=2018-09-01&end_date=',
            datetime.datetime.now().strftime("%Y-%m-%d"),
            '&page_no='
        ]
        url = ''.join(url_basic)

        json = self.get_request('{}{}'.format(url, 1), 1, lambda i: not i)
        if not json:
            return
        if not 'data' in json:
            if 'code' in json:
                echo('0|warning', json)
            return
        echo(3, 'zhihu', json)
        for index in json['data']:
            zhihu_title = index['title']
            zhihu_id = int(index['url_token'])
            zhihu_count = int(index['read_count'])

            if zhihu_title in self.title2slug:
                temp_slug = self.title2slug[zhihu_title]
                self.zhihu_id[temp_slug] = zhihu_id
                self.zhihu_views[temp_slug] = zhihu_count
            elif zhihu_id in self.zhihu_id_map:
                temp_slug = self.zhihu_id_map[zhihu_id]
                self.zhihu_id[temp_slug] = zhihu_id
                self.zhihu_views[temp_slug] = zhihu_count
            else:
                echo('0|debug', index['title'])

        for index in range(1, json['count'] // 10):
            echo(1, 'zhihu', index)
            json = self.get_request('{}{}'.format(url, 1 + index), 1, lambda i: not i)
            echo(2, 'zhihu', json)
            if not json:
                continue
            for index in json['data']:
                zhihu_title = index['title']
                zhihu_id = int(index['url_token'])
                zhihu_count = int(index['read_count'])

                if zhihu_title in self.title2slug:
                    temp_slug = self.title2slug[zhihu_title]
                    self.zhihu_id[temp_slug] = zhihu_id
                    self.zhihu_views[temp_slug] = zhihu_count
                elif zhihu_id in self.zhihu_id_map:
                    temp_slug = self.zhihu_id_map[zhihu_id]
                    self.zhihu_id[temp_slug] = zhihu_id
                    self.zhihu_views[temp_slug] = zhihu_count
                else:
                    echo('0|debug', index['title'])

    def get_request(self, url: str, types: int, functs, header: dict = {}):
        if len(header):
            req = basic_req(url, types, header=header)
        else:
            req = basic_req(url, types)

        if functs(req):
            if can_retry(url):
                self.get_request(url, types, functs, header)
            return
        return req

    def getJianshuViews(self):
        ''' get jianshu views '''
        header = {'accept': get_accept('html')}

        for rounds in range(1, 4):
            url = self.JIANSHU_URL
            if rounds > 1:
                url += '?order_by=shared_at&page={}'.format(rounds)
            echo('1|debug', 'jianshu req url:', url)
            html = self.get_request(url, 0, lambda i: not i or not len(
                i.find_all('div', class_='content')), header)
            if html is None:
                echo(0, 'None')
                return
            for index in html.find_all('li', class_=["", 'have-img']):
                if len(index.find_all('i')) < 3:
                    continue
                title = index.find_all('a', class_='title')[
                    0].text.replace('`', '')
                jianshu_id = int(index['data-note-id'])
                jianshu_count = int(index.find_all('a')[-2].text)
                if title in self.title2slug:
                    temp_slug = self.title2slug[title]
                    self.jianshu_id[temp_slug] = jianshu_id
                    self.jianshu_views[temp_slug] = jianshu_count
                elif jianshu_id in self.jianshu_id_map:
                    temp_slug = self.jianshu_id_map[jianshu_id]
                    self.jianshu_id[temp_slug] = jianshu_id
                    self.jianshu_views[temp_slug] = jianshu_count
                else:
                    echo(1, title)

    def getCsdnViews(self):
        ''' get csdn views '''

        for index in range(1, 3):
            url = self.CSDN_URL
            if index > 1:
                url += '/article/list/{}?'.format(index)
            echo(1, 'csdn url', url)

            html = self.get_request(url, 0, lambda i: i is None or not i or not len(
                i.find_all('p', class_='content')))
            if html is None:
                echo(0, 'None')
                return
            for div_lists in html.find_all('div', class_='article-item-box csdn-tracking-statistics'):
                if 'style' in div_lists.attrs:
                    continue
                csdn_id = int(div_lists['data-articleid'])
                title = div_lists.a.contents[2].replace(
                    '\n', '').strip().replace('`', '')
                csdn_count = int(div_lists.find_all(
                    'span', class_='read-num')[0].span.text)
                if title in self.title2slug:
                    temp_slug = self.title2slug[title]
                    self.csdn_id[temp_slug] = csdn_id
                    self.csdn_views[temp_slug] = csdn_count
                elif csdn_id in self.csdn_id_map:
                    temp_slug = self.csdn_id_map[csdn_id]
                    self.csdn_id[temp_slug] = csdn_id
                    self.csdn_views[temp_slug] = csdn_count
                else:
                    echo(1, title)

    def filter_emoji(self, desstr, restr=''):
        ''' filter emoji '''
        desstr = str(desstr)
        try:
            co = re.compile(u'[\U00010000-\U0010ffff]')
        except re.error:
            co = re.compile(u'[\uD800-\uDBFF][\uDC00-\uDFFF]')
        return co.sub(restr, desstr)

    def init_db(self):
        self.loadLocalView()
        self.getZhihuView()
        self.getJianshuViews()
        self.getCsdnViews()
        insert_list = []
        for index in self.title_map.keys():
            insert_list.append((index, self.local_views[index] if index in self.local_views else 0, self.zhihu_views[index] if index in self.zhihu_views else 0, self.csdn_views[index] if index in self.csdn_views else 0, self.jianshu_views[index]
                                if index in self.jianshu_views else 0, self.zhihu_id[index] if index in self.zhihu_id else 0, self.csdn_id[index] if index in self.csdn_id else 0, self.jianshu_id[index] if index in self.jianshu_id else 0))
        # return insert_list
        results = self.Db.insert_db(self.insert_sql % str(insert_list)[1:-1])
        if results:
            if len(insert_list):
                print('Insert ' + str(len(insert_list)) + ' Success!')
        else:
            pass

    def select_all(self):
        result = self.Db.select_db(
            "SELECT `id`, `title_name`, `local_views`, `zhihu_views`, `csdn_views`, `jianshu_views`, `zhihu_id`, `csdn_id`, `jianshu_id`, `created_at` from title_views where `is_deleted`=0")
        if result == False:
            print("SELECT Error!")
        else:
            self.exist_data = {index[1]: list(index) for index in result}
            self.zhihu_id_map = {index[6]: index[1]
                                 for index in result if index[6]}
            self.csdn_id_map = {index[7]: index[1]
                                for index in result if index[7]}
            self.jianshu_id_map = {index[8]: index[1]
                                   for index in result if index[8]}
            for index in self.exist_data:
                self.exist_data[index][-1] = self.exist_data[index][-1].strftime(
                    '%Y-%m-%d %H:%M:%S')

    def update_view(self):
        changeHtmlTimeout(10)
        wait_map = {}
        self.select_all()
        self.getZhihuView()
        self.getJianshuViews()
        self.getCsdnViews()
        for index in self.zhihu_views.keys():
            if self.zhihu_views[index] == self.exist_data[index][3] and self.zhihu_id[index] == self.exist_data[index][6]:
                continue
            wait_map[index] = self.exist_data[index]
            wait_map[index][3] = self.zhihu_views[index]
            wait_map[index][6] = self.zhihu_id[index]
        for index in self.csdn_views.keys():
            if self.csdn_views[index] == self.exist_data[index][4] and self.csdn_id[index] == self.exist_data[index][7]:
                continue
            if index not in wait_map:
                wait_map[index] = self.exist_data[index]
            wait_map[index][4] = self.csdn_views[index]
            wait_map[index][7] = self.csdn_id[index]
        for index in self.jianshu_views.keys():
            if self.jianshu_views[index] == self.exist_data[index][5] and self.jianshu_id[index] == self.exist_data[index][8]:
                continue
            wait_map[index] = self.exist_data[index]
            wait_map[index][5] = self.jianshu_views[index]
            wait_map[index][8] = self.jianshu_id[index]
        update_list = [tuple(index) for index in wait_map.values()]
        # return update_list:q
        if not len(update_list):
            return
        results = self.Db.update_db(self.update_sql % str(update_list)[1:-1])
        if results:
            if len(update_list):
                print('Update ' + str(len(update_list)) + ' Success!')
        else:
            pass

    def new_day(self):
        day_data = self.Db.select_db(
            "SELECT `today_views`, `existed_views` from page_views order by `id` desc limit 1")
        if not os.path.exists('../blog/log/basic'):
            print('File not exist!!!')
            return
        with codecs.open("../blog/log/basic", 'r', encoding='utf-8') as f:
            existed_spider = int(f.readlines()[1])
        today_date = datetime.datetime.now().strftime('%Y-%m-%d')
        new_day_list = [(today_date, day_data[0][0] +
                         day_data[0][1], existed_spider)]
        results = self.Db.insert_db(self.new_day_sql % str(new_day_list)[1:-1])
        if results:
            if len(new_day_list):
                print('New day update' + str(len(new_day_list)) + ' Success!')
        else:
            pass

    def load_csdn_img(self):
        ''' load csdn img '''
        mkdir(data_dir)
        urls = ['/article/list/2?', '']
        article_ids = []
        for url in urls:
            req = basic_req('{}{}'.format(self.CSDN_URL, url), 3)
            article_ids.extend(re.findall('data-articleid="(\w*?)"', req))
        echo(0, article_ids)
        article_thread = [threading.Thread(
            target=self.load_csdn_img_batch, args=(ii,)) for ii in article_ids]
        for work in article_thread:
            work.start()
        for work in article_thread:
            work.join()

    def load_csdn_img_batch(self, article_id: int):
        url = '{}/article/details/{}'.format(self.CSDN_URL, article_id)
        req = proxy_req(url, 3)
        if not 'iofu728' in req:
            if can_retry(url):
                self.load_csdn_img_batch(article_id)
            return
        img_lists = re.findall('"(https://cdn.nlark.com.*)" alt', req)
        img_thread = [threading.Thread(target=self.load_csdn_img_load, args=(
            jj, article_id, ii))for ii, jj in enumerate(img_lists)]
        echo(1, 'Article Need Load {} Img...'.format(len(img_lists)))
        for work in img_thread:
            work.start()
        for work in img_thread:
            work.join()

    def load_csdn_img_load(self, img_url: str, article_id: int, idx: int):
        img_dir = '{}{}/'.format(data_dir, article_id)
        img_path = '{}{}.png'.format(img_dir, idx)
        if os.path.exists(img_path):
            return
        req = proxy_req(img_url, 2)
        if type(req) == bool or req is None:
            if can_retry(img_url):
                self.load_csdn_img_load(img_url, article_id, idx)
            return
        mkdir(img_dir)
        with open(img_path, 'wb') as f:
            f.write(req.content)


if __name__ == '__main__':
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    parser = argparse.ArgumentParser(description='gunjianpan blog backup code')
    parser.add_argument('--model', type=int, default=1, metavar='N',
                        help='model update or new day')
    model = parser.parse_args().model
    bb = TitleViews()
    if model == 1:
        bb.update_view()
    else:
        bb.new_day()
        bb.update_view()
