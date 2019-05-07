# -*- coding: utf-8 -*-
# @Author: gunjianpan
# @Date:   2019-05-07 00:20:48
# @Last Modified by:   gunjianpan
# @Last Modified time: 2019-05-07 22:34:22

import js2py
import re

from util.util import basic_req, echo

"""
  * 66ip @http
    js decoder
"""

IP66_URL = 'http://www.66ip.cn/'
PRE_URL = '{}favicon.ico'.format(IP66_URL)

header = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3',
    'Host': 'www.66ip.cn',
    'Referer': 'http://www.66ip.cn/',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3785.0 Safari/537.36'
}


def generate_cookie():
    ''' eval 66ip.cn test in 19.5.7 '''
    req = basic_req(IP66_URL, 2, header=header)
    basic_cookie = req.cookies.get_dict()

    ''' !important \b in py -> \x80 '''
    req_text = r'{}'.format(req.text)

    ''' get the script will be eval '''
    script_text = re.findall('<script>(.*?)</script>', req_text)[0]
    script_text = script_text.replace(
        '{eval(', '{aaa=').replace(');break', ';break')
    script_eval = r'{}'.format(js2py.eval_js(script_text + 'aaa'))
    echo(0, script_eval)

    try:
        ''' replace document & window '''
        params = re.findall(
            r'(__jsl_clearance=.*?)\'\+\(function\(\){(.*?join\(\'\'\))}\)\(\)', script_eval)
        wait_eval = params[0][1].replace(
            "document.createElement('div')", "{}").replace("", '')
        wait_replace = re.findall(
            r'=(.{1,5}\.firstChild\.href;)', wait_eval)[0]
        wait_eval = wait_eval.replace(wait_replace, '"http://www.66ip.cn/";')

        ''' eval & encoder cookie '''
        other_param = js2py.eval_js(
            'function ddd() {window={};' + wait_eval + '}ddd()')
        cookie = '{}; {}{}'.format(encoder_cookie(
            basic_cookie), params[0][0], other_param)
        echo(1, 'cookie', cookie)

        return cookie
    except:
        generate_cookie()


def encoder_cookie(cookie_dict: {}) -> str:
    return '; '.join(['{}={}'.format(ii, jj)for ii, jj in cookie_dict.items()])


def req_ip66():
    ''' 66ip.cn js decoder '''
    header['Cookie'] = generate_cookie()

    req_text = basic_req(IP66_URL, 3, header=header)
    echo(2, req_text)
    return req_text


if __name__ == "__main__":
    req_ip66()
