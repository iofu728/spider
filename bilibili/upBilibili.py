# -*- coding: utf-8 -*-
# @Author: gunjianpan
# @Date:   2019-04-07 20:25:45
# @Last Modified by:   gunjianpan
# @Last Modified time: 2021-05-10 01:59:50


import codecs
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List

import numpy as np
import regex

sys.path.append(os.getcwd())
from util.util import (
    begin_time,
    end_time,
    echo,
    get_time_str,
    mkdir,
    read_file,
    send_email,
    time_stamp,
    time_str,
    map_get,
    write,
)
from bilibili.analysis import clean_csv
from bilibili.basicBilibili import BasicBilibili


proxy_req = 0
one_day = 86400
root_dir = os.path.abspath("bilibili")
data_dir = os.path.join(root_dir, "data/")
history_data_dir = os.path.join(data_dir, "history_data/")
history_dir = os.path.join(data_dir, "history/")
comment_dir = os.path.join(data_dir, "comment/")
ranks_dir = os.path.join(data_dir, "ranks/")
dm_dir = os.path.join(data_dir, "dm/")

"""
  * bilibili @h5,grpc,app
"""


class Up(BasicBilibili):
    """ Detail Implementation Layer """

    VIEW_KEYS = [
        "bvid",
        "tid",
        "title",
        "pubdate",
        "desc",
        "state",
        "duration",
        "dynamic",
        "cid",
        "owner/mid",
        "owner/name",
    ]
    STAT_KEYS = ["view", "like", "coin", "favorite", "reply", "share", "danmaku"]
    STAT_ZH = ["播放量", "点赞", "硬币", "收藏", "评论", "分享", "弹幕", "评分", "排名"]
    RANK_KEYS = (
        ["score"]
        + [f"stat/{ii}" for ii in STAT_KEYS]
        + [
            "bvid",
            "title",
            "pubdate",
            "owner/mid",
            "owner/name",
        ]
    )
    BVLIST_KEYS = [
        "title",
        "bvid",
        "created",
        "length",
        "play",
        "comment",
        "video_review",
        "description",
        "pic",
    ]
    BVLIST_ZH = ["标题", "地址", "发布时间", "视频时长", "播放量", "评论", "弹幕", "描述", "图片"]
    COMMENT_KEYS = [
        "idx",
        "rpid",
        "ctime",
        "like",
        "member/uname",
        "member/sex",
        "member/level_info/current_level",
        "member/sign",
        "member/avatar",
        "content/message",
    ]
    COMMENT_ZH = ["序号", "链接", "评论时间", "点赞", "昵称", "性别", "级别", "签名", "头像", "评论内容"]
    LOAD_KEYS = ["time"] + STAT_KEYS + ["pts", "type", "day"]
    PV_KEYS = ["history_rank", "realtime_rank", "channel_rank", "clean_csv", "comment"]
    STAT_LOCAL_KEYS = STAT_KEYS + ["score", "idx"]
    RANK_LOCAL_KEYS = ["time", "idx"] + RANK_KEYS
    SORT = ["按热度", "按热度+时间", "按时间"]

    def __init__(self):
        super(Up, self).__init__()
        self.update_proxy(do_refresh=False)
        self.view_detail_map = {}
        self.bv_ids = {}
        self.h_map = {}
        self.rank_map = {}
        self.rank_local_map = {}
        self.pv = {key: set() for key in self.PV_KEYS}
        self.mid_stat = {}
        self.pool = ThreadPoolExecutor(max_workers=10)
        self.load_history_data()

    def load_bv_list(self):
        url = self.SPACE_AVS_URL % (self.assign_mid, 1)
        bv_list = self.get_web_api(url, is_proxy=False)
        if not bv_list:
            return
        bv_ids = {ii["bvid"]: ii for ii in bv_list.get("list", {}).get("vlist", [])}
        if self.assign_bvid in bv_ids:
            self.send_video_public(bv_ids)
            self.bv_ids = bv_ids

    def send_video_public(self, bv_ids: dict):
        if not self.bv_ids or set(self.bv_ids.keys()) == set(bv_ids):
            return
        bv_id = [ii for ii in bv_ids if ii not in self.bv_ids][0]
        space_view = bv_ids[bv_id]
        shell_str = f"nohup python3 bilibili/bsocket.py {bv_id} %d >> log.txt 2>&1 &"
        echo("0|error", "Shell str:", shell_str)
        os.system(shell_str % 1)
        os.system(shell_str % 2)
        title_text = "发布({}){}#{}".format(
            time_str(space_view["created"], time_format=self.T_FORMAT),
            bv_id,
            space_view["title"],
        )
        context_text = (
            self.get_str_text(space_view, self.BVLIST_KEYS, self.BVLIST_ZH, "\n")
            .replace(str(space_view["created"]), time_str(space_view["created"]))
            .replace(space_view["bvid"], self.BASIC_BV_URL % space_view["bvid"])
            .replace(space_view["pic"], self.IMG_MARKDOWN % ("img", space_view["pic"]))
        )
        send_email(context_text, title_text, self.special_info_email)
        self.update_ini(bv_id)

    def load_history_file(self, bv_id: str, bv_info: dict):
        data_path = "{}{}_new.csv".format(history_data_dir, bv_id)
        history_list = read_file(data_path)[:3660]
        if not history_list:
            return
        created, title = bv_info["created"], bv_info["title"]
        history_list = [ii.split(",") for ii in history_list]
        time_map = {
            round((time_stamp(ii[0]) - created) / 120) * 2: ii
            for ii in history_list
            if ii[0]
        }
        last_data = {ii: 0 for ii in self.STAT_LOCAL_KEYS}
        for ii in self.h_map.keys():
            if ii in time_map:
                for value, key in zip(time_map[ii][1:], self.STAT_LOCAL_KEYS):
                    last_data[key] = value
            self.h_map[ii][bv_id] = last_data.copy()

    def load_history_data(self):
        self.load_bv_list()
        self.h_map = {ii * 2: {} for ii in range(0, 3660)}
        for bv_id, bv_info in self.bv_ids.items():
            self.load_history_file(bv_id, bv_info)

    def delay_load_history_data(self):
        time.sleep(60)
        self.load_history_data()

    def load_view_detail(self, bv_id: str) -> dict:
        view = self.get_view_info(bv_id)
        if not view:
            return
        info = {ii: map_get(view, ii) for ii in self.VIEW_KEYS}
        self.view_detail_map[bv_id] = info
        return self.load_stat_detail(bv_id, view["stat"])

    def load_stat_detail(self, bv_id: str, stat=None) -> dict:
        if stat is None:
            stat = self.get_video_stat_info(bv_id)
        view = self.view_detail_map.get(bv_id, {})
        if not stat:
            return view
        info = {ii: map_get(stat, ii) for ii in self.STAT_KEYS}
        self.view_detail_map[bv_id] = {**view, **info}
        return self.view_detail_map[bv_id]

    def load_ranking_detail(self):
        ranks = self.get_rank_info()
        if not ranks:
            return {}
        now_time = time_str()
        ranks = {
            jj["bvid"]: dict(
                {ii: map_get(jj, ii) for ii in self.RANK_KEYS},
                **{"time": time_stamp(), "idx": idx + 1},
            )
            for idx, jj in enumerate(ranks["list"])
            if jj["tid"] == self.assign_tid
        }
        self.rank_map = ranks
        return ranks

    def load_bv_stat_detail(self, bv_id: str):
        pub_data = self.view_detail_map.get(bv_id, {}).get("pubdate", time_stamp())
        if time_stamp() - pub_data > one_day * 8:
            return
        rank_info = self.rank_map.get(bv_id, {})
        if bv_id not in self.view_detail_map:
            view = self.load_view_detail(bv_id)
        else:
            view = self.load_stat_detail(bv_id)
        if not view:
            return
        data = {**view, "time": time_stamp(), **rank_info}
        need = ["time"] + self.STAT_KEYS + ["score", "idx"]
        output = [str(data.get(ii, "")) for ii in need]
        write(f"{history_dir}{bv_id}.csv", ",".join(output) + "\n", "a")
        self.maintenance_bv_schedule(bv_id, view)

    def maintenance_bv_schedule(self, bv_id: str, view: dict):
        if bv_id not in self.bv_ids:
            return
        pub_date = view.get("pubdate", time_stamp())
        now_time = time_stamp()
        if (now_time - pub_date > one_day * 4) and bv_id in self.pv["clean_csv"]:
            clean_csv(bv_id)
            self.pv["clean_csv"].add(bv_id)
        time_gap = (now_time - pub_date) / 60
        echo("0|debug", bv_id, time_gap < (4.5 * one_day / 60), time_str(pub_date))
        if time_gap >= (4.5 * one_day / 60):
            return
        echo("3|info", "Time Gap:", int(time_gap / 10))
        if (
            int(time_gap / 10) in self.history_ids
            and f"{bv_id}-{int(time_gap/10)}" not in self.pv["history_rank"]
        ):
            self.send_history_rank(bv_id, view, int(time_gap / 10) * 10)

    def get_ZH_view_detail(self, view: dict):
        return self.get_str_text(view, self.STAT_LOCAL_KEYS, self.STAT_ZH, ", ")

    def send_history_rank(self, bv_id: str, view: dict, time_gap: int):
        echo(
            "0|info",
            f"Send {bv_id} time {time_gap} history rank",
        )
        h_map = {ii: jj for ii, jj in self.h_map[time_gap].items() if jj["view"]}
        if len(h_map) < 5:
            self.load_history_data()
        view_list = [int(ii["view"]) for ii in h_map.values()]
        view_len = len(view_list)
        view_list.append(view["view"])
        view_sort_idx = np.argsort(-np.array(view_list))
        bv_ids = list(h_map.keys())
        now_sorted = list(view_sort_idx).index(view_len) + 1

        time_tt = get_time_str(time_gap)
        title = self.get_title_part(view)
        title_rank_text = f"No.{now_sorted}/{view_len}, {self.get_ZH_view_detail(view)}"
        title_text = f"排名(发布{time_tt}){title}{title_rank_text}"
        context_text = f"{bv_id}发布{time_tt}, {title_rank_text}\n\n"
        for idx, rank in enumerate(view_sort_idx[: self.rank_len + 1]):
            if rank == view_len:
                continue
            bv = bv_ids[rank]
            if bv not in self.view_detail_map:
                view = self.load_bv_stat_detail(bv)
                if not view:
                    continue
            view = self.view_detail_map[bv]
            context_text += "{}, {}, 本年度No.{}, {}, 累计播放: {}, 发布时间: {}\n".format(
                self.get_title_part(view),
                bv,
                idx + 1,
                self.get_ZH_view_detail(h_map[bv]),
                view["view"],
                time_str(view["pubdate"]),
            )
        send_email(context_text, title_text, mode="single")
        self.pv["history_rank"].add(f"{bv_id}-{int(time_gap / 10)}")

    def get_star_num(self, mid: int, load_disk: bool = False):
        star_json = self.get_people_stat_info(mid)
        if not star_json:
            return
        follower = star_json["follower"]
        self.mid_stat[mid] = follower
        if not load_disk or not self.check_star(mid, follower):
            return
        write(f"{data_dir}star.csv", "{},{}\n".format(time_str(), follower), "a")

    def send_realtime_rank(self, bv_id: str, rank: dict):
        idx, score = rank["idx"], rank["score"]
        rank_id = "{}-{}".format(bv_id, idx if idx < 20 else (idx // 10) * 10)
        if bv_id not in self.bv_ids or rank_id in self.pv["realtime_rank"]:
            return
        view = self.view_detail_map[bv_id]
        is_hot = self.is_hot(bv_id)
        is_hot = "[热门]" if is_hot else ""
        title = self.get_title_part(view)
        pub_data = view.get("pubdate", time_stamp())
        gap_str = get_time_str((time_stamp() - pub_data) / 60)
        title_text = "热榜{}({}){}, 排名: {}, 评分: {}".format(
            is_hot, title, gap_str, idx, score
        )
        send_email(title_text, title_text)
        self.pv["realtime_rank"].add(rank_id)

    def check_star(self, mid: int, star: int) -> bool:
        if not mid in self.mid_stat:
            return True
        last_star = self.mid_stat[mid]
        return abs(last_star - star) < self.view_abnormal

    def send_channel_rank(self, channel_id: str):
        ranks = self.get_rank_info(rid=channel_id, types="channel")
        if not ranks:
            return
        items = [map_get(ii, "author/mid") for ii in ranks.get("items", [])]
        if self.assign_mid not in items:
            return
        idx = items.index(self.assign_mid)
        rank = ranks.get("items", [])[idx]
        bv_id = rank.get("id", "")

        rank_id = "{}-{}-{}".format(channel_id, bv_id, idx)
        if bv_id not in self.view_detail_map or rank_id in self.pv["channel_rank"]:
            return
        view = self.view_detail_map[bv_id]
        is_hot = self.is_hot(bv_id)
        is_hot = "[热门]" if is_hot else ""
        title = self.get_title_part(rank)
        pub_data = view.get("pubdate", time_stamp())
        gap_str = get_time_str((time_stamp() - pub_data) / 60)
        title_text = "热榜{}({}){}, {}频道排名: {}".format(
            is_hot, title, gap_str, self.channel_ids[channel_id], idx + 1
        )
        send_email(title_text, title_text)
        self.pv["channel_rank"].add(rank_id)

    def load_rank2local(self, bv_id: str, rank: dict):
        local_rank = self.rank_local_map.get(bv_id, {})
        if rank["score"] == local_rank.get("score", 0):
            return
        rank_text = self.get_str_text(rank, self.RANK_LOCAL_KEYS)
        write(f"{ranks_dir}{bv_id}.csv", rank_text + "\n", "a")

    def send_data_miss(self, ranks: dict):
        if self.assign_bvid in ranks or self.assign_bvid not in self.rank_local_map:
            return
        view = self.view_detail_map.get(self.assign_bvid, {})
        title = self.get_title_part(view)
        title_text = "下榜({}){},{}".format(
            time_str(time_format=self.T_FORMAT), title, self.NO_RANK_CONSTANT
        )
        context_text = self.get_ZH_view_detail(view)
        send_email(context_text, title_text, self.special_info_email)
        echo("4|error", title_text)

    def load_ranking(self):
        ranks = self.load_ranking_detail()
        others_text = []
        for bv_id, rank in ranks.items():
            self.load_rank2local(bv_id, rank)
            self.send_realtime_rank(bv_id, rank)
            others_text.append(self.get_str_text(rank, self.RANK_LOCAL_KEYS))
        self.send_data_miss(ranks)
        self.rank_local_map = ranks
        write(f"{data_dir}rank.csv", "\n".join(others_text))
        echo("4|debug", "Rank_map_len:", len(ranks))

    def load_click(self, num: int = 1000000):
        for idx in range(num):
            flag = begin_time()
            if idx % 5 == 0:
                self.load_ranking()
            for bv_id in self.bv_ids:
                self.load_bv_stat_detail(bv_id)
                if np.random.rand() < 0.2:
                    self.load_comment_detail(bv_id)
            if np.random.rand() < 0.02:
                self.get_star_num(self.assign_mid, True)
            for channel_id in self.channel_ids:
                if np.random.rand() < 0.2:
                    self.send_channel_rank(channel_id)
            self.load_configure()
            self.load_bv_list()
            if idx % 20 == 9:
                self.load_history_data()
            if idx % 100 == 99:
                self.update_proxy()
            spend_time = end_time(flag, 0)
            echo(
                3,
                f"No. {idx + 1} load click spend {get_time_str(spend_time, False)}",
            )
            time.sleep(max(120 - spend_time, 0))

    def update_proxy(self, do_refresh: bool = True):
        global proxy_req
        if do_refresh:
            self.update_proxy_basic()
        proxy_req = self.proxy_req

    def load_comment_detail(self, bv_id: str):
        pub_data = self.view_detail_map.get(bv_id, {}).get("pubdate", time_stamp())
        if not 600 < time_stamp() - pub_data < one_day * 8:
            return
        for pn in range(1, 4):
            for sort in range(3):
                self.load_comment_info(bv_id, pn, sort)

    def load_comment_info(self, bv_id: str, pn: int, sort: int):
        comments = self.get_comment_info(bv_id, pn, sort)
        if not comments:
            return
        echo("2|debug", "Comment check, bv_id:", bv_id, "pn:", pn, "sort:", sort)
        replies = comments["replies"]
        if not replies:
            replies = []
        if pn == 1 and comments["hots"]:
            replies = comments["hots"] + replies
        for ii, reply in enumerate(replies):
            idx = f"{self.SORT[sort]}第{pn}页第{ii + 1}条评论"
            r = {ii: map_get(reply, ii) for ii in self.COMMENT_KEYS}
            r["idx"] = idx
            self.send_comment_warning(bv_id, r)
            if not reply["replies"]:
                continue
            for jj, subreply in enumerate(reply["replies"]):
                idx += f"的第{jj + 1}条子评论"
                r = {ii: map_get(subreply, ii) for ii in self.COMMENT_KEYS}
                r["idx"] = idx
                self.send_comment_warning(bv_id, r)

    def send_comment_warning(self, bv_id: str, reply: dict):
        if reply["rpid"] in self.pv["comment"]:
            return
        if not len(regex.findall(self.keyword, reply["content/message"])):
            return
        url = self.BASIC_BV_URL % bv_id
        if bv_id not in self.view_detail_map:
            view = self.load_bv_stat_detail(bv_id)
            if not view:
                return
        view = self.view_detail_map[bv_id]
        title = self.get_title_part(view)
        context_text = (
            self.get_str_text(reply, self.COMMENT_KEYS, self.COMMENT_ZH, ",\n")
            .replace(str(reply["rpid"]), f"{url}/#" + str(reply["rpid"]))
            .replace(
                reply["member/avatar"],
                self.IMG_MARKDOWN % ("img", reply["member/avatar"]),
            )
        )
        context_text = f"{title},\n{context_text}"
        title_text = "评论({}){}|{}".format(
            time_str(reply["ctime"], time_format=self.T_FORMAT), title, reply["idx"]
        )
        echo("4|warning", title_text, context_text)
        send_email(context_text, title_text, assign_rec=self.assign_rec)
        self.pv["comment"].add(reply["rpid"])

    def is_hot(self, bv_id: str) -> bool:
        m_html = self.get_m_html(bv_id, False)
        return "<span>热门</span>" in m_html


if __name__ == "__main__":
    mkdir(data_dir)
    mkdir(comment_dir)
    mkdir(history_dir)
    mkdir(history_data_dir)
    mkdir(ranks_dir)
    bb = Up()
    bb.load_click()
