<p align="center">
<a href="https://wyydsb.xin" target="_blank" rel="noopener noreferrer">
<img width="100" src="https://cdn.nlark.com/yuque/0/2018/jpeg/104214/1540358574166-46cbbfd2-69fa-4406-aba9-784bf65efdf9.jpeg" alt="Spider logo"></a></p>
<h1 align="center">Spider Man</h1>

[![GitHub](https://img.shields.io/github/license/iofu728/spider.svg?style=popout-square)](https://github.com/iofu728/spider/blob/master/LICENSE)
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
      - [int32](#int32)
      - [js charCodeAt() in py](#js-charcodeat-in-py)
      - [python access file fold import](#python-access-file-fold-import)
      - [generate char list](#generate-char-list)
      - [Can't get cookie in `document.cookie`](#cant-get-cookie-in-documentcookie)
      - [ctrip cookie analysis](#ctrip-cookie-analysis)
      - [some function](#some-function)
      - [Get current timezone offset](#get-current-timezone-offset)

## keyword

- Big data store
- High concurrency requests
- Support WebSocket
- method for font cheat
- method for js compile
- Some Application

## Proxy pool

> proxy pool is the heart of this project.

- <u>`Highly Available Proxy IP Pool`</u>
  - By obtaining data from `Gatherproxy`, `Goubanjia`, `xici` etc. Free Proxy WebSite
  - Analysis of the Goubanjia port data
  - Quickly verify IP availability
  - Cooperate with Requests to automatically assign proxy Ip, with Retry mechanism, fail to write DB mechanism
  - two models for proxy shell
    - model 1: load gather proxy list && update proxy list file(need over the GFW, your personality passwd in http://gatherproxy.com to `proxy/data/passage` one line by username, one line by passwd)
    - model 0: update proxy pool db && test available
  - one common proxy api
    - `from proxy.getproxy import GetFreeProxy`
    - `get_request_proxy = GetFreeProxy().get_request_proxy`
    - `get_request_proxy(url: str, types: int, data=None, test_func=None, header=None)`
  - also one common basic req api
    - `from util import basic_req`
    - `basic_req(url: str, types: int, proxies=None, data=None, header=None)`
  - if you want spider by using proxy
    - because access proxy web need over the GFW, so maybe you can't use `model 1` to download proxy file.
    - 1. download proxy txt from http://gatherproxy.com
    - 2. cp download_file proxy/data/gatherproxy
    - 3. python proxy/getproxy.py --model==0

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
- The thing you only need do is to wait for the program run.
- And you copy the Thunder URL for one to download the movies.
- Now The Winter will come, I think you need it to review `<Game of Thrones>`.

### `Bilibili`

8. <u>`Get av data by http`</u> - <u>`bilibili/bilibili.py`</u>

- `homepage rank` -> check `tids` -> to check data every 2min(during on rank + one day)
- monitor every rank av -> star num & basic data

9. <u>`Get av data by websocket`</u> - <u>`bilibili/bsocket.py`</u>

- base on WebSocket
- byte analysis
- heartbeat

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

**All model base on `proxy.getproxy`, so it is a very !import.**

`docker` is on the road.

```bash
$ git clone https://github.com/iofu728/spider.git
$ cd spider
$ pip3 install -r requirement.txt

# using proxy pool
$ python proxy/getproxy.py --model=1         # model = 1: load gather proxy (now need have qualification to request google)
$ python proxy/getproxy.py --model=0         # model = 0: test proxy

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

1. get data from HTML -> json
2. get font map -> transform num
3. or load font analysis font(contrast with base)

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

basic_req auto add `host` to headers, but this URL can't request in ‘Host’

##### int32

```python
np.int32()
```

##### js charCodeAt() in py

[python 中如何实现 js 里的 charCodeAt()方法？](https://www.zhihu.com/question/57108214)

```python
ord(string[index])
```

##### python access file fold import

```python
import sys
sys.path.append(os.getcwd())
```

##### generate char list

using ASCII

```python
lower_char = [chr(i) for i in range(97,123)] # a-z
upper_char = [chr(i) for i in range(65,91)]  # A-Z
```

##### Can't get cookie in `document.cookie`

Service use `HttpOnly` in `Set-Cookie`

- [Why doesn't document.cookie show all the cookie for the site?](https://stackoverflow.com/questions/1022112/why-doesnt-document-cookie-show-all-the-cookie-for-the-site)
- [Secure and HttpOnly](https://en.wikipedia.org/wiki/HTTP_cookie#Secure_and_HttpOnly)

> The Secure attribute is meant to keep cookie communication limited to encrypted transmission, directing browsers to use cookies only via secure/encrypted connections. However, if a web server sets a cookie with a secure attribute from a non-secure connection, the cookie can still be intercepted when it is sent to the user by **man-in-the-middle attacks**. Therefore, for maximum security, cookies with the Secure attribute should only be set over a secure connection.
>
> The HttpOnly attribute directs browsers not to expose cookies through channels other than HTTP (and HTTPS) requests. This means that the cookie cannot be accessed via client-side scripting languages (notably JavaScript), and therefore cannot be stolen easily via cross-site scripting (a pervasive attack technique).

##### ctrip cookie analysis

| key                           | method | how                                                                                                 | constant | login | finish |
| ----------------------------- | ------ | --------------------------------------------------------------------------------------------------- | -------- | ----- | ------ |
| `magicid`                     | set    | `https://hotels.ctrip.com/hotel/xxx.html`                                                           | 1        | 0     | 1      |
| `ASP.NET_SessionId`           | set    | `https://hotels.ctrip.com/hotel/xxx.html`                                                           | 1        | 0     | 1      |
| `clientid`                    | set    | `https://hotels.ctrip.com/hotel/xxx.html`                                                           | 1        | 0     | 1      |
| `_abtest_userid`              | set    | `https://hotels.ctrip.com/hotel/xxx.html`                                                           | 1        | 0     | 1      |
| `hoteluuid`                   | js     | `https://hotels.ctrip.com/hotel/xxx.html`                                                           | 1        | 0     |
| `fcerror`                     | js     | `https://hotels.ctrip.com/hotel/xxx.html`                                                           | 1        | 0     |
| `_zQdjfing`                   | js     | `https://hotels.ctrip.com/hotel/xxx.html`                                                           | 1        | 0     |
| `OID_ForOnlineHotel`          | js     | `https://webresource.c-ctrip.com/ResHotelOnline/R8/search/js.merge/showhotelinformation.js`         | 1        | 0     |
| `_RSG`                        | req    | `https://cdid.c-ctrip.com/chloro-device/v2/d`                                                       | 1        | 0     |
| `_RDG`                        | req    | `https://cdid.c-ctrip.com/chloro-device/v2/d`                                                       | 1        | 0     |
| `_RGUID`                      | set    | `https://cdid.c-ctrip.com/chloro-device/v2/d`                                                       | 1        | 0     |
| `_ga`                         | js     | for google analysis                                                                                 | 1        | 0     |
| `_gid`                        | js     | for google analysis                                                                                 | 1        | 0     |
| `MKT_Pagesource`              | js     | `https://webresource.c-ctrip.com/ResUnionOnline/R3/float/floating_normal.min.js`                    | 1        | 0     |
| `_HGUID`                      | js     | `https://hotels.ctrip.com/hotel/xxx.html`                                                           | 1        | 0     |
| `HotelDomesticVisitedHotels1` | set    | `https://hotels.ctrip.com/Domestic/tool/AjaxGetHotelAddtionalInfo.ashx`                             | 1        | 0     |
| `_RF1`                        | req    | `https://cdid.c-ctrip.com/chloro-device/v2/d`                                                       | 1        | 0     |
| `appFloatCnt`                 | js     | `https://webresource.c-ctrip.com/ResUnionOnline/R3/float/floating_normal.min.js?20190428`           | 1        | 0     |
| `gad_city`                    | set    | `https://crm.ws.ctrip.com/Customer-Market-Proxy/AdCallProxyV2.aspx`                                 | 1        | 0     |
| `login_uid`                   | set    | `https://accounts.ctrip.com/ssoproxy/ssoCrossSetCookie`                                             | 1        | 1     |
| `login_type`                  | set    | `https://accounts.ctrip.com/ssoproxy/ssoCrossSetCookie`                                             | 1        | 1     |
| `cticket`                     | set    | `https://accounts.ctrip.com/ssoproxy/ssoCrossSetCookie`                                             | 1        | 1     |
| `AHeadUserInfo`               | set    | `https://accounts.ctrip.com/ssoproxy/ssoCrossSetCookie`                                             | 1        | 1     |
| `ticket_ctrip`                | set    | `https://accounts.ctrip.com/ssoproxy/ssoCrossSetCookie`                                             | 1        | 1     |
| `DUID`                        | set    | `https://accounts.ctrip.com/ssoproxy/ssoCrossSetCookie`                                             | 1        | 1     |
| `IsNonUser`                   | set    | `https://accounts.ctrip.com/ssoproxy/ssoCrossSetCookie`                                             | 1        | 1     |
| `UUID`                        | req    | `https://passport.ctrip.com/gateway/api/soa2/12770/setGuestData`                                    | 1        | 1     |
| `IsPersonalizedLogin`         | js     | `https://webresource.c-ctrip.com/ares2/basebiz/cusersdk/~0.0.8/default/login/1.0.0/loginsdk.min.js` | 1        | 1     |
| `_bfi`                        | js     | `https://webresource.c-ctrip.com/code/ubt/_bfa.min.js?v=20193_28.js`                                | 1        | 0     |
| `_jzqco`                      | js     | `https://webresource.c-ctrip.com/ResUnionOnline/R1/remarketing/js/mba_ctrip.js`                     | 1        | 0     |
| `__zpspc`                     | js     | `https://webresource.c-ctrip.com/ResUnionOnline/R1/remarketing/js/s.js`                             | 1        | 0     |
| `_bfa`                        | js     | `https://webresource.c-ctrip.com/code/ubt/_bfa.min.js?v=20193_28.js`                                | 1        | 0     |
| `_bfs`                        | js     | `https://webresource.c-ctrip.com/code/ubt/_bfa.min.js?v=20193_28.js`                                | 1        | 0     |
| `utc`                         | js     | `https://hotels.ctrip.com/hotel/xxx.html`                                                           | 0        | 0     | 1      |
| `htltmp`                      | js     | `https://hotels.ctrip.com/hotel/xxx.html`                                                           | 0        | 0     | 1      |
| `htlstm`                      | js     | `https://hotels.ctrip.com/hotel/xxx.html`                                                           | 0        | 0     | 1      |
| `arp_scroll_position`         | js     | `https://hotels.ctrip.com/hotel/xxx.html`                                                           | 0        | 0     | 1      |

##### some function

```js
function a31(a233, a23, a94) {
  var a120 = {
    KWcVI: "mMa",
    hqRkQ: function a272(a309, a20) {
      return a309 + a20;
    },
    WILPP: function a69(a242, a488) {
      return a242(a488);
    },
    ydraP: function a293(a338, a255) {
      return a338 == a255;
    },
    ceIER: ";expires=",
    mDTlQ: function a221(a234, a225) {
      return a234 + a225;
    },
    dnvrD: function a268(a61, a351) {
      return a61 + a351;
    },
    DIGJw: function a368(a62, a223) {
      return a62 == a223;
    },
    pIWEz: function a260(a256, a284) {
      return a256 + a284;
    },
    jXvnT: ";path=/"
  };
  if (a120["KWcVI"] !== a120["KWcVI"]) {
    var a67 = new Date();
    a67[a845("0x1a", "4Vqw")](
      a120[a845("0x1b", "RswF")](a67["getDate"](), a94)
    );
    document[a845("0x1c", "WjvM")] =
      a120[a845("0x1d", "3082")](a233, "=") +
      a120[a845("0x1e", "TDHu")](escape, a23) +
      (a120["ydraP"](a94, null)
        ? ""
        : a120["hqRkQ"](a120["ceIER"], a67[a845("0x1f", "IErH")]())) +
      a845("0x20", "eHIq");
  } else {
    var a148 = a921(this, function() {
      var a291 = function() {
          return "dev";
        },
        a366 = function() {
          return "window";
        };
      var a198 = function() {
        var a168 = new RegExp("\\w+ *\\(\\) *{\\w+ *[' | '].+[' | '];? *}");
        return !a168["test"](a291["toString"]());
      };
      var a354 = function() {
        var a29 = new RegExp("(\\[x|u](\\w){2,4})+");
        return a29["test"](a366["toString"]());
      };
      var a243 = function(a2) {
        var a315 = ~-0x1 >> (0x1 + (0xff % 0x0));
        if (a2["indexOf"]("i" === a315)) {
          a310(a2);
        }
      };
      var a310 = function(a213) {
        var a200 = ~-0x4 >> (0x1 + (0xff % 0x0));
        if (a213["indexOf"]((!![] + "")[0x3]) !== a200) {
          a243(a213);
        }
      };
      if (!a198()) {
        if (!a354()) {
          a243("indÐµxOf");
        } else {
          a243("indexOf");
        }
      } else {
        a243("indÐµxOf");
      }
    });
    // a148();
    var a169 = new Date();
    a169["setDate"](a169["getDate"]() + a94);
    document["cookie"] = a120["mDTlQ"](
      a120["dnvrD"](
        a120["dnvrD"](a120["dnvrD"](a233, "="), escape(a23)),
        a120["DIGJw"](a94, null)
          ? ""
          : a120["pIWEz"](a120["ceIER"], a169["toGMTString"]())
      ),
      a120["jXvnT"]
    );
  }
}
```

equal to

```js
document["cookie"] =
  a233 +
  "=" +
  escape(a23) +
  (a94 == null ? "" : ";expires=" + a169["toGMTString"]()) +
  ";path=/";
```

So, It is only a function to set cookie & expires.

And you can think `a31` is a entry point to judge where code about compiler cookie.

##### Get current timezone offset
