# -*- coding: utf-8 -*-
# @Author: gunjianpan
# @Date:   2019-09-14 14:47:48
# @Last Modified by:   gunjianpan
# @Last Modified time: 2019-09-14 17:46:04

import base64
import os
import rsa
import sys
import urllib

import numpy as np
import regex

sys.path.append(os.getcwd())
from util.util import can_retry, echo, encoder_cookie, send_email
from .basicBilibili import BasicBilibili


proxy_req = 0
one_day = 86400
root_dir = os.path.abspath('bilibili')
data_dir = os.path.join(root_dir, 'data/')


class S(object):
    def __init__(self):
        e = [(255 & int(65536 * np.random.random())) for _ in range(256)]
        S = [ii for ii in range(256)]
        n = 0
        for t in range(256):
            n = (n + S[t] + e[t % len(e)]) & 255
            S[t], S[n] = S[n], S[t]
        self.S = S
        self.i = 0
        self.j = 0

    def __call__(self):
        if not len(self.S):
            self.get_S()
        self.i = (self.i + 1) & 255
        self.j = (self.j + self.S[self.i]) & 255
        self.S[self.i], self.S[self.j] = self.S[self.j], self.S[self.i]
        return self.S[(self.S[self.i] + self.S[self.j]) & 255]


class E(object):
    def __init__(self, e: list, t: int = 256):
        self.t = 0
        self.s = 0


class Login(BasicBilibili):
    ''' bilibili login module '''

    def __init__(self):
        super(Login, self).__init__()
        self.update_proxy(1)
        self.access_key = ''
        self.aes_key = ''
        self.S = []
        self.i = 0
        self.j = 0
        self.E = {}

    def get_access_key(self):
        captcha, cookie = self.get_captcha()
        hash_salt, key, cookie = self.get_hash_salt(cookie)

    def wl(self):
        return hex(int(65536 * (1 + np.random.random())))[3:]

    def get_aes_key(self):
        return self.wl() + self.wl() + self.wl() + self.wl()

    def get_rsa_key(self, aes_key: str, t: int = 128):
        r = len(aes_key) - 1
        n = np.zeros(t).astype(np.int)
        for r in range(r, -1, -1):
            o = ord(aes_key[r])
            if o < 128:
                n[t - 1] = o
                t -= 1
            else:
                n[t - 1] = (63 & 0 | 128)
                t -= 1
                if o > 127 and o < 2048:
                    n[t - 1] = (o >> 6 | 192)
                    t -= 1
                else:
                    n[t - 1] = (o >> 6 & 63 | 128)
                    t -= 1
                    n[t - 1] = (o >> 12 | 224)
                    t -= 1
        i = S()
        for ii in range(t - 2, 1, -1):
            n[ii] = i()
        n[1] = 2

    # def get_E(self):

    def get_hash_salt(self, cookie: dict = {}):
        url = self.GET_KEY_URL % np.random.random()
        headers = {
            'Accept': '*/*',
            'Referer': self.LOGIN_URL,
            'X-Requested-With': 'XMLHttpRequest'
        }
        if len(cookie):
            headers['Cookie'] = encoder_cookie(cookie)
        hash_salt, cookies = proxy_req(
            url, 1, header=headers, need_cookie=True)
        if hash_salt is None or list(hash_salt.keys()) != ['hash', 'key']:
            if can_retry(url):
                return self.get_hash_salt()
            else:
                return
        return hash_salt['hash'], hash_salt['key'], cookies

    def get_captcha(self, cookie: dict = {}):
        url = self.CAPTCHA_URL
        headers = {
            'Accept': 'application/json, text/plain, */*',
            'Referer': self.LOGIN_URL,
        }
        if len(cookie):
            headers['Cookie'] = encoder_cookie(cookie)
        captcha, cookies = proxy_req(url, 1, header=headers, need_cookie=True)
        if captcha is None or list(captcha.keys()) != ['data', 'code']:
            if can_retry(url):
                return self.get_captcha()
            else:
                return
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
        headers = {
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Referer': self.LOGIN_URL
        }
        if len(cookie):
            headers['Cookie'] = encoder_cookie(cookie)
        login = proxy_req(self.LOGIN_V2_URL, 12, header=headers)

    def encode_login_info(self, hash_salt: str, key: str):
        public_key = rsa.PublicKey.load_pkcs1_openssl_pem(key.encode())
        concate = rsa.encrypt(hash_salt + self.password).encode('utf-8')
        s = base64.b64encode(concate, public_key)
        s = urllib.parse.quote_plus(s)
        return s

    def update_proxy(self, mode: int = 0):
        global proxy_req
        if not mode:
            self.update_proxy_basic()
        proxy_req = self.proxy_req
