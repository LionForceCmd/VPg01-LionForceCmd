"""Консольный чат с обоими ботами — чтобы проверить логику без Telegram.

  python cli.py dory
  python cli.py nemo [--user 1] [--debug]     (--debug печатает системный промпт)
Команды в nemo: /mytheses, /reset, /reset_history, /exit
"""
import argparse
import sys

from dotenv import load_dotenv

load_dotenv()

import assistant  # noqa: E402
import db  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bot", choices=["dory", "nemo"])
    ap.add_argument("--user", type=int, default=1)
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    db.init_db()
    if args.bot == "nemo":
        print("[NEMO] загружено из БД: пользователей=%s, реплик=%s, тезисов=%s" % db.stats())
    print(f"=== {args.bot.upper()} ({'с памятью' if args.bot == 'nemo' else 'без памяти'}) ===")
    while True:
        try:
            text = input("Вы: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not text:
            continue
        if text == "/exit":
            break
        if args.bot == "nemo" and text == "/mytheses":
            print("Бот:", assistant.theses_text(args.user))
        elif args.bot == "nemo" and text == "/reset":
            print("Бот:", assistant.reset_all(args.user))
        elif args.bot == "nemo" and text == "/reset_history":
            print("Бот:", assistant.reset_history(args.user))
        elif args.bot == "dory":
            print("Бот:", assistant.dory_reply(text))
        else:
            if args.debug:
                print("--- системный промпт ---\n" + assistant.build_system_prompt(args.user) + "\n---")
            answer, theses = assistant.nemo_reply(args.user, text)
            print("Бот:", answer)
            print("   (тезисы в лог:", theses, ")")


if __name__ == "__main__":
    main()
