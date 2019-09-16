# -*- coding: utf-8 -*-
# @Author: gunjianpan
# @Date:   2019-09-14 14:49:01
# @Last Modified by:   gunjianpan
# @Last Modified time: 2019-09-17 01:33:07

import json
import os
import shutil
import sys
import urllib
from configparser import ConfigParser

sys.path.append(os.getcwd())
from proxy.getproxy import GetFreeProxy
from util.util import can_retry


one_day = 86400
root_dir = os.path.abspath('bilibili')
data_dir = os.path.join(root_dir, 'data/')
assign_path = os.path.join(root_dir, 'assign_up.ini')
if not os.path.exists(assign_path):
    shutil.copy(assign_path + '.tmp', assign_path)


class BasicBilibili(object):
    BILIBILI_URL = 'https://www.bilibili.com'
    BASIC_AV_URL = 'http://www.bilibili.com/video/av%d'
    ARCHIVE_STAT_URL = 'http://api.bilibili.com/x/web-interface/archive/stat?aid=%d'
    VIEW_URL = 'http://api.bilibili.com/x/web-interface/view?aid=%d'
    RELATION_STAT_URL = 'http://api.bilibili.com/x/relation/stat?jsonp=jsonp&callback=__jp11&vmid=%d'
    BASIC_RANKING_URL = 'https://www.bilibili.com/ranking/all/%d/'
    MEMBER_SUBMIT_URL = 'http://space.bilibili.com/ajax/member/getSubmitVideos?mid=%s&page=1&pagesize=50'
    REPLY_V2_URL = 'http://api.bilibili.com/x/v2/reply?jsonp=jsonp&pn=%d&type=1&oid=%d&sort=2'
    PLAYLIST_URL = 'https://api.bilibili.com/x/player/pagelist?aid=%d&jsonp=jsonp'
    DM_URL = 'https://api.bilibili.com/x/v1/dm/list.so?oid=%d'
    GET_KEY_URL = 'http://passport.bilibili.com/login?act=getkey&r=%f'
    LOGIN_URL = 'https://passport.bilibili.com/login'
    LOGIN_V2_URL = 'https://passport.bilibili.com/web/login/v2'
    LOGIN_OAUTH_URL = 'https://passport.bilibili.com/api/v2/oauth2/login'
    CAPTCHA_URL = 'https://passport.bilibili.com/web/captcha/combine?plat=11'
    GETTYPE_URL = 'https://api.geetest.com/gettype.php?gt=%s&callback=geetest_%d'
    NO_RANK_CONSTANT = 'No rank.....No Rank......No Rank.....'
    JSON_KEYS = ['code', 'message', 'ttl', 'data']

    def __init__(self):
        super(BasicBilibili, self).__init__()
        self.proxy_req = GetFreeProxy().proxy_req
        self.del_map = {}
        self.rank_map = {}
        self.load_configure()

    def load_configure(self):
        ''' load assign configure '''
        cfg = ConfigParser()
        cfg.read(assign_path, 'utf-8')
        self.assign_up_name = cfg.get('basic', 'up_name')
        mid = cfg['basic']['up_mid']
        self.assign_up_mid = int(mid) if len(mid) else -1
        self.assign_rank_id = cfg.getint('basic', 'rank_id')
        self.assign_tid = cfg.getint('basic', 'tid')
        self.basic_av_id = cfg.getint('basic', 'basic_av_id')
        self.view_abnormal = cfg.getint('basic', 'view_abnormal')
        assign_id = cfg.get('assign', 'av_ids').split(',')
        self.assign_ids = [int(ii) for ii in assign_id]
        rank_map = {ii: [] for ii in self.assign_ids if ii not in self.del_map}
        self.rank_map = {**rank_map, **self.rank_map}
        self.keyword = cfg.get('comment', 'keyword')
        self.ignore_rpid = json.loads(cfg.get('comment', 'ignore_rpid'))
        self.ignore_list = cfg.get('comment', 'ignore_list')
        self.ignore_start = cfg.getfloat('comment', 'ignore_start')
        self.ignore_end = cfg.getfloat('comment', 'ignore_end')
        self.email_limit = cfg.getint('comment', 'email_limit')
        self.AV_URL = self.BASIC_AV_URL % self.basic_av_id
        self.RANKING_URL = self.BASIC_RANKING_URL % self.assign_rank_id + '%d/%d'
        self.history_check_list = [int(ii) for ii in cfg.get(
            'basic', 'history_check_list').split(',')]
        self.special_info_email = cfg.get(
            'basic', 'special_info_email').split(',')
        self.username = urllib.parse.quote_plus(cfg.get('login', 'username'))
        self.password = cfg.get('login', 'password')

    def get_api_req(self, url: str, av_id: int):
        req = self.proxy_req(url, 1, header=self.get_api_headers(av_id))
        if req is None or list(req.keys()) != self.JSON_KEYS:
            if can_retry(url):
                return self.get_api_req(url, av_id)
            else:
                return
        return req['data']

    def get_api_headers(self, av_id: int) -> dict:
        return {
            'Accept': '*/*',
            'Referer': self.BASIC_AV_URL % av_id
        }

    def update_ini(self, av_id: int):
        cfg = ConfigParser()
        cfg.read(assign_path, 'utf-8')
        cfg.set('basic', 'basic_av_id', str(av_id))
        history_av_ids = cfg.get('assign', 'av_ids')
        cfg.set('assign', 'av_ids', '{},{}'.format(history_av_ids, av_id))
        cfg.write(open(assign_path, 'w'))

    def update_proxy_basic(self):
        self.proxy_req = GetFreeProxy().proxy_req
