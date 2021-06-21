# -*- coding: utf-8 -*-
# @Author: gunjianpan
# @Date:   2020-06-08 21:23:05
# @Last Modified by:   gunjianpan
# @Last Modified time: 2021-06-21 17:28:39


import json
import os
import sys
import time

import numpy as np
import codecs

sys.path.append(os.getcwd())
from util.util import basic_req, begin_time, echo, end_time, get_accept, mkdir, load_cfg


root_dir = os.path.abspath("buildmd")
assign_path = os.path.join(root_dir, "tbk.ini")
DATA_DIR = os.path.join(root_dir, "data")
mkdir(DATA_DIR)


class TBRelated(object):
    ITEMLIST_URL = "https://buyertrade.taobao.com/trade/itemlist/asyncBought.htm?action=itemlist/BoughtQueryAction&event_submit_do_query=1&_input_charset=utf8"
    TRADE_URL = "https://buyertrade.taobao.com/trade/itemlist/list_bought_items.htm"
    JSON_KEYS = set(["error", "extra", "mainOrders", "page", "query", "tabs"])

    def __init__(self):
        self.total_count = 1
        self.load_configure()

    def load_configure(self):
        cfg = load_cfg(assign_path, True)
        self.cookie = cfg.get("TB", "cookie")[1:-1]
        self.tb_id = cfg.get("TB", "tb_id")
        self.output_path = os.path.join(DATA_DIR, "{}.json".format(self.tb_id))
        self.header = {
            "Cookie": self.cookie,
            "Accept": get_accept("json"),
            "User-Agent": cfg.get("TB", "UserAgent")[1:-1],
            "Origin": self.TRADE_URL.split("/")[0],
            "Referer": self.TRADE_URL,
        }

    def get_itemlist_once(self, pn: int):
        data = {"pageNum": pn, "pageSize": 15, "prePageNo": max(1, pn - 1)}
        req = basic_req(
            self.ITEMLIST_URL,
            11,
            data=data,
            header=self.header,
            config={"timeout": 120},
        )
        if req is not None and set(req.keys()) == self.JSON_KEYS:
            self.total_count = req["page"]["totalPage"]
            return req["mainOrders"]
        return req

    def get_itemlist(self):
        self.res, self.error, pn = [], [], 1
        while pn <= self.total_count:
            version = begin_time()
            echo(2, "======Page No.{} begin getting!======".format(pn))
            mainOrders = self.get_itemlist_once(pn)
            pn += 1
            if mainOrders is None or type(mainOrders) == dict:
                return
            if not len(mainOrders):
                self.error.append(pn)
            for order in mainOrders:
                createTime = order["orderInfo"]["createTime"]
                actualFee = order["payInfo"]["actualFee"]
                if "seller" in order:
                    shopName = order["seller"].get(
                        "shopName", order["seller"].get("nick", "")
                    )
                    shopUrl = "https:" + order["seller"].get("shopUrl", "")
                else:
                    shopName, shopUrl = "", "https:"
                statusInfo = order["statusInfo"].get("text", "0")
                subOrders = [
                    {
                        "title": sub["itemInfo"]["title"],
                        "skuText": sub["itemInfo"].get("skuText", []),
                        "itemUrl": "https:" + sub["itemInfo"].get("itemUrl", ""),
                        "price": sub.get("priceInfo", 0),
                        "quantity": sub.get("quantity", 0),
                    }
                    for sub in order["subOrders"]
                    if len(sub["itemInfo"]) > 3
                ]
                self.res.append(
                    {
                        "createTime": createTime,
                        "actualFee": actualFee,
                        "shopName": shopName,
                        "shopUrl": shopUrl,
                        "statusInfo": statusInfo,
                        "subOrders": subOrders,
                    }
                )
            with codecs.open(self.output_path, "w", encoding="utf-8") as f:
                json.dump(self.res, f, indent=4, ensure_ascii=False)
            echo(
                1,
                "======Page No.{} end, spend: {}, get {} orders!======".format(
                    pn - 1, end_time(version), len(self.res)
                ),
            )
            time.sleep(30 + 10 * np.random.rand() * np.random.randint(10))


if __name__ == "__main__":
    bt = TBRelated()
    bt.get_itemlist()
