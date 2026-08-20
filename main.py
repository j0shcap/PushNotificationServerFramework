"""
This file is the entry point for the FastAPI application.
It configures middleware, adds sub-routers, and defines application-level health checks.
"""

import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

import database
from apis import devices, push
from entities import EntityBase
from push import shutdown_push_handler
from utils import getenv


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not os.getenv("API_KEY"):
        raise RuntimeError(
            "API_KEY environment variable must be set; protected endpoints "
            "require clients to send it as 'Authorization: Bearer <API_KEY>'"
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
    if cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    routers: list[APIRouter] = [devices.router, push.router]
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
