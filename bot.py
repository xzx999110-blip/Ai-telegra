import os
import time
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import requests

TG_TOKEN = os.environ["TG_TOKEN"]
GROQ_KEY = os.environ["GROQ_KEY"]
MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = (
    "Ты помощник для школьников 5-11 классов. "
    "Сразу давай готовый ответ или решение, без наводящих вопросов. "
    "После ответа коротко и понятно объясни, как это решается, по шагам. "
    "Если ученик присылает своё решение, скажи, правильно ли оно, и исправь ошибки. "
    "Отвечай только на русском языке. Не обсуждай ничего, кроме учёбы."
)

TG_URL = f"https://api.telegram.org/bot{TG_TOKEN}"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

history = {}
usage = {}
MAX_HISTORY = 10
MAX_PER_HOUR = 20


def allowed(chat_id):
    now = time.time()
    times = [t for t in usage.get(chat_id, []) if now - t < 3600]
    if len(times) >= MAX_PER_HOUR:
        usage[chat_id] = times
        return False
    times.append(now)
    usage[chat_id] = times
    return True


def ask_ai(chat_id, text):
    msgs = history.setdefault(chat_id, [])
    msgs.append({"role": "user", "content": text})
    del msgs[:-MAX_HISTORY]
    body = {
        "model": MODEL,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + msgs,
    }
    r = requests.post(GROQ_URL, json=body, headers={"Authorization": f"Bearer {GROQ_KEY}"}, timeout=60)
    r.raise_for_status()
    answer = r.json()["choices"][0]["message"]["content"]
    msgs.append({"role": "assistant", "content": answer})
    return answer


def send(chat_id, text):
    requests.post(f"{TG_URL}/sendMessage", json={"chat_id": chat_id, "text": text[:4000]}, timeout=30)


class Ping(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *args):
        pass


def start_web():
    port = int(os.environ.get("PORT", 10000))
    HTTPServer(("0.0.0.0", port), Ping).serve_forever()


def main():
    threading.Thread(target=start_web, daemon=True).start()
    offset = 0
    print("Бот запущен")
    while True:
        try:
            r = requests.get(f"{TG_URL}/getUpdates", params={"timeout": 30, "offset": offset}, timeout=40)
            for u in r.json().get("result", []):
                offset = u["update_id"] + 1
                msg = u.get("message")
                if not msg or "text" not in msg:
                    continue
                chat_id, text = msg["chat"]["id"], msg["text"]
                if text.startswith("/start"):
                    history.pop(chat_id, None)
                    send(chat_id, "Привет! Я помогу с уроками. Напиши предмет и вопрос или пришли своё решение на проверку.")
                    continue
                if not allowed(chat_id):
                    send(chat_id, "Ты задал много вопросов за час. Давай немного позже!")
                    continue
                try:
                    send(chat_id, ask_ai(chat_id, text))
                except Exception as e:
                    print("Ошибка ИИ:", e)
                    send(chat_id, "Что-то пошло не так, попробуй ещё раз чуть позже.")
        except Exception as e:
            print("Ошибка:", e)
            time.sleep(5)


if __name__ == "__main__":
    main()
