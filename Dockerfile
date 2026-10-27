FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# db.py, llm.py и assistant.py — общие модули, их обязательно копировать (ошибка из урока)
COPY db.py llm.py assistant.py bot_dory.py bot_nemo.py ./
CMD ["python", "bot_nemo.py"]
