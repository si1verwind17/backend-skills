"""Entry point for uvicorn: `uvicorn parking_reservation.asgi:app`."""

from parking_reservation.main import build_app

app = build_app()
