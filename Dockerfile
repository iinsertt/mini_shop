FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml poetry.lock* /app/

ENV POETRY_VIRTUALENVS_CREATE=false

RUN pip install --upgrade pip && pip install poetry \
    && poetry install --no-root

COPY . /app

CMD ["python", "-u", "main.py"]
