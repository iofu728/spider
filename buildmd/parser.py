# -*- coding: utf-8 -*-
# @Author: gunjianpan
# @Date:   2021-05-29 13:47:05
# @Last Modified by:   gunjianpan
# @Last Modified time: 2021-05-29 20:44:26

import regex
from bs4 import BeautifulSoup


class YNGood(object):
    KEYS = ["name", "size", "price", "shop", "tpwd", "evaluation", "pic"]

    def __init__(self, config: dict):
        for k, v in config.items():
            self.__dict__[k] = v

    def __repr__(self):
        return "\n".join([f"{k}:{self.__dict__[k]}" for k in self.KEYS])

    def __str__(self):
        return self.__repr__()


class YNParser(object):
    TPWD_REG3 = "(\p{Sc}|[\u4e00-\u9fff。！，？；“”’【】、「」《》])([a-zA-Z0-9]{8,12}?)(\p{Sc}|[\u4e00-\u9fff。！，？；“”’【】、「」《》])"

    def __init__(self):
        pass

    def parse(self, text: str) -> list:
        res = []
        xml = BeautifulSoup(text, "lxml")
        texts = xml.find_all(regex.compile("source|text"))
        blocks, block, have_tpwd = [], [], False
        for ii in texts:
            if not ii.text:
                if have_tpwd:
                    blocks.append(block)
                block, have_tpwd = [], False
                continue
            text, flag = ii.text, False
            if regex.findall(self.TPWD_REG3, text):
                have_tpwd = True
                flag = True
            block.append((text, flag))
        for block in blocks:
            name, size, price, shop, tpwd, evaluation, pic = [""] * 7
            flag_idx = [ii[1] for ii in block].index(True)
            block = [ii[0] for ii in block]
            ab = block[:flag_idx]
            if len(ab) >= 3:
                ab = ab[-2:]
            if len(ab) >= 1:
                if "店铺" in block[0]:
                    shop = block[0]
                else:
                    types = block[0].split()
                    for ii in types:
                        if ii.lower() in "xsmxl":
                            size = ii
                        elif regex.findall("^\d", ii):
                            price = ii
                        elif not name:
                            name = ii
                        elif regex.findall("\d", ii):
                            price = ii
            if len(ab) >= 2:
                shop = ab[1]
            tpwd = block[flag_idx]
            for ii in ab[1:] + block[flag_idx + 1 :]:
                if "店铺" in ii:
                    shop = ii
                elif "http" in ii:
                    pic = ii
                else:
                    evaluation += ii
            res.append(
                YNGood(
                    {
                        "name": name,
                        "size": size,
                        "price": price,
                        "shop": shop,
                        "tpwd": tpwd,
                        "evaluation": evaluation,
                        "pic": pic,
                    }
                )
            )
        return blocks, res
