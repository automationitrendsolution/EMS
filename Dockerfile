FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps for Pillow / reportlab. gosu lets the entrypoint drop from root
# to an unprivileged user after fixing volume ownership.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libjpeg-dev zlib1g-dev libfreetype6-dev gosu \
    && rm -rf /var/lib/apt/lists/*

# Unprivileged runtime user (silences Celery's superuser SecurityWarning).
RUN useradd --create-home --uid 1000 appuser

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

RUN chmod +x /app/docker/entrypoint.sh && chown -R appuser:appuser /app

EXPOSE 8000

ENTRYPOINT ["sh", "/app/docker/entrypoint.sh"]
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]
