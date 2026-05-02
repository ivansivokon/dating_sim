import json, asyncio
from http.server import BaseHTTPRequestHandler
from ._init_kv import get_state, save_state

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
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
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(res).encode())