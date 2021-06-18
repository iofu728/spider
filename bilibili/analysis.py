# -*- coding: utf-8 -*-
# @Author: gunjianpan
# @Date:   2019-04-04 10:57:24
# @Last Modified by:   gunjianpan
# @Last Modified time: 2021-06-18 20:53:52

import pandas as pd
import numpy as np
import time
import os
import sys

sys.path.append(os.getcwd())
from util.util import echo, read_file, time_stamp, time_str

root_dir = os.path.abspath("bilibili")
data_dir = os.path.join(root_dir, "data/")
history_data_dir = os.path.join(data_dir, "history_data/")
history_dir = os.path.join(data_dir, "history/")


def analysis_csv():
    data_dir = "bilibili/"
    df = pd.read_csv("%spublic.csv" % data_dir)

    """one day"""
    df["fan"] = df["3"].fillna(0)
    df["time"] = df["1"].map(lambda x: x.split(None, 1)[1])
    df["fanadd"] = df["4"] - df["3"]
    df["fanadd"] = df["fanadd"].map(lambda x: x if x > 0 else 0)
    df["fanadd_ratio"] = df["fanadd"] / df["3"]
    df["fanadd_ratio"] = df["fanadd_ratio"].replace([np.inf, -np.inf], np.nan).fillna(0)
    df["viewadd"] = (df["18"] - df["6"]).fillna(0)
    df["viewadd"] = df["viewadd"].map(lambda x: x if x > 0 else 0)
    df["viewadd_ratio"] = (
        (df["viewadd"] / df["6"]).replace([np.inf, -np.inf], np.nan).fillna(0)
    )
    df["view_fan"] = (
        (df["viewadd"] / df["3"]).replace([np.inf, -np.inf], np.nan).fillna(0)
    )
    df["view_fan_20"] = df["view_fan"].map(lambda x: x if x < 20 else 0)
    df["view_fanadd"] = (
        (df["viewadd"] / df["fanadd"]).replace([np.inf, -np.inf], np.nan).fillna(0)
    )

    """seven day"""
    df["seven"] = df["1"].map(
        lambda x: "1970-01-%d %s"
        % (
            int(time.strftime("%w", time.strptime(x, "%Y-%m-%d %H:%M:%S"))) + 4,
            x.split(None, 1)[1],
        )
    )
    need_columns = [
        "time",
        "fan",
        "fanadd",
        "fanadd_ratio",
        "viewadd",
        "viewadd_ratio",
        "view_fan",
        "view_fan_20",
        "view_fanadd",
        "seven",
    ]
    result_df = pd.DataFrame(df, columns=need_columns)
    result_df.to_csv("%spublic_re.csv" % data_dir, index=False)


def clean_csv(av_id: int, bv_id: str, bv_info: dict):
    csv_path = os.path.join(history_dir, f"{av_id}.csv")
    if not os.path.exists(csv_path):
        csv_path = os.path.join(history_dir, f"{bv_id}.csv")
    output_path = os.path.join(history_data_dir, f"{bv_id}_new.csv")
    csv = read_file(csv_path)
    last_time, last_view = bv_info["created"], 0
    result, t_idx, idx, N = [], 2, 0, len(csv)
    empty_line = ",".join([" "] * 12)
    for line in csv:
        now_time, now_view = line.split(",")[:2]
        if not now_time.strip():
            continue
        if "-" not in now_time:
            line = line.replace(now_time, time_str(float(now_time)))
            now_time = float(now_time)
        else:
            now_time = time_stamp(now_time)
        now_view = int(now_view)
        time_gap = now_time - last_time
        idx = round(time_gap / 120)
        if idx == 0:
            continue
        if idx > 20000:
            break
        result.extend([empty_line] * (idx - 1))
        result.append(line)
        last_view, last_time = now_view, now_time
    with open(output_path, "w") as f:
        f.write("\n".join(result))
