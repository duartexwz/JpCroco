FROM python:3.13-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --no-cache-dir poetry

COPY pyproject.toml poetry.lock ./

RUN poetry config virtualenvs.create false \
    && poetry install --no-root --no-interaction --no-ansi \
    && pip install --no-cache-dir httpx pywebpush

COPY api ./api
COPY schema.sql ./
COPY migrate.py ./
COPY migrations ./migrations

RUN mkdir -p /app/uploads

EXPOSE 8055

CMD ["fastapi", "run", "api/app.py", "--host", "0.0.0.0", "--port", "8055"]
