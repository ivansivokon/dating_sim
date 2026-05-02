import os
import json
from redis.asyncio import from_url

KV_URL = os.environ.get('KV_URL')

# Временное in-memory хранилище на случай отсутствия KV
_in_memory_state = None

async def get_redis():
    if not KV_URL:
        raise RuntimeError("KV_URL not set. Please add Vercel KV integration.")
    return from_url(KV_URL, decode_responses=True)

async def get_state():
    global _in_memory_state
    if not KV_URL:
        if _in_memory_state is None:
            _in_memory_state = {
                'girls': default_girls(),
                'players': [],
                'active_dialogues': []
            }
        return _in_memory_state
    r = await get_redis()
    girls = await r.get('girls')
    players = await r.get('players')
    dialogues = await r.get('active_dialogues')
    return {
        'girls': json.loads(girls) if girls else default_girls(),
        'players': json.loads(players) if players else [],
        'active_dialogues': json.loads(dialogues) if dialogues else []
    }

async def save_state(state):
    global _in_memory_state
    if not KV_URL:
        _in_memory_state = state
        return
    r = await get_redis()
    await r.set('girls', json.dumps(state['girls']))
    await r.set('players', json.dumps(state['players']))
    await r.set('active_dialogues', json.dumps(state['active_dialogues']))

def default_girls():
    return [
        {"id": "girl1", "name": "Сакура", "currentLocation": "School", "boyfriendId": None},
        {"id": "girl2", "name": "Юки", "currentLocation": "Park", "boyfriendId": None},
        {"id": "girl3", "name": "Хана", "currentLocation": "Cafe", "boyfriendId": None}
    ]