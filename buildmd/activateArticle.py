# -*- coding: utf-8 -*-
# @Author: gunjianpan
# @Date:   2019-08-26 20:46:29
# @Last Modified by:   gunjianpan
# @Last Modified time: 2019-11-06 23:33:01

import hashlib
import json
import os
import sys
import threading
import time
import urllib
import cv2
from concurrent.futures import ThreadPoolExecutor, as_completed
from configparser import ConfigParser

import numpy as np
import regex

sys.path.append(os.getcwd())
import top
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
    encoder_cookie,
    encoder_url,
    end_time,
    headers,
    json_str,
    mkdir,
    read_file,
    send_email,
    time_stamp,
    time_str,
    get_accept,
    get_content_type,
    get_use_agent,
)


proxy_req = GetFreeProxy().proxy_req
root_dir = os.path.abspath("buildmd")
assign_path = os.path.join(root_dir, "tbk.ini")


class TBK(object):
    """ tbk info class """

    CSTK_KEY = "YNOTE_CSTK"

    def __init__(self):
        super(TBK, self).__init__()
        self.items = {}
        self.load_configure()
        self.load_tbk_info()

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
        self.uland_url = cfg.get("TBK", "uland_url")
        self.unlogin_id = cfg.get("YNOTE", "unlogin_id")
        self.cookie = cfg.get("YNOTE", "cookie")[1:-1]
        self.assign_rec = cfg.get("YNOTE", "assign_email").split(",")
        cookie_de = decoder_cookie(self.cookie)
        self.cstk = cookie_de[self.CSTK_KEY] if self.CSTK_KEY in cookie_de else ""
        top.setDefaultAppInfo(self.appkey, self.secret)

    def load_tbk_info(self):
        favorites = self.get_uatm_favor()
        for ii in favorites:
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
            self.items = {**self.items, **items}
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
            return tpwds["tbk_tpwd_create_response"]["data"]["model"][1:-1]
        except Exception as e:
            echo(0, "Generate tpwd failed", url, title, e)


class ActivateArticle(TBK):
    """ activate article in youdao Cloud"""

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
    DECODER_TPWD_URL = "http://www.taokouling.com/index/taobao_tkljm"
    Y_DOC_JS_URL = "https://shared-https.ydstatic.com/ynote/ydoc/index-6f5231c139.js"
    MTOP_URL = "https://h5api.m.taobao.com/h5/%s/1.0/"
    ITEM_URL = "https://item.taobao.com/item.htm?id=%d"
    S_LIST_SQL = "SELECT `id`, article_id, title, q, created_at from article;"
    I_LIST_SQL = "INSERT INTO article (article_id, title, q) VALUES %s;"
    R_LIST_SQL = "REPLACE INTO article (`id`, article_id, title, q, is_deleted, created_at) VALUES %s;"
    S_ARTICLE_SQL = 'SELECT `id`, article_id, tpwd_id, item_id, tpwd, domain, content, url, commission_rate, commission_type, expire_at, created_at from article_tpwd WHERE `article_id` = "%s";'
    I_ARTICLE_SQL = "INSERT INTO article_tpwd (article_id, tpwd_id, item_id, tpwd, domain, content, url, commission_rate, commission_type, expire_at) VALUES %s;"
    R_ARTICLE_SQL = "REPLACE INTO article_tpwd (`id`, article_id, tpwd_id, item_id, tpwd, domain, content, url, commission_rate, commission_type, expire_at, created_at, is_deleted) VALUES %s;"
    END_TEXT = "</text><inline-styles/><styles/></para></body></note>"
    TPWD_REG = "\p{Sc}(\w{8,12}?)\p{Sc}"
    TPWD_REG2 = "(\p{Sc}\w{8,12}\p{Sc})"
    JSON_KEYS = ["p", "ct", "su", "pr",
        "au","pv","mt","sz","domain",
        "tl","content",
    ]
    URL_DOMAIN = {
        0: "s.click.taobao.com",
        1: "item.taobao.com",
        2: "detail.tmall.com",
        5: "uland.taobao.com",
        10: "taoquan.taobao.com",
        11: "a.m.taobao.com",
        15: "empty",
        16: "failure",
    }
    NEED_KEY = ["content", "url", "validDate", "picUrl"]
    ONE_HOURS = 3600
    ONE_DAY = 24
    M = "_m_h5_tk"
    ZERO_STAMP = "0天0小时0分0秒"
    T_FORMAT = "%m-%d %H:%M"
    BASIC_STAMP = (
        time_stamp(time_format="%d天%H小时%M分%S秒", time_str="1天0小时0分0秒")
        - ONE_DAY * ONE_HOURS
    )

    def __init__(self):
        super(ActivateArticle, self).__init__()
        self.Db = Db("tbk")
        self.Db.create_table(os.path.join(root_dir, "tpwd.sql"))
        self.Db.create_table(os.path.join(root_dir, "article.sql"))
        self.tpwd_map = {}
        self.tpwd_db_map = {}
        self.tpwds = {}
        self.cookies = {}
        self.share2article = {}
        self.article_list = {}
        self.list_recent = {}
        self.idx = []
        self.empty_content = ""
        self.tpwd_exec = ThreadPoolExecutor(max_workers=20)
        self.get_share_list()

    def load_process(self):
        self.load_ids()
        self.load_article_list()
        self.update_tpwd()
        self.get_m_h5_tk()
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
        req = proxy_req(url, 1, header=headers)
        if req is None:
            if can_retry(url):
                return self.get_share_info(share_id)
            else:
                return
        info = req["entry"]
        self.share2article[share_id] = (info["name"], info["id"])
        return req

    def basic_youdao(self, idx: str, use_proxy: bool = True):
        url = self.NOTE_URL % idx
        refer_url = self.SHARE_URL % idx
        headers = {
            "Accept": "*/*",
            "Referer": refer_url,
            "X-Requested-With": "XMLHttpRequest",
        }
        req_req = proxy_req if use_proxy else basic_req
        req = req_req(url, 1, header=headers)
        if req is None or list(req.keys()) != self.JSON_KEYS:
            if can_retry(url):
                echo(2, "retry")
                return self.basic_youdao(idx)
            else:
                echo(1, "retry upper time")
                return ""
        return req["content"]

    def load_article_pipeline(self, mode: int = 0):
        article_exec = ThreadPoolExecutor(max_workers=5)
        a_list = [article_exec.submit(self.load_article, ii, mode) for ii in self.idx]
        list(as_completed(a_list))
        self.load_list2db()

    def load_article(self, article_id: str, mode: int = 0, is_load2db: bool = True):
        if mode:
            self.get_share_info(article_id)
            return
        if article_id not in self.tpwds:
            article = self.basic_youdao(article_id)
            tpwds = list({ii: 0 for ii in regex.findall(self.TPWD_REG, article)})
            self.tpwds[article_id] = tpwds
        else:
            tpwds = self.tpwds[article_id]
        if article_id not in self.tpwd_map:
            self.tpwd_map[article_id] = {}
        time = 0
        au_list = []
        no_type = [
            ii
            for ii, jj in self.tpwd_map[article_id].items()
            if "type" not in jj or jj["item_id"] is None
        ]
        while (
            len(self.tpwd_map[article_id]) < len(tpwds) or (len(no_type) and not time)
        ) and time < 5:
            thread_list = [ii for ii in tpwds if not ii in self.tpwd_map[article_id]]
            echo(1, article_id, "tpwds len:", len(tpwds), "need load", len(thread_list))
            thread_list = [
                self.tpwd_exec.submit(self.decoder_tpwd_once, article_id, ii)
                for ii in thread_list
            ]
            list(as_completed(thread_list))
            no_type = [
                ii
                for ii, jj in self.tpwd_map[article_id].items()
                if "type" not in jj or jj["item_id"] is None
            ]
            au_list.extend(
                [
                    self.tpwd_exec.submit(self.decoder_tpwd_url, article_id, ii)
                    for ii in no_type
                ]
            )
            time += 1
        list(as_completed(au_list))
        no_title = [
            ii for ii, jj in self.tpwd_map[article_id].items() if "title" not in jj
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
                ii for ii, jj in self.tpwd_map[article_id].items() if "title" not in jj
            ]
        if is_load2db:
            self.load_article2db(article_id)

    def update_title(self, article_id: str):
        self.tpwd_map[article_id] = {
            ii[3]: {"content": ii[1], "item_id": ii[0]}
            for ii in self.article_list[article_id].values()
        }
        no_title = [
            ii for ii, jj in self.tpwd_map[article_id].items() if "title" not in jj
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
                ii for ii, jj in self.tpwd_map[article_id].items() if "title" not in jj
            ]
        update_num = len(
            [
                1
                for ii, jj in self.tpwd_map[article_id].items()
                if "title" in jj and jj["content"] != jj["title"]
            ]
        )
        echo(2, "Update", article_id, update_num, "Title Success!!!")
        self.update_article2db(article_id)

    def load_list2db(self):
        share_map = self.get_share_list()
        insert_list, update_list = [], []
        for ii, jj in self.share2article.items():
            if ii in share_map:
                t = share_map[ii]
                update_list.append((t[0], ii, jj[0], jj[1], 0, t[-1]))
            else:
                insert_list.append((ii, jj[0], jj[1]))
        self.update_db(insert_list, "Insert Article List", 1)
        self.update_db(update_list, "Update Article List", 1)

    def get_share_list(self):
        share_list = self.Db.select_db(self.S_LIST_SQL)
        share_map = {}
        for ii, jj in enumerate(share_list):
            t = jj[-1].strftime("%Y-%m-%d %H:%M:%S")
            share_map[jj[1]] = (*jj[:-1], t)
        self.share2article = share_map
        return share_map

    def load_article2db(self, article_id: str):
        m = self.tpwd_map[article_id]
        m = {ii: jj for ii, jj in m.items() if jj["url"]}
        article_list = self.get_article_db(article_id)
        self.tpwd_db_map[article_id] = {ii[2]: ii for ii in article_list}
        data = [
            (
                article_id,
                ii,
                m[jj]["item_id"],
                jj,
                m[jj]["type"],
                m[jj]["content"],
                m[jj]["url"],
                0,
                "",
                m[jj]["validDate"],
            )
            for ii, jj in enumerate(self.tpwds[article_id])
            if jj in m and "item_id" in m[jj] and m[jj]["type"] != 15
        ]
        data_map = {ii[1]: ii for ii in data}
        update_list, insert_list = [], []
        for ii in data:
            if ii[1] in self.tpwd_db_map[article_id]:
                t = self.tpwd_db_map[article_id][ii[1]]
                update_list.append((t[0], *ii, t[-1], 0))
            else:
                insert_list.append(ii)
        for ii, jj in self.tpwd_db_map[article_id].items():
            if ii not in data_map:
                update_list.append((*jj, 1))
        self.update_db(insert_list, f"article_id {article_id} Insert")
        self.update_db(update_list, f"article_id {article_id} Update")

    def update_tpwd(self, mode: int = 0):
        update_num = 0
        for ii, jj in self.article_list.items():
            for kk, (num_iid, title, domain, tpwd, _, _, url) in jj.items():
                c = self.article_list[ii][kk]
                if (
                    self.URL_DOMAIN[1] not in url
                    and self.URL_DOMAIN[2] not in url
                    and self.URL_DOMAIN[10] not in url
                ):
                    renew_type = 2 if url in self.URL_DOMAIN[5] else 1
                    origin_tpwd = self.convert2tpwd(url, title)
                else:
                    renew_type = 0
                    origin_tpwd = tpwd
                if num_iid == "" or domain == 16:
                    c = (
                        *c[:2],
                        16,
                        origin_tpwd,
                        1 if renew_type == 0 else 2,
                        *c[-2:],
                    )
                else:
                    c = self.generate_tpwd(
                        title, int(num_iid), origin_tpwd, renew_type, c, mode
                    )
                self.article_list[ii][kk] = c
                update_num += int(c[2] < 15 or (renew_type))
        echo(2, "Update {} Tpwd Info Success!!".format(update_num))

    def generate_tpwd(
        self, title: str, num_iid: int, renew_tpwd: str, renew_type: int, c: dict, mode: int
    ):
        goods = self.get_dg_material(title, num_iid)
        if goods is None or not len(goods):
            echo(0, "goods get error:", title, num_iid)
            return (*c[:2], 17, renew_tpwd, 1 if renew_type == 0 else 2, *c[-2:])
        goods = goods[0]
        if "coupon_share_url" in goods and len(goods["coupon_share_url"]):
            url = goods["coupon_share_url"]
        else:
            url = goods["url"]
        url = "https:{}".format(url)
        commission_rate = int(goods["commission_rate"])
        commission_type = goods["commission_type"]
        tpwd = self.convert2tpwd(url, title)
        if tpwd is None:
            echo(0, "tpwd error:", tpwd)
            return (*c[:2], 18, renew_tpwd, 1 if renew_type == 0 else 2 * c[-2:])
        if mode:
           return (*c[:3], tpwd, commission_rate, commission_type, c[-1]) 
        if renew_type == 1:
            return (*c[:3], tpwd, 2, commission_type, c[-1])
        return (*c[:3], tpwd, commission_rate, commission_type, c[-1])

    def load_article_list(self):
        for article_id in self.idx:
            article_list = self.get_article_db(article_id)
            self.article_list[article_id] = {
                ii[2]: (ii[3], ii[6], ii[5], ii[4], ii[8], ii[9], ii[7])
                for ii in article_list
            }
        item_num = sum([len(ii) for ii in self.article_list.values()])
        echo(1, "Load {} article list from db.".format(item_num))

    def get_article_db(self, article_id: str):
        article_list = list(self.Db.select_db(self.S_ARTICLE_SQL % article_id))
        for ii, jj in enumerate(article_list):
            t = jj[-1].strftime("%Y-%m-%d %H:%M:%S")
            y = jj[-2].strftime("%Y-%m-%d %H:%M:%S")
            article_list[ii] = (*jj[:-2], y, t)
        return article_list

    def update_db(self, data: list, types: str, mode: int = 0):
        if not len(data):
            return
        if "insert" in types.lower():
            basic_sql = self.I_LIST_SQL if mode else self.I_ARTICLE_SQL
        else:
            basic_sql = self.R_LIST_SQL if mode else self.R_ARTICLE_SQL

        i_sql = basic_sql % str(data)[1:-1]
        insert_re = self.Db.insert_db(i_sql)
        if insert_re:
            echo(3, "{} {} info Success".format(types, len(data)))
        else:
            echo(0, "{} failed".format(types))

    def decoder_tpwd_once(self, article_id: str, tpwd: str, mode: int = 0):
        req = self.decoder_tpwd(tpwd)
        if req is None or not "data" in req or "!DOCTYPE html" in req or not len(req):
            return
        req = req["data"]
        temp_map = {ii: req[ii] for ii in self.NEED_KEY}
        if temp_map["validDate"] == self.ZERO_STAMP or "-" in temp_map["validDate"]:
            temp_map["validDate"] = time_stamp()
        else:
            temp_map["validDate"] = (
                time_stamp(time_format="%d天%H小时%M分%S秒", time_str=req["validDate"])
                - self.BASIC_STAMP
                + time_stamp()
            )
        temp_map["validDate"] = time_str(temp_map["validDate"])
        temp_map["url"] = temp_map["url"].strip()
        if article_id not in self.tpwd_map:
            self.tpwd_map[article_id] = {}
        self.tpwd_map[article_id][tpwd] = temp_map
        if not mode:
            self.decoder_tpwd_url(article_id, tpwd)

    def decoder_tpwd_url(self, article_id: str, tpwd: str):
        temp_map = self.tpwd_map[article_id][tpwd]
        tpwd_type, item_id = self.analysis_tpwd_url(temp_map["url"])
        if item_id is None:
            return
        temp_map["type"] = tpwd_type
        temp_map["item_id"] = item_id
        if tpwd_type < 20:
            echo(2, "Domain:", self.URL_DOMAIN[tpwd_type], "item id:", item_id)
        self.tpwd_map[article_id][tpwd] = temp_map

    def analysis_tpwd_url(self, url: str):
        if self.URL_DOMAIN[5] in url:
            return 5, self.get_uland_url(url)
        elif self.URL_DOMAIN[11] in url:
            return 11, self.get_a_m_url(url)
        elif self.URL_DOMAIN[0] in url:
            return 0, self.get_s_click_url(url)
        elif self.URL_DOMAIN[10] in url:
            return 10, 0
        elif self.URL_DOMAIN[1] in url:
            good_id = self.get_item_detail(url)
            if good_id != "":
                return 1, good_id
            return 16, 0
        elif url == "":
            return 15, 0
        echo("0|warning", "New Domain:", regex.findall("https://(.*?)/", url), url)
        return 20, 0

    def decoder_tpwd(self, tpwd: str):
        """ decoder the tpwd from taokouling """
        headers = {
            "Referer": self.DECODER_TPWD_URL,
            "X-Requested-With": "XMLHttpRequest",
        }
        text = {"text": "￥{}￥".format(tpwd)}
        req = proxy_req(self.DECODER_TPWD_URL, 11, data=text, header=headers)
        if (
            req is None
            or isinstance(req, str)
            or list(req.keys()) != ["code", "msg", "time", "data"]
        ):
            if can_retry(tpwd):
                return self.decoder_tpwd(tpwd)
            else:
                return {}
        return req

    def get_s_click_url(self, s_click_url: str):
        """ decoder s.click real jump url @validation time: 2019.10.23"""
        time.sleep(np.random.randint(0, 10))
        item_url = self.get_s_click_location(s_click_url)
        if item_url is None:
            echo(3, "s_click_url location Error..")
            return
        return self.get_item_detail(item_url)

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
        return self.get_item_detail(req.url)

    def get_item_detail(self, item_url: str) -> str:
        item = decoder_url(item_url)
        if not "id" in item:
            echo(0, "id not found:", item_url)
            return ""
        return item["id"]

    def get_item_title(self, article_id: str, tpwd: str):
        temp_map = self.tpwd_map[article_id][tpwd]
        if (
            "item_id" not in temp_map
            or temp_map["item_id"] == ""
            or temp_map["item_id"] == "0"
        ):
            return
        item_id = int(temp_map["item_id"])
        title = self.get_item_title_once(item_id)
        if title != "":
            self.tpwd_map[article_id][tpwd]["title"] = title

    def get_item_title_once(self, item_id: int) -> str:
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
            not self.M in self.cookies
            or time_stamp() - self.m_time > self.ONE_HOURS / 2
        ):
            self.get_m_h5_tk()
        s_req = self.get_uland_url_once(uland_url, self.cookies)
        req_text = s_req.text
        re_json = json.loads(req_text[req_text.find("{") : -1])
        return re_json["data"]["resultList"][0]["itemId"]

    def get_a_m_url(self, a_m_url: str):
        req = self.get_a_m_basic(a_m_url)
        if req is None:
            return
        item_url = req.headers["location"]
        return self.get_item_detail(item_url)

    def get_a_m_basic(self, a_m_url: str):
        headers = self.get_tb_headers(a_m_url)
        req = proxy_req(a_m_url, 2, header=headers, config={"allow_redirects": False})
        if req is None or "location" not in req.headers:
            if can_retry(a_m_url):
                return self.get_a_m_basic(a_m_url)
            return
        return req

    def get_m_h5_tk(self):
        self.m_time = time_stamp()
        req = self.get_uland_url_once(self.uland_url)
        if req is None:
            return
        self.cookies = req.cookies.get_dict()
        echo(1, "get m h5 tk cookie:", self.cookies)

    def get_tb_h5_api(self, api: str, jsv: str, refer_url: str, data: dict, j_data_t: dict = {}, cookies: dict = {}):
        """ tb h5 api @2019.11.6 ✔️Tested"""
        step = self.M in cookies
        data = json_str(data)
        
        headers = {"referer": refer_url}
        if step:
            headers["Cookie"] = encoder_cookie(cookies)
        appkey = "12574478"

        token = cookies[self.M].split("_")[0] if step else ""
        t = int(time_stamp() * 1000)
        j_data = {
            "jsv": jsv,
            "appKey": appkey,
            "t": t,
            "sign": self.get_tb_h5_token(token, appkey, data, t),
            "api": api,
            "v": 1.0,
            "timeout": 20000,
            "AntiCreep": True,
            "AntiFlood": True,
            "type": "originaljson",
            "dataType": "jsonp",
            "data": data,
            **j_data_t
        }
        mtop_url = encoder_url(j_data, self.MTOP_URL % api)
        req = proxy_req(mtop_url, 2, header=headers)
        echo(4, 'request once.')
        if req is None:
            if can_retry(self.MTOP_URL % api):
                return self.get_tb_h5_api(api, jsv, refer_url, data, cookies)
            else:
                return
        return req

    def get_uland_url_once(self, uland_url: str, cookies: dict = {}):
        """ tb h5 api @2019.9.7 ✔️Tested"""
        step = self.M in cookies
        uland_params = decoder_url(uland_url)
        tt = {
                "floorId": "13193" if step else "13052",
                "variableMap": json_str(
                    {
                        "taoAppEnv": "0",
                        "e": uland_params["e"],
                        "scm": uland_params["scm"],
                    }
                ),
                }
        api = "mtop.alimama.union.xt.en.api.entry"
        jsv = '2.4.0'
        j_data = {'type': 'jsonp', "callback": "mtopjsonp{}".format(int(step) + 1),}
        return self.get_tb_h5_api(api, jsv, uland_url, tt, j_data, cookies)

    def get_finger(self, item_id: int, cookies: dict = {}):
        api = 'mtop.taobao.hacker.finger.create'
        refer_url = self.ITEM_URL % item_id
        jsv = '2.4.11'
        return self.get_tb_h5_api(api, jsv, refer_url, {}, cookies)

    def get_tb_h5_token(self, token: str, appkey: str, data: str, t: int):
        md5 = hashlib.md5()
        wait_enc = "&".join([token, str(t), appkey, data])
        md5.update(wait_enc.encode())
        return md5.hexdigest()

    def get_ynote_file(self, offset: int = 0):
        url = self.LISTRECENT_URL % (offset, self.cstk)
        data = {"cstk": self.cstk}
        req = proxy_req(url, 11, data=data, header=self.get_ynote_web_header(1))
        if req is None or type(req) != list:
            if can_retry(url):
                return self.get_ynote_file(offset)
            else:
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
            self.email_update_result(article_id, r_log, r_num)
            self.update_valid(article_id)
            self.update_article2db(article_id)
            self.share_article(article_id)

    def email_update_result(self, article_id: str, r_log: list, r_num: int):
        p = self.share2article[article_id][-2].split("/")[-1]
        article_info = self.list_recent[p]
        name = article_info["name"].replace(".note", "")
        subject = "更新({}){}/{}条[{}]".format(
            time_str(time_format=self.T_FORMAT), r_num, len(r_log), article_info["name"]
        )
        content = "\n".join(
            [
                "Title: {}".format(article_info["name"]),
                "Time: {}".format(time_str()),
                "Update Num: {}/{}条".format(r_num, len(r_log)),
                "",
                *r_log,
            ]
        )
        send_email(content, subject, assign_rec=self.assign_rec)

    def update_valid(self, article_id: str):
        if article_id not in self.tpwd_map:
            self.tpwd_map[article_id] = {}
        wait_list = [
            ii[-4]
            for ii in self.article_list[article_id].values()
            if ii[-4] not in self.tpwd_map[article_id]
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
                ii[-4]
                for ii in self.article_list[article_id].values()
                if ii[-4] not in self.tpwd_map[article_id]
            ]
            update_time += 1

    def update_article2db(self, article_id: str):
        def valid_t(types: str, maps: dict):
            return types in maps and maps[types] != ''
        m = {ii[2]: ii for ii in self.get_article_db(article_id)}
        data = []
        for (
            ii,
            (num_iid, title, domain, tpwd, commission_rate, commission_type, ur),
        ) in self.article_list[article_id].items():
            """
            `id`, article_id, tpwd_id, item_id, tpwd, domain, content, url, commission_rate, commission_type, expire_at, created_at, is_deleted
            """
            n = m[ii]
            if tpwd in self.tpwd_map[article_id]:
                t = self.tpwd_map[article_id][tpwd]
                content = (
                    t["title"]
                    if valid_t('title', t)
                    else (t['content'] if valid_t('content', t) else n[6])
                )
                url = t["url"] if valid_t('url', t) else n[7]
                validDate = t["validDate"] if valid_t('validDate', t) else n[-2]
                data.append(
                    (
                        *n[:4],
                        tpwd,
                        domain,
                        content,
                        url,
                        commission_rate,
                        commission_type,
                        validDate,
                        n[-1],
                        0,
                    )
                )
            else:
                data.append(
                    (
                        *n[:4],
                        tpwd,
                        domain,
                        n[6],
                        n[7],
                        commission_rate,
                        commission_type,
                        n[-2],
                        n[-1],
                        0,
                    )
                )
        self.update_db(data, "Update Article {} TPWD".format(article_id))

    def replace_tpwd(self, article_id: str, xml: str):
        tpwds = regex.findall(self.TPWD_REG2, xml)
        m = self.article_list[article_id]
        r_log, r_num = [], 0
        EXIST = "PASSWORD_NOT_EXIST::口令不存在"
        DECODER_EXC = "DECODER_EXCEPTION::商品已下架"
        NO_GOODS = "GOODS_NOT_FOUND::未参加淘客"
        TPWD_ERROR = "TPWD_ERROR::淘口令生成异常"
        for ii, jj in enumerate(tpwds):
            no_t = "No.{} tpwd: {}, ".format(ii + 1, jj)
            if ii not in m:
                r_log.append("{}{}".format(no_t, EXIST))
                continue
                # tpwd = 'NOTNOTEXIST'
            num_iid, title, domain, tpwd, commission_rate, commission_type, ur = m[ii]
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
            xml = xml.replace(jj, "￥{}￥".format(tpwd))
            if commission_rate == 2:
                COMMISSION = "->￥{}￥ SUCCESS, 保持原链接, {}".format(tpwd, applied)
            elif commission_rate == 1:
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
        req = proxy_req(url, 12, data=data, header=self.get_ynote_web_header(1))
        if req is None or len(req.text) < 100:
            if can_retry(url):
                return self.get_xml(article_id)
            else:
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
            tt = '||||'.join(read_file(file_path))
            tpwds = regex.findall(self.TPWD_REG, tt)
            self.tpwds[file_path] = tpwds
        else:
            tpwds = self.tpwds[file_path]
        if file_path not in self.tpwd_map:
            self.tpwd_map[file_path] = {}
        time = 0
        while (len(self.tpwd_map[file_path]) < len(tpwds)) and time < 5:
            thread_list = [ii for ii in tpwds if not ii in self.tpwd_map[file_path]]
            echo(1, file_path, "tpwds len:", len(tpwds), "need load", len(thread_list))
            thread_list = [
                self.tpwd_exec.submit(self.decoder_tpwd_once, file_path, ii, 1)
                for ii in thread_list
            ]
            list(as_completed(thread_list))

    def load_picture(self, url: str, idx: int):
        td = basic_req(url, 2)
        picture_path = 'picture/{}.jpg'.format(idx)
        with open(picture_path, 'wb') as f:
            f.write(td.content)
        pic = cv2.imread(picture_path)
        pic.resize(pic, (600, 600), interpolation=cv2.INTER_CUBIC)
        cv2.imwrite(picture_path, pic)

    def load_picture_pipeline(self, file_path: str):
        mkdir('picture')
        picture_url = [(ii['picUrl'], idx) for idx, ii in enumerate(list(self.tpwd_map[file_path].values()))]
        picture_url = [(ii, idx) for ii, idx in picture_url if not os.path.exists('picture/{}.jpg'.format(idx))]
        echo(1, 'Load {} picture Begin'.format(len(picture_url)))
        pp = [self.tpwd_exec.submit(self.load_picture, ii, jj) for ii, jj in picture_url]
        return pp

