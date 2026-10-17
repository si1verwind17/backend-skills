FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Cloud Run sets $PORT; uvicorn binds to it directly (single process — see
# stack-selection.md; Cloud Run scales via instances, not in-container
# worker fan-out, for a service this small).
ENV PORT=8080
EXPOSE 8080
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
