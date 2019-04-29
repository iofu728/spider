# -*- coding: utf-8 -*-
# @Author: gunjianpan
# @Date:   2019-01-25 01:36:52
# @Last Modified by:   gunjianpan
# @Last Modified time: 2019-03-27 23:51:45

import codecs
import threading
import time
import pandas as pd
import pkuseg
import re

from proxy.getproxy import GetFreeProxy
from util.db import Db
from util.util import begin_time, end_time, basic_req, can_retry

proxy_req = GetFreeProxy().proxy_req

"""
  * news @http
  * www.baidu.com/s?
  * www.jianshu.com/u/
  * blog.csdn.net
"""


class Get_baidu_news():
    """
    get baidu news
    """

    def __init__(self):
        self.failuredmap = {}
        self.summarizations = {}

    def get_summarization(self):
        """
        get summarization from http://news.baidu.com/ns?word=%E6%AF%92%E7%8B%97%E8%82%89&tn=news&from=news&cl=2&rn=20&ct=1
        """

        version = begin_time()
        threadings = []
        for index in range(30):
            work = threading.Thread(
                target=self.summarization_once, args=(index,))
            threadings.append(work)

        for work in threadings:
            # time.sleep(.5)
            work.start()
        for work in threadings:
            work.join()

        summarizations = [self.summarizations[k]
                          for k in sorted(self.summarizations.keys())]
        self.summarizations = sum(summarizations, [])
        with codecs.open('news_posion.txt', 'w', encoding='utf-8') as f:
            f.write('\n'.join(self.summarizations))
        end_time(version)

    def summarization_once(self, index):
        """
        get html from news
        """
        print(index)
        texts = []
        if index:
            url = 'https://www.baidu.com/s?ie=utf-8&mod=1&isbd=1&isid=919fab3c0002c9f1&wd=%E5%81%B7%E7%8B%97&pn=730&oq=%E5%81%B7%E7%8B%97&tn=baiduhome_pg&ie=utf-8&rsv_idx=2&rsv_pq=919fab3c0002c9f1&rsv_t=7e30ggF%2BMa91oOURk1bMtN8af5unSwOR08TodNBB%2F%2B6B6RBEwUi8l8IAe28ACA%2B8b5I5&gpc=stf%3D1517038564%2C1548574564%7Cstftype%3D1&tfflag=1&bs=%E5%81%B7%E7%8B%97&rsv_sid=undefined&_ss=1&clist=28bc21fb856a58b7%09350102124f079888%0928bc21fb856a58b7%0928bc2159845c1cf3%0928bc2015823fa56b%0928a121fb84a7d1a6&hsug=&f4s=1&csor=2&_cr1=34767&pn=' + \
                str(index * 20)
        else:
            url = 'http://news.baidu.com/ns?rn=20&ie=utf-8&cl=2&ct=1&bs=%E6%AF%92%E7%8B%97%E8%82%89&rsv_bp=1&sr=0&f=8&prevct=no&tn=news&word=%E5%81%B7%E7%8B%97'
        news_lists = proxy_req(url, 0)
        if not news_lists:
            if can_retry(url):
                self.summarization_once(index)
            return
        summarization_lists = news_lists.find_all('div', class_='result')
        if not len(summarization_lists):
            if can_retry(url):
                self.summarization_once(index)
            return
        print('num: ', len(summarization_lists), url)
        for summarization in summarization_lists:
            temp_text = summarization.text.replace('\n', '').replace(
                '\xa0', '').replace('\t', '').strip()
            temp_text = ' '.join(temp_text.split())
            texts.append(temp_text[:-8])
        self.summarizations[int(index)] = texts


class Get_google_news():
    """
    get google news
    """

    def __init__(self):
        self.failuredmap = {}
        self.summarizations = {}
        self.hrefs = {}

    def get_summarization(self):
        """
        get summarization from https://www.google.com.hk/search?q=%E6%AF%92%E7%8B%97%E8%82%89&newwindow=1&safe=strict&tbm=nws&ei=FK1KXJ3EJbWx0PEPytmq2AI&start=0&sa=N&ved=0ahUKEwidnv-7p4jgAhW1GDQIHcqsCis4ChDy0wMIRw&biw=1627&bih=427&dpr=2
        """

        version = begin_time()
        threadings = []
        for index in range(25):
            work = threading.Thread(
                target=self.summarization_once, args=(index,))
            threadings.append(work)

        for work in threadings:
            time.sleep(1)
            work.start()
        for work in threadings:
            work.join()

        summarizations = [self.summarizations[k]
                          for k in sorted(self.summarizations.keys())]
        self.summarizations = sum(summarizations, [])

        hrefs = [self.hrefs[k] for k in sorted(self.hrefs.keys())]
        self.hrefs = sum(hrefs, [])
        with codecs.open('google_steal.txt', 'w', encoding='utf-8') as f:
            f.write('\n'.join(self.summarizations))
        with codecs.open('google_steal_href.txt', 'w', encoding='utf-8') as f:
            f.write('\n'.join(self.hrefs))
        end_time(version)

    def summarization_once(self, index):
        """
        get html from news
        """
        print(index)
        texts = []
        hrefs = []
        if index:
            url = 'https://www.google.com.hk/search?q=%E5%81%B7%E7%8B%97&newwindow=1&safe=strict&tbm=nws&ei=PcVKXJKRIc7s8AXB05e4Dw&sa=N&ved=0ahUKEwjSo5nBvojgAhVONrwKHcHpBfcQ8tMDCFE&biw=1627&bih=427&dpr=2&start=' + \
                str(index * 10)
        else:
            url = 'https://www.google.com.hk/search?q=%E5%81%B7%E7%8B%97&newwindow=1&safe=strict&tbm=nws&ei=O8VKXJ7nFoP_8QX1oK_gDA&start=0&sa=N&ved=0ahUKEwje8JTAvojgAhWDf7wKHXXQC8w4ChDy0wMISQ&biw=1627&bih=427&dpr=2'
        news_lists = basic_req(url, 0)
        href_lists = news_lists.find_all('a', class_=['RTNUJf', 'l lLrAF'])
        summarization_lists = news_lists.find_all('div', class_='gG0TJc')

        if not len(href_lists) or not len(summarization_lists):
            if can_retry(url):
                self.summarization_once(index)
            return
        print('num: ', len(summarization_lists), url)
        for href in href_lists:
            hrefs.append(href['href'])
        for summarization in summarization_lists:
            temp_text = summarization.text.replace('\n', '').replace(
                '\xa0', '').replace('\t', '').replace('...', '').strip()
            temp_text = ' '.join(temp_text.split())
            texts.append(temp_text)
        self.summarizations[int(index)] = texts
        self.hrefs[int(index)] = hrefs


class find_location(object):
    """
    find location
    """

    def __init__(self):
        self.Db = Db("china_regions")
        china = pd.read_csv('news/china_city_list.csv', encoding='gbk')
        self.province = list(china.groupby(by=['Province']).count().axes[0])
        self.city = list(china.groupby(by=['City']).count().axes[0])
        self.filelists = ['google_steal.txt', 'google_posion.txt', 'bjh', 'bjh_detail', 'bjh_detail_poison',
                          'news_steal.txt', 'news_poison.txt']
        self.city_province = {}
        self.province_map = {}

        self.pre_data()
        for index, row in china.iterrows():
            self.city_province[row['City']] = row['Province']

    def search_location(self):
        word = ''
        count = 0
        for file in self.filelists:
            temp_word_list = codecs.open(
                file, 'r', encoding='utf-8').readlines()
            count += len(temp_word_list)
            word += " ".join(temp_word_list)
        # return word
        print(count)
        word_province = {}
        word_city = {}
        word_city_pro = {}
        for index in self.province:
            temp_num = word.count(index)
            if temp_num:
                word_province[index] = temp_num
        for index in self.city:
            temp_num = word.count(index)
            if temp_num:
                word_city[index] = temp_num
        for index in word_city:
            province = self.city_province[index]
            if province in word_city_pro:
                word_city_pro[province] += word_city[index]
            else:
                word_city_pro[province] = word_city[index]
        print(sum(word_province.values()), sum(
            word_city.values()), sum(word_city_pro.values()))
        return word_province, word_city, word_city_pro

    def participles_word(self):
        """
        participles word
        """
        version = begin_time()

        for file in self.filelists:
            pkuseg.test(file, file[:-4] + '_pkuseg.txt',
                        model_name='../Model_retrieval/pkuseg', nthread=20)
        end_time(version)

    def pre_data(self):
        """
        load city key-value from mysql
        """
        province = self.Db.select_db(
            'select * from china_regions where level=1')
        self.province_map = {int(index[2]): index[3][:3] if len(index[3]) == 4 or len(
            index[3]) == 6 else index[3][:2] for index in province}

        city = self.Db.select_db(
            'select * from china_regions where level=2')
        city_state = [index for index in city if index[3][-1:] == '州']
        seg = pkuseg.pkuseg()
        city_state = {seg.cut(index[3])[0] if len(seg.cut(index[3])[0]) > 1 else seg.cut(
            index[3])[0] + seg.cut(index[3])[1]: int(index[1]) for index in city if index[3][-1:] == '州'}
        seg = pkuseg.pkuseg(model_name='../Model_retrieval/pkuseg')
        city_state1 = {seg.cut(index)[0] if len(seg.cut(index)[0]) > 1 else seg.cut(
            index)[0] + seg.cut(index)[1]: city_state[index] for index in city_state}
        city_area = {index[3][:-2]: int(index[1])
                     for index in city if '地区' in index[3]}
        city_other = {index[3][:-1]: int(index[1])
                      for index in city if index[3][-1:] == '市' or index[3][-1:] == '盟'}
        self.city_province = {**city_state1, **city_area, **city_other}
        self.city_province = {
            index: self.province_map[self.city_province[index]] for index in self.city_province}
        county = self.Db.select_db(
            'select * from china_regions where level=3')
        county_area_pre = {index for index in county if index[3][-1] == '区'}
        county_area_two = {index[3][:-2]: int(index[1][:2]) for index in county_area_pre if len(
            index[3]) > 3 and (index[3][-2] == '矿' or index[3][-2] == '林')}
        # print('芒' in county_area_two, 'two')
        county_area_state = {seg.cut(index[3][:-2])[0]: int(index[1][:2])
                             for index in county_area_pre if len(index[3]) > 2 and index[3][-2] == '族'}
        # print('芒' in county_area_state, 'state')
        county_area_other = {index[3][:-1]: int(index[1][:2]) for index in county_area_pre if len(
            index[3]) > 2 and index[3][-2] != '族' and index[3][-2] != '林' and index[3][-2] != '矿'}
        # print('芒' in county_area_other, 'other')
        county_county_pre = {index for index in county if index[3][-1] == '县'}
        county_county_two = {index[3]: int(
            index[1][:2]) for index in county_county_pre if len(index[3]) == 2}
        # print('芒' in county_county_two, 'two')
        seg = pkuseg.pkuseg()
        county_county_state = {seg.cut(index[3])[0] if len(seg.cut(index[3])[0]) > 1 else seg.cut(index[3])[0] + seg.cut(
            index[3])[1]: int(index[1][:2]) for index in county_county_pre if len(index[3]) > 2 and index[3][-3:-1] == '自治'}
        county_county_state = {
            index[:-2] if '族' in index and len(index) > 3 else index: county_county_state[index] for index in county_county_state}
        # print('芒' in county_county_state, 'state')
        county_county_other = {
            index[3][:-1]: int(index[1][:2]) for index in county_county_pre if index[3][-3:-1] != '自治' and len(index[3]) > 2}
        # print('芒' in county_county_other, 'other')
        county_city = {index[3][:-1] if len(index[3]) > 2 else index[3]: int(index[1][:2])
                       for index in county if index[3][-1] == '市'}
        # print('芒' in county_city, 'city')
        county_domain = {index[3][:4]: int(
            index[1][:2]) for index in county if index[3][-1] == '域'}
        # print('芒' in county_domain, 'domain')
        county_other = {index[3]: int(
            index[1][:2]) for index in county if index[3][-1] == '盟' or index[3][-1] == '岛'}
        # print('芒' in county_other, 'other')
        county_province = {**county_area_two, **county_area_state, **county_area_other, **county_county_two,
                           **county_county_state, **county_county_other, **county_city, **county_domain, **county_other}
        county_province = {
            index: self.province_map[county_province[index]] for index in county_province}
        self.city_province = {**self.city_province, **county_province}
        print({index for index in self.city_province if len(index) == 1})

    def test_province(self, maps, words):
        word_city = {}
        for index in maps:
            temp_num = words.count(index)
            province = maps[index]
            if temp_num:
                if province in word_city:
                    word_city[province] += temp_num
                else:
                    word_city[province] = temp_num
        print(sum(word_city.values()))
        return word_city


class Get_baidu():
    """
    get info from baidu
    """

    def __init__(self):
        self.failuredmap = {}
        self.total_map = {}
        self.text_map = {}
        self.word = {}
        self.find_location = find_location()

    def get_summarization(self):
        """
        get summarization from http://news.baidu.com/ns?word=%E6%AF%92%E7%8B%97%E8%82%89&tn=news&from=news&cl=2&rn=20&ct=1
        """

        version = begin_time()
        threadings = []
        for index in range(75):
            work = threading.Thread(
                target=self.summarization_once, args=(index,))
            threadings.append(work)

        for work in threadings:
            # time.sleep(.5)
            work.start()
        for work in threadings:
            work.join()
        # self.text_map = self.total_map[0]

        # for index in list(range(1, len(self.total_map))):
        #     for ids in self.total_map[index]:
        #         if ids in self.text_map:
        #             self.text_map[ids] += self.total_map[index][ids]
        #         else:
        #             self.text_map[ids] = self.total_map[index][ids]
        # print(sum(self.text_map))
        word = [self.word[k] for k in sorted(self.word.keys())]
        with codecs.open('test', 'w', encoding='utf-8') as f:
            f.write("\n".join(word))
        end_time(version)

    def summarization_once(self, index):
        """
        get html from news
        """
        print(index)
        texts = []
        url = 'https://www.baidu.com/s?ie=utf-8&mod=1&isbd=1&isid=919fab3c0002c9f1&wd=%E5%81%B7%E7%8B%97&oq=%E5%81%B7%E7%8B%97&tn=baiduhome_pg&ie=utf-8&rsv_idx=2&rsv_pq=919fab3c0002c9f1&rsv_t=7e30ggF%2BMa91oOURk1bMtN8af5unSwOR08TodNBB%2F%2B6B6RBEwUi8l8IAe28ACA%2B8b5I5&gpc=stf%3D1517038564%2C1548574564%7Cstftype%3D1&tfflag=1&bs=%E5%81%B7%E7%8B%97&rsv_sid=undefined&_ss=1&clist=28bc21fb856a58b7%09350102124f079888%0928bc21fb856a58b7%0928bc2159845c1cf3%0928bc2015823fa56b%0928a121fb84a7d1a6&hsug=&f4s=1&csor=2&_cr1=34767&pn=' + \
            str(index * 10)
        news_lists = proxy_req(url, 0)
        if not news_lists:
            if can_retry(url):
                self.summarization_once(index)
            return
        test = news_lists.find_all(
            'div', class_=['c-row c-gap-top-small', 'c-span18 c-span-last'])
        word = self.cleantxt(news_lists.text)
        if not len(word):
            if can_retry(url):
                self.summarization_once(index)
            return
        temp_map = self.find_location.test_province(
            self.find_location.city_province, word)
        self.total_map[int(index)] = temp_map
        self.word[index] = word

    def cleantxt(self, raw):
        fil = re.compile(u'[^\u4e00-\u9fa5]+', re.UNICODE)
        return fil.sub(' ', raw)


class Get_baidu_bjh():
    """
    get info from baidu bjh
    """

    def __init__(self):
        self.failuredmap = {}
        self.fail = []
        self.href_map = {}
        self.text_map = {}
        self.word = {}
        self.word_list = {}

    def get_href(self):
        """
        get summarization from http://news.baidu.com/ns?word=%E6%AF%92%E7%8B%97%E8%82%89&tn=news&from=news&cl=2&rn=20&ct=1
        """

        version = begin_time()
        threadings = []
        for index in range(71):
            work = threading.Thread(
                target=self.href_once, args=(index,))
            threadings.append(work)

        for work in threadings:
            # time.sleep(.5)
            work.start()
        for work in threadings:
            work.join()
        href_map = [self.href_map[k] for k in sorted(self.href_map.keys())]
        self.href_map = sum(href_map, [])
        with codecs.open('bjh_href_poison.txt', 'w', encoding='utf-8') as f:
            f.write("\n".join(self.href_map))
        end_time(version)

    def href_once(self, index):
        """
        get html from news
        """
        print(index)
        texts = []
        url = 'https://www.baidu.com/s?tn=news&rtt=4&bsst=1&cl=2&wd=毒狗肉&pn=' + \
            str(index * 10)
        news_lists = proxy_req(url, 0)
        if not news_lists:
            if can_retry(url):
                self.href_once(index)
            return
        test = news_lists.find_all('div', class_='result')
        if not len(test):
            if can_retry(url):
                self.href_once(index)
            return
        href_list = [index.a['href'] for index in test]
        self.href_map[int(index)] = href_list

    def cleantxt(self, raw):
        fil = re.compile(u'[^\u4e00-\u9fa5]+', re.UNICODE)
        return fil.sub(' ', raw)

    def get_detail(self):
        """
        get summarization from http://news.baidu.com/ns?word=%E6%AF%92%E7%8B%97%E8%82%89&tn=news&from=news&cl=2&rn=20&ct=1
        """

        version = begin_time()
        threadings = []
        with codecs.open('bjh_href_poison.txt', 'r', encoding='utf-8') as f:
            href_list = f.readlines()
        for index, url in enumerate(href_list):
            work = threading.Thread(
                target=self.detail_once, args=(index, url,))
            threadings.append(work)

        for work in threadings:
            # time.sleep(.5)
            work.start()
        for work in threadings:
            work.join()
        word_list = [self.word_list[k] for k in sorted(self.word_list.keys())]
        with codecs.open('bjh_detail_poison', 'w', encoding='utf-8') as f:
            f.write("\n".join(word_list))
        self.failuredmap = {}
        with codecs.open('bjh.log', 'w', encoding='utf-8') as f:
            f.write('\n'.join(self.fail))
        self.fail = []
        end_time(version)

    def detail_once(self, index, url):
        """
        get html from news
        """
        # print(index)
        news_lists = proxy_req(url, 0)
        if not news_lists:
            if can_retry(url):
                self.detail_once(index, url)
            return
        test = news_lists.find_all(
            'div', class_=['article-content', 'mth-editor-content', 'con-news-art', 'Custom_UnionStyle'])
        if not len(test):
            test = self.cleantxt(news_lists.text)
            if not len(test):
                if can_retry(url):
                    self.detail_once(index, url)
                return
            self.word_list[index] = test
            return
        word_list = ''.join([index.text for index in test]
                            ).replace('\u3000', '').replace('\n', '')
        self.word_list[int(index)] = word_list
