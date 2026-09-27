"""EventSub chat client; unexpected disconnects intentionally require Start."""
import asyncio
import json
import time
from contextlib import suppress
from src.core.models import AppError
from src.adapters.twitch_protocol import SeenMessages, validate_reconnect_url, protocol_error

HELIX = 'https://api.twitch.tv/helix'
WS = 'wss://eventsub.wss.twitch.tv/ws'


class TwitchAdapter:
    def __init__(self, channel, auth, http, ws_connect, *, clock=time.monotonic):
        self.channel, self.auth, self.http, self.ws_connect = channel, auth, http, ws_connect
        self.clock = clock
        self.seen = SeenMessages(clock=clock)
        self._sockets = set()
        self._child = None
        self._stopped = False
        self._channel_id = None

    def _http_error(self, response):
        if response.status_code == 401:
            raise AppError('twitch_auth_required', 'Połącz ponownie konto Twitch.')
        if response.status_code == 403:
            raise AppError('twitch_forbidden', 'Brak dostępu do czatu Twitcha. Sprawdź uprawnienia konta lub blokadę na kanale.')
        raise AppError('connection_error', 'Nie można połączyć się z Twitchem. Sprawdź sieć i spróbuj ponownie.')

    async def _receive(self, ws, timeout):
        raw = await asyncio.wait_for(ws.recv(), timeout)
        try:
            data = json.loads(raw)
            if not isinstance(data,dict) or not isinstance(data.get('metadata'),dict) or not isinstance(data.get('payload'),dict) or not isinstance(data['metadata'].get('message_type'),str):
                raise ValueError()
            return data
        except (TypeError, ValueError):
            raise protocol_error() from None

    async def _open(self, url):
        ws = await self.ws_connect(url, open_timeout=10, close_timeout=1, max_size=1024*1024, max_queue=32, ping_interval=None)
        self._sockets.add(ws)
        data = await self._receive(ws,10)
        try:
            session = data['payload']['session']
            if data['metadata']['message_type'] != 'session_welcome' or not isinstance(session['id'],str) or not session['id'] or not 0 < float(session['keepalive_timeout_seconds']) <= 600:
                raise ValueError()
            return ws, session
        except (KeyError, TypeError, ValueError):
            raise protocol_error() from None

    async def connect(self, on_comment):
        try:
            credentials = await self.auth.credentials()
            headers = {'Client-Id':credentials.client_id,'Authorization':'Bearer '+credentials.access_token}
            response = await self.http.get(HELIX+'/users',params={'login':self.channel},headers=headers,timeout=10)
            if response.status_code != 200:
                self._http_error(response)
            users = response.json()['data']
            if not users:
                raise AppError('streamer_not_found','Nie znaleziono kanału Twitch.')
            self._channel_id = users[0]['id']
            ws, session = await self._open(WS)
            async with asyncio.timeout(10):
                response = await self.http.post(HELIX+'/eventsub/subscriptions',headers=headers,json={
                    'type':'channel.chat.message','version':'1',
                    'condition':{'broadcaster_user_id':self._channel_id,'user_id':credentials.user_id},
                    'transport':{'method':'websocket','session_id':session['id']}
                },timeout=9)
            if response.status_code != 202:
                self._http_error(response)
            self._child=asyncio.create_task(self._run(ws,session,on_comment))
            return self._child
        except BaseException as exc:
            await self.disconnect()
            if isinstance(exc,(asyncio.CancelledError,AppError)):
                raise
            raise AppError('connection_error','Nie można połączyć się z Twitchem. Sprawdź kanał i sieć.') from None

    async def _notification(self, data, callback):
        try:
            payload = data['payload']
            if payload['subscription']['type'] != 'channel.chat.message':
                return
            event = payload['event']
            if event['broadcaster_user_id'] != self._channel_id:
                return
            if event.get('source_broadcaster_user_id') not in (None, self._channel_id):
                return
            user, text = event['chatter_user_login'], event['message']['text']
            event_id, message_id = data['metadata']['message_id'], event['message_id']
            if not all(isinstance(x,str) and x for x in (user,event_id,message_id)) or not isinstance(text,str):
                raise ValueError()
        except (KeyError, TypeError, ValueError):
            raise protocol_error() from None
        if self.seen.accept(event_id,message_id) and not self._stopped:
            await callback(user.lower(),text)

    async def _run(self, ws, session, callback):
        read = handoff = None
        timeout = float(session['keepalive_timeout_seconds'])
        deadline = self.clock()+timeout
        try:
            while not self._stopped:
                if read is None:
                    read=asyncio.create_task(self._receive(ws,max(.001,deadline-self.clock())))
                pending=[read] + ([handoff] if handoff else [])
                done,_=await asyncio.wait(pending,return_when=asyncio.FIRST_COMPLETED)
                if read in done:
                    data=await read
                    read=None
                    kind=data['metadata']['message_type']
                    if kind in ('notification','session_keepalive'):
                        deadline=self.clock()+timeout
                    if kind=='notification':
                        await self._notification(data,callback)
                    elif kind=='revocation':
                        raise AppError('twitch_auth_required','Twitch cofnął dostęp do czatu. Połącz konto ponownie.')
                    elif kind=='session_reconnect' and handoff is None:
                        url=validate_reconnect_url(data['payload']['session']['reconnect_url'])
                        handoff=asyncio.create_task(self._open(url))
                if handoff and handoff in done:
                    new_ws,new_session=await handoff
                    handoff=None
                    if read:
                        read.cancel(); await asyncio.gather(read,return_exceptions=True); read=None
                    old_ws=ws
                    ws,session=new_ws,new_session
                    timeout=float(session['keepalive_timeout_seconds'])
                    deadline=self.clock()+timeout
                    await old_ws.close()
                    self._sockets.discard(old_ws)
        except asyncio.CancelledError:
            raise
        except AppError:
            raise
        except (KeyError,TypeError,ValueError):
            raise protocol_error() from None
        except Exception:
            raise AppError('connection_lost','Połączenie z Twitchem zostało przerwane. Uruchom nasłuch ponownie.') from None
        finally:
            for task in (read,handoff):
                if task:
                    task.cancel()
            await asyncio.gather(*(t for t in (read,handoff) if t),return_exceptions=True)

    async def disconnect(self):
        self._stopped=True
        if self._child and self._child is not asyncio.current_task():
            self._child.cancel()
            await asyncio.gather(self._child,return_exceptions=True)
        sockets=tuple(self._sockets)
        self._sockets.clear()
        async def close(ws):
            with suppress(Exception):
                await asyncio.wait_for(ws.close(),1)
        await asyncio.gather(*(close(ws) for ws in sockets))
