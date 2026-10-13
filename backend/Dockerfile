FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

COPY app ./app
COPY alembic.ini ./alembic.ini
COPY alembic ./alembic
COPY entrypoint.sh ./entrypoint.sh
RUN sed -i 's/\r$//' ./entrypoint.sh \
    && chmod +x ./entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
