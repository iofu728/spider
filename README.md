<p align="center">
<a href="https://wyydsb.xin" target="_blank" rel="noopener noreferrer">
<img width="100" src="https://cdn.nlark.com/yuque/0/2018/jpeg/104214/1540358574166-46cbbfd2-69fa-4406-aba9-784bf65efdf9.jpeg" alt="Spider logo"></a></p>
<h1 align="center">Spider Man</h1>

[![GitHub](https://img.shields.io/github/license/iofu728/spider.svg?style=popout-square)](https://github.com/iofu728/spider/master/LICENSE)
[![GitHub tag](https://img.shields.io/github/tag/iofu728/spider.svg?style=popout-square)](https://github.com/iofu728/spider/releases)
[![GitHub code size in bytes](https://img.shields.io/github/languages/code-size/iofu728/spider.svg?style=popout-square)](https://github.com/iofu728/spider)

<div align="center"><strong>高可用代理IP池 高并发生成器 一些实战经验</strong></div>
<div align="center"><strong>Highly Available Proxy IP Pool, Highly Concurrent Request Builder, Some Application</strong></div>

- [keyword](#keyword)
- [Proxy pool](#proxy-pool)
- [Application](#application)
  - [`Netease`](#netease)
  - [`Press Test System`](#press-test-system)
  - [`News`](#news)
  - [`Youdao Note`](#youdao-note)
  - [`blog`](#blog)
  - [`Brush Class`](#brush-class)
  - [`zimuzu`](#zimuzu)
  - [`Bilibili`](#bilibili)
  - [`shaoq`](#shaoq)
  - [`eastmoney`](#eastmoney)
- [Development](#development)
- [Structure](#structure)
- [Design document](#design-document)
  - [exam.Shaoq](#examshaoq)
    - [Idea](#idea)
    - [Requirement](#requirement)
    - [Trouble Shooting](#trouble-shooting)
      - [Can't get true html](#cant-get-true-html)
      - [Error: Cannot find module 'jsdom'](#error-cannot-find-module-jsdom)
      - [remove subtree & edit subtree & re.findall](#remove-subtree--edit-subtree--refindall)
  - [eastmoney.eastmoney](#eastmoneyeastmoney)
    - [Idea](#idea-1)
    - [Trouble Shooting](#trouble-shooting-1)
      - [error: unpack requires a buffer of 20 bytes](#error-unpack-requires-a-buffer-of-20-bytes)
      - [How to analysis font](#how-to-analysis-font)
      - [configure file](#configure-file)
      - [UnicodeEncodeError: 'ascii' codec can't encode characters in position 7-10: ordinal not in range(128)](#unicodeencodeerror-ascii-codec-cant-encode-characters-in-position-7-10-ordinal-not-in-range128)
      - [`bilibili` some url return 404 like `http://api.bilibili.com/x/relation/stat?jsonp=jsonp&callback=__jp11&vmid=`](#bilibili-some-url-return-404-like-httpapibilibilicomxrelationstatjsonpjsonpcallbackjp11vmid)

## keyword

- Big data store
- High concurrency requests
- Support Websocket
- method for font cheat
- method for js compile
- Some Application

## Proxy pool

> proxy pool is the heart of this project.

- <u>`Highly Available Proxy IP Pool`</u>
  - By obtaining data from `Gatherproxy`, `Goubanjia`, `xici` etc. Free Proxy WebSite
  - Analysis the Goubanjia port data
  - Quickly verify IP availability
  - Cooperate with Requests to automatically assign proxy Ip, with Retry mechanism, fail to write DB mechanism
  - two model for proxy shell
    - model 1: load gather proxy list && update proxy list file
    - model 2: update proxy pool db && test available
  - one common proxy api
    - `from proxy.getproxy import GetFreeProxy`
    - `get_request_proxy = GetFreeProxy().get_request_proxy`
    - `get_request_proxy(url: str, types: int, data=None, test_func=None, header=None)`
  - also one comon basic req api
    - `from util import baisc_req`
    - `basic_req(url: str, types: int, proxies=None, data=None, header=None)`

## Application

### `Netease`

1. <u>`Netease Music song playlist crawl`</u> - <u>`netease/netease_music_db.py`</u>

- problem: `big data store`
- classify -> playlist id -> song_detail
- V1 Write file, One run version, no proxy, no record progress mechanism
- V1.5 Small amount of proxy IP
- V2 Proxy IP pool, Record progress, Write to MySQL
  - Optimize the write to DB `Load data/ Replace INTO`

### `Press Test System`

2. <u>`Press Test System`</u> - <u>`press/press.py`</u>

- problem: `high concurrency requests`
- By highly available proxy IP pool to pretend user.
- Give some web service uneven pressure
- To do: press uniform

### `News`

3. <u>`google & baidu info crawl`</u> - <u>`news/news.py`</u>

- get news from search engine by Proxy Engine
- one model: careful analysis `DOM`
- the other model: rough analysis `Chinese words`

### `Youdao Note`

4. <u>`Youdao Note documents crawl`</u> -`buildmd/buildmd.py`

- load data from `youdaoyun`
- by series of rules to deal data to .md

### `blog`

5. <u>`csdn && zhihu && jianshu view info crawl`</u> - <u>`blog/titleview.py`</u>

### `Brush Class`

6. <u>`PKU Class brush`</u> - <u>`brushclass/brushclass.py`</u>

- when your expected class have places, It will send you some email.

### `zimuzu`

7. <u>`ZiMuZu download list crawl`</u> - <u>`zimuzu/zimuzu.py`</u>

- when you want to download lots of show like Season 22, Season 21.
- If click one by one, It is very boring, so zimuzu.py is all you need.
- The thing you only need do is to wait the program run.
- And you copy the Thunder url for one to download the movies.
- Now The Winter will coming, I think you need it to review `<Game of Thrones>`.

### `Bilibili`

8. <u>`Get av data by http`</u> - <u>`bilibili/bilibili.py`</u>

- `homepage rank` -> check `tids` -> to check data every 2min(during on rank + one day)
- monitor every rank av -> star num & basic data

9. <u>`Get av data by websocket`</u> - <u>`bilibili/bsocket.py`</u>

- base on websocket
- byte analysis
- heart beat

10. <u>`Get comment data by http`</u> - <u>`bilibili/bilibili.py`</u>

- load comment from `/x/v2/reply`

### `shaoq`

11. <u>`Get text data by compiling javascript`</u> - <u>`exam/shaoq.py`</u>

[more detail](#examshaoq)

### `eastmoney`

12. <u>`Get stock info by analysis font`</u> - <u>`eastmoney/eastmoney.py`</u>

- font analysis

[more detail](#eastmoneyeastmoney)

**----To be continued----**

## Development

**All model base on `proxy.getproxy`, so it is very !import.**

`docker` is in the road.

```bash
$ git clone https://github.com/iofu728/spider.git
$ cd spider
$ pip3 install -r requirement.txt

# using proxy pool
$ python proxy/getproxy.py --model=1         # model = 1: load gather proxy (now need have qualification to request google)
$ python proxy/getproxy.py --model=1         # model = 0: test proxy

$ from  proxy.getproxy import GetFreeProxy
$ get_request_proxy = GetFreeProxy().get_request_proxy
$ requests.gatherproxy(0) # load http proxy to pool
$ requests.get_request_proxy(url, types) # use proxy

# proxy shell
$ python blog/titleviews.py --model=1 >> log 2>&1 # model = 1: load gather model or python blog/titleviews.py --model=1 >> proxy.log 2>&1
$ python blog/titleviews.py --model=0 >> log 2>&1 # model = 0: update gather model

```

## Structure

```bash
.
├── LICENSE
├── README.md
├── bilibili
│   ├── analysis.py                // data analysis
│   ├── bilibili.py                // bilibili basic
│   └── bsocket.py                 // bilibili websocket
├── blog
│   └── titleviews.py              // Zhihu && CSDN && jianshu
├── brushclass
│   └── brushclass.py              // PKU elective
├── buildmd
│   └── buildmd.py                 // Youdao Note
├── eastmoney
│   └── eastmoney.py               // font analysis
├── exam
│   ├── shaoq.js                   // jsdom
│   └── shaoq.py                   // compile js shaoq
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
│   ├── getproxy.py                // Proxy pool
│   └── table.sql
├── requirement.txt
├── utils
│   ├── db.py
│   └── utils.py
└── zimuzu
    └── zimuzu.py                  // zimuzi
```

## Design document

- [Netease Music Spider for DB](https://wyydsb.xin/other/neteasedb.html)
- [Netease Music Spider](https://wyydsb.xin/other/netease.html)

### exam.Shaoq

#### Idea

1. get cookie
2. request image
3. requests after 5.5s
4. compile javascript code -> get css
5. analysic css

#### Requirement

```sh
pip3 install PyExecJS
yarn install add jsdom # npm install jsdom PS: not global
```

#### Trouble Shooting

##### Can't get true html

- Wait time must be 5.5s.
- So you can use `threading` or `await asyncio.gather` to request image

- [Coroutines and Tasks](https://docs.python.org/3/library/asyncio-task.html)

##### Error: Cannot find module 'jsdom'

> jsdom must install in local not in global

- [Cannot find module 'jsdom'](https://github.com/scala-js/scala-js/issues/2642)

##### remove subtree & edit subtree & re.findall

```py
subtree.extract()
subtree.string = new_string
parent_tree.find_all(re.compile('''))
```

- [extract()](https://www.crummy.com/software/BeautifulSoup/bs4/doc/#extract)
- [NavigableString](https://www.crummy.com/software/BeautifulSoup/bs4/doc/#navigablestring)
- [A regular expression](https://www.crummy.com/software/BeautifulSoup/bs4/doc/#a-regular-expression)

### eastmoney.eastmoney

#### Idea

1. get data from html -> json
2. get font map -> transform num
3. or load font analysis font(contrast withe base)

#### Trouble Shooting

##### error: unpack requires a buffer of 20 bytes

- requests.text -> str,
- requests.content -> byte

- [Struct.error: unpack requires a buffer of 16 bytes](https://stackoverflow.com/questions/51110525/struct-error-unpack-requires-a-buffer-of-16-bytes)

##### How to analysis font

- use fonttools
- get TTFont().getBestCamp()
- contrast with base

##### configure file

- cfg = ConfigParser()
- cfg.read(assign_path, 'utf-8')
- [13.10read configure file](https://python3-cookbook.readthedocs.io/zh_CN/latest/c13/p10_read_configuration_files.html)

##### UnicodeEncodeError: 'ascii' codec can't encode characters in position 7-10: ordinal not in range(128)

- read/write in `utf-8`
- with codecs.open(filename, 'r/w', encoding='utf-8')

##### `bilibili` some url return 404 like `http://api.bilibili.com/x/relation/stat?jsonp=jsonp&callback=__jp11&vmid=`

basic_req auto add `host` to headers, but this url can't request in ‘Host’
