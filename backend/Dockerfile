FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY backend /app/backend

RUN pip install --no-cache-dir -e /app/backend

RUN mkdir -p /app/data

EXPOSE 8000

CMD ["python", "-m", "cava_backend.run"]
