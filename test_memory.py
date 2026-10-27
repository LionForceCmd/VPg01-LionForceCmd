"""Тесты памяти на офлайн-заглушке LLM:  python -m unittest -v test_memory"""
import os
import subprocess
import sys
import tempfile
import unittest

_tmp = tempfile.mkdtemp()
os.environ["LLM_MODE"] = "fake"
os.environ["DB_PATH"] = os.path.join(_tmp, "test.db")

import assistant  # noqa: E402
import db  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


class MemoryTests(unittest.TestCase):
    def setUp(self):
        if os.path.exists(db.DB_PATH):
            os.remove(db.DB_PATH)
        db.init_db()

    # --- 1. сравнение моделей ---
    def test_dory_forgets_nemo_remembers(self):
        assistant.dory_reply("Привет. Меня зовут Никита.")
        self.assertIn("не знаю", assistant.dory_reply("Я забыл свое имя. Напомни."))

        assistant.nemo_reply(1, "Привет. Меня зовут Никита.")
        answer, _ = assistant.nemo_reply(1, "Я забыл свое имя. Напомни.")
        self.assertIn("Никита", answer)

    def test_followup_question_needs_context(self):
        assistant.dory_reply("Расскажи про Питер")
        self.assertIn("О каком", assistant.dory_reply("Что там можно посетить?"))
        assistant.nemo_reply(1, "Расскажи про Питер")
        answer, _ = assistant.nemo_reply(1, "Что там можно посетить?")
        self.assertIn("Санкт-Петербург", answer)

    # --- 2. долгосрочная память: рестарт процесса ---
    def test_memory_survives_restart(self):
        assistant.nemo_reply(1, "Меня зовут Никита")
        env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        out = subprocess.run(
            [sys.executable, "cli.py", "nemo", "--user", "1"], cwd=HERE, env=env,
            input="Как меня зовут?\n/exit\n", capture_output=True, text=True,
            encoding="utf-8").stdout
        self.assertIn("загружено из БД", out)
        self.assertIn("Тебя зовут Никита", out)

    def test_saved_context_is_in_system_prompt(self):
        assistant.nemo_reply(1, "Меня зовут Никита")
        prompt = assistant.build_system_prompt(1)
        self.assertIn("Тезисы из базы данных", prompt)
        self.assertIn("Пользователя зовут Никита", prompt)
        self.assertIn("Предыдущий диалог", prompt)

    def test_users_are_isolated(self):
        assistant.nemo_reply(1, "Меня зовут Никита")
        answer, _ = assistant.nemo_reply(2, "Как меня зовут?")
        self.assertNotIn("Никита", answer)

    def test_theses_deduplicated(self):
        db.add_theses(1, ["a", "a", " a ", "b"])
        db.add_theses(1, ["b"])
        self.assertEqual(db.get_theses(1), ["a", "b"])

    def test_history_limit(self):
        for i in range(30):
            db.add_message(1, "user", f"q{i}")
            db.add_message(1, "assistant", f"a{i}")
        recent = db.get_recent_messages(1, assistant.HISTORY_PAIRS * 2)
        self.assertEqual(len(recent), 40)
        self.assertEqual(recent[0], ("user", "q10"))  # самые старые 10 пар отброшены

    # --- 3. сброс памяти ---
    def test_reset_all(self):
        assistant.nemo_reply(1, "Меня зовут Никита")
        assistant.nemo_reply(2, "Меня зовут Олег")
        assistant.reset_all(1)
        answer, _ = assistant.nemo_reply(1, "Как меня зовут?")
        self.assertIn("не знаю", answer)
        self.assertEqual(db.get_theses(1), [])
        self.assertTrue(db.get_theses(2))  # чужая память не тронута

    def test_reset_history_keeps_theses(self):
        assistant.nemo_reply(1, "Меня зовут Никита")
        assistant.reset_history(1)
        self.assertEqual(db.get_recent_messages(1, 40), [])
        answer, _ = assistant.nemo_reply(1, "Как меня зовут?")
        self.assertIn("Никита", answer)  # вспомнил по тезису из БД


if __name__ == "__main__":
    unittest.main()
