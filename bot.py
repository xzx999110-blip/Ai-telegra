import os
import time
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import requests

TG_TOKEN = os.environ["TG_TOKEN"]
GEMINI_KEY = os.environ["GEMINI_KEY"]
MODEL = "gemini-2.5-flash"  # если будет ошибка модели, замени на актуальную из AI Studio

SYSTEM_PROMPT = (
    "Ты дружелюбный репетитор для школьников 5-11 классов. "
    "Не давай готовое решение сразу: веди наводящими вопросами и объясняй просто, с примерами. "
    "Если ученик просит проверить решение, найди ошибку и подскажи, как её исправить. "
    "Отвечай коротко и на русском. Не обсуждай ничего, кроме учёбы."
)

TG_URL = f"https://api.telegram.org/bot{TG_TOKEN}"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"

history = {}      # chat_id -> список сообщений
usage = {}        # chat_id -> времена последних запросов
MAX_HISTORY = 10  # сколько последних сообщений помнить
MAX_PER_HOUR = 20 # лимит запросов на ученика в час


def allowed(chat_id):
    now = time.time()
    times = [t for t in usage.get(chat_id, []) if now - t < 3600]
