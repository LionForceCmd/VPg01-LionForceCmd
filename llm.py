"""Обёртка над LLM. LLM_MODE=fake включает офлайн-заглушку (для проверки без ключей)."""
import os
import re

from pydantic import BaseModel

LLM_MODE = os.getenv("LLM_MODE", "openai")
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


class StructuredResponse(BaseModel):
    theses: list[str]  # тезисы текущего обмена (вопрос + ответ)
    message: str       # текст, который уйдёт пользователю


_client = None


def _get_client():
    global _client
    if _client is None:
        from openai import OpenAI
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"),
                         base_url=os.getenv("OPENAI_BASE_URL") or None)
    return _client


def ask_plain(system_prompt: str, user_message: str) -> str:
    """Запрос без структурированного вывода (бот Дори)."""
    if LLM_MODE == "fake":
        return _fake(system_prompt, user_message).message
    r = _get_client().chat.completions.create(
        model=MODEL, max_tokens=1000,
        messages=[{"role": "system", "content": system_prompt},
                  {"role": "user", "content": user_message}])
    return r.choices[0].message.content


def ask_structured(system_prompt: str, user_message: str) -> StructuredResponse:
    """Запрос со structured output (theses + message), как в уроке."""
    if LLM_MODE == "fake":
        return _fake(system_prompt, user_message)
    r = _get_client().beta.chat.completions.parse(
        model=MODEL, max_tokens=3000, temperature=0.7,
        messages=[{"role": "system", "content": system_prompt},
                  {"role": "user", "content": user_message}],
        response_format=StructuredResponse)
    parsed = r.choices[0].message.parsed
    if parsed is None:  # отказ модели / сбой парсинга
        return StructuredResponse(
            theses=[],
            message=r.choices[0].message.refusal or "Не удалось получить ответ, попробуйте ещё раз.")
    return parsed


# ---------------------------------------------------------------------------
# Офлайн-заглушка. Видит ТОЛЬКО то, что попало в промпт, — как настоящая модель,
# поэтому наглядно показывает, работает ли память. Это не замена LLM.
# ---------------------------------------------------------------------------
def _fake(system_prompt: str, msg: str) -> StructuredResponse:
    low = msg.lower().strip()
    ctx = system_prompt  # всё, что бот сумел «вспомнить»

    m = re.search(r"меня зовут (\w+)", low)
    if m:
        name = m.group(1).capitalize()
        return StructuredResponse(theses=[f"Пользователя зовут {name}"],
                                  message=f"Приятно познакомиться, {name}! Чем могу помочь?")

    if "как меня зовут" in low or "забыл свое имя" in low or "забыл своё имя" in low:
        names = (re.findall(r"Пользователя зовут (\w+)", ctx)
                 or re.findall(r"меня зовут (\w+)", ctx.lower()))
        if names:
            return StructuredResponse(theses=[], message=f"Тебя зовут {names[-1].capitalize()}.")
        return StructuredResponse(
            theses=[], message="Я не знаю вашего имени. Спросите у друзей или посмотрите в документах.")

    if "умнож" in low:
        k = re.search(r"на (\d+)", low)
        nums = re.findall(r"\b(\d+)\b", re.sub(r"умножить на \d+", "", ctx))
        if nums and k:
            res = int(nums[-1]) * int(k.group(1))
            return StructuredResponse(theses=[f"Результат умножения: {res}"],
                                      message=f"{nums[-1]} × {k.group(1)} = {res}")
        return StructuredResponse(theses=[], message="Уточните, что именно умножить?")

    m = re.search(r"(\d+)\s*\+\s*(\d+)", low)
    if m:
        s = int(m.group(1)) + int(m.group(2))
        return StructuredResponse(theses=[f"Пользователь спрашивал {m.group(0)}, ответ {s}"],
                                  message=str(s))

    cities = {"питер": "Санкт-Петербург", "мехико": "Мехико"}
    for key, city in cities.items():
        if key in low:
            return StructuredResponse(theses=[f"Пользователя интересует {city}"],
                                      message=f"{city}: есть что посмотреть — музеи, площади, парки.")

    if "что там" in low or "что в нем" in low or "что в нём" in low or "посетить" in low:
        known = re.findall(r"(Санкт-Петербург|Мехико)", ctx)
        if known:
            city = known[-1]
            return StructuredResponse(theses=[f"Пользователь выбирает, что посетить: {city}"],
                                      message=f"В городе {city} стоит посетить главные музеи и исторический центр.")
        return StructuredResponse(theses=[], message="О каком месте речь? Уточните, пожалуйста.")

    return StructuredResponse(theses=[], message="Чем могу помочь?")
