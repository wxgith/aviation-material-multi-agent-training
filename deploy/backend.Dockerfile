FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /opt/aviation-training

COPY backend/requirements.txt backend/requirements.txt
RUN python -m pip install --upgrade pip && \
    python -m pip install -r backend/requirements.txt

COPY backend/app backend/app
COPY backend/tests backend/tests
COPY backend/alembic.ini backend/alembic.ini
COPY backend/migrations backend/migrations
COPY knowledge_corpus knowledge_corpus
COPY evaluation evaluation

WORKDIR /opt/aviation-training/backend
EXPOSE 8000

CMD ["sh", "-c", "python -m app.db.migrate && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"]
