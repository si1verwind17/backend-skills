# Cloud Run image (SD7). Dependencies come from the fully pinned lock file (SD9).
FROM python:3.14.8-slim-trixie

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock

COPY src ./src
COPY migrations ./migrations
ENV PYTHONPATH=/app/src
RUN useradd --system --no-create-home app
USER app

# Cloud Run sets PORT; uvicorn serves the app built by the composition root.
CMD ["sh", "-c", "exec uvicorn parking_reservation.asgi:app --host 0.0.0.0 --port ${PORT:-8080}"]
