# -*- coding: utf-8 -*-
# @Author: gunjianpan
# @Date:   2019-02-09 11:10:52
# @Last Modified by:   gunjianpan
# @Last Modified time: 2021-07-09 00:42:46

import json
import regex
import os
import sys

sys.path.append(os.getcwd())
from util.db import Db
from util.util import (
    basic_req,
    changeHtmlTimeout,
    echo,
    mkdir,
    read_file,
    get_accept,
    create_argparser,
    set_args,
    load_cfg,
    generate_sql,
    time_str,
)

"""
  * blog @http
  * www.zhihu.com/api/v4/creator/content_statistics
  * www.jianshu.com/u/
  * blog.csdn.net
"""
BASIC_DIR = "blog/"
DATA_DIR = f"{BASIC_DIR}data/"
CFG_PATH = f"{BASIC_DIR}blog.ini"


class TitleViews(object):
    """ script of load my blog data -> analysis """

    CSDN_URL = "https://blog.csdn.net/%s"
    JIANSHU_URL = "https://www.jianshu.com/u/%s?order_by=shared_at&page=%d"
    ZHIHU_URL = "https://www.zhihu.com/api/v4/creators/analysis/content?content_type=article&offset=%d&limit=100&order=created_at"
    BLOG_LIST = [
        "`id`",
        "title_name",
        "local_views",
        "zhihu_views",
        "csdn_views",
        "jianshu_views",
        "zhihu_id",
        "csdn_id",
        "jianshu_id",
        "created_at",
    ]
    S_BLOGS_SQL = generate_sql("select", "title_views", BLOG_LIST)
    I_BLOGS_SQL = generate_sql("insert", "title_views", BLOG_LIST)
    R_BLOGS_SQL = generate_sql("replace", "title_views", BLOG_LIST)
    I_PAGE_SQL = (
        "INSERT INTO page_views(`date`, `existed_views`, `existed_spider`) VALUES %s"
    )
    S_PAGE_SQL = "SELECT `today_views`, `existed_views` from page_views order by `id` desc limit 1"

    def __init__(self):
        self.Db = Db("blog")
        self.blogs_detail_map = {}
        self.blogs_detail_db_map = {}
        self.load_configure()
        self.load_db()

    def load_configure(self):
        cfg = load_cfg(CFG_PATH)
        self.csdn_id = cfg.get("Blog", "csdn_id")
        self.jianshu_id = cfg.get("Blog", "jianshu_id")
        self.jianshu_pn = cfg.getint("Blog", "jianshu_pn")
        self.zhihu_cookie = cfg.get("Blog", "zhihu_cookie")[1:-1]
        self.expand_path = cfg.get("Blog", "expand_path")

    def search_blogs(self, title: str):
        for k, v in self.blogs_detail_map.items():
            if v["title_name"] in title or title in v["title_name"]:
                return k
        return -1

    def get_zhihu_views(self):
        url = self.ZHIHU_URL % 0
        header = {
            "Accept": get_accept("all"),
            "Cookie": self.zhihu_cookie,
        }
        req = basic_req(url, 1, header=header)
        if not isinstance(req, dict) or list(req.keys()) != ["count", "data", "zetta"]:
            return
        data = req.get("data", [])
        for ii in data:
            zhihu_idx = int(ii.get("id", 0))
            if zhihu_idx in self.zhihu_map:
                idx = self.zhihu_map[zhihu_idx]
            else:
                idx = self.search_blogs(ii.get("title", ""))
                if idx == -1:
                    echo("0|debug", "zhihu", ii.get("title", ""))
                    continue
            view = ii.get("interaction", {}).get("reading", 0)
            if view <= self.blogs_detail_map[idx]["zhihu_views"]:
                continue
            self.blogs_detail_map[idx]["zhihu_id"] = zhihu_idx
            self.blogs_detail_map[idx]["zhihu_views"] = view
        echo(3, f"Load zhihu {len(data)} blogs.", url)

    def get_jianshu_views(self, pn: int = 1):
        url = self.JIANSHU_URL % (self.jianshu_id, pn)
        header = {"accept": get_accept("html")}
        req = basic_req(url, 0, header=header)
        if req is None:
            return
        data = [ii for ii in req.find_all("li") if ii.get("data-note-id")]
        for ii in data:
            jianshu_id = int(ii.get("data-note-id", 0))
            title = ii.find_all("a", class_="title")[0].text.replace("`", "")
            if jianshu_id in self.jianshu_map:
                idx = self.jianshu_map[jianshu_id]
            else:
                idx = self.search_blogs(title)
                if idx == -1:
                    echo("0|debug", "jianshu", title)
                    continue

            view = int(ii.find_all("a")[-2].text)
            if view <= self.blogs_detail_map[idx]["jianshu_views"]:
                continue
            self.blogs_detail_map[idx]["jianshu_id"] = jianshu_id
            self.blogs_detail_map[idx]["jianshu_views"] = view
        echo(3, f"Load jianshu {len(data)} blogs.", url)

    def get_csdn_views(self):
        url = self.CSDN_URL % self.csdn_id
        header = {"accept": get_accept("html")}
        req = basic_req(url, 3, header=header)
        if not req:
            return
        left = req.index("window.__INITIAL_STATE__")
        right = req.index("};</script><script type=")
        data = json.loads(req[left + 26 : right + 1])
        data = (
            data.get("pageData", {})
            .get("data", {})
            .get("baseInfo", {})
            .get("latelyList", [])
        )
        for ii in data:
            href = ii.get("url", "")
            csdn_ids = regex.findall("details/(\d*)", href)
            if not csdn_ids:
                echo("0|debug", "csdn", href)
                continue
            csdn_id = int(csdn_ids[0])
            title = ii.get("title", "")
            if csdn_id in self.csdn_map:
                idx = self.csdn_map[csdn_id]
            else:
                idx = self.search_blogs(title)
                if idx == -1:
                    echo("0|debug", "csdn", title)
                    continue
            view = ii.get("viewCount", 0)
            if view <= self.blogs_detail_map[idx]["csdn_views"]:
                continue
            self.blogs_detail_map[idx]["csdn_id"] = csdn_id
            self.blogs_detail_map[idx]["csdn_views"] = view
        echo(3, f"Load csdn {len(data)} blogs.", url)

    def filter_emoji(self, desstr, restr=""):
        """ filter emoji """
        desstr = str(desstr)
        try:
            co = regex.compile("[\U00010000-\U0010ffff]")
        except regex.error:
            co = regex.compile("[\uD800-\uDBFF][\uDC00-\uDFFF]")
        return co.sub(restr, desstr)

    def load_db(self, is_load: bool = True):
        blogs = self.Db.load_db_table(
            self.S_BLOGS_SQL % "",
            self.BLOG_LIST,
            self.blogs_detail_db_map,
            "`id`",
        ).copy()
        if is_load:
            self.blogs_detail_map = blogs
            self.zhihu_map = {ii["zhihu_id"]: ii["`id`"] for ii in blogs.values()}
            self.csdn_map = {ii["csdn_id"]: ii["`id`"] for ii in blogs.values()}
            self.jianshu_map = {ii["jianshu_id"]: ii["`id`"] for ii in blogs.values()}

    def store_db(self):
        self.load_db(False)
        self.Db.store_one_table(
            self.R_BLOGS_SQL,
            self.I_BLOGS_SQL,
            self.blogs_detail_map,
            self.blogs_detail_db_map,
            self.BLOG_LIST,
            "blog",
        )

    def update_view(self):
        changeHtmlTimeout(10)
        self.get_zhihu_views()
        for pn in range(1, self.jianshu_pn + 1):
            self.get_jianshu_views(pn)
        self.get_csdn_views()
        self.store_db()

    def new_day(self):
        day_data = self.Db.select_db(self.S_PAGE_SQL)
        spider = [int(ii) for ii in read_file(self.expand_path)]
        today_date = time_str(time_format="%Y-%m-%d")
        new_day_list = [(today_date, day_data[0][0] + day_data[0][1], spider[1])]
        results = self.Db.insert_db(self.I_PAGE_SQL % str(new_day_list)[1:-1])
        echo(
            1, f"New Day update {'Success' if results else 'Error'}!", len(new_day_list)
        )


if __name__ == "__main__":
    mkdir(DATA_DIR)
    parser = create_argparser("Blog Script")
    parser.add_argument("--do_new", type=bool, default=False)
    args = set_args(parser)
    bt = TitleViews()
    if args.do_new:
        bt.new_day()
    bt.update_view()
