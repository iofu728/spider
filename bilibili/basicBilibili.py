# -*- coding: utf-8 -*-
# @Author: gunjianpan
# @Date:   2019-09-14 14:49:01
# @Last Modified by:   gunjianpan
# @Last Modified time: 2021-12-10 21:56:13

import json
import os
import sys
import urllib

import numpy as np


sys.path.append(os.getcwd())
from proxy.getproxy import GetFreeProxy
from util.util import (
    basic_req,
    can_retry,
    decoder_url,
    echo,
    encoder_url,
    get_accept,
    get_use_agent,
    load_cfg,
    md5,
    time_stamp,
    time_str,
)


one_day = 86400
root_dir = os.path.abspath("bilibili")
data_dir = os.path.join(root_dir, "data/")
assign_path = os.path.join(root_dir, "assign_up.ini")


class BasicBilibili(object):
    BILIBILI_URL = "https://www.bilibili.com"
    APP_BASIC_URL = "http://app.bilibili.com/x/"
    API_BASIC_URL = "http://api.bilibili.com/x/"
    API_WEB_URL = f"{API_BASIC_URL}web-interface/"
    BASIC_BV_URL = "http://www.bilibili.com/video/%s"
    STAT_URL = f"{API_WEB_URL}archive/stat?bvid=%s"
    VIEW_URL = f"{API_WEB_URL}view?bvid=%s"
    RELATION_STAT_URL = f"{API_BASIC_URL}relation/stat?vmid=%s"
    SPACE_AVS_URL = f"{API_BASIC_URL}space/arc/search?mid=%s&pn=%d&ps=50&jsonp=jsonp"
    REPLY_V2_URL = f"{API_BASIC_URL}v2/reply?pn=%d&type=1&oid=%s&sort=%d&ps=49"
    RANKING_URL = f"{API_WEB_URL}ranking/v2?rid=%d"
    RANK_REGION_URL = f"{API_WEB_URL}ranking/region?rid=%d&day=%d"
    DM_URL = f"{API_BASIC_URL}v2/dm/h5/seg.so?type=1&oid=%s&pid=%s&segment_index=1"
    CHANNEL_URL = f"{APP_BASIC_URL}v2/channel/rank?id=%s"
    GET_KEY_URL = "http://passport.bilibili.com/login?act=getkey&r=%f"
    LOGIN_URL = "https://passport.bilibili.com/login"
    LOGIN_V2_URL = "https://passport.bilibili.com/web/login/v2"
    LOGIN_OAUTH_URL = "https://passport.bilibili.com/api/v2/oauth2/login"
    CAPTCHA_URL = "https://passport.bilibili.com/web/captcha/combine?plat=11"
    GET_KEY_URL = "https://passport.bilibili.com/api/oauth2/getKey"
    GETTYPE_URL = "https://api.geetest.com/gettype.php?gt=%s&callback=geetest_%d"
    M_B_URL = "https://m.bilibili.com"
    M_BILIBILI_URL = f"{M_B_URL}/video/%s"
    CLICK_URL = f"{API_BASIC_URL}click-interface/click/h5"
    PLAYER_URL = f"{API_BASIC_URL}player.so?id=cid:%s&aid=%s&bvid=%s&buvid=%s"
    TABLE = "fZodR9XQDSUm21yCkr6zBqiveYah8bt4xsWpHnJE7jL5VG3guMTKNPAwcF"
    S = [11, 10, 3, 8, 4, 6]
    XOR = 177451812
    ADD = 8728348608
    NO_RANK_CONSTANT = "No rank.....No Rank......No Rank....."
    JSON_KEYS = ["code", "message", "ttl", "data"]
    T_FORMAT = "%m-%d %H:%M"
    IMG_MARKDOWN = "![%s](%s)"

    def __init__(self):
        super(BasicBilibili, self).__init__()
        self.TR = {self.TABLE[ii]: ii for ii in range(58)}
        self.proxy_req = GetFreeProxy().proxy_req
        self.del_map = {}
        self.rank_map = {}
        self.load_configure()

    def load_configure(self):
        """ load assign configure """
        cfg = load_cfg(assign_path)
        self.assign_author = cfg.get("basic", "author")
        self.assign_mid = cfg["basic"].getint("mid", -1)
        self.assign_rid = cfg.getint("basic", "rid")
        self.assign_tid = cfg.getint("basic", "tid")
        self.assign_bvid = cfg.get("basic", "bv_id")
        self.view_abnormal = cfg.getint("basic", "view_abnormal")
        self.special_info_email = cfg.get("basic", "special_info_email").split(",")
        self.assign_rec = cfg.get("basic", "assign_email").split(",")
        self.rank_len = cfg.getint("basic", "rank_len")
        self.history_ids = [
            int(ii) for ii in cfg.get("basic", "history_ids").split(",")
        ]
        channel_str = [
            ii.split(",") for ii in cfg.get("basic", "channel_ids").split("|") if ii
        ]
        self.channel_ids = {ii: jj for ii, jj in channel_str}
        self.assign_ids = cfg.get("assign", "bv_ids").split(",")
        rank_map = {ii: {} for ii in self.assign_ids if ii not in self.del_map}
        self.rank_map = {**rank_map, **self.rank_map}
        self.keyword = cfg.get("comment", "keyword")
        self.ignore_rpid = set(cfg.get("comment", "ignore_rpid").split(","))
        self.ignore_list = cfg.get("comment", "ignore_list")
        self.ignore_start = cfg.getfloat("comment", "ignore_start")
        self.ignore_end = cfg.getfloat("comment", "ignore_end")
        self.email_limit = cfg.getint("comment", "email_limit")
        self.username = urllib.parse.quote_plus(cfg.get("login", "username"))
        self.password = cfg.get("login", "password")
        appkey_list = cfg.get("app", "appkey_list").split("|")
        self.appkey_map = {
            ii[0]: ii[1:] for ii in [ii.split(",") for ii in appkey_list]
        }
        self.platform = cfg.get("app", "platform")
        self.appkey, self.appsec = self.appkey_map.get(self.platform, [""] * 2)

    def get_web_api(
        self,
        url: str,
        types: int = 1,
        data: dict = None,
        is_proxy: bool = True,
        is_jsonp: bool = False,
    ):
        r_req = self.proxy_req if is_proxy else basic_req
        header = self.get_api_headers(self.av2bv(np.random.randint(10 ** 8)))
        if types > 9:
            req = r_req(url, types, data=data, header=header)
        else:
            req = r_req(url, types, header=header)
        if types % 10 == 3 and is_jsonp:
            req = self.decoder_jp(req)
        if not req or (
            types == 1 and isinstance(req, dict) and (list(req.keys()) != self.JSON_KEYS or req["code"] != 0)
        ):
            if is_proxy and can_retry(url):
                return self.get_web_api(url, types, data, is_proxy, is_jsonp)
            else:
                return
        return req["data"] if types == 1 else req

    def get_api_headers(self, bv_id: str, types: int = 0) -> dict:
        if isinstance(bv_id, int):
            bv_id = "av{}".format(bv_id)
        if types == 0:
            return {"Accept": "*/*", "Referer": self.BASIC_BV_URL % bv_id}
        if types == 1:
            return {"Accept": get_accept("html"), "Host": self.BILIBILI_URL}

    def update_ini(self, bv_id: str):
        cfg = load_cfg(assign_path)
        cfg.set("basic", "bv_id", bv_id)
        bv_ids = cfg.get("assign", "bv_ids")
        cfg.set("assign", "bv_ids", f"{bv_ids},{bv_id}")
        cfg.write(open(assign_path, "w"))

    def decoder_jp(self, text: str) -> dict:
        try:
            return json.loads(text[text.find("{") : -1])
        except:
            return {}

    def update_proxy_basic(self):
        self.proxy_req = GetFreeProxy().proxy_req

    def bv2av(self, bv_id: str) -> str:
        r = 0
        for ii in range(6):
            r += self.TR[bv_id[self.S[ii]]] * 58 ** ii
        return (r - self.ADD) ^ self.XOR

    def av2bv(self, aid: str) -> str:
        aid = (aid ^ self.XOR) + self.ADD
        r = list("BV1  4 1 7  ")
        for ii in range(6):
            r[self.S[ii]] = self.TABLE[aid // 58 ** ii % 58]
        return "".join(r)

    def pack_sign(self, params, appsec: str = ""):
        if isinstance(params, str):
            params = decoder_url(params)
        params = {ii: jj for ii, jj in params.items() if ii != "sign"}
        params_key = sorted(params.keys())
        wait_enc = "&".join(["{}={}".format(ii, params[ii]) for ii in params_key])
        appsec = appsec if appsec else self.appsec
        if not appsec:
            echo(0, "AppSec Miss.")
            return ""
        sign = md5(wait_enc + appsec)
        params["sign"] = sign
        params_key = sorted(params.keys())
        return "&".join(["{}={}".format(ii, params[ii]) for ii in params_key])

    def get_app_api(
        self,
        url: str,
        types: int = 1,
        data: dict = {},
        is_proxy: bool = True,
        is_jsonp: bool = False,
    ):
        origin_url = url
        data["ts"] = str(int(time_stamp()))
        if types > 9:
            data = decoder_url(self.pack_sign(data))
        else:
            url = encoder_url(self.pack_sign(data), url)
        r_req = self.proxy_req if is_proxy else basic_req
        if types > 9:
            req = r_req(url, types, data=data)
        else:
            req = r_req(url, types)
        if types % 10 == 3 and is_jsonp:
            req = self.decoder_jp(req)
        if not req or (
            types == 1 and (list(req.keys()) != self.JSON_KEYS or req["code"] != 0)
        ):
            if is_proxy and can_retry(origin_url):

                return self.get_app_api(origin_url, types, data, is_proxy, is_jsonp)
            else:
                return
        return req["data"] if types == 1 else req

    def get_view_info(self, bv_id: str):
        view_url = self.VIEW_URL % bv_id
        return self.get_web_api(view_url)

    def get_video_stat_info(self, bv_id: str):
        stat_url = self.STAT_URL % bv_id
        return self.get_web_api(stat_url)

    def get_people_stat_info(self, mid: str):
        stat_url = self.RELATION_STAT_URL % mid
        return self.get_web_api(stat_url)

    def get_rank_info(self, day: int = 3, rid: int = None, types: str = "v2"):
        if rid is None:
            rid = self.assign_rid
        if types == "v2":
            rank_url = self.RANKING_URL % (rid)
        elif types == "region":
            rank_url = self.RANK_REGION_URL % (rid, day)
        elif types == "channel":
            rank_url = self.CHANNEL_URL % (rid)
        return self.get_web_api(rank_url)

    def get_comment_info(self, aid: str, pn: int, sort: int):
        aid = str(aid)
        if aid.startswith("BV"):
            aid = self.bv2av(aid)
        comment_url = self.REPLY_V2_URL % (pn, aid, sort)
        return self.get_web_api(comment_url)

    def get_dm_info(self, bv_id: str, cid: str):
        import bilibili.grpc.community.service.dm.v1_pb2 as Danmaku
        from google.protobuf.json_format import MessageToDict

        dm_url = self.DM_URL % (str(cid), self.bv2av(bv_id))
        dm = self.get_web_api(dm_url, 2)
        if not dm:
            return
        danmaku_seg = Danmaku.DmSegMobileReply()
        danmaku_seg.ParseFromString(dm.content)

        return MessageToDict(danmaku_seg)

    def get_cid(self, bv_id: str):
        view = self.get_view_info(bv_id)
        if view:
            return [ii.get("cid", "") for ii in view.get("pages", [{}])]

    def get_m_html(self, bv_id: str, is_proxy: bool = True) -> str:
        url = self.M_BILIBILI_URL % bv_id
        headers = {
            "Accept": get_accept("html"),
            "Host": url.split("/")[2],
            "User-Agent": get_use_agent("mobile"),
        }
        r_req = self.proxy_req if is_proxy else basic_req
        m_html = r_req(url, 3, header=headers)
        if len(m_html) < 1000:
            if is_proxy and can_retry(url):
                return self.get_m_html(bv_id, is_proxy)
            else:
                return ""
        return m_html

    def get_title_part(self, view: dict):
        return view.get("title", "").split("|", 1)[0]

    def get_str_text(
        self,
        data: dict,
        keys: list,
        keys2: list = None,
        split_flag: str = "\t",
        compare_data: dict = None,
    ):
        def get_value(key, d: dict = data):
            return (
                time_str(d[key]) if "time" in key or "pubdate" in key else d.get(key, 0)
            )

        if keys2:
            return split_flag.join(
                [
                    "{}: {}{}".format(
                        jj,
                        get_value(ii),
                        "({:.2f}%)".format(
                            int(get_value(ii, compare_data)) * 100 / int(get_value(ii))
                            if get_value(ii) not in ["0", "", 0]
                            else 0
                        )
                        if compare_data
                        else "",
                    )
                    for ii, jj in zip(keys, keys2)
                    if data.get(ii, 0)
                ]
            )
        return split_flag.join(
            [
                "{}{}".format(
                    str(get_value(ii)),
                    "({:.2f}%)".format(
                        int(get_value(ii, compare_data)) * 100 / int(get_value(ii))
                        if get_value(ii) not in ["0", "", 0]
                        else 0
                    )
                    if compare_data
                    else "",
                )
                for ii in keys
                if data.get(ii, 0)
            ]
        )
