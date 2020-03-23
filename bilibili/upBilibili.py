# -*- coding: utf-8 -*-
# @Author: gunjianpan
# @Date:   2019-04-07 20:25:45
# @Last Modified by:   gunjianpan
# @Last Modified time: 2020-03-24 01:27:35


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
    can_retry,
    echo,
    get_min_s,
    get_time_str,
    mkdir,
    read_file,
    send_email,
    time_stamp,
    time_str,
    get_accept,
    get_use_agent,
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
dm_dir = os.path.join(data_dir, "dm/")

"""
  * bilibili @http
  * www.bilibili.com/video/av{av_id}
  * www.bilibili.com/ranking/all/155/{0/1}/{day}
  * space.bilibili.com/ajax/member/getSubmitVideos?mid={mid}&page=1&pagesize=50
  * api.bilibili.com/x/v2/reply?jsonp=jsonp&pn=%d&type=1&oid=%d&sort=0
    api.bilibili.com/x/report/click/now?jsonp=jsonp
    api.bilibili.com/x/report/click/web/h5
    api.bilibili.com/x/report/web/heartbeat
    api.bilibili.com/x/web-interface/archive/stat?aid={av_id}
    api.bilibili.com/x/relation/stat?jsonp=jsonp&callback=__jp11&vmid={mid}
"""


class Up(BasicBilibili):
    """ some business layer application about bilibili"""

    def __init__(self):
        super(Up, self).__init__()
        self.update_proxy(1)
        self.rank = {"T": {}, "L": {}}
        self.rank_type = {}
        self.public = {"T": {}, "L": []}
        self.star = {"T": {}, "L": {}}
        self.data_v2 = {}
        self.have_assign = {1: [], 3: [], "T": []}
        self.last_check = {}
        self.last_view = {}
        self.comment = {}
        self.email_send_time = {}
        self.begin_timestamp = int(time_stamp())
        self.bv_list = []
        self.bv_ids = {}
        self.check_done = {}
        self.pool = ThreadPoolExecutor(max_workers=10)
        self.monitor_pool = ThreadPoolExecutor(max_workers=50)
        self.load_history_data()

    def load_bv_list(self):
        url = self.SPACE_AVS_URL % self.assign_mid
        bv_list = self.get_api_req(url, self.basic_bv_id)
        if bv_list is None:
            return
        bv_ids = {ii["bvid"]: ii for ii in bv_list["list"]["vlist"]}
        if self.basic_bv_id not in bv_ids:
            return
        self.bv_ids = bv_ids

    def load_history_file(self, bv_id: str, bv_info: dict):
        data_path = "{}{}_new.csv".format(history_data_dir, bv_id)
        history_list = read_file(data_path)[:3660]
        if not len(history_list):
            return
        created, title = bv_info["created"], bv_info["title"]
        history_list = [ii.split(",") for ii in history_list]
        time_map = {
            round((time_stamp(ii[0]) - created) / 120) * 2: ii
            for ii in history_list
            if ii[0] != ""
        }
        last_data = [0] * 8
        for ii in self.history_map.keys():
            if ii in time_map:
                self.history_map[ii][bv_id] = time_map[ii]
                last_data = time_map[ii] + last_data[len(time_map[ii]) :]
            else:
                self.history_map[ii][bv_id] = last_data

    def load_history_data(self):
        self.load_bv_list()
        bv_public = {ii: [jj["created"], jj["mid"]] for ii, jj in self.bv_ids.items()}
        self.public["T"] = {**bv_public, **self.public["T"]}
        self.history_map = {ii * 2: {} for ii in range(0, 3660)}
        for bv_id, bv_info in self.bv_ids.items():
            self.load_history_file(bv_id, bv_info)

    def delay_load_history_data(self):
        time.sleep(60)
        self.load_history_data()

    def check_rank(self, bv_id: str):
        rank_info = self.rank_map[bv_id] if bv_id in self.rank_map else {}
        stat = self.get_view_detail(bv_id)
        if stat is None or "stat" not in stat:
            return
        stat = stat["stat"]
        data = {**stat, "time": time_str(), **rank_info}
        need = [
            "time",
            "view",
            "like",
            "coin",
            "favorite",
            "reply",
            "share",
            "danmaku",
            "id",
            "pts",
            "type",
            "day",
        ]
        output = [str(data[ii]) for ii in need if ii in data]
        output = output + [str(v) for k, v in data.items() if k not in need]
        with codecs.open(
            "{}{}.csv".format(history_dir, bv_id), "a", encoding="utf-8"
        ) as f:
            f.write(",".join(output) + "\n")

        if (
            bv_id in self.last_check
            and int(time_stamp()) - self.last_check[bv_id] > one_day / 2
        ):
            self.del_map[bv_id] = 1
            del self.rank_map[bv_id]
            if bv_id == self.basic_bv_id:
                clean_csv(bv_id)
        elif (
            bv_id not in self.last_check
            and int(time_stamp()) > one_day + self.begin_timestamp
        ):
            self.del_map[bv_id] = 1
            del self.rank_map[bv_id]
            if bv_id == self.basic_bv_id:
                clean_csv(bv_id)
        self.last_view[bv_id] = data["view"]
        now_time = time_stamp()
        if not bv_id in self.public["T"] or bv_id not in self.assign_ids:
            return
        time_gap = (now_time - self.public["T"][bv_id][0]) / 60
        echo("0|debug", bv_id, time_gap < (4.5 * one_day / 60), self.public["T"][bv_id])
        if time_gap >= (4.5 * one_day / 60):
            return
        if not bv_id in self.check_done:
            self.check_done[bv_id] = []
        echo("3|info", "Time Gap:", int(time_gap / 10))
        if (
            int(time_gap / 10) in self.history_check_list
            and int(time_gap / 10) not in self.check_done[bv_id]
        ):
            self.history_rank(time_gap, data, bv_id)

    def history_rank(self, time_gap: int, now_info: dict, bv_id: int):
        echo("0|info", "send history rank")
        time_gap = int(time_gap / 10) * 10
        history_map = {ii: jj for ii, jj in self.history_map[time_gap].items() if jj[1]}
        if len(history_map) < 5:
            self.load_history_data()
        other_views = [int(ii[1]) for ii in history_map.values()]
        other_views_len = len(other_views)
        other_views.append(now_info["view"])
        ov_sort_idx = np.argsort(-np.array(other_views))
        av_ids = list(history_map.keys())
        now_sorted = [jj for jj, ii in enumerate(ov_sort_idx) if ii == other_views_len][
            0
        ] + 1
        other_result = [
            (jj + 1, av_ids[ii])
            for jj, ii in enumerate(ov_sort_idx[:4])
            if ii != other_views_len
        ]
        time_tt = get_time_str(time_gap)
        rank_info = self.bv_ids[bv_id]
        title = rank_info["title"].split("|", 1)[0]
        title_email = "排名(发布{}){}本年度排名No.{}/{}, 播放量: {}, 点赞: {}, 硬币: {}, 收藏: {}, 弹幕: {}".format(
            time_tt,
            title,
            now_sorted,
            len(other_views),
            now_info["view"],
            now_info["like"],
            now_info["coin"],
            now_info["favorite"],
            now_info["danmaku"],
        )
        email_title = "bv{}发布{}, 本年度排名No.{}/{}, 播放量: {}, 点赞: {}, 硬币: {}, 收藏: {}, 弹幕: {}".format(
            bv_id,
            time_tt,
            now_sorted,
            len(other_views),
            now_info["view"],
            now_info["like"],
            now_info["coin"],
            now_info["favorite"],
            now_info["danmaku"],
        )
        email_title += self.get_history_rank(now_info)
        context = "{}\n\n".format(email_title)
        for no, bv in other_result[:3]:
            data_info = history_map[bv]
            context += "{}, bv{}, 本年度No.{}, 播放量: {}, 点赞: {}, 硬币: {}, 收藏: {}, 弹幕: {}, 累计播放: {}{}, 发布时间: {}\n".format(
                self.bv_ids[bv]["title"].split("|", 1)[0],
                bv,
                no,
                data_info[1],
                data_info[2],
                data_info[3],
                data_info[4],
                data_info[7],
                self.bv_ids[av]["play"],
                self.get_history_rank(data_info),
                time_str(self.bv_ids[bv]["created"]),
            )
        send_email(context, title_email)
        self.check_done[bv_id].append(round(time_gap / 10))

    def get_history_rank(self, data_info: dict) -> str:
        if "id" not in data_info:
            return ""
        return ", Rank: {}, Score: {}".format(data_info["id"], data_info["pts"])

    def check_rank_info(self, bv_id: int, rank_info: dict) -> bool:
        """ Check Rank Info """
        if not len(rank_info) or rank_info["author"] != self.assign_author:
            return False
        b_id = bv_id + str(rank_info["day"]) + str(rank_info["type"])
        if b_id not in self.rank["T"]:
            return True
        idx = rank_info["id"]
        prefix_rank = idx // 10
        if (
            prefix_rank not in self.rank["T"][b_id]
            or prefix_rank == 0
            or (prefix_rank == 1 and not idx % 3)
        ):
            if self.rank["L"][b_id] != idx:
                return True
        return False

    def check_rank_v2(self, bv_id: str):
        rank_info = self.rank_map[bv_id] if bv_id in self.rank_map else {}
        stat = self.get_view_detail(bv_id)
        if stat is None or "stat" not in stat:
            return
        stat = stat["stat"]
        data = {**stat, "time": time_str(), **rank_info}
        self.data_v2[bv_id] = data

    def check_type(self, bv_id: str):
        """ check type """
        if bv_id in self.rank_type:
            return self.rank_type[bv_id]
        if bv_id in self.rank_map and not len(self.rank_map[bv_id]):
            self.rank_type[bv_id] = True
            return True
        return 2

    def check_type_req(self, bv_id: str):
        view_data = self.get_view_detail(bv_id)
        if view_data is None:
            return
        self.rank_type[bv_id] = view_data["tid"] == self.assign_tid

    def add_av(self, bv_id: int, idx: int, score: int) -> bool:
        """ decide add av """
        if bv_id not in self.rank_map:
            return idx < 95 or score > 5000
        if not len(self.rank_map[bv_id]):
            return True
        if self.rank_map[bv_id]["id"] - idx > 5:
            return True
        return score - self.rank_map[bv_id]["pts"] > 200

    def public_monitor(self, bv_id: str):
        """ a monitor """
        self.public["L"].append(bv_id)
        created, mid = self.public["T"][bv_id]
        self.get_star_num(mid)
        self.check_rank_v2(bv_id)
        time.sleep(5)
        follower = self.star["T"][mid] if mid in self.star["T"] else 0
        data1 = self.data_v2[bv_id] if bv_id in self.data_v2 else {}
        sleep_time = created + one_day - int(time_stamp())
        if sleep_time < 0:
            return
        echo("4|debug", "Monitor Begin %s" % (bv_id))
        time.sleep(sleep_time)
        self.get_star_num(mid)
        self.check_rank_v2(bv_id)
        time.sleep(5)
        follower_2 = self.star["T"][mid] if mid in self.star["T"] else 0
        data2 = self.data_v2[bv_id] if bv_id in self.data_v2 else []

        data = [
            time_str(created),
            bv_id,
            follower,
            follower_2,
            *list(data.values()),
            *list(data2.values()),
        ]
        with codecs.open(data_dir + "public.csv", "a", encoding="utf-8") as f:
            f.write(",".join([str(ii) for ii in data]) + "\n")

    def public_data(self, bv_id: str):
        """ get public basic data """
        view_data = self.get_view_detail(bv_id)
        if view_data is None:
            return
        data_time = view_data["pubdate"]
        mid = view_data["owner"]["mid"]
        self.get_star_num(mid)
        self.public["T"][av_id] = [data_time, mid]

    def get_star_num(self, mid: int, load_disk: bool = False):
        """ get star num"""
        url = self.RELATION_STAT_URL % mid
        star_json = self.get_api_req(url, self.basic_bv_id, 1)
        if star_json is None:
            return
        self.star["T"][mid] = star_json["follower"]
        if not load_disk or not self.check_star(mid, star_json["follower"]):
            return
        self.star["L"][mid] = star_json["follower"]
        with open("{}star.csv".format(data_dir), "a") as f:
            f.write("{},{}\n".format(time_str(), star_json["follower"]))

    def check_rank_rose(self, bv_id: str, rank_info: dict):
        """ check rank rose """
        if not self.check_rank_info(bv_id, rank_info):
            return
        idx, pts = rank_info["id"], rank_info["pts"]
        b_id = bv_id + str(rank_info["day"]) + str(rank_info["type"])
        if b_id not in self.rank["T"]:
            self.rank["T"][b_id] = [idx // 10]
        else:
            self.rank["T"][b_id].append(idx // 10)
        self.rank["L"][b_id] = idx
        is_hot = self.is_hot(bv_id)
        is_hot = "[热门]" if is_hot else ""
        title = (
            self.bv_ids[bv_id]["title"].split("|", 1)[0] if bv_id in self.bv_ids else ""
        )
        rank_str = "热榜{}(%s){}|{}Day List, Rank: {}, Score: {}".format(
            is_hot, title, rank_info["day"], idx, rank_info["pts"]
        )
        if bv_id in self.bv_ids:
            created = self.bv_ids[bv_id]["created"]
            ts = get_time_str((time.time() - created) / 60)
            ts_str = time_str(created) + "-" + time_str()
        else:
            ts, ts_str = "", ""
        rank_context = rank_str % ts_str
        rank_str = rank_str % ts
        send_email(rank_context, rank_str)

    def check_star(self, mid: int, star: int) -> bool:
        """ check star """
        if not mid in self.star["L"]:
            return True
        last_star = self.star["L"][mid]
        if last_star > star:
            return False
        if last_star + self.view_abnormal < star:
            return False
        return True

    def load_rank_index(self, index: int, day_index: int):
        """ load rank """
        self.have_assign[day_index] = []
        url = self.RANKING_URL % (self.assign_rank_id, day_index, index)
        text = self.get_api_req(url, self.basic_bv_id, 1)
        if text is None:
            return

        rank_list = text["list"]
        need_params = [
            "pts",
            "bvid",
            "aid",
            "author",
            "mid",
            "play",
            "video_review",
            "coins",
            "duration",
            "title",
        ]
        now_bv_ids, checks, rank_map = [], [], {}

        ## loop for Rank List
        #  1. Filter different `tid` bv
        #  2. Send email for [热榜].
        #  3. Update rank map
        for idx, rank in enumerate(rank_list):
            bv_id = rank["bvid"]
            rank_info = {
                "id": idx + 1,
                **{ii: rank[ii] for ii in rank},
                "type": index,
                "day": day_index,
            }
            now_bv_ids.append(bv_id)
            if not self.check_type(bv_id):
                continue
            if day_index < 5:
                self.check_rank_rose(bv_id, rank_info)
            if self.add_av(bv_id, idx, rank_info["pts"]):
                rank_map[bv_id] = rank_info

        ## check ids
        for bv_id in self.assign_ids:
            if not bv_id in self.public["T"]:
                checks.append(bv_id)
            if not bv_id in self.last_view and not bv_id in self.rank_map:
                self.rank_map[bv_id] = {}
        have_assign = [ii for ii in self.assign_ids if ii in now_bv_ids]

        ## check tid type
        threads = [
            self.pool.submit(self.check_type_req, bv_id) for bv_id in rank_map.keys()
        ]
        list(as_completed(threads))

        ## update rank_map
        for bv_id, rank_info in rank_map.items():
            if not self.check_type(bv_id):
                continue
            if not bv_id in self.public["T"]:
                checks.append(bv_id)
            self.last_check[bv_id] = int(time_stamp())
            self.rank_map[bv_id] = rank_info

        ## update public
        threads = [self.pool.submit(self.public_data, bv_id) for bv_id in checks]
        list(as_completed(threads))

        ## monitor
        need_monitor = [
            bv_id
            for bv_id, (created, mid) in self.public["T"].items()
            if not bv_id in self.public["L"] and created + one_day > int(time_stamp())
        ]
        threads = [
            self.monitor_pool.submit(self.public_monitor, bv_id)
            for bv_id in need_monitor
        ]

        self.have_assign[day_index] = have_assign

    def load_rank(self):
        """ load rank """
        self.load_rank_index(1, 3)
        self.load_rank_index(1, 1)
        assign_1, assign_2 = self.have_assign[1], self.have_assign[3]
        have_assign = assign_1 + assign_2
        echo("4|debug", assign_1, assign_2, have_assign)
        not_ranks = [ii for ii in self.have_assign["T"] if not ii in have_assign]
        self.have_assign = have_assign

        echo(
            "4|debug",
            "Rank_map_len:",
            len(self.rank_map.keys()),
            "Empty:",
            len([1 for ii in self.rank_map.values() if not len(ii)]),
        )
        youshan = [
            ",".join([str(kk) for kk in [ii, *list(jj.values())]])
            for ii, jj in self.rank_map.items()
        ]
        with codecs.open(data_dir + "youshang", "w", encoding="utf-8") as f:
            f.write("\n".join(youshan))

        if not len(not_ranks):
            return
        for bv_id in not_ranks:
            title = (
                self.bv_ids[bv_id]["title"].split("|", 1)[0]
                if bv_id in self.bv_ids
                else ""
            )
            no_rank_warning = "下榜({}){},{}".format(
                time_str(time_format=self.T_FORMAT), title, self.NO_RANK_CONSTANT
            )
            send_email(no_rank_warning, no_rank_warning, self.special_info_email)
            time.sleep(pow(np.pi, 2))
            send_email(no_rank_warning, no_rank_warning, self.special_info_email)
            echo("4|error", no_rank_warning)

    def schedule_main(self, num=1000000):
        """ schedule click """
        self.rank_map = {ii: {} for ii in self.assign_ids}

        for index in range(num):
            threads = []
            if not index % 5:
                threads.append(threading.Thread(target=self.load_rank, args=()))
            if index % 15 == 1:
                threads.append(
                    threading.Thread(
                        target=self.get_star_num, args=(self.assign_mid, True)
                    )
                )
                threads.append(threading.Thread(target=self.update_proxy, args=()))
            threads.append(threading.Thread(target=self.load_configure, args=()))
            if index % 5 == 4:
                threads.append(threading.Thread(target=self.get_check, args=()))
            for bv_id in self.rank_map.keys():
                if bv_id in self.bv_ids or bv_id in self.assign_ids:
                    threads.append(
                        threading.Thread(target=self.check_rank, args=(bv_id,))
                    )
                elif index % 20 == 3:
                    threads.append(
                        threading.Thread(target=self.check_rank, args=(bv_id,))
                    )
            for work in threads:
                work.start()
            time.sleep(120)

    def update_proxy(self, mode: int = 0):
        global proxy_req
        if not mode:
            self.update_proxy_basic()
        proxy_req = self.proxy_req

    def get_check(self):
        """ check comment """
        self.delay_load_history_data()
        bv_list = [
            [ii["bvid"], ii["aid"], ii["comment"]]
            for ii in self.bv_ids.values()
            if not regex.findall(self.ignore_list, str(ii["aid"]))
        ]
        bv_map = {ii["bvid"]: ii for ii in self.bv_ids.values()}
        if self.bv_list and len(self.bv_list) and len(self.bv_list) != len(bv_list):
            new_bv_list = [
                (ii, jj)
                for ii, jj, _ in bv_list
                if not ii in self.bv_list and not ii in self.del_map
            ]
            self.rank_map = {**self.rank_map, **{ii: {} for ii, _ in new_bv_list}}
            echo("1|error", "New Bv av ids:", new_bv_list)
            for bv_id, av_id in new_bv_list:
                rank_info = bv_map[bv_id]
                shell_str = "nohup python3 bilibili/bsocket.py {} %d >> log.txt 2>&1 &".format(
                    av_id
                )
                echo("0|error", "Shell str:", shell_str)
                os.system(shell_str % 1)
                os.system(shell_str % 2)
                email_str = "发布({}){}#{} {}".format(
                    time_str(rank_info["created"], time_format=self.T_FORMAT),
                    rank_info["title"],
                    bv_id,
                    av_id,
                )
                email_str2 = "{} {} is release at {}.\nPlease check the online & common program.".format(
                    rank_info["title"],
                    time_str(rank_info["created"]),
                    self.BASIC_BV_URL % bv_id,
                )
                send_email(email_str2, email_str, self.special_info_email)
                self.update_ini(bv_id, av_id)
                self.public["T"][bv_id] = [rank_info["created"], rank_info["mid"]]
                self.last_check[bv_id] = int(time_stamp())

        self.bv_list = [ii for (ii, _, _) in bv_list]
        now_hour = int(time_str(time_format="%H"))
        now_min = int(time_str(time_format="%M"))
        now_time = now_hour + now_min / 60
        if now_time > self.ignore_start and now_time < self.ignore_end:
            return
        if self.assign_mid == -1:
            return

        # threads = [self.pool.submit(self.check_type_req, bv_id) for bv_id in rank_map.keys()]
        # list(as_completed(threads))
        threading_list = []
        for (_, ii, jj) in bv_list:
            work = threading.Thread(target=self.comment_check_schedule, args=(ii, jj))
            threading_list.append(work)
        for work in threading_list:
            work.start()
        for work in threading_list:
            work.join()
        return bv_list

    def comment_check_schedule(self, av_id: int, comment: int):
        """ schedule comment check thread """

        threading_list = []
        for pn in range(1, min((comment - 1) // 20 + 2, 3)):
            for sort in [2, 0]:
                work = threading.Thread(
                    target=self.check_comment_once, args=(av_id, pn, sort)
                )
                threading_list.append(work)
        for work in threading_list:
            work.start()
        for work in threading_list:
            work.join()

    def check_comment_once(
        self, av_id: str, pn: int, sort: int, root: int = -1, ps: int = 10
    ):
        """ check comment once """
        comment = self.get_comment_info(av_id, pn, sort, root, ps)
        if comment is None:
            return
        if root != -1:
            echo(
                "2|debug",
                "Comment check, av_id:",
                av_id,
                "pn:",
                pn,
                "sort:",
                sort,
                "root:",
                root,
                "ps:",
                ps,
            )
        else:
            echo("2|debug", "Comment check, av_id:", av_id, "pn:", pn, "sort:", sort)
        hots = comment["hots"]
        replies = comment["replies"]
        if pn > 1 or root != -1:
            wait_check = replies
        else:
            wait_check = replies if hots is None else [*hots, *replies]
        if root == -1:
            wait_check = [{**jj, "idx": ii + 1} for ii, jj in enumerate(wait_check)]
        else:
            wait_check = [
                {**jj, "idx": "reply-{}".format(ii + 1)}
                for ii, jj in enumerate(wait_check)
            ]

        for ii in wait_check:
            info = {"basic": self.get_comment_detail(ii, av_id, pn, sort)}
            rpid = info["basic"][0]
            crep = ii["replies"]
            idx = ii["idx"]

            if not crep is None:
                info["replies"] = [
                    self.get_comment_detail(
                        {**kk, "idx": "{}-{}".format(idx, ww + 1)},
                        av_id,
                        pn,
                        sort,
                        rpid,
                    )
                    for ww, kk in enumerate(crep)
                ]

    def get_comment_detail(
        self, comment: dict, av_id: int, pn: int, sort: int, parent_rpid=None
    ) -> List:
        """ get comment detail """
        wait_list = ["rpid", "member", "content", "like", "idx", "ctime"]
        wait_list_mem = ["uname", "sex", "sign", "level_info"]
        wait_list_content = ["message", "plat"]
        rpid, member, content, like, idx, ctime = [comment[ii] for ii in wait_list]
        uname, sex, sign, level = [member[ii] for ii in wait_list_mem]
        current_level = level["current_level"]
        content, plat = [content[ii] for ii in wait_list_content]
        req_list = [
            rpid,
            ctime,
            like,
            plat,
            current_level,
            uname,
            sex,
            content,
            sign,
            idx,
            sort,
        ]
        self.have_bad_comment(req_list, av_id, pn, parent_rpid)
        req_list[-3] = req_list[-3].replace(",", " ").replace("\n", " ")
        req_list[-4] = req_list[-4].replace(",", " ").replace("\n", " ")
        return req_list

    def have_bad_comment(self, req_list: list, av_id: int, pn: int, parent_rpid=None):
        """ check comment and send warning email if error """
        rpid, ctime, like, plat, current_level, uname, sex, content, sign, idx, sort = (
            req_list
        )
        ctimes = time_str(ctime, time_format=self.T_FORMAT)
        ctime = time_str(ctime)

        if not len(regex.findall(self.keyword, content)):
            return True
        rpid = "{}{}".format(rpid, "" if not parent_rpid else "-{}".format(parent_rpid))

        url = self.BASIC_AV_URL % av_id
        rpid_str = "{}-{}".format(av_id, rpid)
        if rpid in [kk for ii in self.ignore_rpid.values() for kk in ii]:
            return True
        if self.email_limit < 1 or (
            rpid_str in self.email_send_time
            and self.email_send_time[rpid_str] >= self.email_limit
        ):
            return True
        if rpid_str in self.email_send_time:
            self.email_send_time[rpid_str] += 1
        else:
            self.email_send_time[rpid_str] = 1
        rank_info = [
            r_info for bv_id, r_info in self.bv_ids.items() if r_info["aid"] == av_id
        ][0]
        title = rank_info["title"].split("|", 1)[0]
        sort = "热门" if sort else "时间"

        email_content = "Date: {}\nUrl: {}\nTitle: {},\nPage: {} #{}@{},\nUser: {},\nSex: {},\nsign: {}\nlike: {}\nplat: {}\nlevel:{}\nconetnt: {},\n".format(
            ctime,
            title,
            url,
            pn,
            idx,
            rpid,
            uname,
            sex,
            sign,
            like,
            plat,
            current_level,
            content,
        )
        email_subject = "评论({}){}{}{}#{}".format(ctimes, title, sort, pn, idx)
        echo("4|warning", email_content, email_subject)
        send_email(email_content, email_subject, assign_rec=self.assign_rec)

    def get_cid(self, av_id: int):
        playlist_url = self.PLAYLIST_URL % av_id
        return self.get_api_req(playlist_url, av_id)

    def get_danmaku_once(self, oid: int):
        dm_url = self.DM_URL % oid
        req = proxy_req(dm_url, 2)
        if req is None:
            if can_retry(dm_url):
                return self.get_danmaku_once(oid)
            else:
                return
        req.encoding = "utf-8"
        dm = regex.findall('p="(.*?)">(.*?)</d>', req.text)
        echo(3, "oid {} have {} dm".format(oid, len(dm)))
        return dm, oid

    def get_view_detail(self, bv_id: str, cid: int = -1):
        view_url = self.VIEW_URL % bv_id
        if cid >= 0:
            view_url += "&cid={}".format(cid)
        return self.get_api_req(view_url, bv_id)

    def get_stat_info(self, av_id: int):
        stat_url = self.ARCHIVE_STAT_URL % av_id
        return self.get_api_req(stat_url, av_id)

    def get_comment_info(
        self, bv_id: str, pn: int, sort: int, root: int = -1, ps: int = 10
    ):
        comment_url = self.REPLY_V2_URL % (pn, bv_id, sort)
        if root != -1:
            comment_url += "&&ps={}&&root={}".format(ps, root)
        return self.get_api_req(comment_url, bv_id)

    def get_danmaku(self, av_id: int):
        self.dm_map = {}
        self.dm_exec = ThreadPoolExecutor(max_workers=100)
        mkdir(dm_dir)
        output_path = "{}{}_dm.csv".format(dm_dir, av_id)

        view_data = self.get_view_detail(av_id)
        if view_data is None:
            return

        cid_list = [ii["cid"] for ii in view_data["pages"]]
        dm_map = self.dm_map[av_id] if av_id in self.dm_map else {}
        cid_list = [ii for ii in cid_list if ii not in dm_map or len(dm_map[ii]) == 0]
        dm_thread = [self.dm_exec.submit(self.get_danmaku_once, ii) for ii in cid_list]
        need_dm = view_data["stat"]["danmaku"]
        need_p = len(view_data["pages"])
        echo(2, "Begin {} p thread, need {} dm".format(need_p, need_dm))

        dm_list = list(as_completed(dm_thread))
        dm_list = [ii.result() for ii in as_completed(dm_thread)]
        dm_list = [ii for ii in dm_list if ii is not None]
        dm_map = {**dm_map, **{jj: ii for ii, jj in dm_list}}
        dm_num = sum([len(ii) for ii in dm_map.values()])
        p_num = len(dm_map)
        self.dm_map[av_id] = dm_map

        title = "{} {} Total {} p {} dm, Actual {} p {} dm".format(
            view_data["title"],
            self.BASIC_AV_URL % av_id,
            need_p,
            need_dm,
            p_num,
            dm_num,
        )
        result = [title, ""]
        for cid in view_data["pages"]:
            if cid["cid"] not in dm_map:
                continue
            dm = dm_map[cid["cid"]]
            dm = [
                [
                    float(ii.split(",")[0]),
                    time_str(time_stamp=int(ii.split(",")[4])),
                    jj,
                ]
                for ii, jj in dm
            ]
            dm = sorted(dm, key=lambda i: i[0])
            dm = [",".join([get_min_s(str(ii)), jj, kk]) for ii, jj, kk in dm]
            p_title = "p{} {} Total {} dm".format(cid["page"], cid["part"], len(dm))
            result.extend([p_title, *dm, ""])

        with open(output_path, "w") as f:
            f.write("\n".join(result))
        print_str = "Load {} p {} dm to {}, except {} p {} m".format(
            output_path, len(dm_list), dm_num, need_p, need_dm
        )
        if need_dm == dm_num:
            echo(1, print_str, "success")
        else:
            echo(0, print_str, "error")

    def get_m_html(self, bv_id: str) -> str:
        url = self.M_BILIBILI_URL % bv_id
        headers = {
            "Accept": get_accept("html"),
            "Host": url.split("/")[2],
            "User-Agent": get_use_agent("mobile"),
        }
        m_html = proxy_req(url, 3, header=headers)
        if len(m_html) < 1000:
            if can_retry(url):
                return self.get_m_html(bv_id)
            else:
                return ""
        return m_html

    def is_hot(self, bv_id: str) -> bool:
        m_html = self.get_m_html(bv_id)
        return "热门" in m_html


if __name__ == "__main__":
    mkdir(data_dir)
    mkdir(comment_dir)
    mkdir(history_dir)
    mkdir(history_data_dir)
    bb = Up()
    bb.schedule_main()
