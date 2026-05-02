import os
import re
import json as json_mod
import openai

openai.api_key = os.environ['NVIDIA_API_KEY']
openai.api_base = 'https://integrate.api.nvidia.com/v1'

async def generate_response(girl, player, session):
    system_prompt = f"""Ты - {girl['name']}, девушка из симулятора свиданий. Ты находишься в локации {girl['currentLocation']}.
Ты разговариваешь с парнем по имени {player['username']}. 
Будь милой, иногда застенчивой, флиртуй.
Ты можешь предложить сменить локацию, написав отдельной строкой JSON: {{"ChangeLocation": "Park"}} (доступны School, Park, Cafe).
Если тебе очень понравится парень, можешь стать его девушкой, написав: {{"SetBoyfriend": "{player['id']}"}}.
Отвечай коротко, как в чате, не больше 2-3 предложений.
"""
    messages = [{"role": "system", "content": system_prompt}]
    # Добавляем историю (все сообщения)
    for h in session['history']:
        if h['sender'] == 'user':
            messages.append({"role": "user", "content": h['text']})
        else:
            messages.append({"role": "assistant", "content": h['text']})
    # Если это первый запрос (нет истории), добавляем приветствие
    if not session['history']:
        messages.append({"role": "user", "content": "Привет!"})

    try:
        completion = await openai.ChatCompletion.acreate(
            model="deepseek-ai/deepseek-v4-pro",
            messages=messages,
            temperature=1,
            max_tokens=512,
            extra_body={"chat_template_kwargs": {"thinking": False}}
        )
        full_text = completion.choices[0].message.content
    except Exception as e:
        full_text = "Привет! Я рада тебя видеть."

    # Разбор команд
    text_lines = []
    commands = []
    for line in full_text.split('\n'):
        line = line.strip()
        if line.startswith('{') and line.endswith('}'):
            try:
                cmd = json_mod.loads(line)
                commands.append(cmd)
            except:
                text_lines.append(line)
        else:
            text_lines.append(line)
    clean_text = '\n'.join(text_lines).strip()
    return clean_text, commands