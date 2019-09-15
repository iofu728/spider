# -*- coding: utf-8 -*-
# @Author: gunjianpan
# @Date:   2019-09-15 19:25:31
# @Last Modified by:   gunjianpan
# @Last Modified time: 2019-09-15 23:18:38

import os
import sys
import time

import numpy as np

sys.path.append(os.getcwd())
from util.util import echo

g = '0123456789abcdefghijklmnopqrstuvwxyz'
FV = 4503599627370496
DV = 268435456
DB = 28
DM = DV - 1
F1 = 24
F2 = 4


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
    def __init__(self, e=None, t: int = 256):
        super(E, self).__init__()
        self.t = 0
        self.s = 0
        self.E = {}
        self.T = {}
        if e is not None:
            if type(e) == int and e == 1:
                self.one()
            else:
                self.prepare_E(e, t)

    def __call__(self, e: list, t: int):
        self.prepare_E(e, t)

    def prepare_E(self, e: list, t: int):
        n, r, o, i, a, s = int(np.log2(t)), 0, 0, len(e) - 1, False, 0
        p = {ii + 48: ii for ii in range(10)}
        p = {**p, **{ii + 55: ii for ii in range(10, 36)}}
        p = {**p, **{ii + 87: ii for ii in range(10, 36)}}

        while 0 <= i:
            if n == 8:
                c = 255 & e[i]
            else:
                idx = ord(e[i])
                c = p[idx] if idx in p else -1
            if c < 0:
                if '-' == e[i]:
                    a = True
                i -= 1
                continue
            a = False
            if s == 0:
                self.E[self.t] = c
                self.t += 1
            elif s + n > DB:
                self.E[self.t - 1] = self.E[self.t
                                            - 1] | ((c & (1 << DB - 3) - 1) << s)
                self.E[self.t] = c >> DB - s
                self.t += 1
            else:
                self.E[self.t - 1] = self.E[self.t - 1] | (c << s)
            s += n
            if s >= DB:
                s -= DB
            i -= 1
        if n == 8 and (128 & e[0]):
            self.s = -1
            if s > 0:
                self.E[self.t - 1] = self.E[self.t
                                            - 1] | ((1 << DB - s) - 1 << s)
        self.clamp()
        if a:
            echo(0, 'a is True')
            E().subTo(self, self)

    def clamp(self):
        ee = self.s & DM
        while 0 < self.t and self.E[self.t - 1] == ee:
            self.t -= 1

    def get_T(self):
        self.T['m'] = self
        self.T['mp'] = self.invDigit()
        self.T['mpl'] = 32767 & self.T['mp']
        self.T['mph'] = self.T['mp'] >> 15
        self.T['um'] = (1 << DB - 15) - 1
        self.T['mt2'] = 2 * self.t

    def invDigit(self):
        if self.t < 1:
            return 0
        e = self.E[0]
        if (0 == (1 & e)):
            return 0
        t = 3 & e
        t = t * (2 - (15 & e) * t) & 15
        t = t * (2 - (255 & e) * t) & 255
        t = t * (2 - ((65535 & e) * t & 65535)) & 65535
        t = t * (2 - e * t % DV) % DV
        return DV - t if t > 0 else -t

    def modPowInt(self, e: int, t):
        if e >= 256 and not t.isEven():
            t.get_T()
        else:
            echo(0, 'e:', e, 'isEven:', self.isEven())
        return self.exp(e, t)

    def exp(self, e: int, t):
        n, r = E(), E()
        i = self.y(e) - 2
        o = t.convert(self)
        o.copyTo(n)
        while 0 <= i:
            t.sqrTo(n, r)
            if (e & 1 << i) > 0:
                t.mulTo(r, o, n)
            else:
                n, r = r, n
            i -= 1
        return t.revert(n)

    def convert(self, e):
        t = E()
        e.dlShiftTo(self.T['m'].t, t)
        t.divRemTo(self.T['m'], t)
        if e.s < 0 and t.compareTo(E()) > 0:
            self.T['m'].subTo(t, t)
        return t

    def revert(self, e):
        t = E()
        e.copyTo(t)
        self.reduceE(t)
        return t

    def divRemTo(self, e, n):
        if (e.t <= 0):
            return False
        if self.t < e.t:
            return False
        i, a, s = E(), self.s, e.s
        c = DB - self.y(e.E[e.t - 1])
        if c > 0:
            e.lShiftTo(c, i)
            self.lShiftTo(c, n)
        else:
            e.copyTo(i)
            self.copyTo(n)
        u = i.t
        uu = i.E[u - 1]
        if uu == 0:
            return False
        l = uu * (1 << F1) + (i.E[u - 2] >> F2 if u > 1 else 0)
        h = FV / l
        f = (1 << F1) / l
        d = 1 << F2
        p = n.t
        g = p - u
        v = E()
        i.dlShiftTo(g, v)
        if n.compareTo(v) >= 0:
            n.E[n.t] = 1
            n.t += 1
            n.subTo(v, n)
        E(1).dlShiftTo(u, v)
        v.subTo(i, i)
        while i.t < u:
            i.E[i.t] = 0
            i.t += 1
        g -= 1
        while g >= 0:
            p -= 1
            if n.E[p] == uu:
                m = DM
            else:
                m = int(n.E[p] * h + (n.E[p - 1] + d) * f)

            n.E[p] += i.am(0, m, n, g, 0, u)
            if n.E[p] < m:
                i.dlShiftTo(g, v)
                n.subTo(v, n)
                m -= 1
                while n.E[p] < m:
                    n.subTo(v, n)
                    m -= 1
            g -= 1
        n.t = u
        n.clamp()
        if c > 0:
            n.rShiftTo(c, n)
        if a < 0:
            E().subTo(n, n)

    def lShiftTo(self, e: int, t):
        r = e % DB
        o = DB - r
        i = (1 << o) - 1
        a = int(e / DB)
        s = self.s << r & DB
        for n in range(self.t - 1, -1, -1):
            t.E[n + a + 1] = self.E[n] >> o | s
            s = (self.E[n] & i) << r
        for n in range(a):
            t.E[n] = 0
        t.E[a] = s
        t.t = self.t + a + 1
        t.s = self.s
        t.clamp()

    def rShiftTo(self, e: int, t):
        t.s = self.s
        n = int(e / DB)
        if n >= self.t:
            t.t = 0
        else:
            r = e % DB
            o = DB - r
            i = (1 << r) - 1
            t.E[0] = self.E[n] >> r
            for a in range(n + 1, self.t):
                t.E[a - n - 1] = (t.E[a - n - 1]) | ((self.E[a] & i) << o)
                t.E[a - n] = self.E[a] >> r
            if r > 0:
                t.E[self.t - n - 1] = t.E[self.t - n - 1] | ((self.s & i) << o)
            t.t = self.t - n
            t.clamp()

    def copyTo(self, e):
        for t in range(self.t):
            e.E[t] = self.E[t]
        e.t = self.t
        e.s = self.s

    def dlShiftTo(self, e: int, t):
        for ii in range(self.t):
            t.E[ii + e] = self.E[ii]
        for ii in range(e):
            t.E[ii] = 0
        t.t = self.t + e
        t.s = self.s

    def y(self, e: int):
        def yy(e: int, n: int, k: int):
            t = e >> k
            if t:
                e = t
                n += k
            return e, n
        n = 1
        e, n = yy(e, n, 16)
        e, n = yy(e, n, 8)
        e, n = yy(e, n, 4)
        e, n = yy(e, n, 2)
        e, n = yy(e, n, 1)
        return n

    def compareTo(self, e):
        t = self.s - e.s
        if t != 0:
            return t
        t = self.t - e.t
        if t != 0:
            return t if self.s > 0 else -t
        for n in range(self.t - 1, -1, -1):
            if self.E[n] - e.E[n] != 0:
                return self.E[n] - e.E[n]
        return 0

    def subTo(self, e, t):
        n, r, o = 0, 0, np.min([e.t, self.t])
        while n < o:
            r += self.E[n] - e.E[n]
            t.E[n] = r & DM
            n += 1
            r = r >> DM
        if e.t < self.t:
            r -= e.s
            while n < self.t:
                r += self.E[n]
                t.E[n] = r & DM
                n += 1
                r = r >> DM
            r += self.s
        else:
            r += self.s
            while n < e.t:
                r -= e.E[n]
                t.E[n] = r & DM
                n += 1
                r = r >> DM
            r -= e.s
        t.s = -1 if r < 0 else 0
        if r < -1 or r > 0:
            t.E[n] = DV + r if r < -1 else r
            n += 1
        t.t = n
        t.clamp()

    def one(self):
        self.E[0] = 1
        self.t = 1

    def am(self, e: int, t: int, n, r: int, o: int, i: int):
        a = 16383 & t
        s = t >> 14
        i -= 1
        while 0 <= i:
            c = 16383 & self.E[e]
            u = self.E[e] >> 14
            e += 1
            uu = s * c + u * a
            c = a * c + ((16383 & uu) << 14) + n.E[r] + o
            o = (c >> 28) + (uu >> 14) + s * u
            n.E[r] = DM & c
            r += 1
            i -= 1
        return o

    def sqrTo(self, e, t):
        e.squareTo(t)
        self.reduceE(t)

    def squareTo(self, e):
        e.t = 2 * self.t
        for n in range(e.t):
            e.E[n] = 0
        for n in range(self.t - 1):
            r = self.am(n, self.E[n], e, 2 * n, 0, 1)
            e.E[n + self.t] += self.am(n + 1, 2 * self.E[n],
                                       e, 2 * n + 1, r, self.t - n - 1)
            if e.E[n + self.t] >= DV:
                e.E[n + self.t] -= DV
                e.E[n + self.t + 1] = 1
        if e.t > 0:
            e.E[e.t - 1] += self.am(n, self.E[n], e, 2 * n, 0, 1)
        e.s = 0
        e.clamp()

    def reduceE(self, e):
        while e.t <= self.T['mt2']:
            e.E[e.t] = 0
            e.t += 1
        for t in range(self.T['m'].t):
            n = 32767 & e.E[t]
            r = (n * self.T['mpl'] + (n * self.T['mph'] + (e.E[t] >> 15)
                                      * self.T['mpl'] & self.T['um']) << 15) & DM
            n = t + self.T['m'].t
            e.E[n] += self.T['m'].am(0, r, e, t, 0, self.T['m'].t)
            while e.E[n] >= DV:
                e.E[n] -= DV
                n += 1
                e.E[n] += 1
        e.clamp()
        e.drShiftTo(self.T['m'].t, e)
        if e.compareTo(self.T['m']) >= 0:
            e.subTo(self.T['m'], e)

    def drShiftTo(self, e: int, t):
        for n in range(e, self.t):
            t.E[n - e] = self.E[n]
        t.t = np.max([self.t - e, 0])
        t.s = self.s

    def mulTo(self, e, t, n):
        e.multiplyTo(t, n)
        self.reduceE(n)

    def multiplyTo(self, e, t):
        t.t = self.t + e.t
        for o in range(self.t):
            t.E[o] = 0
        for o in range(e.t):
            t.E[o + self.t] = self.am(0, e.E[o], t, o, 0, self.t)
        t.s = 0
        t.clamp()
        if self.s != e.s:
            E().subTo(t, t)

    def isEven(self):
        t = 1 & self.E[0] if self.t else self.s
        return t == 0

    def abs(self):
        return self if self.s > 0 else self

    def tostring(self, e: int):
        if self.s < 0:
            echo('0|warning', '.s < 0', self.s)
            return '-'
        t = int(np.log2(e))
        r, o, i, a = (1 << t) - 1, False, '', self.t
        s = DB - a * DB % t
        if a > 0:
            if s < DB:
                n = self.E[a] >> s
                if n > 0:
                    o = True
                    i = g[n]
            a -= 1
            while a >= 0:
                if s < t:
                    n = (self.E[a] & (1 << s) - 1) << t - s
                    a -= 1
                    s += DB - t
                    n = n | (self.E[a] >> s)
                else:
                    s -= t
                    n = self.E[a] >> s & r
                    if s <= 0:
                        s += DB
                        a -= 1
                if n > 0:
                    o = True
                if o:
                    i += g[n]
        return i if o else '0'


class BrowserStyle(object):
    def __init__(self):
        self.n = {
            'A': 48,
            'BUTTON': 1,
            'CANVAS': 1,
            'CPUClass': None,
            'DIV': 71,
            'HTMLLength': 158225,
            'IMG': 5,
            'INPUT': 4,
            'LABEL': 1,
            'LI': 21,
            'LINK': 3,
            'P': 10,
            'SCRIPT': 14,
            'SPAN': 9,
            'STYLE': 18,
            'UL': 4,
            'browserLanguage': "zh-CN",
            'browserLanguages': "zh-CN,zh",
            'canvas2DFP': "5eb3d9a167292cc324a4a6b692171a49",
            'canvas3DFP': "b2284dba7b1ccb5ef8fabc22c0065611",
            'colorDepth': 24,
            'cookieEnabled': 1,
            'devicePixelRatio': 2,
            'deviceorientation': False,
            'doNotTrack': 0,
            'documentMode': "CSS1Compat",
            'flashEnabled': -1,
            'hardwareConcurrency': 8,
            'indexedDBEnabled': 1,
            'innerHeight': 150,
            'innerWidth': 1680,
            'internalip': None,
            'javaEnabled': 0,
            'jsFonts': "AndaleMono,Arial,ArialBlack,ArialHebrew,ArialNarrow,ArialRoundedMTBold,ArialUnicodeMS,ComicSansMS,Courier,CourierNew,Geneva,Georgia,Helvetica,HelveticaNeue,Impact,LUCIDAGRANDE,MicrosoftSansSerif,Monaco,Palatino,Tahoma,Times,TimesNewRoman,TrebuchetMS,Verdana,Wingdings,Wingdings2,Wingdings3",
            'localStorageEnabled': 1,
            'maxTouchPoints': 0,
            'mediaDevices': -1,
            'netEnabled': 1,
            'outerHeight': 987,
            'outerWidth': 1680,
            'performanceTiming': "-1,-1,16,2,122,0,274,0,209,137,6,6,32,3405,3405,3408,35543,35544,35547,-1",
            'platform': "MacIntel",
            'plugins': "internal-pdf-viewer,mhjfbmdgcfjbbpaeojofohoefgiehjai,internal-nacl-plugin",
            'screenAvailHeight': 987,
            'screenAvailLeft': 0,
            'screenAvailTop': 23,
            'screenAvailWidth': 1680,
            'screenHeight': 1050,
            'screenLeft': 0,
            'screenTop': 23,
            'screenWidth': 1680,
            'sessionStorageEnabled': 1,
            'systemLanguage': None,
            'textLength': 93737,
            'timestamp': int(time.time()),
            'timezone': -8,
            'touchEvent': False,
            'userAgent': "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3818.0 Safari/537.36",
        }
        self.t = ['textLength', 'HTMLLength', 'documentMode', 'A', 'ARTICLE', 'ASIDE', 'AUDIO', 'BASE', 'BUTTON', 'CANVAS', 'CODE', 'IFRAME', 'IMG', 'INPUT', 'LABEL', 'LINK', 'NAV', 'OBJECT', 'OL', 'PICTURE', 'PRE', 'SECTION', 'SELECT', 'SOURCE', 'SPAN', 'STYLE', 'TABLE', 'TEXTAREA', 'VIDEO', 'screenLeft', 'screenTop', 'screenAvailLeft', 'screenAvailTop', 'innerWidth', 'innerHeight', 'outerWidth', 'outerHeight', 'browserLanguage', 'browserLanguages', 'systemLanguage', 'devicePixelRatio', 'colorDepth',
                  'userAgent', 'cookieEnabled', 'netEnabled', 'screenWidth', 'screenHeight', 'screenAvailWidth', 'screenAvailHeight', 'localStorageEnabled', 'sessionStorageEnabled', 'indexedDBEnabled', 'CPUClass', 'platform', 'doNotTrack', 'timezone', 'canvas2DFP', 'canvas3DFP', 'plugins', 'maxTouchPoints', 'flashEnabled', 'javaEnabled', 'hardwareConcurrency', 'jsFonts', 'timestamp', 'performanceTiming', 'internalip', 'mediaDevices', 'DIV', 'P', 'UL', 'LI', 'SCRIPT', 'deviceorientation', 'touchEvent']

    def get_performanceTiming(self):
        r = ['navigationStart', 'redirectStart', 'redirectEnd', 'fetchStart', 'domainLookupStart',
             'domainLookupEnd', 'connectStart', 'connectEnd', 'requestStart', 'responseStart']
        o = ['responseEnd', 'unloadEventStart', 'unloadEventEnd', 'domLoading', 'domInteractive', 'domContentLoadedEventStart',
             'domContentLoadedEventEnd', 'domComplete', 'loadEventStart', 'loadEventEnd', 'msFirstPaint']
        n = {
            'connectEnd': 1568518372487,
            'connectStart': 1568518372213,
            'domComplete': 1568518408239,
            'domContentLoadedEventEnd': 1568518376104,
            'domContentLoadedEventStart': 1568518376101,
            'domInteractive': 1568518376101,
            'domLoading': 1568518372728,
            'domainLookupEnd': 1568518372213,
            'domainLookupStart': 1568518372091,
            'fetchStart': 1568518372089,
            'loadEventEnd': 1568518408243,
            'loadEventStart': 1568518408240,
            'navigationStart': 1568518372073,
            'redirectEnd': 0,
            'redirectStart': 0,
            'requestStart': 1568518372487,
            'responseEnd': 1568518372833,
            'responseStart': 1568518372696,
            'secureConnectionStart': 1568518372348,
            'unloadEventEnd': 1568518372702,
            'unloadEventStart': 1568518372702,
        }
        i = []
        for e in range(1, len(r)):
            a = n[r[e]]
            if a == 0:
                i.append(-1)
            else:
                for s in range(e - 1, -1, -1):
                    c = n[r[s]]
                    if c:
                        i.append(a - c)
                        break
        u = n[r[len(r) - 1]]
        for e in o:
            if e in n and n[e]:
                i.append(n[e] - u)
            else:
                i.append(-1)
        self.n['performanceTiming'] = ','.join([str(ii) for ii in i])

    def __call__(self):
        self.get_performanceTiming()
        self.r = [self.n[ii] if ii in self.n else -1 for ii in self.t]
        return '!!'.join([str(ii) for ii in self.r]).replace('False', 'false').replace('True', 'true')
