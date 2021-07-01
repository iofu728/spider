# -*- coding: utf-8 -*-
# @Author: gunjianpan
# @Date:   2021-06-23 15:31:00
# @Last Modified by:   gunjianpan
# @Last Modified time: 2021-07-02 02:07:53

import bisect
import ipaddress
import json
import os
import sys
import shlex
import time
from collections import Counter, defaultdict
from functools import lru_cache

sys.path.append(os.getcwd())
from util.db import Db
from util.util import (
    echo,
    load_cfg,
    json_str,
    time_stamp,
    time_str,
    read_file,
    decoder_str,
    begin_time,
    end_time,
    get_time_str,
    create_argparser,
    set_args,
)

BASIC_DIR = "blog/"
DATA_DIR = f"{BASIC_DIR}data/"
SQL_DIR = f"{BASIC_DIR}sql/"
CFG_PATH = f"{BASIC_DIR}blog.ini"


class Defender(object):
    IP2URL = "https://www.ip2location.com/download/?token=%s&file=%s"
    IP2KEYS = ["DB", "PX", "ASN"]
    IP2CODES = ["DB11LITECSV", "PX10LITECSV", "DBASNLITE"]
    IP2TABLES = ["ip2location", "ip2proxy", "ip2asn"]
    IP2FILES = [
        "IP2LOCATION-LITE-DB11.CSV",
        "IP2PROXY-LITE-PX10.CSV",
        "IP2LOCATION-LITE-ASN.CSV",
    ]
    IP2DETAILS = [
        "IP1-IP2-CN-COUNTRY-REGION-CITY-LATITUDE-LONGITUDE-ZIPCODE-TIMEZONE",
        "IP1-IP2-PROXYTYPE-CNCODE-COUNTRY-REGION-CITY-ISP-DOMAIN-USAGETYPE-ASN-LASTSEEN-THREAT-RESIDENTIAL",
        "IP1-IP2-ASN",
    ]
    IP2TERMINATED = ["\r\n", "\n", "\r\n"]
    SHOW_SQL = "SHOW TABLES LIKE '%s';"
    DROP_SQL = "DROP TABLE IF EXISTS %s;"
    CREATE_SQL = "CREATE TABLE %s LIKE %s;"
    LOAD_SQL = """LOAD DATA LOCAL INFILE '%s' INTO TABLE %s FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '%s';"""
    RENAME_SQL = "RENAME TABLE %s TO %s"
    IP_SQL = "SET @a:= inet_aton('%s');"
    PROXY_FIND_SQL = "SELECT * FROM ip2proxy WHERE asn=%d and ip_to %s %d AND ip_to %s %d ORDER BY ip_to %s LIMIT 1;"
    ONE_HOURS = 3600
    ONE_DAY = 24 * ONE_HOURS
    TMP_SUFFIX = "_tmp"
    DROP_SUFFIX = "_drop"
    SQL_SUFFIX = ".sql"
    L_LISTS = ["L1", "L2", "L3"]

    def __init__(self):
        self.r = Db("redis").r
        self.es = Db("es").es
        self.mysql = Db("ip2", local_infile=True)
        self.IP_indexs = {}
        self.IP_detail = {}
        self.score_blocks = {ii: [] for ii in self.L_LISTS}
        self.click_blocks = {ii: [] for ii in self.L_LISTS}
        self.blocks_flag = {ii: "" for ii in self.L_LISTS}
        self.L_size = {}
        self.L_ratio = {}
        self.L_threshold = {}
        self.load_configure()
        for key in self.L_LISTS:
            self.load_blocks(key)

    def load_configure(self):
        cfg = load_cfg(CFG_PATH)
        self.ip2location_token = cfg.get("IP2LOCATION", "token")
        self.es_body = json.loads(cfg.get("Defender", "es_body"))
        self.es_index = cfg.get("Defender", "es_index")
        self.es_size = cfg.getint("Defender", "es_size")
        self.es_body["size"] = self.es_size
        for k in ["L1", "L2"]:
            self.L_size[k] = cfg.getint("Defender", f"{k}_size")
        for k in ["L0"] + self.L_LISTS:
            self.L_ratio[k] = cfg.getfloat("Defender", f"{k}_ratio")
            self.L_threshold[k] = cfg.getint("Defender", f"{k}_threshold")
        self.L_threshold["score"] = cfg.getint("Defender", "score_threshold")
        self.delta_ip = cfg.getint("Defender", "delta_ip")
        self.ipset_name = cfg.get("Defender", "ipset_name")

    def dot2LongIP(self, ip: str):
        return int(ipaddress.IPv4Address(ip))

    def long2DotIP(self, ip_long: int):
        w = (ip_long // 16777216) % 256
        x = (ip_long // 65536) % 256
        y = (ip_long // 256) % 256
        z = ip_long % 256
        return f"{w}.{x}.{y}.{z}"

    def load_ip2db_thread(self, idx: int):
        path = f"{DATA_DIR}{self.IP2FILES[idx]}"
        if not os.path.exists(path):
            self.download_ip2db_file(idx)
            self.load_ip2db_file(idx)
        else:
            mtime = os.path.getmtime(path)
            month = time_str(mtime, "%m")
            if time_stamp() - mtime > 10 * self.ONE_DAY and month != time_str(
                time_format="%m"
            ):
                self.download_ip2db_file(idx)
                self.load_ip2db_file(idx)

    def decoder_data(self, data: list, idx: int):
        KEYS = self.IP2DETAILS[idx].split("-")
        return {ii: jj for ii, jj in zip(KEYS, data)}

    def load_ip2db_file(self, idx: int):
        flag = begin_time()
        path = f"{DATA_DIR}{self.IP2FILES[idx]}"
        table_name = self.IP2TABLES[idx]
        tmp_table_name = f"{table_name}{self.TMP_SUFFIX}"
        drop_table_name = f"{table_name}{self.DROP_SUFFIX}"
        term = self.IP2TERMINATED[idx]
        is_existed = self.mysql.select_db(self.SHOW_SQL % table_name)
        if is_existed:
            self.mysql.execute(self.DROP_SQL % tmp_table_name, True)
            self.mysql.execute(self.CREATE_SQL % (tmp_table_name, table_name), True)
        else:
            self.mysql.create_table(f"{SQL_DIR}{table_name}{self.SQL_SUFFIX}")
        self.mysql.execute(self.LOAD_SQL % (path, tmp_table_name, term), True)
        if is_existed:
            self.mysql.execute(self.RENAME_SQL % (table_name, drop_table_name), True)
        self.mysql.execute(self.RENAME_SQL % (tmp_table_name, table_name), True)
        if is_existed:
            self.mysql.execute(self.DROP_SQL % drop_table_name, True)
        spend_time = end_time(flag, 0)
        echo(
            "1|debug",
            f"Load {K} file data to mysql spend {get_time_str(spend_time, False)}.",
        )

    def download_ip2db_file(self, idx: int):
        zip_path = f"{self.IP2CODES[idx]}.zip"
        url = shlex.quote(self.IP2URL % (self.ip2location_token, self.IP2CODES[idx]))
        shell_str = f"cd {DATA_DIR} && wget {url} -O {zip_path} && unzip -o {zip_path} && rm -rf *.TXT && rm -rf *.zip"
        echo("2|debug", shell_str)
        os.system(shell_str)

    def load_past(self):
        body, index, size = self.es_body, self.es_index, self.es_size
        res, total = self.load_past_req(index, body)
        id_set = set([ii["_id"] for ii in res])
        res = [ii["_source"] for ii in res]
        for ii in range(1, (total - 1) // size + 1):
            body["from"] = ii + 1
            tmp, _ = self.load_past_req(index, body)
            for ii in tmp:
                if ii["_id"] not in id_set:
                    res.append(ii["_source"])
                    id_set.add(ii["_id"])
        return res

    def load_past_req(self, index: str, body: dict):
        res = self.es.search(index=index, body=body)
        return res["hits"]["hits"], res["hits"]["total"]["value"]

    def analysis_user_agent(self, req: dict):
        score = 0
        user_agent = req.get("user_agent", {})
        name = user_agent.get("name", "")
        device = user_agent.get("device", {}).get("name", "")
        if name in ["", "Other", "Go-http-client"]:
            score += 20
        if device in ["", "Other"] and "os" not in user_agent:
            score += 20
        if "os" not in user_agent:
            score += 5
        if "version" not in user_agent:
            score += 5
        if not user_agent:
            score += 30
        echo("1|debug", score, user_agent)
        return score

    @lru_cache(maxsize=2 ** 31)
    def load_asn_usage(self, asn_number: int, ip_long: int):
        USAGETYPE = ""
        prev = self.mysql.execute(
            self.PROXY_FIND_SQL
            % (asn_number, ">=", ip_long, "<=", ip_long + 1000000, "ASC")
        )
        prev = self.decoder_data(prev[0], 1) if prev else {}
        nex = self.mysql.execute(
            self.PROXY_FIND_SQL
            % (asn_number, "<=", ip_long, ">=", ip_long - 1000000, "DESC")
        )
        nex = self.decoder_data(nex[0], 1) if nex else {}

        if prev and abs(prev["IP1"] - ip_long) <= self.delta_ip:
            USAGETYPE = prev["USAGETYPE"]
        elif nex and abs(nex["IP2"] - ip_long) <= self.delta_ip:
            USAGETYPE = nex["USAGETYPE"]
        return USAGETYPE

    def analysis_ip(self, req: dict, ipc: dict):
        score = 0
        ip_long, source = [req[ii] for ii in ["ip_long", "source"]]
        ip, geo, asn = [
            source.get(ii, jj) for ii, jj in zip(["ip", "geo", "as"], ["", {}, {}])
        ]
        USAGETYPE = ""
        if asn:
            asn_number = asn["number"]
            USAGETYPE = self.load_asn_usage(asn_number, ip_long)
            if geo["country_name"] != "China":
                score += 5
            if "city_name" in geo or "region_name" in geo:
                score -= 5
            if "Alibaba" in asn["organization"]["name"]:
                score += 10
        if USAGETYPE == "SES":
            score += 2
        elif USAGETYPE == "DCH":
            score += 20
        click, ip_num = 0, 0
        for k, v in ipc.items():
            if abs(k - ip_long) <= self.delta_ip * 10:
                click += v
                ip_num += 1
        if click >= 1000 or ip_num >= 5:
            score += 30
        echo("1|debug", score, ip, geo["country_name"], asn, USAGETYPE)
        return score

    def analysis_url(self, req: dict):
        score = 0
        url = req["url"]["original"]
        http = req["http"]
        if any([ii in url for ii in ["admin", "php", "wp"]]):
            score += 20
        if "referrer" not in http["request"]:
            score += 5
        if http["response"]["status_code"] not in [200, 204, 302, 301]:
            score += 15
        echo(
            "1|debug",
            score,
            http["response"]["status_code"],
            http["request"].get("referrer", ""),
            url,
        )
        return score

    def analysis_reqs(self, reqs: list):
        res = []
        L0_score, L0_click = self.analysis_L0(reqs)
        for k, s in L0_score.items():
            c0 = L0_click[k]
            s1, c1 = self.analysis_LX(k, "L1")
            s2, c2 = self.analysis_LX(k, "L2")
            s3, c3 = self.analysis_LX(k, "L3")
            s = sum(
                [
                    ii * self.L_ratio[jj]
                    for ii, jj in zip([s, s1, s2, s3], ["L0"] + self.L_LISTS)
                ]
            )
            echo("1|debug", self.long2DotIP(k), s, s1, s2, s3, c0, c1, c2, c3)
            if any(
                [
                    ii >= self.L_threshold[jj]
                    for ii, jj in zip(
                        [s, c0, c1, c2, c3], ["score", "L0"] + self.L_LISTS
                    )
                ]
            ):
                res.append(self.long2DotIP(k))
        return res

    def analysis_L0(self, reqs: list):
        def pop_block(key: str) -> bool:
            size = self.L_size[key]
            if len(self.score_blocks[key]) > size:
                self.score_blocks[key].pop(0)
                self.click_blocks[key].pop(0)
                return True
            return False

        res, ipc = defaultdict(list), []
        for req in reqs:
            req["ip_long"] = self.dot2LongIP(req["source"]["ip"])
            ipc.append(req["ip_long"])
        ipc = Counter(ipc)
        for req in reqs:
            ip_long = req["ip_long"]
            score = 0
            score += self.analysis_user_agent(req)
            score += self.analysis_url(req)
            score += self.analysis_ip(req, ipc)
            res[ip_long].append(score)
        res_score = Counter({k: max(v) for k, v in res.items()})
        res_click = Counter({k: len(v) for k, v in res.items()})
        self.score_blocks["L1"].append(res_score)
        self.click_blocks["L1"].append(res_click)
        L1_pop = pop_block("L1")
        L2_flag = time_str(time_format="%H")
        L2_pop = False
        if L2_flag != self.blocks_flag["L2"]:
            self.score_blocks["L2"].append(Counter())
            self.click_blocks["L2"].append(Counter())
            L2_pop = pop_block("L2")
        self.click_blocks["L2"][-1] += res_click
        self.click_blocks["L3"] += res_click
        for k, v in res_score.items():
            self.score_blocks["L2"][-1][k] = max(self.score_blocks["L2"][-1][k], v)
            self.score_blocks["L3"][k] = max(self.score_blocks["L3"][k], v)
        self.blocks_flag["L2"] = L2_flag
        for k, pop in zip(self.L_LISTS, [L1_pop, L2_pop, False]):
            self.store_blocks2redis(k, pop)
        return res_score, res_click

    def store_blocks2redis(self, key: str, is_pop: bool = False):
        def store(kk: str, data: dict):
            if key == "L3":
                self.r.set(f"{kk}:{key}", json_str(list(data[key].items())))
            else:
                if is_pop:
                    self.r.ltrim(f"{kk}:{key}", 0, -2)
                elif key == "L2":
                    self.r.lpop(f"{kk}:{key}")
                self.r.lpush(f"{kk}:{key}", json_str(list(data[key][-1].items())))

        store("score", self.score_blocks)
        store("click", self.click_blocks)
        if key == "L2":
            self.r.set(f"flag:{key}", self.blocks_flag[key])

    def load_blocks(self, key: str):
        def load(kk: str):
            if key == "L3":
                d = self.r.get(f"{kk}:{key}")
                d = Counter(dict(json.loads(d))) if d else Counter()
            else:
                d = self.r.lrange(f"{kk}:{key}", 0, -1)
                d = [dict(json.loads(ii)) for ii in d][::-1]
                if d:
                    d[-1] = Counter(d[-1])
            return d

        self.score_blocks[key] = load("score")
        self.click_blocks[key] = load("click")
        if key == "L2":
            d = self.r.get(f"flag:{key}")
            self.blocks_flag[key] = d if d else ""

    def get_cluster(self, ip_long: int, data: dict, key: str):
        if key not in ["L1", "L2"]:
            return 0
        keys = sorted(set([jj for ii in data for jj in ii]))
        left_idx = bisect.bisect_left(keys, ip_long - self.delta_ip * 10)
        right_idx = bisect.bisect_left(keys, ip_long + self.delta_ip * 10, left_idx)
        if right_idx - right_idx >= 6:
            echo("2|debug", self.long2DotIP(ip_long))
        return 30 if right_idx - right_idx >= 6 else 0

    def analysis_LX(self, ip_long: str, key: str):
        def get(data: dict, kk: str):
            if key == "L3":
                return data.get(ip_long, 0)
            res = []
            for ii in data:
                if ip_long not in ii:
                    continue
                res.append(ii[ip_long])
            if kk == "sum":
                return sum(res) if res else 0
            else:
                return max(res) + self.get_cluster(ip_long, data, key) if res else 0

        return get(self.score_blocks[key], "max"), get(self.click_blocks[key], "sum")

    def block_ips(self, block_list: list):
        res = defaultdict(list)
        for ip in block_list:
            t = self.r.get(f"block:{ip}") or 0
            res[t + 1].append(ip)
            shell_str = (
                f"ipset add {self.ipset_name} {ip} timeout {self.ONE_HOURS * (2 ** t)}"
            )
            os.system(shell_str)
            self.r.set(f"block:{ip}", t + 1, self.ONE_DAY * 8)
        echo("2", "Block ips", res)

    def load_click(self, num=1000000):
        for index in range(num):
            flag = begin_time()
            res = self.load_past()
            block_list = self.analysis_reqs(res)
            self.block_ips(block_list)
            spend_time = end_time(flag, 0)
            echo(
                3,
                f"No. {index + 1} block {len(block_list)}/{len(res)} log spend {get_time_str(spend_time, False)}",
            )
            time.sleep(max(60 - spend_time, 0))


if __name__ == "__main__":
    parser = create_argparser("Defender")
    args = set_args(parser)
    ba = Defender()
    ba.load_click()