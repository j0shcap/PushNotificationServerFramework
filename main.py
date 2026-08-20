"""
This file is the entry point for the FastAPI application.
It configures middleware, adds sub-routers, and defines application-level health checks.
"""

import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

import database
from apis import devices, push
from entities import EntityBase
from push import shutdown_push_handler
from utils import getenv

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    api_key = getenv("API_KEY", "")
    if not api_key:
        raise RuntimeError(
            "API_KEY environment variable must be set; protected endpoints "
            "require clients to send it as 'Authorization: Bearer <API_KEY>'"
        )
    if api_key == "CHANGE_ME":
        logger.warning(
            "API_KEY is still the CHANGE_ME placeholder from .env.template; "
            "set a real secret before exposing this server"
        )
    EntityBase.metadata.create_all(database.engine)
    yield
    shutdown_push_handler()


def create_app() -> FastAPI:
    """
    Builds the FastAPI application.

    Cross-origin requests are disabled unless the CORS_ORIGINS environment
    variable lists the allowed origins (comma-separated). iOS apps do not use
    CORS; only enable it when serving a web frontend.
    """
    app = FastAPI(lifespan=lifespan)

    cors_origins = [
        origin.strip() for origin in getenv("CORS_ORIGINS", "").split(",") if origin.strip()
    ]
    if "*" in cors_origins:
        raise ValueError(
            "CORS_ORIGINS must list explicit origins; a wildcard combined "
            "with credentials would let any website make authenticated requests"
        )
    if cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    routers: list[APIRouter] = [devices.router, devices.protected_router, push.router]
    for router in routers:
        app.include_router(router)

    @app.get("/health")
    async def health():
        return {"message": "OK"}

    @app.get("/")
    async def root():
        return {"message": "Hello World"}

    return app


app = create_app()

if __name__ == "__main__":
    uvicorn.run(app, host=getenv("HOST", "127.0.0.1"), port=int(getenv("PORT", "8000")))
