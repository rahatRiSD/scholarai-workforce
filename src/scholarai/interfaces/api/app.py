"""FastAPI application factory (build spec §19)."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from scholarai.composition import Container, bootstrap, build_container
from scholarai.interfaces.api.errors import register_error_handlers
from scholarai.interfaces.api.middleware import RequestLoggingMiddleware
from scholarai.interfaces.api.routes import (
    applications,
    dashboard,
    health,
    knowledge_base,
    memory,
    scholarships,
)


def create_app(container: Container | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.container = container or build_container()
        await bootstrap(app.state.container)
        yield

    app = FastAPI(
        title="ScholarAI Workforce API",
        description=(
            "A Supervisor-orchestrated multi-agent AI system for explainable, "
            "human-in-the-loop university scholarship evaluation."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestLoggingMiddleware)
    register_error_handlers(app)

    app.include_router(health.router)
    app.include_router(scholarships.router)
    app.include_router(applications.router)
    app.include_router(dashboard.router)
    app.include_router(knowledge_base.router)
    app.include_router(memory.router)

    return app


app = create_app()
