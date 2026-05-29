FROM python:3.12-slim AS base

WORKDIR /app

RUN pip install poetry==2.4.0

COPY pyproject.toml poetry.lock* ./

RUN poetry config virtualenvs.create false \
    && poetry install --no-root --only main

FROM base AS runtime

COPY src/ ./src/

CMD ["uvicorn", "src.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
