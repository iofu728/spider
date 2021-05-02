import os
import sys

sys.path.append(os.getcwd())
from bilibili.basicBilibili import BasicBilibili
from util.util import time_str, echo, basic_req, mkdir, begin_time, end_time, get_accept

SPACE_AVS_URL = "https://api.bilibili.com/x/space/arc/search?mid=%s&ps=50&tid=0&pn=%s&keyword=&order=pubdate&jsonp=jsonp"
PIC_DIR = "bilibili/data/cover"


def load_picture(url: str, title: str):
    td = basic_req(url, 2)
    picture_path = "{}/{}.jpg".format(PIC_DIR, title)
    with open(picture_path, "wb") as f:
        f.write(td.content)


def load_vlist(assign_mid: str, pn: int):
    url = SPACE_AVS_URL % (assign_mid, str(pn))
    header = {"Accept": get_accept("json")}
    req = basic_req(url, 1)
    vlist = req.get("data", {}).get("list", {}).get("vlist", [])
    return vlist


def load_cover_pipeline(assign_mid: str):
    mkdir(PIC_DIR)
    flag = begin_time()
    vlist = []
    for ii in range(3):
        vlist.extend(load_vlist(assign_mid, ii))
    for k in vlist:
        title = k["title"].split("|")[0]
        title = "{}{}".format(time_str(k["created"], "%y-%m"), title)
        load_picture(k["pic"], title)
    store_cover_info(vlist)
    spend_time = end_time(flag, 0)
    echo(2, "Load {} img spend {:.2f}s.".format(len(vlist), spend_time))


def store_cover_info(vlist: list):
    infos = ["{} {}".format(time_str(ii["created"]), ii["title"]) for ii in vlist]
    with open(f"{PIC_DIR}/infos.txt", "w") as f:
        f.write("\n".join(infos))


if __name__ == "__main__":
    assign_mid = BasicBilibili().assign_mid
    load_cover_pipeline(assign_mid)