"""Рыбка Дори — Telegram-бот БЕЗ памяти: каждое сообщение — отдельный запрос."""
import logging
import os

import telebot
from dotenv import load_dotenv

load_dotenv()

import assistant  # noqa: E402  (после load_dotenv, чтобы llm увидел переменные)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [DORY] %(message)s")
log = logging.getLogger("dory")

bot = telebot.TeleBot(os.environ["BOT_TOKEN_DORY"])


@bot.message_handler(commands=["start", "help"])
def start(message):
    bot.reply_to(message, "Я Рыбка Дори. Я ничего не помню между сообщениями :)")


@bot.message_handler(func=lambda m: True, content_types=["text"])
def handle_message(message):
    log.info("user=%s text=%r", message.from_user.id, message.text)
    try:
        answer = assistant.dory_reply(message.text)
    except Exception:
        log.exception("ошибка LLM")
        answer = "Произошла ошибка, попробуйте ещё раз."
    bot.reply_to(message, answer)


if __name__ == "__main__":
    log.info("Dory запущена (без памяти)")
    bot.infinity_polling()
