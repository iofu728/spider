# -*- coding: utf-8 -*-
# @Author: gunjianpan
# @Date:   2019-03-26 10:21:05
# @Last Modified by:   gunjianpan
# @Last Modified time: 2020-03-23 23:42:04


import asyncio
import codecs
import json
import logging
import os
import shutil
import struct
import sys
import time
from collections import namedtuple
from configparser import ConfigParser
from enum import IntEnum
from ssl import _create_unverified_context

import aiohttp
import regex

sys.path.append(os.getcwd())
from proxy.getproxy import GetFreeProxy
from util.util import basic_req, can_retry, echo, mkdir, time_stamp, time_str

logger = logging.getLogger(__name__)
proxy_req = GetFreeProxy().proxy_req
data_dir = 'bilibili/data/'
websocket_dir = '%swebsocket/' % data_dir
assign_path = 'bilibili/assign_up.ini'
one_day = 86400

"""
  * bilibili @websocket
  * www.bilibili.com/video/av{av_id}
  * wss://broadcast.chat.bilibili.com:7823/sub
"""


class Operation(IntEnum):
    SEND_HEARTBEAT = 2
    ONLINE = 3
    COMMAND = 5
    AUTH = 7
    RECV = 8
    NESTED = 9
    DANMAKU = 1000


class BWebsocketClient:
    ''' bilibili websocket client '''
    ROOM_INIT_URL = 'https://www.bilibili.com/video/av%d'
    WEBSOCKET_URL = 'wss://broadcast.chat.bilibili.com:7823/sub'
    PLAYLIST_URL = 'https://api.bilibili.com/x/player/pagelist?aid=%d&jsonp=jsonp'
    HEARTBEAT_BODY = '[object Object]'
    JSON_KEYS = ['code', 'message', 'ttl', 'data']

    HEADER_STRUCT = struct.Struct('>I2H2IH')
    HeaderTuple = namedtuple(
        'HeaderTuple', ('total_len', 'header_len', 'proto_ver', 'operation', 'time', 'zero'))
    _COMMAND_HANDLERS = {
        'DM': lambda client, command: client._on_get_danmaku(command['info'][1], command['info'][0])
    }

    def __init__(self, av_id: int, types=0, p: int = -1):
        ''' init class '''
        self._av_id = av_id
        self._room_id = None
        self._count = 1
        self._types = types
        self._begin_time = int(time_stamp())
        self._loop = asyncio.get_event_loop()
        self._session = aiohttp.ClientSession(loop=self._loop)
        self._is_running = False
        self._websocket = None
        self._p = p if p > 0 else 1
        self._getroom_id()

    async def close(self):
        await self._session.close()

    def run(self):
        ''' Create Thread '''
        if self._is_running:
            raise RuntimeError('This client is already running')
        self._is_running = True
        return asyncio.ensure_future(self._message_loop(), loop=self._loop)

    def get_cid(self, av_id: int):
        playlist_url = self.PLAYLIST_URL % av_id
        headers = {
            'Accept': '*/*',
            'Referer': self.ROOM_INIT_URL % av_id
        }
        req = proxy_req(playlist_url, 1, header=headers)
        if req is None or list(req.keys()) != self.JSON_KEYS:
            if can_retry(playlist_url):
                return self.get_cid(av_id)
            else:
                return
        cid = [ii['cid'] for ii in req['data']]
        return cid

    def _getroom_id(self, proxy: bool = True):
        ''' get av room id '''
        cid = self.get_cid(self._av_id)
        assert len(cid) >= self._p, 'Actual Page len: {} <=> Need Pages Num: {}'.format(
            len(cid), self._p)
        self._room_id = int(cid[self._p - 1])
        echo(3, 'Room_id:', self._room_id)

    def parse_struct(self, data: dict, operation: int):
        ''' parse struct '''
        assert int(time_stamp()) < self._begin_time + \
            7 * one_day, 'Excess Max RunTime!!!'

        if operation == 7:
            body = json.dumps(data).replace(" ", '').encode('utf-8')
        else:
            body = self.HEARTBEAT_BODY.encode('utf-8')
        header = self.HEADER_STRUCT.pack(
            self.HEADER_STRUCT.size + len(body),
            self.HEADER_STRUCT.size,
            1,
            operation,
            self._count,
            0
        )
        self._count += 1
        return header + body

    async def _send_auth(self):
        ''' send auth '''
        auth_params = {
            'room_id': 'video://%d/%d' % (self._av_id, self._room_id),
            "platform": "web",
            "accepts": [1000]
        }
        await self._websocket.send_bytes(self.parse_struct(auth_params, Operation.AUTH))

    async def _message_loop(self):
        ''' loop sent message '''

        if self._room_id is None:
            self._getroom_id()

        while True:
            heartbeat_con = None
            try:
                async with self._session.ws_connect(self.WEBSOCKET_URL) as websocket:
                    self._websocket = websocket
                    await self._send_auth()
                    heartbeat_con = asyncio.ensure_future(
                        self._heartbeat_loop(), loop=self._loop)

                    async for message in websocket:
                        if message.type == aiohttp.WSMsgType.BINARY:
                            await self._handle_message(message.data, 0)
                        else:
                            logger.warning(
                                'Unknown Message type = %s %s', message.type, message.data)

            except asyncio.CancelledError:
                break
            except aiohttp.ClientConnectorError:
                logger.warning('Retrying */*/*/*/---')
                try:
                    await asyncio.sleep(5)
                except asyncio.CancelledError:
                    break
            finally:
                if heartbeat_con is not None:
                    heartbeat_con.cancel()
                    try:
                        await heartbeat_con
                    except asyncio.CancelledError:
                        break
                self._websocket = None

        self._is_running = False

    async def _heartbeat_loop(self):
        ''' heart beat every 30s '''
        if self._types and int(time_stamp()) > self._begin_time + one_day:
            self.close()
        for _ in range(int(one_day * 7 / 30)):
            try:
                await self._websocket.send_bytes(self.parse_struct({}, Operation.SEND_HEARTBEAT))
                await asyncio.sleep(30)
            except (asyncio.CancelledError, aiohttp.ClientConnectorError):
                break

    async def _handle_message(self, message: str, offset: int = 0):
        ''' handle message'''
        while offset < len(message):
            try:
                header = self.HeaderTuple(
                    *self.HEADER_STRUCT.unpack_from(message, offset))
                body = message[offset +
                               self.HEADER_STRUCT.size: offset + header.total_len]
                if header.operation == Operation.ONLINE or header.operation == Operation.COMMAND:
                    body = json.loads(body.decode('utf-8'))
                    if header.operation == Operation.ONLINE:
                        await self._on_get_online(body)
                    else:
                        await self._handle_command(body)
                elif header.operation == Operation.RECV:
                    print('Connect Build!!!')
                elif header.operation == Operation.NESTED:
                    offset += self.HEADER_STRUCT.size
                    continue
                elif header.operation == Operation.DANMAKU:
                    body = json.loads(body.decode('utf-8'))
                    print(body)
                    print('>>>>DANMAKU tail socket>>>>')
                else:
                    logger.warning('Unknown operation = %d %s %s',
                                   header.operation, header, body)
                offset += header.total_len
            except:
                pass

    async def _handle_command(self, command):
        if isinstance(command, list):
            for one_command in command:
                await self._handle_command(one_command)
            return

        cmd = command['cmd']
        if cmd in self._COMMAND_HANDLERS:
            handler = self._COMMAND_HANDLERS[cmd]
            if handler is not None:
                await handler(self, command)
        else:
            logger.warning('Unknown Command = %s %s', cmd, command)

    async def _on_get_online(self, online):
        ''' get online num '''
        pass

    async def _on_get_danmaku(self, content, user_name):
        ''' get danmaku '''
        pass


class OneBWebsocketClient(BWebsocketClient):
    ''' get one bilibili websocket client '''

    async def _on_get_online(self, online):
        online = online['data']['room']['online']
        with codecs.open(self.get_path('online'), 'a', encoding='utf-8') as f:
            f.write(self.get_data([online]))
        print('Online:', online)

    async def _on_get_danmaku(self, content, user_name):
        with codecs.open(self.get_path('danmaku'), 'a', encoding='utf-8') as f:
            f.write(self.get_data([content, user_name]))
        print(content, user_name)

    def get_data(self, origin_data: list) -> str:
        ''' get data '''
        return ','.join(str(ii) for ii in [time_str(), *origin_data]) + '\n'

    def get_path(self, types: str) -> str:
        ''' get path '''
        p_path = '_p%d' % self._p if self._p != -1 else ''
        return '%s%d_%s%s.csv' % (websocket_dir, self._av_id, types, p_path)


async def async_main(av_id: int, types: int, p: int):
    client = OneBWebsocketClient(av_id, types, p=p)
    future = client.run()
    try:
        await future
    finally:
        await client.close()


def BSocket(av_id: int, types: int = 0, p: int = -1):
    ''' build a loop websocket connect'''
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(async_main(av_id, types, p))
    finally:
        loop.close()


if __name__ == '__main__':
    mkdir(data_dir)
    mkdir(websocket_dir)
    if not os.path.exists(assign_path):
        shutil.copy(assign_path + '.tmp', assign_path)

    ''' Test for San Diego demon '''
    ''' PS: the thread of BSocket have to be currentThread in its processing. '''
    if len(sys.argv) == 3:
        av_id = int(sys.argv[1])
        p = int(sys.argv[2])
    else:
        cfg = ConfigParser()
        cfg.read(assign_path, 'utf-8')
        av_id = cfg.getint('basic', 'av_id')
        p = cfg.getint('basic', 'basic_av_p') if len(
            cfg['basic']['basic_av_p']) else -1

    BSocket(av_id, p=p)
