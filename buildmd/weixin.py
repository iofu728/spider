# -*- coding: utf-8 -*-
# @Author: gunjianpan
# @Date:   2021-04-29 18:09:24
# @Last Modified by:   gunjianpan
# @Last Modified time: 2021-04-29 23:02:19

import json
import os
import regex
import sys

from configparser import ConfigParser

sys.path.append(os.getcwd())
from util.util import echo, basic_req, time_stamp, time_str

root_dir = os.path.abspath("buildmd")
sql_dir = os.path.join(root_dir, "sql")
assign_path = os.path.join(root_dir, "tbk.ini")


class OfficialAccountObject(object):
    API_BASE_URL = "https://api.weixin.qq.com/cgi-bin/"
    ACCESS_TOKEN_URL = "{}token?grant_type=%s&appid=%s&secret=%s".format(API_BASE_URL)
    GET_MATERIAL_URL = "{}material/get_material?access_token=%s".format(API_BASE_URL)
    MATERIAL_NUM_URL = "{}material/get_materialcount?access_token=%s".format(
        API_BASE_URL
    )
    ADD_NEWS_URL = "{}material/add_news?access_token=%s".format(API_BASE_URL)
    UPDATE_NEWS_URL = "{}material/update_news?access_token=%s".format(API_BASE_URL)
    MATERIAL_LIST_URL = "{}material/batchget_material?access_token=%s".format(
        API_BASE_URL
    )
    TPWD_REG2 = "(\p{Sc}\w{8,12}\p{Sc})"
    ONE_HOURS = 3600
    ONE_DAY = 24

    def __init__(self):
        self.load_configure()
        self.access_token = {"key": "", "generated_stamp": ""}
        self.material_map = {}
        self.load_num = 0

    def load_configure(self):
        cfg = ConfigParser(interpolation=None)
        cfg.read(assign_path, "utf-8")
        self.app_id = cfg.get("WX", "app_id")
        self.secret = cfg.get("WX", "secret")

    def get_access_token(self):
        key, generated_stamp = [
            self.access_token.get(ii, "") for ii in ["key", "generated_stamp"]
        ]
        if key and time_stamp() - generated_stamp > self.ONE_HOURS // 6:
            return key
        url = self.ACCESS_TOKEN_URL % ("client_credential", self.app_id, self.secret)
        req = basic_req(url, 1)
        if self.is_failure(req, "Get Access Token Error"):
            return ""
        self.access_token = {
            "key": req["access_token"],
            "generated_stamp": time_stamp(),
        }
        return self.access_token["key"]

    def get_material_list_req(
        self, offset: int = 0, count: int = 20, types: str = "news"
    ):
        url = self.MATERIAL_LIST_URL % self.get_access_token()
        data = {"type": types, "offset": offset, "count": count}
        req = basic_req(url, 11, data=json.dumps(data))
        if self.is_failure(
            req,
            "Get {} material list request failed, offset: {}, count: {}".format(
                types, offset, count
            ),
        ):
            return
        for ii in req["item"]:
            self.load_num += 1
            self.material_map[ii["media_id"]] = ii["content"]
        return req

    def get_material_list(self):
        self.load_num = 0
        for ii in range(8):
            self.get_material_list_req(20 * ii)
        echo(2, "Load {} material.".format(self.load_num))

    def get_material_detail(self, media_id: str):
        url = self.GET_MATERIAL_URL % self.get_access_token()
        data = {"media_id": media_id}
        req = basic_req(url, 11, data=json.dumps(data))
        if self.is_failure(req, "Get {} material detail failed".format(media_id)):
            return
        self.material_map[media_id] = req
        return req

    def get_material_num(self):
        url = self.MATERIAL_NUM_URL % self.get_access_token()
        req = basic_req(url, 1)
        self.count = {ii[:-6]: jj for ii, jj in req.items()}
        return req

    def update_material(self, media_id: str, content: str, title: str, index: int = 0):
        if media_id not in self.material_map:
            echo(0, "Material {} not found.".format(media_id))
            return
        url = self.UPDATE_NEWS_URL % self.get_access_token()
        m = self.material_map[media_id]["news_item"][index]
        data = {
            "media_id": media_id,
            "index": index,
            "articles": {
                "title": m.get("title", ""),
                "thumb_media_id": m.get("thumb_media_id", ""),
                "author": m.get("author", ""),
                "digest": m.get("digest", ""),
                "show_cover_pic": m.get("show_cover_pic", 1),
                "content": content,
                "content_source_url": m.get("content_source_url", ""),
            },
        }
        req = basic_req(url, 11, data=json.dumps(data))
        if self.is_failure(req, "Update News {}({}) Error".format(title, media_id)):
            return
        echo(
            1,
            "Update News {}({}) Success".format(title, media_id),
        )

    def update_tpwds(self, title: str, tpwds: list, media_id: str = "", index: int = 0):
        if not media_id:
            media_id = ""
        detail = self.get_material_detail(media_id)
        if "news_item" not in detail or len(detail["news_item"]) < index + 1:
            return
        content = detail["news_item"][index].get("content", "").replace("\\uffe5", "￥")
        origin_tpwds = regex.findall(self.TPWD_REG2, content)
        if len(origin_tpwds) != len(tpwds):
            echo(
                0,
                "TPWDS length error, origin have {} tpwds but now give {} tpwds".format(
                    len(origin_tpwds), len(tpwds)
                ),
            )
            return
        for o_tpwd, tpwd in zip(origin_tpwds, tpwds):
            if f"3{o_tpwd}/" not in content:
                content = content.replace(o_tpwd, f"3￥{o_tpwd[1:-1]}￥/")
            content = content.replace(o_tpwd[1:-1], tpwd)
        self.update_material(media_id, content, title, index)

    def add_news(self, media_id: str, content):
        url = self.ADD_NEWS_URL % self.get_access_token()
        data = {
            "articles": [
                {
                    "title": "XXXXXX",
                    "thumb_media_id": media_id,
                    "author": "XXXXX",
                    "digest": "XXXXXXX，",
                    "show_cover_pic": 1,
                    "content": content,
                    "content_source_url": "",
                    "need_open_comment": 1,
                    "only_fans_can_comment": 1,
                }
            ]
        }
        req = basic_req(url, 11, data=json.dumps(data))
        return req

    def is_failure(self, req, info: str) -> bool:
        if "errcode" in req and req["errcode"] != 0:
            echo(
                0,
                "{}, error code: {}, error message: {}".format(
                    info, req["errcode"], req["errmsg"]
                ),
            )
            return True
        return False
