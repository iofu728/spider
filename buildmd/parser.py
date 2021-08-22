# -*- coding: utf-8 -*-
# @Author: gunjianpan
# @Date:   2021-05-29 13:47:05
# @Last Modified by:   gunjianpan
# @Last Modified time: 2021-08-22 19:34:18

import os
import sys
import time

import numpy as np
import regex
from bs4 import BeautifulSoup
from tqdm import tqdm


sys.path.append(os.getcwd())
from util.util import basic_req, dhash, echo, encoder_cookie, encoder_url, hash_distance, md5, mkdir, time_stamp


BASIC_IMG_DIR = "buildmd/data/img/"


class YNGoods(object):
    KEYS = [
        "name",
        "size",
        "price",
        "shop",
        "tpwd",
        "evaluation",
        "pic",
        "picHash",
        "ydId",
    ]

    def __init__(self, config: dict):
        for k, v in config.items():
            self.__dict__[k] = v

    def __repr__(self):
        return "\n".join(
            ["{}:{}".format(k, self.__dict__.get(k, "")) for k in self.KEYS]
        )

    def __str__(self):
        return self.__repr__()


class YNParser(object):
    TPWD_REG = "\p{Sc}(\w{8,12}?)\p{Sc}"
    PIC_BASIC_URL = "https://note.youdao.com/"
    SESS_URL = f"{PIC_BASIC_URL}login/acc/pe/getsess?product=YNOTE&_=%d"
    RLOG_URL = "https://rlogs.youdao.com/rlog.php"
    RESULT_NAME = ["pic", "shop", "name"]

    def __init__(self):
        mkdir(BASIC_IMG_DIR)
        self.cookies = {}
        self.blocks_map = {}
        self.goods_map = {}
        self.empty_map = {}
        self.pics_map = {}
        self.get_cookie()

    def get_cookie(self):
        t = int(time_stamp() * 1000)
        _ncoo = 2147483647 * np.random.rand()
        url = self.SESS_URL % t
        req = basic_req(url, 2, config={"allow_redirects": False})
        if req:
            self.cookies = req.cookies.get_dict()
        params = {
            "_npid": "ynote-web-rlogs",
            "_ncat": "pageview",
            "_ncoo": _ncoo,
            "_nssn": "NULL",
            "_nver": "1.2.0",
            "_ntms": t,
            "_nref": "",
            "_nurl": "https://note.youdao.com/ynoteshare1/index.html",
            "_nres": "1680x1050",
            "_nlmf": "",
            "_njve": 0,
            "_nchr": "utf-8",
            "_nfrg": "",
        }
        url = encoder_url(params, self.RLOG_URL)
        req = basic_req(
            url,
            2,
            config={"allow_redirects": False},
            header={
                "Cookie": encoder_cookie({"OUTFOX_SEARCH_USER_ID_NCOO": _ncoo}),
            },
        )
        if req is None:
            return
        self.cookies = {
            **self.cookies,
            **req.cookies.get_dict(),
            "OUTFOX_SEARCH_USER_ID_NCOO": _ncoo,
        }
        echo(2, "Get Cookies", self.cookies)

    def md5_pic(self, url: str, yd_id: str):
        if not url.startswith(self.PIC_BASIC_URL):
            return ""
        idx = regex.findall("res\/(.*?)\/", url)[0]
        url = url.replace(f"res/{idx}", f"public/resource/{yd_id}/xmlnote") + f"/{idx}"
        print(url)
        header = {"Cookie": encoder_cookie(self.cookies)}
        req = basic_req(url, 2, config={"allow_redirects": False}, header=header)
        if req.status_code == 302:
            url = req.headers.get("Location", "")
            if not url:
                return ""
            req = basic_req(url, 2)
        elif req.status_code != 200:
            return
        img_path = f"{BASIC_IMG_DIR}{md5(req.text)}.jpg"
        with open(img_path, "wb") as f:
            f.write(req.content)
        time.sleep(2)
        return dhash(img_path)

    def resize_block(self, block: list):
        text, blocks = block[0], block[1:]
        res = []
        last, idx, t_time = 0, 0, 0
        while idx < len(blocks):
            if blocks[idx][1]:
                if t_time >= 1:
                    x = idx
                    while x > last and blocks[x][0] != "" and not blocks[x][1]:
                        x -= 1
                    if x == last or blocks[x - 1][0]:
                        x = idx
                    res.append([ii for ii in blocks[last:x] if ii[0]])
                    last = x
                t_time += 1
            idx += 1
        res.append([ii for ii in blocks[last:] if ii[0]])
        return [text, res]

    def decoder_blocks(self, text: str):
        xml = BeautifulSoup(text, "lxml")
        paragraphs = xml.find_all(regex.compile("para|source"))
        blocks, block, have_tpwd = [], [], False
        no_tpwds = []
        for p in paragraphs:
            values = [
                ii.text
                for ii in p.find_all("value")
                if ii.text.startswith("#") or ii.text.startswith("rgb")
            ]
            if p.name == "source":
                text = p.text
            else:
                texts = p.find_all(regex.compile("source|text"))
                text = "".join([ii.text for ii in texts])
            if (
                set(values) == set(["#ffffff", "#aca0f6"])
                or set(values) == set(["#ffffff", "rgb(172, 160, 246)"])
                or set(values) == set(["#407600", "#e9f5f4"])
            ):
                if block and have_tpwd:
                    blocks.append(self.resize_block(block))
                elif block:
                    no_tpwds.append(block)
                block, have_tpwd = [text], False
                continue
            if not block or not text:
                if block and len(block) > 1 and block[-1][0]:
                    block.append((text, False))
                continue
            flag = False
            if regex.findall(self.TPWD_REG, text):
                have_tpwd = True
                flag = True
            block.append((text, flag))
        if block and have_tpwd:
            blocks.append(self.resize_block(block))
        elif block:
            no_tpwds.append(block)
        return blocks, no_tpwds

    def decoder_basic(self, text: str):
        name, size, price = "", "", ""
        types = text.replace("//", "").replace("￥", "").split()
        for ii in types:
            if ii.lower() in "xsmxl":
                size = ii
            elif regex.findall("^\d", ii):
                price = ii
            elif not name:
                name = ii
            elif regex.findall("\d", ii):
                price = ii
        return name, size, price

    def decoder_shop(self, shop: str) -> str:
        if ":" in shop:
            shop = shop.split(":", 1)[1]
        if "：" in shop:
            shop = shop.split("：", 1)[1]
        shop = shop.replace("店铺", "").replace("店", "").strip()
        return shop

    def decode_no_tpwd(self, block: list, yd_id: str):
        text, block = block[0], block[1:]
        name, size, price = self.decoder_basic(text)
        shop, evaluation = [""] * 2
        pic = []
        for idx, (t, flag) in enumerate(block):
            if "http" in t:
                pic.append(t)
            elif "下架" in t:
                evaluation += t
            elif idx == 0:
                shop = self.decoder_shop(t)
            else:
                evaluation += t
        return YNGoods(
            {
                "name": name,
                "size": size,
                "price": price,
                "shop": shop,
                "evaluation": evaluation,
                "pic": pic,
                "picHash": ["" for ii in pic],
                # "picHash": [self.md5_pic(ii, yd_id) for ii in pic],
                "ydId": yd_id,
            }
        )

    def parse(self, text: str, yd_id: str) -> list:
        res = []
        blocks, no_tpwds = self.decoder_blocks(text)
        no_tpwds = [self.decode_no_tpwd(block, yd_id) for block in no_tpwds]
        for text, block in tqdm(blocks):
            name, size, price = self.decoder_basic(text)
            for b in block:
                shop, tpwd, evaluation = [""] * 3
                pic = []
                for idx, (t, flag) in enumerate(b):
                    if flag:
                        tpwd = t
                    elif "http" in t:
                        pic.append(t)
                    elif idx == 0 or (idx == 1 and tpwd and "店" in t):
                        shop = self.decoder_shop(t)
                    else:
                        evaluation += t
                if not pic:
                    pic = [""]
                res.append(
                    YNGoods(
                        {
                            "name": name,
                            "size": size,
                            "price": price,
                            "shop": shop,
                            "tpwd": regex.findall(self.TPWD_REG, tpwd)[0],
                            "evaluation": evaluation,
                            "pic": pic,
                            "picHash": ["" for ii in pic],
                            # "picHash": [self.md5_pic(ii, yd_id) for ii in pic],
                            "ydId": yd_id,
                        }
                    )
                )
        self.goods_map[yd_id] = res
        self.blocks_map[yd_id] = blocks
        self.empty_map[yd_id] = no_tpwds
        echo(2, f"Load {len(res)} goods.", f"And {len(no_tpwds)} no tpwd blocks.")
        return blocks, res, no_tpwds

    def pic_cluster(self):
        goods_num = 0
        for goods_list in self.goods_map.values():
            for goods in goods_list:
                for picHash in goods.picHash:
                    if picHash == "":
                        continue
                    goods_num += 1
                    flag = False
                    for k in self.pics_map.keys():
                        if hash_distance(k, picHash) > 0.9:
                            self.pics_map[k].append(goods)
                            flag = True
                            break
                    if not flag:
                        self.pics_map[picHash] = [goods]
        echo(1, f"Load {goods_num} Goods and {len(self.pics_map)} picture's clusters.")

    def search_pic(self, picHash: str):
        if picHash in self.pics_map:
            return self.pics_map[picHash]
        for k, v in self.pics_map.items():
            if hash_distance(k, picHash) > 0.9:
                return v
        return {}

    def search(self, goods: YNGoods):
        if isinstance(goods.picHash, list):
            pic_results = []
            for p in goods.picHash:
                pic_results.extend(self.search_pic(p))
        else:
            pic_results = self.search_pic(p)
        shop_results, name_results = [], []
        for goods_list in self.goods_map.values():
            for g in goods_list:
                if goods.name and goods.name in g.name:
                    name_results.append(g)
                if goods.shop and goods.shop in g.shop:
                    shop_results.append(g)
        return pic_results, shop_results, name_results

    def load_picHash(self, data: dict):
        num = 0
        for yd_id, data_list in tqdm(data.items()):
            for idx, d in enumerate(data_list):
                for k, (ii, jj) in enumerate(zip(d.picHash, d.pic)):
                    if ii or not jj:
                        continue
                    print(jj, yd_id)
                    hash_value = self.md5_pic(jj, yd_id)
                    data[yd_id][idx].picHash[k] = hash_value
                    num += 1
        echo(1, f"Hash {num} pictures.")
        return data
