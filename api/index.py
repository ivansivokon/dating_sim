import json
import asyncio
import uuid
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse

from ._lib.kv import get_state, save_state, default_girls
from ._lib.ai import generate_response

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        """Обрабатываем POST-запросы."""
        path = urlparse(self.path).path
        content_length = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(content_length)) if content_length else {}

        if path == '/api/register':
            self._handle_register(body)
        elif path == '/api/login':
            self._handle_login(body)
        elif path == '/api/start-dialogue':
            self._handle_start_dialogue(body)
        elif path == '/api/send-message':
            self._handle_send_message(body)
        elif path == '/api/leave-dialogue':
            self._handle_leave_dialogue(body)
        elif path == '/api/move':
            self._handle_move(body)
        else:
            self.send_error(404)

    def do_GET(self):
        """GET только для /api/state."""
        if urlparse(self.path).path == '/api/state':
            self._handle_get_state()
        else:
            self.send_error(404)

    # -------- Обработчики --------
    def _handle_register(self, body):
        username = body.get('username')
        password = body.get('password')
        if not username or not password:
            return self._send_json({'error': 'Missing fields'}, 400)

        async def main():
            state = await get_state()
            if any(p['username'] == username for p in state['players']):
                return {'error': 'Username exists'}
            player_id = str(uuid.uuid4())
            import random
            new_player = {
                'id': player_id,
                'username': username,
                'password': password,
                'currentLocation': random.choice(['School', 'Park', 'Cafe']),
                'relationships': {}
            }
            state['players'].append(new_player)
            await save_state(state)
            return {'playerId': player_id}
        res = asyncio.run(main())
        self._send_json(res, 200 if 'playerId' in res else 400)

    def _handle_login(self, body):
        username = body.get('username')
        password = body.get('password')
        async def main():
            state = await get_state()
            for p in state['players']:
                if p['username'] == username and p['password'] == password:
                    return {'playerId': p['id']}
            return {'error': 'Invalid credentials'}
        res = asyncio.run(main())
        self._send_json(res, 200 if 'playerId' in res else 401)

    def _handle_get_state(self):
        async def main():
            state = await get_state()
            # убираем пароли
            safe_players = [{k:v for k,v in p.items() if k != 'password'} for p in state['players']]
            return {
                'players': safe_players,
                'girls': state['girls'],
                'active_dialogues': state['active_dialogues'],
                'locations': ['School', 'Park', 'Cafe']
            }
        res = asyncio.run(main())
        self._send_json(res)

    def _handle_start_dialogue(self, body):
        player_id = body['playerId']
        girl_id = body['girlId']
        async def main():
            state = await get_state()
            player = next((p for p in state['players'] if p['id'] == player_id), None)
            girl = next((g for g in state['girls'] if g['id'] == girl_id), None)
            if not player or not girl:
                return {'error': 'Not found'}, 400
            if player['currentLocation'] != girl['currentLocation']:
                return {'error': 'Different locations'}, 400
            if any(d['girlId'] == girl_id for d in state['active_dialogues']):
                return {'error': 'Already in dialogue'}, 400

            session = {
                'girlId': girl_id,
                'participants': [player_id],
                'history': []
            }
            state['active_dialogues'].append(session)
            await save_state(state)

            # генерируем первый ответ
            reply_text, commands = await generate_response(girl, player, session)
            session['history'].append({'sender': 'girl', 'text': reply_text})
            # обрабатываем команды
            self._apply_commands(commands, session, state)
            await save_state(state)
            return {'reply': reply_text, 'commands': commands}
        res = asyncio.run(main())
        if isinstance(res, tuple):
            self._send_json(res[0], res[1])
        else:
            self._send_json(res)

    def _handle_send_message(self, body):
        player_id = body['playerId']
        text = body['text']
        async def main():
            state = await get_state()
            session = next((d for d in state['active_dialogues'] if player_id in d['participants']), None)
            if not session:
                return {'error': 'Not in dialogue'}, 400

            player = next(p for p in state['players'] if p['id'] == player_id)
            girl = next(g for g in state['girls'] if g['id'] == session['girlId'])
            # обновим время последнего взаимодействия
            if girl['id'] not in player['relationships']:
                player['relationships'][girl['id']] = {}
            from datetime import datetime, timezone
            player['relationships'][girl['id']]['lastInteraction'] = datetime.now(timezone.utc).isoformat()

            session['history'].append({'sender': 'user', 'text': text})
            reply_text, commands = await generate_response(girl, player, session)
            session['history'].append({'sender': 'girl', 'text': reply_text})
            self._apply_commands(commands, session, state)
            await save_state(state)
            return {'reply': reply_text, 'commands': commands}
        res = asyncio.run(main())
        if isinstance(res, tuple):
            self._send_json(res[0], res[1])
        else:
            self._send_json(res)

    def _handle_leave_dialogue(self, body):
        player_id = body['playerId']
        async def main():
            state = await get_state()
            for d in state['active_dialogues']:
                if player_id in d['participants']:
                    d['participants'].remove(player_id)
                    if not d['participants']:
                        state['active_dialogues'].remove(d)
                    break
            await save_state(state)
            return {'success': True}
        res = asyncio.run(main())
        self._send_json(res)

    def _handle_move(self, body):
        player_id = body['playerId']
        location = body['location']
        async def main():
            state = await get_state()
            player = next((p for p in state['players'] if p['id'] == player_id), None)
            if not player:
                return {'error': 'Player not found'}, 400
            if any(player_id in d['participants'] for d in state['active_dialogues']):
                return {'error': 'Cannot move while in dialogue'}, 400
            if location not in ['School', 'Park', 'Cafe']:
                return {'error': 'Invalid location'}, 400
            player['currentLocation'] = location
            await save_state(state)
            return {'success': True}
        res = asyncio.run(main())
        if isinstance(res, tuple):
            self._send_json(res[0], res[1])
        else:
            self._send_json(res)

    def _apply_commands(self, commands, session, state):
        """Применяет команды, полученные от ИИ."""
        girl = next(g for g in state['girls'] if g['id'] == session['girlId'])
        for cmd in commands:
            if 'ChangeLocation' in cmd and cmd['ChangeLocation'] in ['School', 'Park', 'Cafe']:
                girl['currentLocation'] = cmd['ChangeLocation']
                for pid in session['participants']:
                    p = next((pp for pp in state['players'] if pp['id'] == pid), None)
                    if p:
                        p['currentLocation'] = cmd['ChangeLocation']
            if 'SetBoyfriend' in cmd:
                girl['boyfriendId'] = cmd['SetBoyfriend']

    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())