# -*- coding: utf-8 -*-
# @Author: gunjianpan
# @Date:   2019-04-04 10:57:24
# @Last Modified by:   gunjianpan
# @Last Modified time: 2019-08-10 14:47:13

import pandas as pd
import numpy as np
import time
import os
from util.util import time_stamp, echo, read_file

data_dir = 'bilibili/data/'
history_data_dir = '{}history_data/'.format(data_dir)
history_dir = '{}history/'.format(data_dir)


def analysis_csv():
    data_dir = 'bilibili/'
    df = pd.read_csv('%spublic.csv' % data_dir)

    '''one day'''
    df['fan'] = df['3'].fillna(0)
    df['time'] = df['1'].map(lambda x: x.split(None, 1)[1])
    df['fanadd'] = df['4'] - df['3']
    df['fanadd'] = df['fanadd'].map(lambda x: x if x > 0 else 0)
    df['fanadd_ratio'] = df['fanadd'] / df['3']
    df['fanadd_ratio'] = df['fanadd_ratio'].replace(
        [np.inf, -np.inf], np.nan).fillna(0)
    df['viewadd'] = (df['18'] - df['6']).fillna(0)
    df['viewadd'] = df['viewadd'].map(lambda x: x if x > 0 else 0)
    df['viewadd_ratio'] = (df['viewadd'] / df['6']).replace(
        [np.inf, -np.inf], np.nan).fillna(0)
    df['view_fan'] = (df['viewadd'] / df['3']).replace(
        [np.inf, -np.inf], np.nan).fillna(0)
    df['view_fan_20'] = df['view_fan'].map(lambda x: x if x < 20 else 0)
    df['view_fanadd'] = (df['viewadd'] / df['fanadd']).replace(
        [np.inf, -np.inf], np.nan).fillna(0)

    '''seven day'''
    df['seven'] = df['1'].map(lambda x: '1970-01-%d %s' % (int(time.strftime(
        "%w", time.strptime(x, "%Y-%m-%d %H:%M:%S"))) + 4, x.split(None, 1)[1]))
    need_columns = ['time', 'fan', 'fanadd', 'fanadd_ratio',
                    'viewadd', 'viewadd_ratio', 'view_fan', 'view_fan_20', 'view_fanadd', 'seven']
    result_df = pd.DataFrame(df, columns=need_columns)
    result_df.to_csv('%spublic_re.csv' % data_dir, index=False)


def clean_csv(av_id: int):
    ''' clean csv '''
    csv_path = os.path.join(history_dir, '{}.csv'.format(av_id))
    output_path = os.path.join(history_data_dir, '{}_new.csv'.format(av_id))
    csv = read_file(csv_path)
    last_time, last_view = csv[0].split(',')[:2]
    result = [csv[0]]
    last_time = time_stamp(last_time)
    last_view = int(last_view)
    empty_line = ','.join([' '] * (len(csv[0].split(',')) + 1))
    for line in csv[1:]:
        now_time, now_view = line.split(',')[:2]
        now_time = time_stamp(now_time)
        now_view = int(now_view)
        time_gap = now_time - last_time

        if now_view < last_view or now_view - last_view > 5000:
            # echo(1, last_view, last_time, now_view, now_time)
            continue
        if abs(time_gap) > 150:
            for ii in range(int((time_gap - 30) // 120)):
                result.append(empty_line)
        if abs(time_gap) > 90:
            # echo(0, last_view, last_time, now_view, now_time)
            result.append(line)
            last_view, last_time = now_view, now_time
        # else:
        #     echo(2, last_view, last_time, now_view, now_time)
    with open(output_path, 'w') as f:
        f.write('\n'.join(result))
