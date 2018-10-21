# -*- coding: utf-8 -*-
# @Author: gunjianpan
# @Date:   2018-10-21 11:00:24
# @Last Modified by:   gunjianpan
# @Last Modified time: 2018-10-21 11:04:31

import threading

from bs4 import BeautifulSoup


class Get_playlist_song():
    """
    1. get playlist id from discover;
    2. get song from play list;
    use url:
    """
    def __init__(self):
        self.classifylist = []

    def run_list(self):
        start = time.time()
        threadings = []
        for id in self.urlslist:
            work = threading.Thread(target=self.get_lists, args=(id,))
            threadings.append(work)
        for work in threadings:
            work.start()
        for work in threadings:
            work.join()
        end = time.time()
        print(end - start)

    def get_lists(self, id):
        if "/" in id or "&" in id:
            f = open(id.split("/" or "&")[0] + '.txt', 'a')
        else:
            f = open(id + '.txt', 'a')

        count = 0
        while True:
            url = "http://music.163.com/discover/playlist/?order=hot&cat=" + \
                urllib.parse.quote_plus(id) + "&limit=35&offset=" + str(count)
            html = requests.get(url, headers=self.headers, verify=False).text
            try:
                table = BeautifulSoup(html, 'html.parser').find(
                    'ul', id='m-pl-container').find_all('li')
            except:
                break
            ids = []
            for item in table:
                ids.append(item.find('div', attrs={'class': 'bottom'}).find(
                    'a').get('data-res-id'))
            count += 35
            f.write(str(ids) + '\n')

    def get_detail_list(self, list_id, file_d, category):
        url = 'http://music.163.com/api/playlist/detail?id=' + str(list_id)
        proxies = {'http': self.proxieslist[random.randint(
            0, len(self.proxieslist) - 1)]}
        try:
            data = requests.get(url, headers=self.headers,
                                proxies=proxies, timeout=5).json()
        except Exception as requestsError:
            print(category + " Error " + list_id + proxies['http'])
            return []
        if data['code'] != 200:
            print(category + " Error " + list_id + proxies['http'])
            return []
        result = data['result']
        musiclist = ""
        tracks = result['tracks']
        if len(tracks) == 1:
            print(category + " Error " + list_id + proxies['http'])
        for track in tracks:
            musiclist += (track['name'] + '\n')
        file_d.write(musiclist)
        self.time += 1
        if self.time % 100 == 0:
            print(self.time)

    def get_detail(self, category):
        iplist = []
        ipfile = open('ip', 'r')
        for index in ipfile.readlines():
            iplist.append(index[0:-1])
        print(iplist)
        self.proxieslist = iplist
        threadings = []
        if "/" in category or "&" in category:
            f = open(category.split("/" or "&")[0] + ".txt", 'r')
        else:
            f = open(category + ".txt", 'r')
        if "/" in category or "&" in category:
            file_d = open(category.split("/" or "&")[0] + "data.txt", 'a')
        else:
            file_d = open(category + "data.txt", 'a')
        for line in f.readlines():
            for id in eval(line.replace('\n', '')):
                work = threading.Thread(
                    target=self.get_detail_list, args=(id, file_d, category))
                threadings.append(work)
        for work in threadings:
            work.start()
        for work in threadings:
            work.join()

    def run_detail(self):
        self.time = 0
        start = time.time()
        threadings = []
        for category in self.urlslist:
            self.get_detail(category)
        end = time.time()
        print(end - start)
        print(self.time)

    def ip_spider(self, numpage):
        file_d = open("ip", 'a')
        headers = {"User-Agent": "IP"}
        for index in range(1, numpage + 1):
            url = 'http://www.xicidaili.com/nn/' + str(index)
            html = requests.get(url, headers=headers, verify=False).text
            bs = BeautifulSoup(html, 'html.parser')
            tem = bs.find_all('tr')
            for index in range(1, len(tem)):
                tds = tem[index].find_all('td')
                if tds[5].text.lower() == 'http':
                    temp = tds[5].text.lower() + '://' + tds[1].text + \
                        ':' + tds[2].text
                    test_url = 'http://music.163.com/api/playlist/detail?id=432853362'
                    proxies = {'http': temp}
                    print(temp)
                    try:
                        data = requests.get(
                            test_url, headers=self.headers, proxies=proxies, timeout=2).json()
                        result = data['result']
                        tracks = result['tracks']
                        print(len(tracks))
                        if len(tracks) != 1:
                            file_d.write(proxies['http'] + '\n')
                    except Exception as e:
                        pass
