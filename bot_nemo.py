"""Рыбка Немо — Telegram-бот С памятью (SQLite): тезисы + последние реплики.

Команды:
  /mytheses       — показать сохранённые тезисы
  /reset          — полностью очистить память (диалог + тезисы)
  /reset_history  — очистить только контекст диалога, тезисы оставить
"""
import logging
import os

import telebot
from dotenv import load_dotenv

load_dotenv()

import assistant  # noqa: E402
import db  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s [NEMO] %(message)s")
log = logging.getLogger("nemo")

bot = telebot.TeleBot(os.environ["BOT_TOKEN_NEMO"])


@bot.message_handler(commands=["start", "help"])
def start(message):
    bot.reply_to(message, (
        "Я Рыбка Немо, я помню наши разговоры — даже после перезапуска.\n"
        "/mytheses — что я о вас помню\n"
        "/reset — забыть всё\n"
        "/reset_history — забыть только текущий диалог, но оставить тезисы"))


@bot.message_handler(commands=["mytheses"])
def mytheses(message):
    bot.reply_to(message, assistant.theses_text(message.from_user.id))


@bot.message_handler(commands=["reset"])
def reset(message):
    uid = message.from_user.id
    answer = assistant.reset_all(uid)
    log.info("user=%s RESET all: %s", uid, answer)
    bot.reply_to(message, answer)


@bot.message_handler(commands=["reset_history"])
def reset_history(message):
    uid = message.from_user.id
    answer = assistant.reset_history(uid)
    log.info("user=%s RESET history: %s", uid, answer)
    bot.reply_to(message, answer)


@bot.message_handler(func=lambda m: True, content_types=["text"])
def handle_message(message):
    uid = message.from_user.id
    log.info("user=%s text=%r", uid, message.text)
    try:
        answer, theses = assistant.nemo_reply(uid, message.text)
        log.info("user=%s тезисы: %s", uid, theses)  # тезисы только в лог, пользователю не показываем
    except Exception:
        log.exception("ошибка LLM")
        answer = "Произошла ошибка, попробуйте ещё раз."
    bot.reply_to(message, answer)


if __name__ == "__main__":
    db.init_db()
    users, msgs, theses = db.stats()
    log.info("Nemo запущена. Загружена память из БД: пользователей=%s, реплик=%s, тезисов=%s",
             users, msgs, theses)
    bot.infinity_polling()
