FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir \
    "aiogram>=3.20.0" \
    "httpx>=0.27.0" \
    "pydantic-settings>=2.4.0"

COPY bot /app/bot

RUN mkdir -p /app/data

CMD ["python", "bot/bot.py"]
