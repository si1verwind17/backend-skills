"""`python -m app` runs the API with uvicorn on $PORT (default 8080), the
same command the container uses."""

from __future__ import annotations

import os

import uvicorn


def main() -> None:
    uvicorn.run(
        "app.main:app",
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", "8080")),
        reload=os.environ.get("RELOAD", "") == "1",
    )


if __name__ == "__main__":
    main()
