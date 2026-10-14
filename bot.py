import os
import time
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import requests

TG_TOKEN = os.environ["TG_TOKEN"]
GROQ_KEY = os.environ["GROQ_KEY"]
MODEL = "llama-3.3-70b-versatile"  # если будет ошибка модели, замени на актуальную с console.groq.com

SYSTEM_PROMPT = (
    "Ты помощник для школьников 5-11 классов. "
    "Сразу давай готовый ответ или решение, без наводящих вопросов. "
    "После ответа коротко и понятно объясни, как это решается, по шагам. "
    "Если ученик присылает своё решение, скажи, правильно ли оно, и исправь ошибки. "
    "Отвечай только на русском языке. Не обсуждай ничего, кроме учёбы."
)

TG_URL = f"https://api.telegram.org/bot{TG_TOKEN}"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

history = {}       # chat_id -> список сообщений
usage = {}         # chat_id -> времена последних запросов
MAX_HISTORY = 10   # сколько последних сообщений помнить
MAX_PER_HOUR = 20  # лимит запросов на ученика в час


def allowed(chat_id):
    now = time.time()
    times = [t for t in usage.get(chat_id, []) if now - t < 3600]
