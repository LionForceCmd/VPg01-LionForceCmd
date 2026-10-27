"""Логика ботов, не зависящая от Telegram (её же использует консольный чат и тесты).

Dory — без памяти: каждое сообщение уходит в модель «как есть».
Nemo — с памятью: в системный промпт на КАЖДЫЙ запрос подмешиваются
  1) тезисы из БД (долгосрочная память),
  2) последние HISTORY_PAIRS пар «вопрос–ответ» из БД (краткосрочный контекст).
Так как всё читается из SQLite, после перезапуска бот ничего не теряет.
"""
import db
import llm

HISTORY_PAIRS = 20   # как в уроке: последние 20 пар
THESES_LIMIT = 50    # сколько последних тезисов подмешивать в промпт

SYSTEM_PROMPT = (
    "Ты полезный AI-ассистент. Отвечай по делу. "
    "Используй факты и историю диалога из этого промпта, если они есть. "
    "Вместе с ответом выдели тезисы текущего обмена репликами (вопрос пользователя и твой ответ) "
    "в виде коротких фактов для сохранения в базу данных, например: "
    "'Пользователя зовут [имя]', 'Пользователь хочет поехать в [место]', "
    "'Пользователь хочет купить [товар]'. Если запоминать нечего — верни пустой список."
)


# ----------------------------- Dory: без памяти -----------------------------
def dory_reply(text: str) -> str:
    return llm.ask_plain(SYSTEM_PROMPT, text)


# ----------------------------- Nemo: с памятью ------------------------------
def format_context_for_prompt(user_id: int) -> str:
    history = db.get_recent_messages(user_id, HISTORY_PAIRS * 2)
    names = {"user": "Пользователь", "assistant": "Ассистент"}
    return "\n".join(f"{names[role]}: {content}" for role, content in history)


def build_system_prompt(user_id: int) -> str:
    parts = [SYSTEM_PROMPT]
    theses = db.get_theses(user_id, THESES_LIMIT)
    if theses:
        parts.append("Тезисы из базы данных (долгосрочная память о пользователе):\n"
                     + "\n".join(f"- {t}" for t in theses))
    context = format_context_for_prompt(user_id)
    if context:
        parts.append("Предыдущий диалог:\n" + context)
    return "\n\n".join(parts)


def nemo_reply(user_id: int, text: str) -> tuple[str, list[str]]:
    """Возвращает (ответ пользователю, новые тезисы). Тезисы пользователю не показываются."""
    system_prompt = build_system_prompt(user_id)
    resp = llm.ask_structured(system_prompt, text)
    db.add_message(user_id, "user", text)
    db.add_message(user_id, "assistant", resp.message)
    db.add_theses(user_id, resp.theses)
    return resp.message, resp.theses


def theses_text(user_id: int) -> str:
    theses = db.get_theses(user_id)
    if not theses:
        return "В памяти пока нет тезисов."
    return "Что я о вас помню:\n" + "\n".join(f"{i}. {t}" for i, t in enumerate(theses, 1))


def reset_all(user_id: int) -> str:
    """Принудительный сброс всей памяти: диалог + тезисы."""
    h, t = db.clear_user(user_id)
    return f"Память очищена: удалено реплик — {h}, тезисов — {t}."


def reset_history(user_id: int) -> str:
    """Сброс только краткосрочного контекста; тезисы (долгосрочная память) остаются."""
    h = db.clear_history(user_id)
    return f"Контекст диалога очищен (реплик: {h}). Тезисы сохранены."
