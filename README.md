<p align="center"><a href="https://wyydsb.xin" target="_blank" rel="noopener noreferrer"><img width="100" src="https://cdn.nlark.com/yuque/0/2018/jpeg/104214/1540358574166-46cbbfd2-69fa-4406-aba9-784bf65efdf9.jpeg" alt="Spider logo"></a></p>
<h1 align="center">Spider Press Man</h1>

[![GitHub](https://img.shields.io/github/license/iofu728/spider-press.svg?style=popout-square)](https://github.com/iofu728/spider-press/blob/master/LICENSE)
[![GitHub tag](https://img.shields.io/github/tag/iofu728/spider-press.svg?style=popout-square)](https://github.com/iofu728/spider-press/releases)
[![GitHub code size in bytes](https://img.shields.io/github/languages/code-size/iofu728/spider-press.svg?style=popout-square)](https://github.com/iofu728/spider-press)

<div align="center"><strong>高可用代理IP池 高并发爬虫 不均匀的压力分发系统 </strong></div>
<div align="center"><strong>Highly Available Proxy IP Pool, Highly Concurrent Spider, Uneven Pressure Distribution System</strong></div>

## Proxy pool

> proxy pool is the heart of this project.

* <u>`Highly Available Proxy IP Pool`</u>
  + By obtaining data from Gatherproxy, Goubanjia, xici etc. Free Proxy WebSite
  + Analysis the Goubanjia port data
  + Quickly verify IP availability
  + Cooperate with Requests to automatically assign proxy Ip, with Retry mechanism, fail to write DB mechanism
  + two model for proxy shell
    * model 1: load gather proxy && update proxy list file
    * model 2: update proxy pool db && test available

## Application

1. <u>`Netease Music song playlist crawl`</u> - <u>`netease/netease_music_db.py`</u>
  + classify -> playlist id -> song_detail
  + V1 Write file, One run version, no proxy, no record progress mechanism
  + V1.5 Small amount of proxy IP
  + V2 Proxy IP pool, Record progress, Write to MySQL
    - Optimize the write to DB `Load data/ Replace INTO`
2. <u>`Press Test System`</u> - <u>`press/press.py`</u>
  + By highly available proxy IP pool to pretend user.
  + Give some web service uneven pressure
  + To do: press uniform
3. <u>`google & baidu info crawl`</u> - <u>`news/news.py`</u>
  + get news from search engine by Proxy Engine
  + one model: careful analysis `DOM`
  + the other model: rough analysis `Chinese words`
4. <u>`Youdao Note documents crawl`</u> -`buildmd/buildmd.py`
  + load data from `youdaoyun`
  + by series of rules to deal data to .md
5. <u>`csdn && zhihu && jianshu view info crawl`</u> - <u>`blog/titleview.py`</u>
6. <u>`PKU Class brush`</u> - <u>`brushclass/brushclass.py`</u>
  + when your zhongyi's class have places, It will send you some email.
7. <u>`ZiMuZu download list crawl`</u> - <u>`zimuzu/zimuzu.py`</u>
  + when you want to download lots of show like Season 22, Season 21.
  + If click one by one, It is very boring, so zimuzu.py is all you need.
  + The thing you only need do is to wait the program run.
  + And you copy the Thunder url for one to download the movies.
  + Now The Winter will coming, I think you need it to review `<Game of Thrones>`.

**----To be continued----**

## Development

**All model base on `proxy.getproxy`, so it is very !import.**

`docker` is in the road.

```bash
$ git clone https://github.com/iofu728/spider.git
$ cd spider
$ pip install -r requirement.txt

# you shoudld load file from http://gatherproxy.com
$ ipython

# using proxy pool
$ from  proxy.getproxy import GetFreeProxy
$ requests = GetFreeProxy()
$ requests.gatherproxy(0) # load http proxy to pool
$ requests.get_request_proxy(url, types) # use proxy

# proxy shell
$ ipython blog/titleviews.py -- --model=1 >> log 2>&1 # model = 1: load gather model or python blog/titleviews.py --model=1 >> proxy.log 2>&1
$ ipython blog/titleviews.py -- --model=0 >> log 2>&1 # model = 0: update gather model

```

## Structure
```bash
.
├── LICENSE                        // LICENSE
├── README.md                      // README
├── blog
│   └── titleviews.py              // Zhihu && CSDN && jianshu
├── brushclass
│   └── brushclass.py              // PKU elective
├── buildmd
│   └── buildmd.py                 // Youdao Note
├── log
├── netease
│   ├── netease_music_base.py
│   ├── netease_music_db.py        // Netease Music
│   └── table.sql
├── news
│   └── news.py                    // Google && Baidu
├── press
│   └── press.py                   // Press text
├── proxy
│   ├── gatherproxy
│   ├── getproxy.py                // Proxy pool
│   └── table.sql
├── requirement.txt
├── utils
│   ├── agent                      // random User-Agent
│   ├── db.py
│   └── utils.py
└── zimuzu
    └── zimuzu.py                  // zimuzi
```

## Design document
* [Netease Music Spider for DB](https://wyydsb.xin/other/neteasedb.html)
* [Netease Music Spider](https://wyydsb.xin/other/netease.html)

