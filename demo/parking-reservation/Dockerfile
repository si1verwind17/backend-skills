# Base image pinned by digest (stack selection): python:3.14.8-slim-bookworm
FROM python@sha256:48b13b003dda20b16f9442b8475aa05fe21bf6579a8c881db92ffb4d8fd20f83

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

COPY requirements.lock requirements-build.lock ./
RUN pip install --require-hashes -r requirements.lock -r requirements-build.lock

COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-deps --no-build-isolation .

RUN useradd --system --uid 10001 app
USER app

# Cloud Run supplies PORT. The server access log is off: the request middleware writes the one
# log line per request (api/request_logging.py). The migration job uses the same image with
# `python -m parking_reservation.migrate_main`.
CMD ["sh", "-c", "exec uvicorn --factory parking_reservation.main:create_app_from_env --host 0.0.0.0 --port ${PORT:-8080} --no-access-log"]
