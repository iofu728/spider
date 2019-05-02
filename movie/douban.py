'''
@Author: gunjianpan
@Date:   2019-04-29 20:04:28
@Last Modified by:   gunjianpan
@Last Modified time: 2019-04-30 00:18:37
'''

import random
import string
import time
import threading
import urllib

from proxy.getproxy import GetFreeProxy
from util.util import basic_req, changeHeaders, can_retry, echo, begin_time, end_time

proxy_req = GetFreeProxy().proxy_req

data_dir = 'movie/data/'


class DouBan(object):
    ''' get douban movie info '''

    API_BASIC_URL = 'http://api.douban.com/v2/movie/'
    API_PROXY_URL = 'http://douban.uieee.com/v2/movie/'
    BASIC_URL = 'https://movie.douban.com/'
    SEARCH_TAG_URL = '{}j/search_tags?type=movie&source='.format(BASIC_URL)
    SEARCH_SUBJECT_URL = '{}j/search_subjects?'.format(BASIC_URL)

    def __init__(self):
        self.movie_id_dict = {}
        self.page_size = 100
        self.sort_list = ['time', 'recommend', 'rank']
        self.get_movie_tag()

    def generate_cookie(self, type: str = 'explore'):
        ''' generate bid '''
        bid = "".join(random.sample(string.ascii_letters + string.digits, 11))
        changeHeaders({"Cookie": "bid={}".format(bid),
                       'Referer': '{}{}'.format(self.BASIC_URL, type)})

    def get_movie_lists(self):
        ''' get movie list '''

        version = begin_time()
        movie_get = []
        for ii in self.tag:
            for jj in self.sort_list:
                movie_get.append(threading.Thread(
                    target=self.get_movie_lists_once, args=('movie', ii, jj, 0,)))
        for ww in movie_get:
            ww.start()
        for ww in movie_get:
            ww.join()
        movie_list = set(sum(self.movie_id_dict.values(), []))
        output_path = '{}douban_movie_id.txt'.format(data_dir)
        with open(output_path, 'w') as f:
            f.write('\n'.join([str(ii) for ii in movie_list]))
        movie_num = len(movie_list)
        echo(1, 'Movie num: {}\nOutput path: {}\nSpend time: {:.2f}s\n'.format(
            movie_num, output_path, end_time(version, 0)))

    def get_movie_lists_once(self, types: str, tag: str, sorts: str, page_start: int):
        ''' get movie lists once '''
        params_dict = {'type': types, 'tag': urllib.parse.quote(tag), 'sort': sorts,
                       'page_limit': self.page_size, 'page_start': page_start}
        params = ['{}={}'.format(ii, jj) for ii, jj in params_dict.items()]
        url = '{}{}'.format(self.SEARCH_SUBJECT_URL, '&'.join(params))
        self.generate_cookie()
        movie_json = proxy_req(url, 1)
        echo(2, url, 'loading')
        if movie_json is None or not 'subjects' in movie_json:
            if can_retry(url):
                time.sleep(5 + random.random() * 5)
                self.get_movie_lists_once(types, tag, sorts, page_start)
            else:
                echo(0, url, 'Failed')
            return
        movie_list = [int(ii['id']) for ii in movie_json['subjects']]
        index = '{}{}{}'.format(tag, sorts, page_start)
        self.movie_id_dict[index] = movie_list
        if len(movie_list):
            self.get_movie_lists_once(
                types, tag, sorts, page_start + self.page_size)

    def get_movie_tag(self):
        ''' get movie tag '''
        tag = basic_req(self.SEARCH_TAG_URL, 1)
        self.tag = tag['tags']


if __name__ == "__main__":
    mv = DouBan()
    mv.get_movie_lists()
