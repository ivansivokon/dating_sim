import json, asyncio, os, re
from http.server import BaseHTTPRequestHandler
from ._init_kv import get_state, save_state
import openai

openai.api_key = os.environ['NVIDIA_API_KEY']
openai.api_base = 'https://integrate.api.nvidia.com/v1'


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        body = json.loads(self.rfile.read(content_length))
        player_id = body['playerId']
        girl_id = body['girlId']

        async def main():
            state = await get_state()
            player = next((p for p in state['players'] if p['id'] == player_id), None)
            girl = next((g for g in state['girls'] if g['id'] == girl_id), None)
            if not player or not girl:
                return {'error': 'Not found'}
            if player['currentLocation'] != girl['currentLocation']:
                return {'error': 'Different locations'}
            if any(d['girlId'] == girl_id for d in state['active_dialogues']):
                return {'error': 'Already in dialogue'}

            session = {
                'girlId': girl_id,
                'participants': [player_id],
                'history': []
            }
            state['active_dialogues'].append(session)
            await save_state(state)

            # Генерация приветствия
            system_prompt = f"""Ты - {girl['name']}, девушка. Ты находишься в локации {girl['currentLocation']}.
Разговариваешь с парнем по имени {player['username']}. Будь милой, флиртуй.
Можешь предложить сменить локацию, написав отдельной строкой JSON: {{"ChangeLocation": "Park"}} (доступны School, Park, Cafe).
Можешь стать его девушкой: {{"SetBoyfriend": "{player_id}"}}.
Отвечай коротко, как в чате."""
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Привет!"}
            ]
            try:
                completion = await openai.ChatCompletion.acreate(
                    model="deepseek-ai/deepseek-v4-pro",
                    messages=messages,
                    temperature=1,
                    max_tokens=512,
                    extra_body={"chat_template_kwargs": {"thinking": False}}
                )
                reply_text = completion.choices[0].message.content
            except Exception as e:
                reply_text = "Привет! Я рада тебя видеть."

            # Парсинг команд
            text_lines = []
            commands = []
            for line in reply_text.split('\n'):
                line = line.strip()
                if line.startswith('{') and line.endswith('}'):
                    try:
                        cmd = json.loads(line)
                        commands.append(cmd)
                    except:
                        text_lines.append(line)
                else:
                    text_lines.append(line)
            clean_text = '\n'.join(text_lines).strip()
            session['history'].append({'sender': 'girl', 'text': clean_text})

            # Обработка команд
            for cmd in commands:
                if 'ChangeLocation' in cmd and cmd['ChangeLocation'] in ['School', 'Park', 'Cafe']:
                    girl['currentLocation'] = cmd['ChangeLocation']
                    for pid in session['participants']:
                        p = next((pp for pp in state['players'] if pp['id'] == pid), None)
                        if p:
                            p['currentLocation'] = cmd['ChangeLocation']
                if 'SetBoyfriend' in cmd:
                    girl['boyfriendId'] = cmd['SetBoyfriend']

            await save_state(state)
            return {'reply': clean_text, 'commands': commands}

        result = asyncio.run(main())
        if 'error' in result:
            self.send_response(400)
        else:
            self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(result).encode())