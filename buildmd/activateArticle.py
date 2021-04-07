# -*- coding: utf-8 -*-
# @Author: gunjianpan
# @Date:   2019-08-26 20:46:29
# @Last Modified by:   gunjianpan
# @Last Modified time: 2021-04-08 00:59:51

import json
import os
import sys
import threading
import time
import urllib
from concurrent.futures import ThreadPoolExecutor, as_completed
from configparser import ConfigParser
from collections import Counter
from emoji import UNICODE_EMOJI

import numpy as np
import regex

sys.path.append(os.getcwd())
import top
from buildmd.items import Items
from proxy.getproxy import GetFreeProxy
from util.db import Db
from util.util import (
    basic_req,
    begin_time,
    can_retry,
    changeHeaders,
    changeJsonTimeout,
    decoder_cookie,
    decoder_url,
    echo,
    encoder_url,
    end_time,
    get_accept,
    get_content_type,
    get_time_str,
    get_use_agent,
    generate_sql,
    headers,
    mkdir,
    read_file,
    send_email,
    time_stamp,
    time_str,
    load_bigger,
    dump_bigger,
)


proxy_req = GetFreeProxy().proxy_req
root_dir = os.path.abspath("buildmd")
sql_dir = os.path.join(root_dir, "sql")
assign_path = os.path.join(root_dir, "tbk.ini")
DATA_DIR = os.path.join(root_dir, "data")
TPWDLIST_PATH = os.path.join(DATA_DIR, "tpwdlist.pkl")
mkdir(DATA_DIR)


class TBK(object):
    """ tbk info class """

    CSTK_KEY = "YNOTE_CSTK"

    def __init__(self):
        super(TBK, self).__init__()
        self.tb_items = {}
        self.load_configure()
        # self.load_tbk_info()

    def load_configure(self):
        cfg = ConfigParser()
        cfg.read(assign_path, "utf-8")
        self.appkey = cfg.get("TBK", "appkey")
        self.secret = cfg.get("TBK", "secret")
        self.user_id = cfg.getint("TBK", "user_id")
        self.site_id = cfg.getint("TBK", "site_id")
        self.adzone_id = cfg.getint("TBK", "adzone_id")
        self.home_id = cfg.get("YNOTE", "home_id")
        self.test_item_id = cfg.getint("TBK", "test_item_id")
        self.test_finger_id = cfg.getint("TBK", "test_finger_id")
        self.uland_url = cfg.get("TBK", "uland_url")
        self.unlogin_id = cfg.get("YNOTE", "unlogin_id")
        self.cookie = cfg.get("YNOTE", "cookie")[1:-1]
        self.api_key = cfg.get("TBK", "apikey")
        self.assign_rec = cfg.get("YNOTE", "assign_email").split(",")
        cookie_de = decoder_cookie(self.cookie)
        self.cstk = cookie_de[self.CSTK_KEY] if self.CSTK_KEY in cookie_de else ""
        top.setDefaultAppInfo(self.appkey, self.secret)

    def load_tbk_info(self):
        favorites = self.get_uatm_favor()
        for ii in favorites:
            time.sleep
            self.get_uatm_detail(ii)

    def get_uatm_favor(self):
        req = top.api.TbkUatmFavoritesGetRequest()
        req.page_no = 1
        req.page_size = 30
        req.fields = "favorites_id"
        uatm_favor = req.getResponse()
        favorites = uatm_favor["tbk_uatm_favorites_get_response"]["results"][
            "tbk_favorites"
        ]
        favorites = [ii["favorites_id"] for ii in favorites]
        return favorites

    def get_uatm_detail(self, favorites_id: int):
        req = top.api.TbkUatmFavoritesItemGetRequest()
        req.adzone_id = self.adzone_id
        req.favorites_id = favorites_id
        req.page_size = 200
        req.fields = "num_iid, title, reserve_price, zk_final_price, user_type, provcity, item_url, click_url, volume, tk_rate, zk_final_price_wap, shop_title, event_start_time, event_end_time, type, status, coupon_click_url, coupon_end_time, coupon_info, coupon_start_time, coupon_total_count, coupon_remain_count"
        try:
            item = req.getResponse()
            item = item["tbk_uatm_favorites_item_get_response"]["results"][
                "uatm_tbk_item"
            ]
            items = {ii["num_iid"]: ii for ii in item}
            self.tb_items = {**self.tb_items, **items}
        except Exception as e:
            echo(0, favorites_id, "favorite error", e)

    def get_dg_material(self, title: str, num_iid: int):
        req = top.api.TbkDgMaterialOptionalRequest()
        req.adzone_id = self.adzone_id
        req.q = title
        req.page_size = 30
        try:
            goods = req.getResponse()
            goods = goods["tbk_dg_material_optional_response"]["result_list"][
                "map_data"
            ]
            return [ii for ii in goods if ii["num_iid"] == num_iid]
        except Exception as e:
            echo(0, "get dg material failed.", title, num_iid, e)

    def convert2tpwd(self, url: str, title: str):
        req = top.api.TbkTpwdCreateRequest()
        req.url = url
        req.text = title
        try:
            tpwds = req.getResponse()
            words = tpwds["tbk_tpwd_create_response"]["data"]["model"]
            tpwds = regex.findall("\p{Sc}(\w{8,12}?)\p{Sc}", words)
            if tpwds:
                return tpwds[0]
            return ""
        except Exception as e:
            echo(0, "Generate tpwd failed", url, title, e)


class ActivateArticle(TBK):
    """ activate article in youdao Cloud and Convert the tpwds to items"""

    Y_URL = "https://note.youdao.com/"
    WEB_URL = f"{Y_URL}web/"
    API_P_URL = f"{Y_URL}yws/api/personal/"
    SYNC_URL = f"{API_P_URL}sync?method=%s&keyfrom=web&cstk=%s"
    NOTE_URL = f"{Y_URL}yws/public/note/%s?editorType=0"
    SHARE_URL = f"{Y_URL}ynoteshare1/index.html?id=%s&type=note"
    GET_SHARE_URL = f"{API_P_URL}share?method=get&shareKey=%s"
    LISTRECENT_URL = (
        f"{API_P_URL}file?method=listRecent&offset=%d&limit=30&keyfrom=web&cstk=%s"
    )
    MYSHARE_URL = (
        f"{API_P_URL}myshare?method=get&checkBan=true&entryId=%s&keyfrom=web&cstk=%s"
    )
    DECODER_TPWD_URL = "https://api.taokouling.com/tkl/tkljm?apikey=%s&tkl=￥%s￥"
    DECODER_TPWD_URL_V2 = "https://taodaxiang.com/taopass/parse/get"
    Y_DOC_JS_URL = "https://shared-https.ydstatic.com/ynote/ydoc/index-6f5231c139.js"
    ITEM_URL = "https://item.taobao.com/item.htm?id=%d"
    TPWD_LIST = [
        "`id`",
        "tpwd",
        "article_id",
        "content",
        "url",
        "item_id",
        "domain",
        "commission_rate",
        "commission_type",
        "is_updated",
        "expire_at",
        "created_at",
    ]
    LIST_LIST = [
        "`id`",
        "article_id",
        "title",
        "q",
        "established_at",
        "modified_at",
        "created_at",
    ]
    S_LIST_SQL = generate_sql("select", "article", LIST_LIST + ["updated_at"]) % ""
    I_LIST_SQL = generate_sql("insert", "article", LIST_LIST)
    R_LIST_SQL = generate_sql("replace", "article", LIST_LIST)
    S_TPWD_SQL = generate_sql("select", "article_tpwd", TPWD_LIST)
    I_TPWD_SQL = generate_sql("insert", "article_tpwd", TPWD_LIST)
    R_TPWD_SQL = generate_sql("replace", "article_tpwd", TPWD_LIST)
    END_TEXT = "</text><inline-styles/><styles/></para></body></note>"
    TPWD_REG = "\p{Sc}(\w{8,12}?)\p{Sc}"
    TPWD_REG2 = "(\p{Sc}\w{8,12}\p{Sc})"
    TPWD_REG3 = "(\p{Sc}|[\u4e00-\u9fff。！，？；“”’【】、「」《》])([a-zA-Z0-9]{8,12}?)(\p{Sc}|[\u4e00-\u9fff。！，？；“”’【】、「」《》])"
    JSON_KEYS = [
        "p",
        "ct",
        "su",
        "pr",
        "au",
        "pv",
        "mt",
        "sz",
        "domain",
        "tl",
        "content",
    ]
    URL_DOMAIN = {
        0: "s.click.taobao.com",
        1: "item.taobao.com",
        2: "detail.m.tmall.com",
        5: "uland.taobao.com",
        10: "taoquan.taobao.com",
        11: "a.m.taobao.com",
        12: "market.m.taobao.com",
        13: "id=",
        15: "empty",
        16: "failure",
    }
    NEED_KEY_V1 = ["content", "url", "validDate", "picUrl"]
    TABLE_LISTS = ["tpwd.sql", "article.sql"]
    ONE_HOURS = 3600
    ONE_DAY = 24
    ZERO_STAMP = "0天0小时0分0秒"
    T_FORMAT = "%m-%d %H:%M"
    BASIC_STAMP = (
        time_stamp(time_format="%d天%H小时%M分%S秒", time_str="1天0小时0分0秒")
        - ONE_DAY * ONE_HOURS
    )

    def __init__(self, is_local: bool = False):
        super(ActivateArticle, self).__init__()
        if is_local:
            self.S_TPWD_SQL = self.S_TPWD_SQL.replace("article_tpwd", "tpwds_local")
            self.I_TPWD_SQL = self.I_TPWD_SQL.replace("article_tpwd", "tpwds_local")
            self.R_TPWD_SQL = self.R_TPWD_SQL.replace("article_tpwd", "tpwds_local")
        self.is_local = is_local
        self.BASIC_TIMEX_STR = time_str()
        self.BASIC_TIMEX_STAMP = time_stamp()
        self.items = Items(
            {
                "time_str": self.BASIC_TIMEX_STR,
                "time_stamp": self.BASIC_TIMEX_STAMP,
                "proxy_req": proxy_req,
                "is_local": is_local,
            }
        )
        self.Db = self.items.Db
        for table in self.TABLE_LISTS:
            self.Db.create_table(os.path.join(sql_dir, table))
        self.tpwds_map = {}
        self.lists_map = {}
        self.tpwds_db_map = {}
        self.lists_db_map = {}
        self.new_tpwds_map = {}
        self.yd_ids = []
        self.tpwds_list = {}
        self.ynote_list = {}
        self.load_num = [0, 0]
        self.tpwd_exec = ThreadPoolExecutor(max_workers=5)

    def load_process(self):
        self.load_yd_ids()
        if len(self.yd_ids) < 30:
            time.sleep(np.random.rand() * 30 + 6)
            self.load_yd_ids()
        self.load_db()
        self.items.get_m_h5_tk()
        self.get_ynote_file()
        self.get_ynote_file(1)

    def load_yd_ids(self):
        changeJsonTimeout(5)
        req = self.basic_youdao(self.home_id)
        if req == "":
            echo("0|error", "Get The Home Page Info Error!!! Please retry->->->")
            return
        self.yd_ids = regex.findall("id=(\w*?)<", req)
        if len(self.yd_ids) < 30:
            echo("0|error", "The Num of id is error!! Please check it.")
        else:
            echo(1, "Load {} Online Articles.".format(len(self.yd_ids)))

    def load_db(self, is_load: bool = True):
        tpwds = self.items.load_db_table(
            self.S_TPWD_SQL % "", self.TPWD_LIST, self.tpwds_db_map, "tpwd"
        ).copy()
        lists = self.items.load_db_table(
            self.S_LIST_SQL,
            self.LIST_LIST + ["updated_at"],
            self.lists_db_map,
            "article_id",
        ).copy()

        if is_load:
            self.tpwds_map = tpwds
            self.new_tpwds_map = tpwds.copy()
            self.lists_map = lists
        need_update = [1 for ii in self.tpwds_db_map.values() if not ii["is_updated"]]
        echo(
            1,
            "Load {} Articles and {} Tpwds from db, {} Tpwds need update.".format(
                len(self.lists_db_map), len(self.tpwds_db_map), len(need_update)
            ),
        )

    def store_db(self):
        self.load_db(False)
        self.items.store_one_table(
            self.R_TPWD_SQL,
            self.I_TPWD_SQL,
            self.tpwds_map,
            self.tpwds_db_map,
            self.TPWD_LIST,
            "tpwd",
        )
        self.items.store_one_table(
            self.R_LIST_SQL,
            self.I_LIST_SQL,
            self.lists_map,
            self.lists_db_map,
            self.LIST_LIST,
            "list",
        )

    def get_yd_detail(
        self, yd_id: str, is_wait: bool = False, force_update: bool = False
    ):
        expired_flag = (
            self.BASIC_TIMEX_STAMP
            - time_stamp(
                self.lists_map.get(yd_id, {}).get("updated_at", self.BASIC_TIMEX_STR)
            )
            >= self.ONE_HOURS * self.ONE_DAY * 10
        )
        if (
            self.lists_map.get(yd_id, {}).get("title", "")
            and not expired_flag
            and not force_update
        ):
            return self.lists_map[yd_id]
        if is_wait:
            time.sleep(np.random.rand() * 5 + 2)
        url = self.GET_SHARE_URL % yd_id
        headers = self.get_headers(self.Y_URL)
        req = basic_req(url, 1, header=headers)
        if req is None:
            return {}

        title, q, established_at, modified_at = [
            req["entry"].get(ii, jj) if "entry" in req else jj
            for ii, jj in [
                ("name", ""),
                ("id", ""),
                ("createTime", self.BASIC_TIMEX_STAMP * 1000),
                ("lastUpdateTime", self.BASIC_TIMEX_STAMP * 1000),
            ]
        ]
        self.lists_map[yd_id] = {
            "article_id": yd_id,
            "title": title.replace(".note", ""),
            "q": q,
            "established_at": time_str(established_at // 1000),
            "modified_at": time_str(modified_at // 1000),
            "updated_at": self.lists_map[yd_id]["updated_at"]
            if yd_id in self.lists_map and not expired_flag
            else self.BASIC_TIMEX_STAMP,
        }
        return self.lists_map[yd_id]

    def basic_youdao(self, idx: str, use_proxy: bool = False):
        url = self.NOTE_URL % idx
        refer_url = self.SHARE_URL % idx
        headers = {
            "Accept": get_accept("all"),
            "Referer": refer_url,
            "X-Requested-With": "XMLHttpRequest",
        }
        req_req = proxy_req if use_proxy else basic_req
        req = req_req(url, 1, header=headers, config={"timeout": 10})
        if req is None or list(req.keys()) != self.JSON_KEYS:
            if can_retry(url) and use_proxy:
                echo(2, "retry")
                return self.basic_youdao(idx)
            else:
                echo(1, "retry upper time")
                return ""
        return (
            req["content"]
            .replace("font-size:12px;", "")
            .replace("color:#494949;", "")
            .replace("background-color:#ffffff;", "")
            .replace('<span style="">', "")
            .replace("</span>", "")
        )

    def get_yd_tpwds_detail(
        self, yd_id: str, is_wait: bool = False, force_update: bool = False
    ):
        self.get_article_tpwds(yd_id, is_wait, force_update)
        self.load_num = [0, 0]
        for tpwd in set(self.tpwds_list[yd_id]):
            self.get_tpwd_detail_pro(tpwd, yd_id, is_wait, force_update)
        self.store_db()
        echo(
            2,
            f"Article {yd_id} Load {self.load_num[0]} Tpwds and {self.load_num[1]} Items Info.",
        )

    def get_tpwd_detail_pro(
        self,
        tpwd: str,
        yd_id: str,
        is_wait: bool = False,
        force_update: bool = False,
    ):
        self.get_tpwd_detail(tpwd, yd_id, is_wait, force_update)
        return self.decoder_tpwd_item(tpwd, force_update)

    def get_tpwd_detail(
        self,
        tpwd: str,
        yd_id: str,
        is_wait: bool = False,
        force_update: bool = False,
    ):
        updated_flag = self.tpwds_map.get(tpwd, {}).get("is_updated", 0)
        if (
            tpwd in self.tpwds_map
            and self.tpwds_map[tpwd]["content"]
            and updated_flag
            and not force_update
        ):
            return self.tpwds_map[tpwd]
        self.load_num[0] += 1
        if is_wait:
            time.sleep(np.random.rand() * 5 + 2)
        req = self.decoder_tpwd(tpwd)
        if req is None or not len(req):
            return {}
        NEED_KEY = ["content", "url", "expire", "picUrl"]
        content, url, expire_at, picUrl = [
            req["data"].get(ii, jj) if "data" in req else jj
            for ii, jj in [
                ("content", ""),
                ("url", ""),
                ("expire", self.BASIC_TIMEX_STR),
                ("picUrl", ""),
            ]
        ]

        self.tpwds_map[tpwd] = {
            "tpwd": tpwd,
            "article_id": yd_id,
            "content": content,
            "url": url.strip(),
            "item_id": self.tpwds_map.get(tpwd, {}).get("item_id", ""),
            "domain": self.tpwds_map.get(tpwd, {}).get("domain", 0),
            "commission_rate": self.tpwds_map.get(tpwd, {}).get("commission_rate", 0),
            "commission_type": self.tpwds_map.get(tpwd, {}).get("commission_type", ""),
            "expire_at": expire_at,
        }
        self.tpwds_map[tpwd]["is_updated"] = (
            1 if content and self.tpwds_map[tpwd]["item_id"] else 0
        )
        self.new_tpwds_map[tpwd] = self.tpwds_map[tpwd].copy()
        self.new_tpwds_map[tpwd]["picUrl"] = picUrl
        self.decoder_tpwd_item(tpwd)
        return self.tpwds_map[tpwd]

    def get_article_tpwds(
        self,
        yd_id: str,
        is_wait: bool = False,
        force_update: bool = False,
        mode: str = "online",
    ):
        if yd_id in self.tpwds_list:
            return self.tpwds_list[yd_id]
        if mode == "online":
            article = self.basic_youdao(yd_id)
        else:
            article = "||||".join(read_file(yd_id))
        if not article:
            return []
        tpwds = regex.findall(self.TPWD_REG, article)
        self.tpwds_list[yd_id] = tpwds
        return tpwds

    def update_tpwds(self, is_renew: bool = True, yd_id: str = None):
        update_num = 0
        c = self.items.items_detail_map
        for o_tpwd, m in self.tpwds_map.items():
            if (
                yd_id is not None
                and m["article_id"] != yd_id
                and o_tpwd not in self.tpwds_list.get(yd_id, [])
            ):
                continue
            item_id, url, domain, title, tpwd, c_rate, c_type = [
                m.get(ii, jj)
                for ii, jj in [
                    ("item_id", ""),
                    ("url", ""),
                    ("domain", 20),
                    ("content", ""),
                    ("tpwd", ""),
                    ("c_rate", 0),
                    ("c_type", ""),
                ]
            ]
            item_title, is_expired = [
                c.get(item_id, {}).get(ii, jj)
                for ii, jj in [
                    ("title", ""),
                    ("is_expired", 0),
                ]
            ]
            title = item_title if item_title else title

            if (
                is_renew
                and self.URL_DOMAIN[1] not in url
                and self.URL_DOMAIN[2] not in url
                and self.URL_DOMAIN[10] not in url
            ):
                renew_type = 2 if self.URL_DOMAIN[5] in url else 1
                renew_tpwd = self.convert2tpwd(url, title)
                if renew_tpwd is None:
                    renew_tpwd = o_tpwd
            else:
                renew_type = 0
                renew_tpwd = o_tpwd
            if item_id == "" or domain == 16:
                tpwd, c_rate = renew_tpwd, 1 if renew_type == 0 else 2
            else:
                (
                    url,
                    tpwd,
                    domain,
                    c_rate,
                    c_type,
                ) = self.generate_tpwd(title, int(item_id), renew_tpwd, renew_type, m)
            for k, v in [
                ("url", url),
                ("tpwd", tpwd),
                ("domain", domain),
                ("commission_rate", c_rate),
                ("commission_type", c_type),
            ]:
                self.new_tpwds_map[k] = v
            update_num += int(domain < 15)
        echo(2, "Update {} Tpwd Info Success!!".format(update_num))

    def generate_tpwd(
        self,
        title: str,
        item_id: int,
        renew_tpwd: str,
        renew_type: int,
        m: dict,
    ):
        goods = self.get_dg_material(title, item_id)
        if not goods:
            echo(
                0,
                "goods get",
                "error" if goods is None else "empty",
                ":",
                title,
                item_id,
            )
            return (
                m["url"],
                renew_tpwd,
                17,
                1 if renew_type == 0 else 2,
                m["commission_type"],
            )

        goods = goods[0]
        if "ysyl_click_url" in goods and len(goods["ysyl_click_url"]):
            url = goods["ysyl_click_url"]
        elif "coupon_share_url" in goods and len(goods["coupon_share_url"]):
            url = goods["coupon_share_url"]
        else:
            url = goods["url"]
        url = "https:{}".format(url)
        commission_rate = int(goods["commission_rate"])
        commission_type = goods["commission_type"]
        tpwd = self.convert2tpwd(url, title)
        if tpwd is None:
            echo(0, "tpwd error:", tpwd)
            return (
                m["url"],
                renew_tpwd,
                18,
                1 if renew_type == 0 else 2,
                m["commission_type"],
            )
        if renew_type == 1:
            commission_rate = 2
        return url, tpwd, m["domain"], commission_rate, commission_type

    def decoder_tpwd_item(self, tpwd: str, force_update: bool = False):
        if tpwd not in self.tpwds_map:
            return {}
        if self.tpwds_map.get(tpwd, {}).get("item_id", "") and not force_update:
            return self.tpwds_map[tpwd]
        self.load_num[1] += 1
        m = self.tpwds_map[tpwd]
        domain, item_id = self.analysis_tpwd_url(m["url"])
        if not item_id:
            return self.tpwds_map[tpwd]
        self.tpwds_map[tpwd] = {
            **m,
            "domain": domain,
            "item_id": item_id,
            "is_updated": 1 if m["content"] and item_id else 0,
        }
        if domain < 20:
            echo(2, "Domain:", self.URL_DOMAIN[domain], "item id:", item_id)
        return self.tpwds_map[tpwd]

    def analysis_tpwd_url(self, url: str):
        if not url:
            idx, item_id = 15, ""
        elif self.URL_DOMAIN[5] in url:
            idx, item_id = 5, self.items.get_uland_url(url)
        elif self.URL_DOMAIN[11] in url:
            idx, item_id = 11, self.get_a_m_url(url)
        elif self.URL_DOMAIN[0] in url:
            idx, item_id = 0, self.get_s_click_url(url)
        elif self.URL_DOMAIN[10] in url:
            idx, item_id = 10, ""
        elif self.URL_DOMAIN[13] in url:
            idx, item_id = 1 if self.URL_DOMAIN[1] in url else 13, self.get_item_id(url)
            if not item_id:
                idx = 16
        else:
            echo("0|warning", "New Domain:", regex.findall("https://(.*?)/", url), url)
            idx, item_id = 20, ""
        return idx, str(item_id)

    def decoder_tpwd_v1(self, tpwd: str):
        """ decoder the tpwd from taokouling from taokouling.com something failure in March 2021"""
        url = self.DECODER_TPWD_URL % (self.api_key, tpwd)
        req = basic_req(url, 1)
        if req is None or isinstance(req, str) or "ret" not in list(req.keys()):
            return {}
        return req

    def decoder_tpwd(self, tpwd: str):
        """ decoder the tpwd from taokouling from https://taodaxiang.com/taopass"""
        url = self.DECODER_TPWD_URL_V2
        data = {"content": f"￥{tpwd}￥"}
        req_func = basic_req if self.is_local else proxy_req
        req = req_func(url, 11, data=data)
        if req is None or not isinstance(req, dict) or "code" not in list(req.keys()):
            return {}
        return req

    def get_s_click_url(self, s_click_url: str):
        """ decoder s.click real jump url @validation time: 2019.10.23"""
        # time.sleep(np.random.randint(0, 10))
        item_url = self.get_s_click_location(s_click_url)
        if item_url is None:
            echo(3, "s_click_url location Error..")
            return
        return self.get_item_id(item_url)

    def get_s_click_url_v1(self, s_click_url: str):
        """ decoder s.click real jump url @validation time: 2019.08.31"""
        if "tu=" not in s_click_url:
            tu_url = self.get_s_click_tu(s_click_url)
        else:
            tu_url = s_click_url
        if tu_url is None or "tu=" not in tu_url:
            echo(3, "s_click_url tu url ENd Retry..", tu_url)
            return
        qso = decoder_url(tu_url)
        if "tu" not in qso:
            if "alisec" in tu_url:
                echo("0|debug", "Request Too Fast")
                time.sleep(np.random.randint(10) * np.random.rand())
            else:
                echo(0, s_click_url, tu_url)
            return
        redirect_url = urllib.parse.unquote(qso["tu"])
        return self.get_s_click_detail(redirect_url, tu_url)

    def get_headers(self, url: str = "", refer_url: str = "") -> dict:
        headers = {"Accept": get_accept("html"), "User-Agent": get_use_agent()}
        if url != "":
            headers["Host"] = url.split("/")[2]
        if refer_url != "":
            headers["referer"] = refer_url
        return headers

    def get_s_click_basic(
        self,
        s_click_url: str,
        retry_func=(lambda x: False),
        referer: str = "",
        allow_redirects: bool = True,
        is_direct: bool = False,
    ):
        headers = self.get_headers(refer_url=referer)
        req_func = basic_req if is_direct or self.is_local else proxy_req
        req = req_func(
            s_click_url, 2, header=headers, config={"allow_redirects": allow_redirects}
        )
        if is_direct:
            return req
        if req is None or retry_func(req):
            if can_retry(s_click_url):
                return self.get_s_click_basic(
                    s_click_url, retry_func, referer, allow_redirects, is_direct
                )
            else:
                return
        return req

    def get_s_click_tu(self, s_click_url: str):
        req = self.get_s_click_basic(s_click_url, lambda i: "tu=" not in i.url)
        if req is None:
            return
        return req.url

    def get_s_click_location(self, s_click_url: str):
        req = self.get_s_click_basic(s_click_url)
        if req is None:
            echo("0|warning", "s_click_url first click error.")
            return
        echo("1", "real_jump_address get")
        rj = regex.findall("real_jump_address = '(.*?)'", req.text)
        if not len(rj):
            echo("0|warning", "real_jump_address get error.")
            return
        rj = rj[0].replace("&amp;", "&")
        req_rj = self.get_s_click_basic(
            rj, lambda i: "Location" not in i.headers, referer=rj, allow_redirects=False
        )
        if req_rj is None:
            return
        return req_rj.headers["Location"]

    def get_s_click_detail(self, redirect_url: str, tu_url: str):
        headers = self.get_headers(refer_url=tu_url)
        req_func = basic_req if self.is_local else proxy_req
        req = req_func(redirect_url, 2, header=headers)
        if req is None or "id=" not in req.url:
            if can_retry(redirect_url):
                return self.get_s_click_detail(redirect_url, tu_url)
            else:
                return
        return self.get_item_id(req.url)

    def get_item_id(self, item_url: str) -> int:
        item = decoder_url(item_url)
        if not "id" in item or not item["id"].isdigit():
            if "user_number_id" in item:
                return "shop{}".format(item["user_number_id"])
            echo(0, "id not found:", item_url)
            return ""
        return int(item["id"])

    def get_a_m_url(self, a_m_url: str):
        req = self.get_a_m_basic(a_m_url)
        if req is None:
            return ""
        item_url = req.headers["location"]
        return self.get_item_id(item_url)

    def get_a_m_basic(self, a_m_url: str):
        headers = self.get_headers(a_m_url)
        req = proxy_req(a_m_url, 2, header=headers, config={"allow_redirects": False})
        if req is None or "location" not in req.headers:
            if can_retry(a_m_url):
                return self.get_a_m_basic(a_m_url)
            return
        return req

    def get_ynote_file(self, offset: int = 0):
        url = self.LISTRECENT_URL % (offset, self.cstk)
        data = {"cstk": self.cstk}
        req = basic_req(url, 11, data=data, header=self.get_ynote_web_header(1))
        if req is None or type(req) != list:
            return None
        ynote_list = {ii["fileEntry"]["id"]: ii["fileEntry"] for ii in req}
        self.ynote_list = {**self.ynote_list, **ynote_list}
        echo(1, "Load ynote file {} items.".format(len(self.ynote_list)))
        return req

    def get_ynote_web_header(self, mode: int = 0):
        headers = {
            "Content-Type": get_content_type(),
            "Cookie": self.cookie,
            "Host": self.Y_URL.split("/")[2],
            "Origin": self.Y_URL,
            "Referer": self.WEB_URL,
        }
        if mode:
            headers["Accept"] = get_accept("xhr")
        else:
            headers["Accept"] = get_accept("html")
        return headers

    def get_empty_content(self):
        headers = {"Referer": self.WEB_URL}
        req = proxy_req(self.Y_DOC_JS_URL, 3, header=headers)
        if len(req) < 1000:
            if can_retry(self.Y_DOC_JS_URL):
                return self.get_empty_content()
            else:
                return
        empty_content = regex.findall("t.EMPTY_NOTE_CONTENT='(.*?)'", req)[0]
        empty_content = empty_content.split(self.END_TEXT)[0]
        self.empty_content = empty_content
        echo(1, "Load empty content", empty_content)
        return empty_content

    def get_web_content(self):
        req = proxy_req(self.WEB_URL, 3, header=self.get_ynote_web_header())
        if len(req) < 1000:
            if can_retry(self.WEB_URL):
                return self.get_web_content()
            else:
                return
        return req

    def replace_tpwd4article_pipeline(self, yd_id: str):
        xml = self.get_xml(yd_id)
        if xml is None:
            echo("0|warning", "get xml error")
            return
        tpwds = set(regex.findall(self.TPWD_REG2, xml))
        coIDs = regex.findall("<coId>\d{4}-\d*</coId><text>", xml)
        xml = xml.replace(
            coIDs[0],
            coIDs[0]
            + "PS: IOS14 用户请复制以“3”开头，以“/”结尾的完整淘口令，如3￥---￥/，或复制淘口令至淘宝搜索栏搜索.</text><inline-styles><color><from>0</from><to>36</to><value>#494949</value></color><back-color><from>0</from><to>36</to><value>#ffffff</value></back-color><bold><from>0</from><to>59</to><value>true</value></bold><underline><from>0</from><to>59</to><value>true</value></underline><color><from>36</from><to>43</to><value>#F33232</value></color><back-color><from>36</from><to>43</to><value>#FFB8B8</value></back-color><color><from>43</from><to>51</to><value>#494949</value></color><color><from>51</from><to>56</to><value>#F33232</value></color><back-color><from>51</from><to>56</to><value>#FFB8B8</value></back-color><color><from>56</from><to>59</to><value>#494949</value></color></inline-styles><styles/></para><para><coId>RpqK-1607447157739</coId><text/><inline-styles/><styles/></para><para><coId>Mx3M-1607447157739</coId><text>",
        )
        for ii in tpwds:
            xml = xml.replace(ii, f"3{ii}/")
        flag = self.update_article(yd_id, xml)
        if flag:
            echo(1, f"Update {yd_id} Success!! replace {len(tpwds)} tpwds")

    def update_article_pipeline(self, yd_id: str):
        xml = self.get_xml(yd_id)
        if xml is None:
            echo("0|warning", "get xml error")
            return
        xml, r_log, r_num = self.replace_tpwd(yd_id, xml)
        if not r_num:
            echo("0|warning", "r_num == 0")
            return
        flag = self.update_article(yd_id, xml)
        if flag:
            need_num = len(regex.findall("\(已失效\)", xml))
            self.email_update_result(yd_id, r_log, r_num, need_num)
            self.update_yd2db(yd_id, True)
            self.share_yd_article(yd_id)

    def fix_failure(self, yd_id: str, store: bool = False):
        xml = self.get_xml(yd_id)
        if xml is None:
            echo("0|warning", "get xml error")
            return
        x = regex.findall("(\\p{Sc}\\w{8,12}/\\p{Sc})", xml)
        for ii in x:
            xml = xml.replace(ii, ii[:-2] + ii[-1:])
        tpwds = regex.findall("(\\p{Sc}\\w{8,12}\\p{Sc}.)", xml)
        num = 0
        for ii, jj in enumerate(tpwds):
            if not jj.endswith("/"):
                num += 1
                xml = xml.replace(jj, jj[:-1] + "/" + jj[-1:])
        if num or store:
            flag = self.update_article(yd_id, xml)
            echo("1", flag, f"Success fix {num} tpwds in {yd_id}.")
        else:
            echo("2", f"No need fix in {yd_id}.")

    def email_update_result(self, yd_id: str, r_log: list, r_num: int, need_num: int):
        title = self.lists_map.get(yd_id, {}).get("title", "")
        subject = "更新({}){}/{}剩{}条[{}]".format(
            time_str(time_format=self.T_FORMAT),
            r_num,
            len(r_log),
            need_num,
            title,
        )
        content = "\n".join(
            [
                f"Title: {title}",
                f"Time: {time_str()}",
                f"Update Num: {r_num}/{len(r_log)}条, 还有{need_num}条需要手动更新",
                "",
                *r_log,
            ]
        )
        send_email(content, subject, assign_rec=self.assign_rec)

    def update_yd2db(self, yd_id: str, is_tpwd_update: bool = False):
        for tpwd in set(self.tpwds_list[yd_id]):
            self.tpwds_map[tpwd] = self.new_tpwds_map[tpwd]
        self.store_db()

    def replace_tpwd(self, yd_id: str, xml: str):
        tpwds = regex.findall(self.TPWD_REG2, xml)
        self.tpwds_list[yd_id] = tpwds
        m = self.new_tpwds_map
        r_log, r_num = [], 0
        EXIST = "PASSWORD_NOT_EXIST::口令不存在"
        DECODER_EXC = "DECODER_EXCEPTION::商品已下架"
        NO_GOODS = "GOODS_NOT_FOUND::未参加淘客"
        TPWD_ERROR = "TPWD_ERROR::淘口令生成异常"
        for idx, o_tpwd_pro in enumerate(tpwds):
            o_tpwd = o_tpwd_pro[1:-1]
            idx_log = f"No.{idx + 1} tpwd: {o_tpwd_pro}, "
            if o_tpwd not in m:
                r_log.append(f"{idx_log}{EXIST}")
                continue
            item_id, domain, title, tpwd, c_rate, c_type = [
                m.get(ii, jj)
                for ii, jj in [
                    ("item_id", ""),
                    ("domain", 20),
                    ("content", ""),
                    ("tpwd", ""),
                    ("c_rate", 0),
                    ("c_type", ""),
                ]
            ]
            tmp_title = self.items.items_detail_map.get(item_id, {}).get("title", title)
            title = tmp_title if tmp_title else title

            if domain >= 15:
                if domain == 15:
                    applied = f"{EXIST},{title}"
                elif domain == 16:
                    applied = f"{DECODER_EXC},{title}"
                elif domain == 17:
                    applied = f"{NO_GOODS},{title}"
                elif domain == 18:
                    applied = f"{TPWD_ERROR},{title}"
            else:
                applied = title
            f = False
            if f"{o_tpwd_pro}/(已失效)" in xml:
                f = True
                o_tpwd_pro = f"{o_tpwd_pro}/(已失效)"
            xml = xml.replace(o_tpwd_pro, "￥{}￥{}".format(tpwd, "/" if f else ""))
            if tpwd == o_tpwd:
                c_rate = 1
            if c_rate == 2:
                COMMISSION = "->￥{}￥ SUCCESS, 保持原链接, {}".format(tpwd, applied)
            elif c_rate == 1:
                xml = xml.replace("￥{}￥/".format(tpwd), "￥{}￥/(已失效)".format(tpwd))
                COMMISSION = "未能更新淘口令, {}".format(applied)
            else:
                COMMISSION = "->￥{}￥ SUCCESS, 佣金: {}, 类型: {}, {}".format(
                    tpwd, c_rate, c_type, applied
                )
            r_log.append(f"{idx_log}{COMMISSION}")
            r_num += int(c_rate != 1)
        return xml, r_log, r_num

    def get_xml(self, yd_id: str):
        url = self.SYNC_URL % ("download", self.cstk)
        data = {
            "fileId": self.lists_map.get(yd_id, {}).get("q", "").split("/")[-1],
            "version": -1,
            "convert": True,
            "editorType": 1,
            "cstk": self.cstk,
        }
        req = basic_req(url, 12, data=data, header=self.get_ynote_web_header(1))
        if req is None or len(req.text) < 100:
            return
        return req.text

    def update_article(self, yd_id: str, content: str):
        q = self.lists_map.get(yd_id, {}).get("q", "").split("/")[-1]
        ynote = self.ynote_list[q]
        data_basic = {
            ii: ynote[ii] for ii in ["parentId", "domain", "orgEditorType", "tags"]
        }
        data = {
            **data_basic,
            "fileId": q,
            "rootVersion": -1,
            "sessionId": "",
            "modifyTime": int(time_stamp()),
            "bodyString": content,
            "transactionId": q,
            "transactionTime": int(time_stamp()),
            "cstk": self.cstk,
        }
        url = self.SYNC_URL % ("push", self.cstk)
        req = basic_req(url, 11, data=data, header=self.get_ynote_web_header(1))
        if req is None or list(req.keys()) != [
            "entry",
            "meta",
            "effectedShareEntries",
            "forcePullVersion",
            "effected",
        ]:
            echo(
                "0|error",
                f"Update atricle {yd_id} Error",
                req.json() if req is not None else "",
            )
            return False
        echo("1|warning", f"Update atricle {yd_id} Success!!!")
        return True

    def share_yd_article(self, yd_id: str):
        q = self.lists_map.get(yd_id, {}).get("q", "").split("/")[-1]
        if not q:
            return False
        url = self.MYSHARE_URL % (q, self.cstk)
        req = basic_req(url, 1, header=self.get_ynote_web_header(1))
        if req is None or list(req.keys()) != ["entry", "meta"]:
            return False
        echo("2", "Share article {} Success!!!".format(yd_id))
        return True

    def load_article_local(self, yd_path: str):
        self.change_tpwd(yd_path)
        self.get_article_tpwds(yd_path, mode="local")
        self.load_num = [0, 0]
        for tpwd in set(self.tpwds_list[yd_path]):
            self.get_tpwd_detail_pro(tpwd, yd_path, is_wait=True)
        echo(
            2,
            f"Article {yd_path} Load {self.load_num[0]} Tpwds and {self.load_num[1]} Items Info.",
        )

    def load_picture(self, url: str, idx: int):
        td = basic_req(url, 2)
        picture_path = "picture/{}.jpg".format(idx)
        with open(picture_path, "wb") as f:
            f.write(td.content)

    def load_picture_pipeline(self, yd_path: str):
        mkdir("picture")
        tpwds = self.tpwds_list[yd_path]
        urls = [
            (self.new_tpwds_map[tpwd]["picUrl"], idx)
            for idx, tpwd in enumerate(tpwds)
            if tpwd in self.new_tpwds_map
            and not os.path.exists("picture/{}.jpg".format(idx))
        ]
        echo(1, "Load {} picture Begin".format(len(urls)))
        pp = [self.tpwd_exec.submit(self.load_picture, ii, jj) for ii, jj in urls]
        return pp

    def check_overdue(self):
        def check_overdue_req(tpwd_data: map) -> bool:
            dif_time = time_stamp(tpwd_data["expire_at"]) - time_stamp()
            return dif_time > 0 and dif_time <= self.ONE_HOURS * self.ONE_DAY

        overdue_tpwds = [
            tpwd
            for tpwd, tpwd_data in self.tpwds_db_map.items()
            if check_overdue_req(tpwd_data)
        ]
        yd_ids_map = Counter(
            [self.tpwds_db_map[tpwd]["article_id"] for tpwd in overdue_tpwds]
        )
        if not yd_ids_map:
            return
        title = "链接需要更新#{}#篇".format(len(yd_ids_map))
        content = f"{title}\n \n"
        for yd_id, num in sorted(yd_ids_map.items(), lambda x: -(x[1])):
            title = self.lists_map.get(yd_id, {}).get("title", "")
            content += f"{title}, 需要更新{num}个链接，{self.SHARE_URL % yd_id}\n"
        content += "\n\nPlease update within 6 hours, Thx!"
        echo("2|debug", title, content)
        send_email(content, title)

    def load_share_total(self):
        for yd_ids in self.yd_ids:
            self.get_yd_detail(yd_ids)
        self.store_db()
        self.__init__()
        self.load_process()

    def load_yds(self):
        yd_ids = self.yd_ids.copy()
        np.random.shuffle(yd_ids)
        for yd_id in yd_ids:
            self.get_yd_tpwds_detail(yd_id, is_wait=True)
        self.check_overdue()

    def load_click(self, num=1000000):
        for index in range(num):
            flag = begin_time()
            if index % 6 != 1:
                self.load_yds()
            if index % 6 == 1:
                self.load_share_total()
            spend_time = end_time(flag, 0)
            echo(
                3,
                f"No. {index + 1} load article spend {get_time_str(spend_time, False)}",
            )
            time.sleep(max(self.ONE_HOURS * 4 - spend_time, 0))

    def does_update(self, do_it: bool) -> int:
        if do_it:
            return 2
        if not os.path.exists(TPWDLIST_PATH):
            return 3
        if len(self.tpwd_list) <= 20:
            return 0
        old, _, _ = load_bigger(TPWDLIST_PATH)
        return int(old != self.tpwd_list)

    def generate_local_yd_info(self, yd_path: str):
        o_text = "\n".join(read_file(yd_path))
        for tpwd in self.tpwds_list[yd_path]:
            item_id = self.tpwds_map.get(tpwd, {}).get("item_id", "")
            if not item_id or item_id not in self.items.items_detail_map:
                continue

            price, shop_id, rate_keywords = [
                self.items.items_detail_map[item_id].get(ii, jj)
                for ii, jj in [
                    ("price", ""),
                    ("shop_id", ""),
                    ("rate_keywords", ""),
                ]
            ]
            shop_name = self.items.shops_detail_map.get(shop_id, {}).get(
                "shop_name", ""
            )
            origin_str = f"\n3￥{tpwd}￥/"
            replace_str = origin_str
            if shop_name:
                replace_str = f"\n店铺 {shop_name}" + replace_str
            if price:
                replace_str = f" {price}" + replace_str
            if rate_keywords:
                keywords_list = sorted(
                    [ii.split(":") for ii in rate_keywords.split(",")],
                    key=lambda i: -int(i[1]),
                )
                advantages = [ii for ii in keywords_list if ii[-1] == "1"]
                disadvantages = [ii for ii in keywords_list if ii[-1] == "-1"]
                if advantages:
                    replace_str += "\n优点: {}".format(
                        ", ".join([f"{ii}({jj}人)" for ii, jj, _ in advantages])
                    )
                if disadvantages:
                    replace_str += "\n缺点: {}".format(
                        ", ".join([f"{ii}({jj}人)" for ii, jj, _ in disadvantages])
                    )
            o_text = o_text.replace(origin_str, replace_str)
        with open(yd_path, "w") as f:
            f.write(o_text)

    def change_tpwd(self, yd_path):
        origin = read_file(yd_path)
        origin = [
            "".join(["￥" if jj in UNICODE_EMOJI else jj for jj in ii]) for ii in origin
        ]
        for ii in range(len(origin)):
            text = origin[ii]
            tpwds = regex.findall(self.TPWD_REG3, text)
            if tpwds:
                text = f"3￥{tpwds[0][1]}￥/"
                origin[ii] = text
        with open(yd_path, "w") as f:
            f.write("\n".join(origin))


if __name__ == "__main__":
    ba = ActivateArticle()
    ba.load_process()
    ba.load_click()
