import json, asyncio, os
from http.server import BaseHTTPRequestHandler
from ._init_kv import get_state, save_state
import openai

openai.api_key = os.environ['NVIDIA_API_KEY']
openai.api_base = 'https://integrate.api.nvidia.com/v1'


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        player_id = body['playerId']
        text = body['text']

        async def main():
            state = await get_state()
            session = next((d for d in state['active_dialogues'] if player_id in d['participants']), None)
            if not session:
                return {'error': 'Not in dialogue'}
            # Добавляем сообщение игрока
            session['history'].append({'sender': 'user', 'text': text})
            # Обновить lastInteraction
            player = next(p for p in state['players'] if p['id'] == player_id)
            girl = next(g for g in state['girls'] if g['id'] == session['girlId'])
            if player and girl:
                if girl['id'] not in player['relationships']:
                    player['relationships'][girl['id']] = {}
                player['relationships'][girl['id']]['lastInteraction'] = datetime.utcnow().isoformat()
            await save_state(state)

            # Генерация ответа...
            # (аналогично start_dialogue, используя историю)
            # ...
            # После ответа парсинг команд и сохранение
            return {'reply': clean_text, 'commands': commands}
        # вызов asyncio.run(main()) и отправка