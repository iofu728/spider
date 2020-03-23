# -*- coding: utf-8 -*-
# @Author: gunjianpan
# @Date:   2019-09-14 14:49:01
# @Last Modified by:   gunjianpan
# @Last Modified time: 2020-03-24 00:37:25

import json
import os
import shutil
import sys
import urllib
from configparser import ConfigParser

sys.path.append(os.getcwd())
from proxy.getproxy import GetFreeProxy
from util.util import can_retry, get_accept


one_day = 86400
root_dir = os.path.abspath("bilibili")
data_dir = os.path.join(root_dir, "data/")
assign_path = os.path.join(root_dir, "assign_up.ini")
if not os.path.exists(assign_path):
    shutil.copy(assign_path + ".tmp", assign_path)


class BasicBilibili(object):
    BILIBILI_URL = "https://www.bilibili.com"
    BASIC_AV_URL = "http://www.bilibili.com/video/av%d"
    BASIC_BV_URL = "http://www.bilibili.com/video/%s"
    ARCHIVE_STAT_URL = "http://api.bilibili.com/x/web-interface/archive/stat?aid=%d"
    VIEW_URL = "http://api.bilibili.com/x/web-interface/view?bvid=%s"
    RELATION_STAT_URL = (
        "http://api.bilibili.com/x/relation/stat?jsonp=jsonp&callback=__jp0&vmid=%d"
    )
    BASIC_RANKING_URL = "https://www.bilibili.com/ranking/all/%d/"
    SPACE_AVS_URL = (
        "https://api.bilibili.com/x/space/arc/search?mid=%s&pn=1&ps=50&jsonp=jsonp"
    )
    REPLY_V2_URL = (
        "http://api.bilibili.com/x/v2/reply?jsonp=jsonp&pn=%d&type=1&oid=%d&sort=%d"
    )
    RANKING_URL = "https://api.bilibili.com/x/web-interface/ranking?rid=%d&day=%d&type=1&arc_type=%d&jsonp=jsonp&callback=__jp1"
    PLAYLIST_URL = "https://api.bilibili.com/x/player/pagelist?aid=%d&jsonp=jsonp"
    DM_URL = "https://api.bilibili.com/x/v1/dm/list.so?oid=%d"
    GET_KEY_URL = "http://passport.bilibili.com/login?act=getkey&r=%f"
    LOGIN_URL = "https://passport.bilibili.com/login"
    LOGIN_V2_URL = "https://passport.bilibili.com/web/login/v2"
    LOGIN_OAUTH_URL = "https://passport.bilibili.com/api/v2/oauth2/login"
    CAPTCHA_URL = "https://passport.bilibili.com/web/captcha/combine?plat=11"
    GET_KEY_URL = "https://passport.bilibili.com/api/oauth2/getKey"
    GETTYPE_URL = "https://api.geetest.com/gettype.php?gt=%s&callback=geetest_%d"
    M_BILIBILI_URL = "https://m.bilibili.com/video/%s"
    NO_RANK_CONSTANT = "No rank.....No Rank......No Rank....."
    JSON_KEYS = ["code", "message", "ttl", "data"]
    T_FORMAT = "%m-%d %H:%M"

    def __init__(self):
        super(BasicBilibili, self).__init__()
        self.proxy_req = GetFreeProxy().proxy_req
        self.del_map = {}
        self.rank_map = {}
        self.load_configure()

    def load_configure(self):
        """ load assign configure """
        cfg = ConfigParser()
        cfg.read(assign_path, "utf-8")
        self.assign_author = cfg.get("basic", "author")
        mid = cfg["basic"]["mid"]
        self.assign_mid = int(mid) if len(mid) else -1
        self.assign_rank_id = cfg.getint("basic", "rank_id")
        self.assign_tid = cfg.getint("basic", "tid")
        self.basic_bv_id = cfg.get("basic", "bv_id")
        self.view_abnormal = cfg.getint("basic", "view_abnormal")
        self.assign_ids = cfg.get("assign", "bv_ids").split(",")
        rank_map = {ii: {} for ii in self.assign_ids if ii not in self.del_map}
        self.rank_map = {**rank_map, **self.rank_map}
        self.keyword = cfg.get("comment", "keyword")
        self.ignore_rpid = json.loads(cfg.get("comment", "ignore_rpid"))
        self.ignore_list = cfg.get("comment", "ignore_list")
        self.ignore_start = cfg.getfloat("comment", "ignore_start")
        self.ignore_end = cfg.getfloat("comment", "ignore_end")
        self.email_limit = cfg.getint("comment", "email_limit")
        self.AV_URL = self.BASIC_BV_URL % self.basic_bv_id
        self.history_check_list = [
            int(ii) for ii in cfg.get("basic", "history_check_list").split(",")
        ]
        self.special_info_email = cfg.get("basic", "special_info_email").split(",")
        self.assign_rec = cfg.get("basic", "assign_email").split(",")
        self.username = urllib.parse.quote_plus(cfg.get("login", "username"))
        self.password = cfg.get("login", "password")

    def get_api_req(self, url: str, bv_id: str, types: int = 0):
        if types == 0:
            req = self.proxy_req(url, 1, header=self.get_api_headers(bv_id))
        else:
            req = self.proxy_req(url, 3, header=self.get_api_headers(bv_id))
            req = self.decoder_jp(req)
        if req is None or list(req.keys()) != self.JSON_KEYS:
            if can_retry(url):
                return self.get_api_req(url, bv_id, types)
            else:
                return
        return req["data"]

    def get_api_headers(self, bv_id: str, types: int = 0) -> dict:
        if isinstance(bv_id, int):
            bv_id = "av{}".format(bv_id)
        if types == 0:
            return {"Accept": "*/*", "Referer": self.BASIC_BV_URL % bv_id}
        if types == 1:
            return {"Accept": get_accept("html"), "Host": self.BILIBILI_URL}

    def update_ini(self, bv_id: str, av_id: int):
        cfg = ConfigParser()
        cfg.read(assign_path, "utf-8")
        cfg.set("basic", "bv_id", bv_id)
        cfg.set("basic", "av_id", str(bv_id))
        bv_ids = cfg.get("assign", "bv_ids")
        cfg.set("assign", "bv_ids", "{},{}".format(bv_ids, bv_id))
        cfg.write(open(assign_path, "w"))

    def decoder_jp(self, text: str) -> dict:
        star_begin = text.find("{")
        if star_begin == -1:
            return {}
        star_json = text[star_begin:-1]
        try:
            return json.loads(star_json)
        except:
            return {}

    def update_proxy_basic(self):
        self.proxy_req = GetFreeProxy().proxy_req
