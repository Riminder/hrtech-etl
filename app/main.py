# app/main.py
import os

from fastapi import FastAPI
from .api import router as api_router
from .playground import router as playground_router

def create_app() -> FastAPI:
    app = FastAPI(title="hrtech-etl")

    mode = os.getenv("mode", "both").lower()
    # mode can be: "api", "playground", "both"

    if mode in ("api", "both"):
        app.include_router(api_router, prefix="/api", tags=["api"])

    if mode in ("playground", "both"):
        app.include_router(playground_router, tags=["playground"])

    return app


app = create_app()
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)