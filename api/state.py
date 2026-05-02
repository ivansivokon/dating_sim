import json, asyncio
from http.server import BaseHTTPRequestHandler
from ._init_kv import get_state

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        async def main():
            state = await get_state()
            # Убираем пароли
            safe_players = [{k: v for k, v in p.items() if k != 'password'} for p in state['players']]
            return {
                'players': safe_players,
                'girls': state['girls'],
                'active_dialogues': state['active_dialogues'],
                'locations': ['School', 'Park', 'Cafe']
            }
        result = asyncio.run(main())
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(result).encode())