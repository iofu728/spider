# -*- coding: utf-8 -*-
# @Author: gunjianpan
# @Date:   2021-03-30 21:39:46
# @Last Modified by:   gunjianpan
# @Last Modified time: 2021-04-07 20:41:58

import os
import sys
import json
import hashlib
import time
import numpy as np
from configparser import ConfigParser
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.append(os.getcwd())
from proxy.getproxy import GetFreeProxy
from util.db import Db
from util.util import (
    begin_time,
    can_retry,
    decoder_url,
    echo,
    encoder_cookie,
    encoder_url,
    end_time,
    generate_sql,
    get_accept,
    get_time_str,
    get_use_agent,
    json_str,
    mkdir,
    time_stamp,
    time_str,
)

proxy_req = None
root_dir = os.path.abspath("buildmd")
sql_dir = os.path.join(root_dir, "sql")
assign_path = os.path.join(root_dir, "tbk.ini")
DATA_DIR = os.path.join(root_dir, "data")
TPWDLIST_PATH = os.path.join(DATA_DIR, "tpwdlist.pkl")
mkdir(DATA_DIR)


class Items(object):
    """ TB Items & Shops detail class from mtop.taobao.detail.getdetail """

    TaoShopURL = "https://shop.m.taobao.com/shop/shop_index.htm?user_id=%s&item_id=%s"
    DETAIL_URL = "https://detail.m.tmall.com/item.htm?id=%d"
    ITEM_URL = "https://item.taobao.com/item.htm?id=%d"
    MTOP_URL = "https://h5api.m.taobao.com/h5/%s/%d.0/"
    API_REFER_URL = "https://h5.m.taobao.com/"
    ITEMS_LIST = [
        "`id`",
        "item_id",
        "title",
        "shop_id",
        "category_id",
        "sku_num",
        "quest_num",
        "favcount",
        "comment_count",
        "rate_keywords",
        "ask_text",
        "props",
        "price",
        "month_sales",
        "quantity",
        "is_expired",
        "created_at",
    ]
    SHOPS_LIST = [
        "`id`",
        "shop_id",
        "shop_name",
        "user_id",
        "seller_nick",
        "item_count",
        "fans_count",
        "credit_level",
        "good_rate_perc",
        "item_desc_rate",
        "seller_serv_rate",
        "logistics_serv_rate",
        "start_at",
        "created_at",
    ]
    S_TPWDS_SQL = "SELECT item_id from article_tpwd;"
    S_ITEMS_SQL = generate_sql("select", "items", ITEMS_LIST + ["updated_at"])
    I_ITEMS_SQL = generate_sql("insert", "items", ITEMS_LIST)
    R_ITEMS_SQL = generate_sql("replace", "items", ITEMS_LIST)
    S_SHOPS_SQL = generate_sql("select", "shops", SHOPS_LIST)
    I_SHOPS_SQL = generate_sql("insert", "shops", SHOPS_LIST)
    R_SHOPS_SQL = generate_sql("replace", "shops", SHOPS_LIST)
    TABLE_LISTS = ["items.sql", "shops.sql"]
    ONE_HOURS = 3600
    ONE_DAY = 24
    M = "_m_h5_tk"

    def __init__(self, config):
        global proxy_req
        self.config = config
        proxy_req = self.config.get("proxy_req")
        self.Db = Db("tbk")
        for table in self.TABLE_LISTS:
            self.Db.create_table(os.path.join(sql_dir, table))
        self.shops_detail_map = {}
        self.items_detail_map = {}
        self.shops_detail_db_map = {}
        self.items_detail_db_map = {}
        self.load_num = 0
        self.items = set()
        self.cookies = {}
        self.load_configure()
        self.load_db()
        self.items_exec = ThreadPoolExecutor(max_workers=5)

    def load_configure(self):
        cfg = ConfigParser()
        cfg.read(assign_path, "utf-8")
        self.appkey = cfg.get("TBK", "appkey")
        self.secret = cfg.get("TBK", "secret")
        self.user_id = cfg.getint("TBK", "user_id")
        self.site_id = cfg.getint("TBK", "site_id")
        self.adzone_id = cfg.getint("TBK", "adzone_id")
        self.test_item_id = cfg.getint("TBK", "test_item_id")
        self.test_finger_id = cfg.getint("TBK", "test_finger_id")
        self.uland_url = cfg.get("TBK", "uland_url")
        self.api_key = cfg.get("TBK", "apikey")

    def get_shop_url(self, item_id: str):
        if not item_id in self.items_detail_map:
            return ""
        shop_id = self.items_detail_map[item_id]["shop_id"]
        user_id = self.shops_detail_map[shop_id]["user_id"]
        return self.TaoShopURL % (user_id, item_id)

    def get_tb_getdetail_req(self, item_id: int, cookies: dict = {}):
        """ tb getdetail api 2.6.1 @2021.04.05 ✔️Tested"""
        data = {"itemNumId": str(item_id)}
        jsv = "2.6.1"
        api = "mtop.taobao.detail.getdetail"
        j_data_t = {
            "v": 6.0,
            "ttid": "2018@taobao_h5_9.9.9",
            "AntiCreep": True,
            "callback": "mtopjsonp1",
        }
        return self.get_tb_h5_api(api, jsv, "", data, j_data_t, cookies)

    def get_tb_getdetail(self, item_id: int):
        if (
            not "uland" in self.cookies
            or time_stamp() - self.m_time > self.ONE_HOURS / 2
        ):
            self.get_m_h5_tk()
        req = self.get_tb_getdetail_req(item_id, self.cookies["uland"])
        if req is not None:
            req_text = req.text
            try:
                re_json = json.loads(req_text[req_text.find("{") : -1])
            except:
                re_json = {}
            if "data" in re_json and "item" in re_json["data"]:
                return re_json["data"]["item"]

    def get_m_h5_tk(self):
        self.m_time = time_stamp()

        def get_cookie(key, func, *param):
            req = func(*param)
            if req is not None:
                self.cookies[key] = req.cookies.get_dict()
                echo(1, "get {} cookie:".format(key), self.cookies[key])

        get_cookie("uland", self.get_uland_url_req, self.uland_url)
        if False:
            get_cookie("finger", self.get_finger_req, self.test_item_id)
            get_cookie(
                "baichuan",
                self.get_baichuan_req,
                self.test_item_id,
                self.test_finger_id,
            )

    def get_baichuan(self, item_id: int):
        if (
            not "baichuan" in self.cookies
            or not self.M in self.cookies["baichuan"]
            or time_stamp() - self.m_time > self.ONE_HOURS / 2
        ):
            self.get_m_h5_tk()
        finger_id = self.get_finger(item_id)
        if finger_id is None:
            return
        echo(4, "finger id:", finger_id)
        req = self.get_baichuan_req(item_id, finger_id, self.cookies["baichuan"])
        if req is not None:
            return req.json()["data"]

    def get_baichuan_req(self, item_id: int, finger_id: str, cookies: dict = {}):
        refer_url = self.DETAIL_URL % item_id
        data = {
            "pageCode": "mallDetail",
            "ua": get_use_agent("mobile"),
            "params": json_str(
                {
                    "url": refer_url,
                    "referrer": "",
                    "oneId": None,
                    "isTBInstalled": "null",
                    "fid": finger_id,
                }
            ),
        }
        data_str = (
            r'{"pageCode":"mallDetail","ua":"%s","params":"{\"url\":\"%s\",\"referrer\":\"\",\"oneId\":null,\"isTBInstalled\":\"null\",\"fid\":\"%s\"}"}'
            % (get_use_agent("mobile"), refer_url, finger_id)
        )
        api = "mtop.taobao.baichuan.smb.get"
        jsv = "2.4.8"

        return self.get_tb_h5_api(
            api, jsv, refer_url, data, cookies=cookies, mode=1, data_str=data_str
        )

    def get_uland_url(self, uland_url: str):
        if (
            not "uland" in self.cookies
            or time_stamp() - self.m_time > self.ONE_HOURS / 2
        ):
            self.get_m_h5_tk()
        s_req = self.get_uland_url_req(uland_url, self.cookies["uland"])
        if s_req is None:
            return ""
        req_text = s_req.text
        try:
            re_json = json.loads(req_text[req_text.find("{") : -1])
            return re_json["data"]["resultList"][0]["itemId"]
        except:
            return ""

    def get_uland_url_req(self, uland_url: str, cookies: dict = {}):
        """ tb h5 api @2020.01.18 ✔️Tested"""

        def get_v1_tt(a: dict):
            """mtop.alimama.union.xt.en.api.entry @2019.11.09"""
            variableMap = json_str(
                {"taoAppEnv": "0", "e": uland_params["e"], "scm": uland_params["scm"]}
            )
            api = "mtop.alimama.union.xt.en.api.entry"
            return variableMap, api

        def get_v2_tt(a: dict):
            """mtop.alimama.union.xt.biz.quan.api.entry @2020.01.18"""
            variableMap = json_str(
                {
                    "e": a["e"],
                    "ptl": a["ptl"],
                    "type": "nBuy",
                    "buyMoreSwitch": "0",
                    "union_lens": a["union_lens"],
                    "recoveryId": "201_11.168.242.104_{}".format(time_stamp() * 1000),
                }
            )
            api = "mtop.alimama.union.xt.biz.quan.api.entry"
            return variableMap, api

        step = self.M in cookies
        uland_params = decoder_url(uland_url, True)
        if "scm" in uland_params:
            variableMap, api = get_v1_tt(uland_params)
        elif "spm" in uland_params:
            variableMap, api = get_v2_tt(uland_params)
        else:
            echo(0, "UnKnowned ULAND mode,", uland_url)
            return

        tt = {"floorId": "13193" if step else "13052", "variableMap": variableMap}
        jsv = "2.4.0"
        j_data = {"type": "jsonp", "callback": "mtopjsonp{}".format(int(step) + 1)}
        return self.get_tb_h5_api(api, jsv, uland_url, tt, j_data, cookies)

    def get_finger(self, item_id: int):
        if (
            not "finger" in self.cookies
            or not self.M in self.cookies["finger"]
            or time_stamp() - self.m_time > self.ONE_HOURS / 2
        ):
            self.get_m_h5_tk()
        s_req = self.get_finger_req(item_id, self.cookies["finger"])
        if s_req is None:
            return
        try:
            return s_req.json()["data"]["fingerId"]
        except Exception as e:
            return

    def get_finger_req(self, item_id: int, cookies: dict = {}):
        step = self.M in cookies
        api = "mtop.taobao.hacker.finger.create"
        refer_url = self.ITEM_URL % item_id
        jsv = "2.4.11"
        j_data = {"type": "jsonp", "callback": "mtopjsonp{}".format(int(step) + 1)}
        return self.get_tb_h5_api(api, jsv, refer_url, {}, cookies=cookies)

    def get_tb_h5_api(
        self,
        api: str,
        jsv: str,
        refer_url: str,
        data: dict,
        j_data_t: dict = {},
        cookies: dict = {},
        mode: int = 0,
        data_str: str = None,
    ):
        """ tb h5 api @2019.11.6 ✔️Tested"""
        step = self.M in cookies
        if data_str is None:
            data_str = json_str(data)

        headers = {
            "Accept": get_accept("all"),
            "referer": self.API_REFER_URL,
            "Agent": get_use_agent("pc"),
        }
        if step:
            headers["Cookie"] = encoder_cookie(cookies)
        appkey = "12574478"

        token = cookies[self.M].split("_")[0] if step else ""
        t = int(time_stamp() * 1000)

        j_data = {
            "jsv": jsv,
            "appKey": appkey,
            "t": t,
            "sign": self.get_tb_h5_token(token, t, appkey, data_str),
            "api": api,
            "v": 1.0,
            "timeout": 20000,
            "AntiCreep": True,
            "AntiFlood": True,
            "type": "originaljson",
            "dataType": "jsonp",
            **j_data_t,
        }
        if mode == 0:
            j_data["data"] = data_str
        mtop_url = encoder_url(j_data, self.MTOP_URL % (api, int(j_data["v"])))
        if mode == 0:
            req = proxy_req(mtop_url, 2, header=headers)
        else:
            req = proxy_req(mtop_url, 12, data=data, header=headers)
        # echo(4, 'request once.')
        if req is None:
            if can_retry(self.MTOP_URL % (api, int(j_data["v"]))):
                return self.get_tb_h5_api(
                    api, jsv, refer_url, data, j_data_t, cookies, mode
                )
            else:
                return
        return req

    def get_tb_h5_token(self, *data: list):
        md5 = hashlib.md5()
        wait_enc = "&".join([str(ii) for ii in data])
        md5.update(wait_enc.encode())
        return md5.hexdigest()

    def get_item_detail(
        self, item_id: str, is_wait: bool = False, force_update: bool = False
    ):
        """ item detail (apiStack) @2021.04.05 ✔️Tested"""
        expired_flag = (
            self.config["time_stamp"]
            - time_stamp(
                self.items_detail_map.get(item_id, {}).get(
                    "updated_at", self.config["time_str"]
                )
            )
            >= self.ONE_HOURS * self.ONE_DAY * 10
        )
        if (
            item_id in self.items_detail_map
            and (
                (
                    self.items_detail_map[item_id]["category_id"]
                    and self.items_detail_map[item_id]["price"] != "0"
                    and not expired_flag
                )
                or self.items_detail_map[item_id]["is_expired"]
            )
            and not force_update
        ):
            return self.items_detail_map[item_id]
        if is_wait:
            time.sleep(np.random.rand() * 5 + 2)
        if (
            not "uland" in self.cookies
            or time_stamp() - self.m_time > self.ONE_HOURS / 2
        ):
            self.get_m_h5_tk()
        self.load_num += 1
        req = self.get_tb_getdetail_req(int(item_id), self.cookies["uland"])
        if req is None:
            return {}
        req_text = req.text
        try:
            req_json = json.loads(req_text[req_text.find("{") : -1])
        except:
            req_json = {}
        if "data" not in req_json:
            return {}
        is_expired = int(
            "expired" in req_json["data"].get("trade", {}).get("redirectUrl", "")
        )
        title, category_id, comment_count, favcount = [
            req_json["data"]["item"].get(ii, jj) if "item" in req_json["data"] else jj
            for ii, jj in [
                ("title", ""),
                ("categoryId", ""),
                ("commentCount", "0"),
                ("favcount", "0"),
            ]
        ]
        ask_text, quest_num = [
            req_json["data"]["vertical"]["askAll"].get(ii, jj)
            if "vertical" in req_json["data"]
            and "askAll" in req_json["data"]["vertical"]
            else jj
            for ii, jj in [
                ("askText", ""),
                ("questNum", "0"),
            ]
        ]
        props = (
            json.dumps(req_json["data"]["props"]["groupProps"], ensure_ascii=False)
            if "props" in req_json["data"] and "groupProps" in req_json["data"]["props"]
            else ""
        )
        rate_keywords = ",".join(
            [
                ":".join([ii[jj] for jj in ["word", "count", "type"]])
                for ii in (
                    req_json["data"]["rate"].get("keywords", [])
                    if "rate" in req_json["data"]
                    else []
                )
            ]
        )
        sku_num = (
            str(len(req_json["data"]["skuBase"].get("skus", [])))
            if "skuBase" in req_json["data"]
            else "0"
        )

        (
            shop_id,
            user_id,
            shop_name,
            fans_count,
            item_count,
            seller_nick,
            credit_level,
            start_at,
            good_rate_perc,
            evaluates,
        ) = [
            req_json["data"]["seller"].get(ii, jj)
            if "seller" in req_json["data"]
            else jj
            for ii, jj in [
                ("shopId", ""),
                ("userId", ""),
                ("shopName", ""),
                ("fans", "0"),
                ("allItemCount", "0"),
                ("sellerNick", ""),
                ("creditLevel", "0"),
                ("starts", self.config["time_str"]),
                ("goodRatePercentage", "0%"),
                ("evaluates", [{}] * 3),
            ]
        ]
        item_desc_rate, logistics_serv_rate, seller_serv_rate = [
            ii.get("score", "0").strip() for ii in evaluates
        ]
        apiStack = req_json["data"].get("apiStack", [{}])[0].get("value", "")
        try:
            apiStack = json.loads(apiStack)
            price = (
                apiStack["price"]["price"].get("priceText", "0")
                if "price" in apiStack and "price" in apiStack["price"]
                else "0"
            )
            month_sales = (
                apiStack["item"].get("vagueSellCount", "0")
                if "item" in apiStack
                else "0"
            )
            quantity = (
                sum(
                    [
                        int(ii["quantity"])
                        for ii in apiStack["skuCore"]["sku2info"].values()
                    ]
                )
                if "skuCore" in apiStack and "sku2info" in apiStack["skuCore"]
                else 0
            )
            quantity = str(quantity)
        except:
            price = "0"
            month_sales = "0"
            quantity = "0"

        self.items_detail_map[item_id] = {
            "item_id": item_id,
            "title": title,
            "shop_id": shop_id,
            "category_id": category_id,
            "sku_num": sku_num,
            "quest_num": quest_num,
            "favcount": favcount,
            "comment_count": comment_count,
            "rate_keywords": rate_keywords,
            "ask_text": ask_text,
            "props": props,
            "price": price,
            "month_sales": month_sales,
            "quantity": quantity,
            "is_expired": is_expired,
            "updated_at": self.items_detail_map[item_id]["updated_at"]
            if item_id in self.items_detail_map and not expired_flag
            else self.config["time_str"],
        }

        if shop_id:
            self.shops_detail_map[shop_id] = {
                "shop_id": shop_id,
                "shop_name": shop_name,
                "user_id": user_id,
                "seller_nick": seller_nick,
                "item_count": item_count,
                "fans_count": fans_count,
                "credit_level": credit_level,
                "good_rate_perc": good_rate_perc,
                "item_desc_rate": item_desc_rate,
                "seller_serv_rate": seller_serv_rate,
                "logistics_serv_rate": logistics_serv_rate,
                "start_at": start_at,
            }
        return self.items_detail_map[item_id]

    def load_db_table(self, sql: str, LIST: list, db_map: dict, key: str):
        lines = self.Db.select_db(sql)
        for line in lines:
            line = {
                ii: jj.strftime("%Y-%m-%d %H:%M:%S") if ii.endswith("_at") else jj
                for ii, jj in zip(LIST, line)
            }
            db_map[line[key]] = line
        return db_map

    def load_db(self, is_load: bool = True):
        self.items = set(
            [
                ii[0]
                for ii in self.Db.select_db(self.S_TPWDS_SQL)
                if ii[0] and ii[0].isdigit()
            ]
        )
        items = self.load_db_table(
            self.S_ITEMS_SQL % "",
            self.ITEMS_LIST + ["updated_at"],
            self.items_detail_db_map,
            "item_id",
        ).copy()
        shops = self.load_db_table(
            self.S_SHOPS_SQL % "", self.SHOPS_LIST, self.shops_detail_db_map, "shop_id"
        ).copy()
        if is_load:
            self.items_detail_map = items
            self.shops_detail_map = shops
        echo(
            1,
            f"Load {len(self.items)} TPWDS {len(self.items_detail_map)} ITEMS and {len(self.shops_detail_map)} SHOPS from db.",
        )

    def update_db(self, data: list, basic_sql: str, types: str):
        if not data:
            return
        sql = basic_sql % str(data)[1:-1]
        flag = self.Db.insert_db(sql)
        if flag:
            echo(3, "{} {} info Success".format(types, len(data)))
        else:
            echo(0, "{} failed".format(types))

    def store_one_table(
        self,
        update_sql: str,
        insert_sql: str,
        detail_map: dict,
        db_map: dict,
        LIST: list,
        types: str,
    ):
        def get_update_info(d_map: dict, LIST: list):
            return {ii: jj for ii, jj in d_map.items() if ii not in [LIST[0], LIST[-1]]}

        update_list, insert_list = [], []
        for key, value in detail_map.items():
            if key in db_map:
                value_db = db_map[key]
                if get_update_info(value_db, LIST) != get_update_info(value, LIST):
                    update_list.append(
                        (
                            value_db[LIST[0]],
                            *[value[ii] for ii in LIST[1:-1]],
                            value_db[LIST[-1]],
                            0,
                        )
                    )
            else:
                insert_list.append(tuple([value[ii] for ii in LIST[1:-1]]))
        self.update_db(update_list, update_sql, f"Update {types.upper()}")
        self.update_db(insert_list, insert_sql, f"Insert {types.upper()}")

    def store_db(self):
        self.load_db(False)
        self.store_one_table(
            self.R_ITEMS_SQL,
            self.I_ITEMS_SQL,
            self.items_detail_map,
            self.items_detail_db_map,
            self.ITEMS_LIST,
            "items",
        )
        self.store_one_table(
            self.R_SHOPS_SQL,
            self.I_SHOPS_SQL,
            self.shops_detail_map,
            self.shops_detail_db_map,
            self.SHOPS_LIST,
            "shops",
        )

    def load_click(self, num: int = 1000000):
        """ schedule click """
        for idx in range(num):
            flag = begin_time()
            self.load_num = 0
            need_items = list(self.items)
            np.random.shuffle(need_items)
            for item in need_items:
                self.get_item_detail(item, True)
            self.store_db()
            spend_time = end_time(flag, 0)
            echo(
                3,
                f"No. {idx + 1} load {self.load_num} items spend {get_time_str(spend_time, False)}",
            )
            time.sleep(max(self.ONE_HOURS * 2 - spend_time, 0))


if __name__ == "__main__":
    items = Items(
        {
            "time_str": time_str(),
            "time_stamp": time_stamp(),
            "proxy_req": GetFreeProxy().proxy_req,
        }
    )
    items.get_m_h5_tk()
    items.load_click()
