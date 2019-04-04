'''
@Author: gunjianpan
@Date:   2019-04-04 10:57:24
@Last Modified by:   gunjianpan
@Last Modified time: 2019-04-04 14:02:54
'''

import pandas as pd
import numpy as np
import time

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
