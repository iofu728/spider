# -*- coding: utf-8 -*-
# @Author: gunjianpan
# @Date:   2019-03-26 10:21:05
# @Last Modified by:   gunjianpan
# @Last Modified time: 2019-03-27 23:41:36
import asyncio
import aiohttp
import json
import logging
import struct
import time

from collections import namedtuple
from enum import IntEnum
from ssl import _create_unverified_context
from proxy.getproxy import GetFreeProxy
from utils.utils import can_retry

logger = logging.getLogger(__name__)
get_request_proxy = GetFreeProxy().get_request_proxy
data_path = 'bilibili/data/'
yybzz_path = 'bilibili/yybzz/'
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


class BWebsocketClient:
    """
    bilibili websocket client
    """
    ROOM_INIT_URL = 'https://www.bilibili.com/video/av%d'
    WEBSOCKET_URL = 'wss://broadcast.chat.bilibili.com:7823/sub'
    HEARTBEAT_BODY = '[object Object]'

    HEADER_STRUCT = struct.Struct('>I2H2IH')
    HeaderTuple = namedtuple(
        'HeaderTuple', ('total_len', 'header_len', 'proto_ver', 'operation', 'time', 'zero'))
    _COMMAND_HANDLERS = {
        'DM': lambda client, command: client._on_get_danmaku(
            command['info'][1], command['info'][0]
        )
    }

    def __init__(self, av_id, types=0, ssl=True, loop=None, session: aiohttp.ClientSession=None):
        """
        :param room_id: av -> room_id get from html
        :param ssl: SSL Test
        :param loop: loop or not
        :param session: cookie
        """
        self._av_id = av_id
        self._room_id = None
        self.count = 1
        self.types = types
        self.begin_time = int(time.time())

        if loop is not None:
            self._loop = loop
        elif session is not None:
            self._loop = session.loop
        else:
            self._loop = asyncio.get_event_loop()
        self._is_running = False

        if session is None:
            self._session = aiohttp.ClientSession(loop=self._loop)
            self._own_session = True
        else:
            self._session = session
            self._own_session = False
            if self._session.loop is not self._loop:
                raise RuntimeError(
                    'BLiveClient and session has to use same event loop')
        self._ssl = ssl if ssl else _create_unverified_context()
        self._websocket = None
        self._get_room_id()

    @property
    def is_running(self):
        return self._is_running

    async def close(self):
        """
        close session when session is owner
        """
        if self._own_session:
            await self._session.close()

    def run(self):
        """
        Create Thread
        """
        if self._is_running:
            raise RuntimeError('This client is already running')
        self._is_running = True
        return asyncio.ensure_future(self._message_loop(), loop=self._loop)

    def _get_room_id(self, next_to=True):
        url = self.ROOM_INIT_URL % self._av_id
        html = get_request_proxy(url, 0)
        head = html.find_all('head')
        if not len(head) or len(head[0].find_all('script')) < 4 or not '{' in head[0].find_all('script')[3].text:
            if can_retry(url):
                self._get_room_id()
            next_to = False
        if next_to:
            script_list = head[0].find_all('script')[3].text
            script_begin = script_list.index('{')
            script_end = script_list.index(';')
            script_data = script_list[script_begin:script_end]
            json_data = json.loads(script_data)
            self._room_id = json_data['videoData']['cid']
            print('Room_id:', self._room_id)

    def _make_packet(self, data, operation):
        if operation == 7:
            body = json.dumps(data).replace(" ", '').encode('utf-8')
        else:
            body = self.HEARTBEAT_BODY.encode('utf-8')
        header = self.HEADER_STRUCT.pack(
            self.HEADER_STRUCT.size + len(body),
            self.HEADER_STRUCT.size,
            1,
            operation,
            self.count,
            0
        )
        self.count += 1
        # print(header + body)
        return header + body

    async def _send_auth(self):
        auth_params = {
            'room_id': 'video://%d/%d' % (self._av_id, self._room_id),
            "platform": "web",
            "accepts": [1000]
        }
        await self._websocket.send_bytes(self._make_packet(auth_params, Operation.AUTH))

    async def _message_loop(self):

        if self._room_id is None:
            self._get_room_id()

        while True:
            heartbeat_future = None
            try:
                async with self._session.ws_connect(self.WEBSOCKET_URL,
                                                    ssl=self._ssl) as websocket:
                    self._websocket = websocket
                    await self._send_auth()
                    heartbeat_future = asyncio.ensure_future(
                        self._heartbeat_loop(), loop=self._loop)

                    async for message in websocket:  # type: aiohttp.WSMessage
                        # print(message.data)
                        if message.type == aiohttp.WSMsgType.BINARY:
                            await self._handle_message(message.data)
                        else:
                            logger.warning(
                                'Unknown Message type = %s %s', message.type, message.data)

            except asyncio.CancelledError:
                break
            except aiohttp.ClientConnectorError:
                # retry
                logger.warning('Retrying */*/*/*/---')
                try:
                    await asyncio.sleep(5)
                except asyncio.CancelledError:
                    break
            finally:
                if heartbeat_future is not None:
                    heartbeat_future.cancel()
                    try:
                        await heartbeat_future
                    except asyncio.CancelledError:
                        break
                self._websocket = None

        self._is_running = False

    async def _heartbeat_loop(self):
        """
        heart beat
        """
        if self.types and int(time.time()) > self.begin_time + one_day:
            self.close()
        while True:
            try:
                await self._websocket.send_bytes(self._make_packet({}, Operation.SEND_HEARTBEAT))
                await asyncio.sleep(30)

            except (asyncio.CancelledError, aiohttp.ClientConnectorError):
                break

    async def _handle_message(self, message):
        offset = 0
        while offset < len(message):
            try:
                header = self.HeaderTuple(
                    *self.HEADER_STRUCT.unpack_from(message, offset))
            except struct.error:
                break

            if header.operation == Operation.ONLINE or header.operation == Operation.COMMAND:
                body = message[offset +
                               self.HEADER_STRUCT.size: offset + header.total_len]
                body = json.loads(body.decode('utf-8'))
                if header.operation == Operation.ONLINE:
                    await self._on_get_online(body)
                else:
                    await self._handle_command(body)
            elif header.operation == Operation.RECV:
                print('Connect Build!!!')
            else:
                body = message[offset +
                               self.HEADER_STRUCT.size: offset + header.total_len]
                logger.warning('Unknow operation = %d %s %s',
                               header.operation, header, body)

            offset += header.total_len

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
            logger.warning('Unknow Command = %s %s', cmd, command)

    async def _on_get_online(self, online):
        """
        get online num
        @param online
        @param av_id
        """
        pass

    async def _on_get_danmaku(self, content, user_name):
        """
        get danmaku
        @param content
        @param user_name
        """
        pass


class OneBWebsocketClient(BWebsocketClient):
    """
    get one bilibili websocket client
    """

    async def _on_get_online(self, online):
        online = online['data']['room']['online']
        data = [time.strftime("%Y-%m-%d %H:%M:%S",
                              time.localtime(time.time())), online]
        path = '%s%d_online.csv' % (
            data_path if self.types else yybzz_path, self._av_id)
        # print(path, self.types, yybzz_path, data_path)
        with open(path, 'a') as f:
            f.write(",".join([str(ii) for ii in data]) + '\n')
        print(f'Online: {online}')

    async def _on_get_danmaku(self, content, user_name):
        data = [time.strftime("%Y-%m-%d %H:%M:%S",
                              time.localtime(time.time())), content, user_name]
        path = '%s%d_danmaku.csv' % (
            data_path if self.types else yybzz_path, self._av_id)
        with open(path, 'a') as f:
            f.write(",".join([str(ii) for ii in data]) + '\n')
        print(f'{content}：{user_name}')


async def async_main(av_id):
    client = OneBWebsocketClient(av_id, ssl=True)
    future = client.run()
    try:
        await future
    finally:
        await client.close()


def BSocket(av_id):
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(async_main(av_id))
    finally:
        loop.close()


if __name__ == '__main__':
    BSocket(47045876)
    BSocket(46412322)
