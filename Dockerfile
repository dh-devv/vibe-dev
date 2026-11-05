FROM node:22-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend ./
RUN npm test && npm run build

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY alembic.ini ./
COPY database/migrations ./database/migrations
COPY --from=web /web/dist ./frontend/dist

RUN useradd --system --no-create-home app
USER app

EXPOSE 8000
# RUN_MIGRATIONS=true일 때만 시작 전에 마이그레이션을 적용한다 (Azure 배포용)
CMD ["sh", "-c", "if [ \"$RUN_MIGRATIONS\" = \"true\" ]; then alembic upgrade head || exit 1; fi; exec uvicorn src.app.main:app --host 0.0.0.0 --port 8000"]
