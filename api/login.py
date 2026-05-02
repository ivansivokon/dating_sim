import json, asyncio
from http.server import BaseHTTPRequestHandler
from ._init_kv import get_state


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        body = json.loads(self.rfile.read(content_length))
        username = body.get('username')
        password = body.get('password')

        async def main():
            state = await get_state()
            for p in state['players']:
                if p['username'] == username and p['password'] == password:
                    return {'playerId': p['id']}
            return {'error': 'Invalid credentials'}

        res = asyncio.run(main())
        if 'error' in res:
            self.send_response(401)
        else:
            self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(res).encode())