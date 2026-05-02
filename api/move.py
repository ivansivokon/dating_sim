import json, asyncio
from http.server import BaseHTTPRequestHandler
from ._init_kv import get_state, save_state

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        player_id = body['playerId']
        location = body['location']
        async def main():
            state = await get_state()
            player = next((p for p in state['players'] if p['id'] == player_id), None)
            if not player:
                return {'error': 'Player not found'}
            if any(d['participants'].count(player_id) for d in state['active_dialogues']):
                return {'error': 'Cannot move while in dialogue'}
            if location not in ['School', 'Park', 'Cafe']:
                return {'error': 'Invalid location'}
            player['currentLocation'] = location
            await save_state(state)
            return {'success': True}
        res = asyncio.run(main())
        if 'error' in res:
            self.send_response(400)
        else:
            self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(res).encode())