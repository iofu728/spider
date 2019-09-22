# -*- coding: utf-8 -*-
# @Author: gunjianpan
# @Date:   2019-09-14 14:47:48
# @Last Modified by:   gunjianpan
# @Last Modified time: 2019-09-22 12:10:52

import base64
import json
import os
import sys
import time
import urllib

import numpy as np
import regex
import rsa

sys.path.append(os.getcwd())
from util.util import can_retry, echo, encoder_cookie, send_email, time_stamp

from .basicBilibili import BasicBilibili
from .geetestE import E, O, S


proxy_req = 0
one_day = 86400
root_dir = os.path.abspath('bilibili')
data_dir = os.path.join(root_dir, 'data/')
PUBLIC = '00C1E3934D1614465B33053E7F48EE4EC87B14B95EF88947713D25EECBFF7E74C7977D02DC1D9451F79DD5D1C10C29ACB6A9B4D6FB7D0A0279B6719E1772565F09AF627715919221AEF91899CAE08C0D686D748B20A3603BE2318CA6BC2B59706592A9219D0BF05C9F65023A21D2330807252AE0066D59CEEFA5F2748EA80BAB81'


class Login(BasicBilibili):
    ''' bilibili login module '''

    def __init__(self):
        super(Login, self).__init__()
        self.update_proxy(1)
        self.access_key = ''
        self.aes_key = ''
        self.T = E(list(PUBLIC), 16)

    def get_access_key(self):
        captcha, cookie = self.get_captcha()
        hash_salt, key, cookie = self.get_hash_salt(cookie)
        if captcha is None:
            return
        types, cookie = self.get_type(captcha['gt'], cookie)
        return {
            'captcha': captcha,
            'hash_salt': hash_salt,
            'types': types,
            'cookie': cookie
        }

    def get_aes_key(self):
        def wl():
            return hex(int(65536 * (1 + np.random.random())))[3:]
        return wl() + wl() + wl() + wl()

    def get_t(self, aes_key: str, t: int = 128):
        n = np.zeros(t).astype(np.int)
        for ii, jj in enumerate(aes_key):
            n[ii + 112] = ord(jj)
        i = S()
        for ii in range(t - 2, 1, -1):
            n[ii] = i()
        n[1] = 2
        return n

    def doPublic(self):
        n = self.get_t(self.get_aes_key())
        self.N = E(n, 256)
        n = self.N.modPowInt(65537, self.T)
        r = n.tostring(16)
        add = '' if not (1 & len(r)) else '0'
        return '{}{}'.format(add, r)

    def get_hash_salt(self, cookie: dict = {}):
        url = self.GET_KEY_URL % np.random.random()
        headers = self.get_login_headers(2, cookie)
        hash_salt, cookies = proxy_req(url, 1, header=headers,
                                       need_cookie=True)
        if hash_salt is None or list(hash_salt.keys()) != ['hash', 'key']:
            if can_retry(url):
                return self.get_hash_salt()
            else:
                return None, {}
        return hash_salt['hash'], hash_salt['key'], cookies

    def get_captcha(self, cookie: dict = {}):
        url = self.CAPTCHA_URL
        headers = self.get_login_headers(0, cookie)
        captcha, cookies = proxy_req(url, 1, header=headers, need_cookie=True)
        if captcha is None or list(captcha.keys()) != ['code', 'data']:
            if can_retry(url):
                return self.get_captcha()
            else:
                return None, {}
        return captcha['data']['result'], cookies

    def get_access_key_req(self, hash_salt: str, key: str, challenge: str, validate: str, cookie: dict = {}):
        data = {
            'captchaType': 11,
            'username': self.username,
            'password': self.encoder_login_info(hash_salt, key),
            'keep': True,
            'key': key,
            'goUrl': self.AV_URL,
            'challenge': challenge,
            'validate': validate,
            'seccode': f'{validate}|jordan'
        }
        headers = self.get_login_headers(1, cookie)
        login = proxy_req(self.LOGIN_V2_URL, 12, header=headers)

    def get_type(self, gt: str, cookies: dict = {}) -> dict:
        url = self.GETTYPE_URL % (gt, int(time_stamp() * 1000))
        headers = self.get_login_headers(3, cookies)
        req, cookie = proxy_req(url, 3, header=headers, need_cookie=True)
        j_begin = req.find('{')
        if req == '' or j_begin == -1:
            if can_retry(self.GETTYPE_URL):
                return self.get_type(gt, cookies)
            else:
                return None, {}
        type_json = json.loads(req[j_begin:-1])
        return type_json['data'], cookie

    def encode_login_info(self, hash_salt: str, key: str):
        public_key = rsa.PublicKey.load_pkcs1_openssl_pem(key.encode())
        concate = rsa.encrypt(hash_salt + self.password).encode('utf-8')
        s = base64.b64encode(concate, public_key)
        s = urllib.parse.quote_plus(s)
        return s

    def get_login_headers(self, mode: int = 0, cookie: dict = {}):
        headers = {
            'Referer': self.LOGIN_URL,
        }
        if mode != 3:
            headers['Accept'] = '*/*' if mode == 2 else 'application/json, text/plain, */*'
        if mode == 1:
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
        elif mode == 2:
            headers['X-Requested-With'] = 'XMLHttpRequest'
        if len(cookie):
            headers['Cookie'] = encoder_cookie(cookie)
        return headers

    def update_proxy(self, mode: int = 0):
        global proxy_req
        if not mode:
            self.update_proxy_basic()
        proxy_req = self.proxy_req
