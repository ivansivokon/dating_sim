from http.server import BaseHTTPRequestHandler
import json
import uuid
import asyncio
from ._init_kv import get_state, save_state
from random import choice


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        body = json.loads(self.rfile.read(content_length))
        username = body.get('username')
        password = body.get('password')
        if not username or not password:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Missing fields'}).encode())
            return

        async def main():
            state = await get_state()
            if any(p['username'] == username for p in state['players']):
                return {'error': 'Username exists'}
            player_id = str(uuid.uuid4())
            locations = ['School', 'Park', 'Cafe']
            new_player = {
                'id': player_id,
                'username': username,
                'password': password,
                'currentLocation': choice(locations),
                'relationships': {}
            }
            state['players'].append(new_player)
            await save_state(state)
            return {'playerId': player_id}

        result = asyncio.run(main())
        if 'error' in result:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
        else:
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())