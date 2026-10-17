from collections.abc import Callable

from fastapi import APIRouter


def build_health_router(check_database: Callable[[], None]) -> APIRouter:
    router = APIRouter()

    @router.get("/healthz")
    def healthz() -> dict[str, str]:
        check_database()  # a failure surfaces through the database-unavailable handler as 503
        return {"status": "ok"}

    return router
