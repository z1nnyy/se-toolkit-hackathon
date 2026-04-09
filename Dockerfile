FROM node:20-alpine AS frontend-build

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend /app/frontend

ARG VITE_API_BASE_URL=
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

RUN npm run build


FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY backend /app/backend
COPY bot /app/bot
COPY --from=frontend-build /app/frontend/dist /app/frontend/dist
COPY docker/start-all.sh /app/docker/start-all.sh

RUN pip install --no-cache-dir -e /app/backend \
    && pip install --no-cache-dir \
      "aiogram>=3.20.0" \
      "httpx>=0.27.0" \
      "pydantic-settings>=2.4.0"

RUN mkdir -p /app/data /app/docker \
    && chmod +x /app/docker/start-all.sh

EXPOSE 8000

CMD ["/app/docker/start-all.sh"]
