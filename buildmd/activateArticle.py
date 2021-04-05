# -*- coding: utf-8 -*-
# @Author: gunjianpan
# @Date:   2019-08-26 20:46:29
# @Last Modified by:   gunjianpan
# @Last Modified time: 2021-04-04 23:39:06

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
    ARTICLE_LIST = [
        "`id`",
        "article_id",
        "tpwd_id",
        "item_id",
        "tpwd",
        "domain",
        "content",
        "url",
        "commission_rate",
        "commission_type",
        "expire_at",
        "created_at",
    ]
    S_LIST_SQL = "SELECT `id`, article_id, title, q, created_at from article;"
    I_LIST_SQL = "INSERT INTO article (article_id, title, q) VALUES %s;"
    R_LIST_SQL = "REPLACE INTO article (`id`, article_id, title, q, is_deleted, created_at) VALUES %s;"
    S_ARTICLE_SQL = "SELECT {} from article_tpwd%s;".format(", ".join(ARTICLE_LIST))
    I_ARTICLE_SQL = "INSERT INTO article_tpwd ({}) VALUES %s;".format(
        ", ".join(ARTICLE_LIST[1:-1])
    )
    R_ARTICLE_SQL = "REPLACE INTO article_tpwd ({}, is_deleted) VALUES %s;".format(
        ", ".join(ARTICLE_LIST)
    )
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
        2: "detail.tmall.com",
        5: "uland.taobao.com",
        10: "taoquan.taobao.com",
        11: "a.m.taobao.com",
        13: "id=",
        15: "empty",
        16: "failure",
    }
    NEED_KEY_V1 = ["content", "url", "validDate", "picUrl"]
    NEED_KEY = ["content", "url", "expire", "picUrl"]
    TABLE_LISTS = ["twpd.sql", "article.sql"]
    ONE_HOURS = 3600
    ONE_DAY = 24
    ZERO_STAMP = "0天0小时0分0秒"
    T_FORMAT = "%m-%d %H:%M"
    BASIC_STAMP = (
        time_stamp(time_format="%d天%H小时%M分%S秒", time_str="1天0小时0分0秒")
        - ONE_DAY * ONE_HOURS
    )

    def __init__(self):
        super(ActivateArticle, self).__init__()
        self.BASIC_TIMEX_STR = time_str()
        self.BASIC_TIMEX_STAMP = time_stamp()
        self.items = Items(
            {
                "time_str": self.BASIC_TIMEX_STR,
                "time_stamp": self.BASIC_TIMEX_STAMP,
                "proxy_req": proxy_req,
            }
        )
        self.Db = self.items.db
        for table in self.TABLE_LISTS:
            self.Db.create_table(os.path.join(sql_dir, table))
        self.tpwd_map = {}
        self.tpwd_db_map = {}
        self.tpwds = {}
        self.tpwd_list = {}
        self.share2article = {}
        self.article_list = {}
        self.list_recent = {}
        self.idx = []
        self.empty_content = ""
        self.tpwd_exec = ThreadPoolExecutor(max_workers=1)
        self.spends = []
        self.lock = threading.Lock()
        self.get_share_list()

    def load_process(self):
        self.load_ids()
        if len(self.idx) < 30:
            time.sleep(np.random.rand() * 30 + 6)
            self.load_ids()
        self.load_article_list()
        # self.update_tpwd()
        self.items.get_m_h5_tk()
        self.get_ynote_file()
        self.get_ynote_file(1)

    def load_ids(self):
        changeJsonTimeout(5)
        req = self.basic_youdao(self.home_id)
        if req == "":
            echo("0|error", "Get The Home Page Info Error!!! Please retry->->->")
            return
        self.idx = regex.findall("id=(\w*?)<", req)
        if len(self.idx) < 30:
            echo("0|error", "The Num of id is error!! Please check it.")
        else:
            echo(1, "Load Article List {} items.".format(len(self.idx)))

    def get_share_info(self, share_id: str):
        changeJsonTimeout(4)
        url = self.GET_SHARE_URL % share_id
        headers = self.get_tb_headers(self.Y_URL)
        req = basic_req(url, 1, header=headers)
        if req is None:
            return
        info = req["entry"]
        self.share2article[share_id] = (
            info["name"].replace(".note", ""),
            info["id"],
            info["lastUpdateTime"],
        )
        return req

    def basic_youdao(self, idx: str, use_proxy: bool = False):
        url = self.NOTE_URL % idx
        refer_url = self.SHARE_URL % idx
        headers = {
            "Accept": "*/*",
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

    def load_article_pipeline(self, mode: int = 0):
        article_exec = ThreadPoolExecutor(max_workers=5)
        a_list = [article_exec.submit(self.load_article, ii, mode) for ii in self.idx]
        list(as_completed(a_list))
        self.load_list2db()

    def load_article(self, article_id: str, mode: int = 0, is_load2db: bool = True):
        if mode:
            self.get_share_info(article_id)
            self.load_list2db()
            return
        if article_id not in self.tpwds:
            article = self.basic_youdao(article_id)
            self.tpwd_list[article_id] = regex.findall(self.TPWD_REG, article)
            tpwds = list({ii: 0 for ii in self.tpwd_list[article_id]})
            if len(tpwds):
                self.tpwds[article_id] = tpwds
        else:
            tpwds = self.tpwds[article_id]
        need_tpwds = []
        for tpwd in tpwds:
            if tpwd in self.tpwd_db_map:
                t = self.tpwd_db_map[tpwd]
                need_tpwds.append(tpwd)
                # if t[-2] >= self.BASIC_TIMEX_STR:
                #     need_tpwds.append(tpwd)
            else:
                need_tpwds.append(tpwd)
        time = 0
        au_list = []
        no_type = [
            ii
            for ii, jj in self.tpwd_map.items()
            if jj["article_id"] == article_id
            and ("type" not in jj or "item_id" not in jj or jj["item_id"] is None)
        ]
        while (
            [1 for ii in need_tpwds if ii not in self.tpwd_map]
            or (len(no_type) and not time)
        ) and time < 5:
            thread_list = [ii for ii in need_tpwds if not ii in self.tpwd_map]
            self.spends = []
            echo(
                1,
                article_id,
                "tpwds len:",
                len(need_tpwds),
                "need load",
                len(thread_list),
            )
            thread_list = [
                self.tpwd_exec.submit(self.decoder_tpwd_once, article_id, ii, 0, True)
                for ii in thread_list
            ]
            list(as_completed(thread_list))
            echo(2, f"Avager spend {np.mean(self.spends):.2f} s.")
            no_type = [
                ii
                for ii, jj in self.tpwd_map.items()
                if jj["article_id"] == article_id
                and ("type" not in jj or "item_id" not in jj or jj["item_id"] is None)
            ]
            au_list.extend(
                [
                    self.tpwd_exec.submit(self.decoder_tpwd_url, article_id, ii)
                    for ii in no_type
                ]
            )
            time += 1
        list(as_completed(au_list))
        if is_load2db:
            self.load_article2db(article_id)

    def update_title(self, article_id: str):
        for ii in self.article_list[article_id].values():
            self.tpwd_map[ii[3]] = {
                "content": ii[1],
                "item_id": ii[0],
                "article_id": article_id,
            }
        no_title = [
            ii
            for ii, jj in self.tpwd_map.items()
            if jj["article_id"] != article_id and "title" not in jj
        ]
        time = 0
        while len(no_title) and time < 5:
            title_list = [
                self.tpwd_exec.submit(self.get_item_title, article_id, ii)
                for ii in no_title
            ]
            echo(1, article_id, "need get title:", len(title_list))
            list(as_completed(title_list))
            time += 1
            no_title = [
                ii
                for ii, jj in self.tpwd_map.items()
                if jj["article_id"] != article_id and "title" not in jj
            ]
        update_num = len(
            [
                1
                for ii, jj in self.tpwd_map.items()
                if jj["article_id"] != article_id
                and "title" in jj
                and jj["content"] != jj["title"]
            ]
        )
        echo(2, "Update", article_id, update_num, "Title Success!!!")
        self.update_article2db(article_id)

    def load_list2db(self):
        t_share_map = self.share2article.copy()
        share_map = self.get_share_list()
        insert_list, update_list = [], []
        for ii, jj in t_share_map.items():
            if ii in share_map:
                t = share_map[ii]
                update_list.append((t[0], ii, jj[0], jj[1], 0, t[-1]))
            else:
                insert_list.append((ii, jj[0], jj[1]))
        self.items.update_db(insert_list, self.I_LIST_SQL, "Insert Article List")
        self.items.update_db(update_list, self.R_LIST_SQL, "Update Article List")

    def get_share_list(self):
        share_list = self.Db.select_db(self.S_LIST_SQL)
        if share_list == False:
            return
        share_map = {}
        for ii, jj in enumerate(share_list):
            t = jj[-1].strftime("%Y-%m-%d %H:%M:%S")
            share_map[jj[1]] = (*jj[:-1], t)
        self.share2article = share_map
        return share_map

    def load_article2db(self, article_id: str):
        m = {
            ii: jj
            for ii, jj in self.tpwd_map.items()
            if jj["article_id"] == article_id and jj["url"]
        }
        if article_id not in self.tpwds:
            return
        tpwds = list(set(self.tpwds[article_id]))
        data = [
            (
                article_id,
                ii,
                m[jj]["item_id"],
                jj,
                m[jj]["type"],
                m[jj]["title"] if "title" in m[jj] else m[jj]["content"],
                m[jj]["url"],
                0,
                "",
                m[jj]["validDate"],
            )
            for ii, jj in enumerate(tpwds)
            if jj in m and "item_id" in m[jj] and m[jj]["type"] != 15
        ]
        data_map = {ii[3]: ii for ii in data}
        update_list, insert_list = [], []
        for ii in data:
            if ii[3] in self.tpwd_db_map:
                t = self.tpwd_db_map[ii[3]]
                if ii[6] or (not ii[6] and not t["url"]):
                    update_list.append((t[0], *ii, t[-1], 0))
            else:
                insert_list.append(ii)
        for ii, jj in self.tpwd_db_map.items():
            if jj[1] != article_id:
                continue
            if ii not in data_map:
                update_list.append((*jj, 1))
        self.items.update_db(
            insert_list, self.I_ARTICLE_SQL, f"article_id {article_id} Insert"
        )
        self.items.update_db(
            update_list, self.R_ARTICLE_SQL, f"article_id {article_id} Update"
        )
        if len(insert_list):
            self.load_ids()
            self.load_article_list()

    def update_tpwd(self, mode: int = 0, is_renew: bool = True, a_id: str = None):
        update_num = 0
        for o_tpwd, c in self.tpwd_db_map.items():
            if a_id is not None and c[1] != a_id:
                continue
            num_iid, title, domain, tpwd, url = [c[i] for i in [3, 6, 5, 4, 7]]
            if num_iid in self.items.items_detail_map:
                titile = self.items.items_detail_map[num_iid]["title"]

            if (
                is_renew
                and self.URL_DOMAIN[1] not in url
                and self.URL_DOMAIN[2] not in url
                and self.URL_DOMAIN[10] not in url
            ):
                renew_type = 2 if self.URL_DOMAIN[5] in url else 1
                origin_tpwd = self.convert2tpwd(url, title)
                if origin_tpwd is None:
                    origin_tpwd = tpwd
            else:
                renew_type = 0
                origin_tpwd = tpwd
            if num_iid == "" or domain == 16:
                c = [
                    *c[:4],
                    origin_tpwd,
                    16,
                    title,
                    url,
                    1 if renew_type == 0 else 2,
                    *c[-3:],
                ]
            else:
                c = self.generate_tpwd(
                    title, int(num_iid), origin_tpwd, renew_type, c, mode
                )
            self.tpwd_db_map[o_tpwd] = c
            update_num += int(c[5] < 15 or (renew_type and not mode))
        echo(2, "Update {} Tpwd Info Success!!".format(update_num))

    def generate_tpwd(
        self,
        title: str,
        num_iid: int,
        renew_tpwd: str,
        renew_type: int,
        c: dict,
        mode: int,
    ):
        goods = self.get_dg_material(title, num_iid)
        if goods is None or not len(goods):
            echo(
                0,
                "goods get",
                "error" if goods is None else "empty",
                ":",
                title,
                num_iid,
            )
            return [
                *c[:4],
                renew_tpwd,
                17,
                title,
                c[7],
                1 if renew_type == 0 else 2,
                *c[-3:],
            ]
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
            return [
                *c[:4],
                renew_tpwd,
                18,
                title,
                c[7],
                1 if renew_type == 0 else 2,
                *c[-3:],
            ]
        if renew_type == 1:
            commission_rate = 2

        return [
            *c[:4],
            tpwd,
            *c[5:8],
            commission_rate,
            commission_type,
            *c[-2:],
        ]

    def load_article_list(self):
        """
        tpwd: [goods_id, goods_name, domain, tpwd, commission_rate, commission_type, url]
        """
        for article_id in self.idx:
            article_list = self.get_article_db(article_id)
            self.article_list[article_id] = {
                ii[4]: [ii[3], ii[6], ii[5], ii[4], ii[8], ii[9], ii[7]]
                for ii in article_list
            }
            for ii in article_list:
                self.tpwd_db_map[ii[4]] = ii
        need_update = [
            1 for ii in self.tpwd_db_map.values() if ii[-2] >= self.BASIC_TIMEX_STR
        ]
        echo(
            1,
            "Load {} TPWD from db, {} TPWD need update.".format(
                len(self.tpwd_db_map), len(need_update)
            ),
        )

    def get_article_db(self, article_id: str):
        sql = (
            self.S_ARTICLE_SQL % (f' WHERE `article_id` = "{article_id}"')
            if article_id
            else ""
        )
        article_list = list(self.Db.select_db(sql))
        for ii, jj in enumerate(article_list):
            t = jj[-1].strftime("%Y-%m-%d %H:%M:%S")
            y = jj[-2].strftime("%Y-%m-%d %H:%M:%S")
            article_list[ii] = [*jj[:-2], y, t]
        return article_list

    def decoder_tpwd_once(
        self, article_id: str, tpwd: str, mode: int = 0, do_sleep: bool = False
    ):
        if tpwd in self.tpwd_map:
            return
        flag = begin_time()
        req = self.decoder_tpwd(tpwd, do_sleep)
        self.spends.append(end_time(flag, 0))
        if req is None or not len(req):
            return
        if "data" not in req or req["code"]:
            temp_map = {ii: "" for ii in self.NEED_KEY}
            temp_map["validDate"] = self.BASIC_TIMEX_STR
        else:
            temp_map = {ii: req["data"][ii] for ii in self.NEED_KEY}
            temp_map["validDate"] = temp_map["expire"]
        temp_map["url"] = temp_map["url"].strip()
        temp_map["article_id"] = article_id
        self.tpwd_map[tpwd] = temp_map
        if not mode:
            self.decoder_tpwd_url(article_id, tpwd)

    def decoder_tpwd_url(self, article_id: str, tpwd: str):
        temp_map = self.tpwd_map[tpwd]
        tpwd_type, item_id = self.analysis_tpwd_url(temp_map["url"])
        if item_id is None:
            return
        temp_map["type"] = tpwd_type
        temp_map["item_id"] = item_id
        if tpwd_type < 20:
            echo(2, "Domain:", self.URL_DOMAIN[tpwd_type], "item id:", item_id)
        self.tpwd_map[tpwd] = temp_map

    def analysis_tpwd_url(self, url: str):
        if self.URL_DOMAIN[5] in url:
            return 5, self.get_uland_url(url)
        elif self.URL_DOMAIN[11] in url:
            return 11, self.get_a_m_url(url)
        elif self.URL_DOMAIN[0] in url:
            return 0, self.get_s_click_url(url)
        elif self.URL_DOMAIN[10] in url:
            return 10, 0
        elif self.URL_DOMAIN[13] in url:
            good_id = self.get_item_id(url)
            if good_id != "":
                return 1 if self.URL_DOMAIN[1] in url else 13, good_id
            return 16, 0
        elif url == "":
            return 15, 0
        echo("0|warning", "New Domain:", regex.findall("https://(.*?)/", url), url)
        return 20, 0

    def decoder_tpwd_v1(self, tpwd: str):
        """ decoder the tpwd from taokouling from taokouling.com something failure in March 2021"""
        url = self.DECODER_TPWD_URL % (self.api_key, tpwd)
        req = basic_req(url, 1)
        # print(req.keys())
        if req is None or isinstance(req, str) or "ret" not in list(req.keys()):
            return {}
        return req

    def decoder_tpwd(self, tpwd: str, do_sleep: bool = False):
        """ decoder the tpwd from taokouling from https://taodaxiang.com/taopass"""
        if do_sleep:
            time.sleep(np.random.rand() * 10 + 2)
        url = self.DECODER_TPWD_URL_V2
        data = {"content": f"￥{tpwd}￥"}
        req = proxy_req(url, 11, data=data)
        if req is None or not isinstance(req, dict) or "code" not in list(req.keys()):
            return {}
        return req

    def get_s_click_url(self, s_click_url: str):
        """ decoder s.click real jump url @validation time: 2019.10.23"""
        time.sleep(np.random.randint(0, 10))
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

    def get_tb_headers(self, url: str = "", refer_url: str = "") -> dict:
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
        headers = self.get_tb_headers(refer_url=referer)
        req_func = basic_req if is_direct else proxy_req
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
        headers = self.get_tb_headers(refer_url=tu_url)
        req = proxy_req(redirect_url, 2, header=headers)
        if req is None or "id=" not in req.url:
            if can_retry(redirect_url):
                return self.get_s_click_detail(redirect_url, tu_url)
            else:
                return
        return self.get_item_id(req.url)

    def get_item_id(self, item_url: str) -> int:
        item = decoder_url(item_url)
        if not "id" in item or not item["id"].isdigit():
            echo(0, "id not found:", item_url)
            return ""
        return int(item["id"])

    def get_item_title_once(self, item_id: int) -> str:
        item = self.get_tb_getdetail(item_id)
        if item is None:
            return ""
        return item["title"]

    def get_item_title(self, article_id: str, tpwd: str):
        ## TODO: REMOVE
        temp_map = self.tpwd_map[tpwd]
        if (
            "item_id" not in temp_map
            or temp_map["item_id"] == ""
            or temp_map["item_id"] == "0"
        ):
            return
        item_id = int(temp_map["item_id"])
        title = self.get_item_title_once(item_id)
        if title != "":
            self.tpwd_map[tpwd]["title"] = title

    def get_item_title_once_v1(self, item_id: int) -> str:
        req = self.get_item_basic(item_id)
        if req is None:
            return ""
        req_text = req.text
        req_title = regex.findall('data-title="(.*?)">', req_text)
        if len(req_title):
            return req_title[0]
        req_title = regex.findall('<meta name="keywords" content="(.*?)"', req_text)
        if len(req_title):
            return req_title[0]
        return ""

    def get_item_basic(self, item_id: int, url: str = ""):
        url = self.ITEM_URL % item_id if url == "" else url
        headers = {"Accept": get_accept("html")}
        req = proxy_req(url, 2, header=headers, config={"allow_redirects": False})
        if req is None:
            if can_retry(url):
                return self.get_item_basic(item_id, url)
            return
        if req.status_code != 200:
            return self.get_item_basic(item_id, req.headers["Location"])
        return req

    def get_uland_url(self, uland_url: str):
        if (
            not "uland" in self.iitems.cookies
            # or not self.M in self.iitems.cookies['uland']
            or time_stamp() - self.m_time > self.ONE_HOURS / 2
        ):
            self.items.get_m_h5_tk()
        s_req = self.items.get_uland_url_req(uland_url, self.iitems.cookies["uland"])
        if s_req is None:
            return ""
        req_text = s_req.text
        re_json = json.loads(req_text[req_text.find("{") : -1])
        return re_json["data"]["resultList"][0]["itemId"]

    def get_a_m_url(self, a_m_url: str):
        req = self.get_a_m_basic(a_m_url)
        if req is None:
            return
        item_url = req.headers["location"]
        return self.get_item_id(item_url)

    def get_a_m_basic(self, a_m_url: str):
        headers = self.get_tb_headers(a_m_url)
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
        list_recent = {ii["fileEntry"]["id"]: ii["fileEntry"] for ii in req}
        self.list_recent = {**self.list_recent, **list_recent}
        echo(1, "Load ynote file {} items.".format(len(self.list_recent)))
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

    def replace_tpwd4article_pipeline(self, article_id: str):
        xml = self.get_xml(article_id)
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
        flag = self.update_article(article_id, xml)
        if flag:
            echo(1, f"Update {article_id} Success!! replace {len(tpwds)} tpwds")

    def update_article_pipeline(self, article_id: str):
        xml = self.get_xml(article_id)
        if xml is None:
            echo("0|warning", "get xml error")
            return
        xml, r_log, r_num = self.replace_tpwd(article_id, xml)
        if not r_num:
            echo("0|warning", "r_num == 0")
            return
        flag = self.update_article(article_id, xml)
        if flag:
            need_num = len(regex.findall("\(已失效\)", xml))
            self.email_update_result(article_id, r_log, r_num, need_num)
            # self.update_valid(article_id)
            self.update_article2db(article_id, True)
            self.share_article(article_id)

    def fix_failure(self, article_id: str, store: bool = False):
        xml = self.get_xml(article_id)
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
            flag = self.update_article(article_id, xml)
            echo("1", flag, "Success fix {} tpwds in {}.".format(num, article_id))
        else:
            echo("2", "No need fix in {}.".format(article_id))

    def email_update_result(
        self, article_id: str, r_log: list, r_num: int, need_num: int
    ):
        p = self.share2article[article_id][-2].split("/")[-1]
        article_info = self.list_recent[p]
        name = article_info["name"].replace(".note", "")
        subject = "更新({}){}/{}剩{}条[{}]".format(
            time_str(time_format=self.T_FORMAT),
            r_num,
            len(r_log),
            need_num,
            article_info["name"].replace(".note", ""),
        )
        content = "\n".join(
            [
                "Title: {}".format(article_info["name"]),
                "Time: {}".format(time_str()),
                "Update Num: {}/{}条, 还有{}条需要手动更新".format(r_num, len(r_log), need_num),
                "",
                *r_log,
            ]
        )
        send_email(content, subject, assign_rec=self.assign_rec)

    def update_valid(self, article_id: str):
        wait_list = [
            ii for ii in self.article_list[article_id].keys() if ii not in self.tpwd_map
        ]
        update_time = 0
        while len(wait_list) and update_time < 5:
            echo(2, "Begin Update No.{} times Tpwd validDate".format(update_time + 1))
            update_v = [
                self.tpwd_exec.submit(self.decoder_tpwd_once, article_id, ii, 1)
                for ii in wait_list
            ]
            list(as_completed(update_v))
            wait_list = [
                ii
                for ii in self.article_list[article_id].keys()
                if ii not in self.tpwd_map
            ]
            update_time += 1

    def update_article2db(self, article_id: str, is_tpwd_update: bool = False):
        data = []
        for o_tpwd in self.tpwds[article_id]:
            """
            `id`, article_id, tpwd_id, item_id, tpwd, domain, content, url, commission_rate, commission_type, expire_at, created_at, is_deleted
            """
            if o_tpwd[1:-1] not in self.tpwd_db_map:
                continue
            n = self.tpwd_db_map[o_tpwd[1:-1]]
            data.append(
                (
                    *n[:-2],
                    time_str(
                        self.BASIC_TIMEX_STAMP + self.ONE_DAY * self.ONE_HOURS * 5
                    ),
                    n[-1],
                    0,
                )
            )
        self.items.update_db(
            data, self.R_ARTICLE_SQL, "Update Article {} TPWD".format(article_id)
        )

    def replace_tpwd(self, article_id: str, xml: str):
        tpwds = regex.findall(self.TPWD_REG2, xml)
        self.tpwds[article_id] = list(set(tpwds))
        m = self.tpwd_db_map
        r_log, r_num = [], 0
        EXIST = "PASSWORD_NOT_EXIST::口令不存在"
        DECODER_EXC = "DECODER_EXCEPTION::商品已下架"
        NO_GOODS = "GOODS_NOT_FOUND::未参加淘客"
        TPWD_ERROR = "TPWD_ERROR::淘口令生成异常"
        for ii, jj in enumerate(tpwds):
            pure_jj = jj[1:-1]
            no_t = "No.{} tpwd: {}, ".format(ii + 1, jj)
            if pure_jj not in m:
                r_log.append("{}{}".format(no_t, EXIST))
                continue
                # tpwd = 'NOTNOTEXIST'
            title, domain, tpwd, commission_rate, commission_type = [
                m[pure_jj][i] for i in [6, 5, 4, 8, 9]
            ]
            if domain >= 15:
                if domain == 15:
                    applied = "{},{}".format(EXIST, title)
                elif domain == 16:
                    applied = "{},{}".format(DECODER_EXC, title)
                elif domain == 17:
                    applied = "{},{}".format(NO_GOODS, title)
                elif domain == 18:
                    applied = "{},{}".format(TPWD_ERROR, title)
            else:
                applied = title
            f = False
            if "{}/(已失效)".format(jj) in xml:
                f = True
                jj = "{}/(已失效)".format(jj)
            xml = xml.replace(jj, "￥{}￥{}".format(tpwd, "/" if f else ""))
            if tpwd == pure_jj:
                commission_rate = 1
            if commission_rate == 2:
                COMMISSION = "->￥{}￥ SUCCESS, 保持原链接, {}".format(tpwd, applied)
            elif commission_rate == 1:
                xml = xml.replace("￥{}￥/".format(tpwd), "￥{}￥/(已失效)".format(tpwd))
                COMMISSION = "未能更新淘口令, {}".format(applied)
            else:
                COMMISSION = "->￥{}￥ SUCCESS, 佣金: {}, 类型: {}, {}".format(
                    tpwd, commission_rate, commission_type, applied
                )
            r_log.append("{}{}".format(no_t, COMMISSION))
            r_num += int(commission_rate != 1)
        return xml, r_log, r_num

    def get_xml(self, article_id: str):
        url = self.SYNC_URL % ("download", self.cstk)
        data = {
            "fileId": self.share2article[article_id][-2].split("/")[-1],
            "version": -1,
            "convert": True,
            "editorType": 1,
            "cstk": self.cstk,
        }
        req = basic_req(url, 12, data=data, header=self.get_ynote_web_header(1))
        if req is None or len(req.text) < 100:
            return
        return req.text

    def update_article(self, article_id: str, article_body: str):
        p = self.share2article[article_id][-2].split("/")[-1]
        article_info = self.list_recent[p]
        data = {
            "fileId": p,
            "parentId": article_info["parentId"],
            "domain": article_info["domain"],
            "rootVersion": -1,
            "sessionId": "",
            "modifyTime": int(time_stamp()),
            "bodyString": article_body,
            "transactionId": p,
            "transactionTime": int(time_stamp()),
            "orgEditorType": article_info["orgEditorType"],
            "tags": article_info["tags"],
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
                "Update atricle_id {} Error".format(article_id),
                req.json() if req is not None else "",
            )
            return False
        echo("1|warning", "Update atricle_id {} Success!!!".format(article_id))
        return True

    def share_article(self, article_id: str):
        p = self.share2article[article_id][-2].split("/")[-1]
        url = self.MYSHARE_URL % (p, self.cstk)
        req = proxy_req(url, 1, header=self.get_ynote_web_header(1))
        if req is None or list(req.keys()) != ["entry", "meta"]:
            if can_retry(url):
                return self.share_article(article_id)
            return False
        echo("2", "Share article {} Success!!!".format(article_id))
        return True

    def load_article_local(self, file_path: str):
        if file_path not in self.tpwds:
            tt = "||||".join(read_file(file_path))
            tpwds = regex.findall(self.TPWD_REG, tt)
            self.tpwds[file_path] = tpwds
        else:
            tpwds = self.tpwds[file_path]
        time = 0
        while [1 for ii in tpwds if ii not in self.tpwd_map] and time < 5:
            thread_list = [ii for ii in tpwds if not ii in self.tpwd_map]
            echo(1, file_path, "tpwds len:", len(tpwds), "need load", len(thread_list))
            thread_list = [
                self.tpwd_exec.submit(self.decoder_tpwd_once, file_path, ii, 1)
                for ii in thread_list
            ]
            list(as_completed(thread_list))
            time += 1

    def load_picture(self, url: str, idx: int):
        td = basic_req(url, 2)
        picture_path = "picture/{}.jpg".format(idx)
        with open(picture_path, "wb") as f:
            f.write(td.content)

    def load_picture_pipeline(self, file_path: str):
        mkdir("picture")
        tpk_list = self.tpwds[file_path]
        picture_url = [
            (self.tpwd_map[tpk]["picUrl"], idx)
            for idx, tpk in enumerate(tpk_list)
            if tpk in self.tpwd_map
        ]
        picture_url = [
            (ii, idx)
            for ii, idx in picture_url
            if not os.path.exists("picture/{}.jpg".format(idx))
        ]
        echo(1, "Load {} picture Begin".format(len(picture_url)))
        pp = [
            self.tpwd_exec.submit(self.load_picture, ii, jj) for ii, jj in picture_url
        ]
        return pp

    def check_overdue(self):
        def check_overdue_once(data: list) -> bool:
            dif_time = time_stamp(data[-2]) - time_stamp()
            return dif_time > 0 and dif_time <= self.ONE_HOURS * self.ONE_DAY

        overdue_article = [
            (jj[1], ii) for ii, jj in self.tpwd_db_map.items() if check_overdue_once(jj)
        ]
        overdue_id = set([article_id for article_id, _ in overdue_article])
        overdue_list = [
            (
                article_id,
                len([1 for a_id, tpwd in overdue_article if article_id == a_id]),
            )
            for article_id in overdue_id
        ]
        if not len(overdue_list):
            return
        title = "链接需要更新#{}#篇".format(len(overdue_list))
        content = title + "\n \n"
        for article_id, num in overdue_list:
            content += "{}, 需要更新{}个链接，{}\n".format(
                self.share2article[article_id][2], num, self.NOTE_URL % article_id
            )
        content += "\n\nPlease update within 6 hours, Thx!"
        echo("2|debug", title, content)
        send_email(content, title)

    def load_share_total(self):
        self.check_overdue()
        for article_id in self.idx:
            self.get_share_info(article_id)
        self.load_list2db()
        self.__init__()
        self.load_process()

    def load_article_new(self):
        article_exec = ThreadPoolExecutor(max_workers=3)
        np.random.shuffle(self.idx)
        N = len(self.idx)
        for i in range(int(N // 3)):
            self.load_article(self.idx[i])
            # a_list = [
            #     article_exec.submit(self.load_article, ii)
            #     for ii in self.idx[i * 3 : i * 3 + 3]
            # ]
            # list(as_completed(a_list))
            time.sleep(np.random.rand() * 20 * 3 + 10)
        self.check_overdue()
        # self.send_repeat_email()

    def load_click(self, num=1000000):
        """ schedule click """
        for index in range(num):
            threading_list = []
            flag = begin_time()
            if index % 6 != 1:
                threading_list.append(
                    threading.Thread(target=self.load_article_new, args=())
                )
            if index % 6 == 1:
                threading_list.append(
                    threading.Thread(target=self.load_share_total, args=())
                )
            for work in threading_list:
                work.start()
            for work in threading_list:
                work.join()
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

    def send_repeat_email(self, do_it: bool = False):
        def get_repeat(items: list):
            repeat_time = {k: v for k, v in Counter(items).items() if v >= 2}
            repeat_order = sorted(repeat_time.items(), key=lambda i: -i[1])
            return ",".join(["￥{}￥出现{}次".format(k, v) for k, v in repeat_order])

        do_update = self.does_update(do_it)
        echo(1, "Do_update:", do_update)
        if not do_update:
            return
        repeats = []
        for article_id, tpwd in self.tpwd_list.items():
            repeat = get_repeat(tpwd)
            if repeat == "":
                continue
            if article_id in self.share2article:
                p = self.share2article[article_id][-2].split("/")[-1]
                if p in self.list_recent:
                    article_info = self.list_recent[p]
                else:
                    echo(0, "P error.", p, article_id)
                    article_info = {"name": ""}
            else:
                article_info = {"name": ""}
            repeats.append(
                "{}({})共{}条: {}".format(
                    article_info["name"]
                    .replace(".note", "")
                    .split("/")[0]
                    .split(" ")[0],
                    article_id,
                    repeat.count(",") + 1,
                    repeat,
                )
            )
        subject = "重复({}){}/{}共{}条".format(
            time_str(time_format=self.T_FORMAT),
            len(repeats),
            len(self.tpwd_list),
            "".join(repeats).count(",") + len(repeats),
        )
        content = "\n".join(
            [
                "重复情况",
                "Time: {}".format(time_str()),
                "Repeat Num: {}/{}篇, 共{}条.".format(
                    len(repeats),
                    len(self.tpwd_list),
                    "".join(repeats).count(",") + len(repeats),
                ),
                "--------------------------------" "",
                *repeats,
            ]
        )
        dump_bigger([self.tpwd_list, content, subject], TPWDLIST_PATH)
        send_email(content, subject)

    def change_tpwd(self, article_path):
        origin = read_file(article_path)
        origin = [
            "".join(["￥" if jj in UNICODE_EMOJI else jj for jj in ii]) for ii in origin
        ]
        for ii in range(len(origin)):
            text = origin[ii]
            tpwds = regex.findall(self.TPWD_REG3, text)
            if tpwds:
                text = f"3￥{tpwds[0][1]}￥/"
                origin[ii] = text
        with open(article_path, "w") as f:
            f.write("\n".join(origin))

    def update_items(self):
        tpwd_list = []
        items = {}
        for tpwd, m in self.tpwd_db_map.items():
            if m[3] and (not m[6] or "打开" in m[6]):
                tpwd_list.append(tpwd)
                items[item_id] = ""
                continue
            if "?id=" in m[7] or "&id=" in m[7]:
                item_id = decoder_url(m[7])
            if "id" not in item_id:
                continue
            item_id = item_id["id"]
            if item_id != m[3] or not m[6]:
                tpwd_list.append(tpwd)
                items[item_id] = ""
        for _ in range(5):
            need_items = [ii for ii, jj in items.items() if not jj]
            echo(1, f"Need load {len(need_items)} Titles.")
            for ii in need_items:
                item = self.get_tb_getdetail(int(ii))
                if item is not None:
                    items[ii] = item["title"]
        need_items = [ii for ii, jj in items.items() if not jj]
        echo(1, f"Need load {len(need_items)} Titles.")
        return items, tpwd_list


if __name__ == "__main__":
    ba = ActivateArticle()
    ba.load_process()
    ba.load_click()
