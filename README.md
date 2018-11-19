<p align="center"><a href="https://wyydsb.xin" target="_blank" rel="noopener noreferrer"><img width="100" src="https://cdn.nlark.com/yuque/0/2018/jpeg/104214/1540358574166-46cbbfd2-69fa-4406-aba9-784bf65efdf9.jpeg" alt="Spider logo"></a></p>
<h1 align="center">Spider Press Man</h1>

[![GitHub](https://img.shields.io/github/license/iofu728/spider-press.svg?style=popout-square)](https://github.com/iofu728/spider-press/master/LICENSE)
[![GitHub tag](https://img.shields.io/github/tag/iofu728/spider-press.svg?style=popout-square)](https://github.com/iofu728/spider-press/release)
[![GitHub code size in bytes](https://img.shields.io/github/languages/code-size/iofu728/spider-press.svg?style=popout-square)](https://github.com/iofu728/spider-press)

<div align="center"><strong>高可用代理IP池 高并发爬虫 不均匀的压力分发系统 </strong></div>
<div align="center"><strong>Highly Available Proxy IP Pool, Highly Concurrent Spider, Uneven Pressure Distribution System</strong></div>

## Key

* <u>`Highly Available Proxy IP Pool`</u>
  + By obtaining data from Gatherproxy, Goubanjia, xici etc. Free Proxy WebSite
  + Analysis the Goubanjia port data
  + Quickly verify IP availability
  + Cooperate with Requests to automatically assign proxy Ip, with Retry mechanism, fail to write DB mechanism
* <u>`Netease`</u>
  + classify -> playlist id -> song_detail
  + V1 Write file, One run version, no proxy, no record progress mechanism
  + V1.5 Small amount of proxy IP
  + V2 Proxy IP pool, Record progress, Write to MySQL
    - Optimize the write to DB `Load data/ Replace INTO`
* <u>`Press Test`</u>
  + By highly available proxy IP pool to pretend user.
  + Give some web service uneven pressure
  + To do: press uniform

## Development

```bash
$ git clone https://github.com/iofu728/spider.git
$ cd spider
$ ipython
# netease spider
$ import netease.netease_music_db
$ xxx = netease.netease_music_db.Get_playlist_song()
# press
$ import press.press
$ xxx = press.press.Press_test()
$ xxx.one_press_attack(url, host, qps, types, total)
```

## Structure
```bash
.
├── LICENSE                        // LICENSE
├── README.md                      // README
├── log                           // failured log
├── netease
│   ├── netease_music_base.py      // v1 spider
│   ├── netease_music_db.py        // v2 spider
│   ├── result.txt                 // result
│   └── table.sql                  // netease sql
├── press
│   └── press.py                   // press
├── proxy
│   ├── gatherproxy                // gatherproxy data
│   ├── getproxy.py                // proxy pool
│   └── table.sql                  // proxy sql
├── song_detail
└── utils
    ├── db.py                      // db operation
    └── utils.py                   // requests operation
```

## Design document
* [Netease Music Spider for DB](https://wyydsb.xin/other/neteasedb.html)
* [Netease Music Spider](https://wyydsb.xin/other/netease.html)

