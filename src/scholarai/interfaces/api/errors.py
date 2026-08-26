"""Centralized translation of domain errors into HTTP responses."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from scholarai.domain.errors import AgentExecutionError, DocumentProcessingError, ScholarAIError
from scholarai.infrastructure.observability import get_logger

log = get_logger(__name__)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DocumentProcessingError)
    async def _document_error(request: Request, exc: DocumentProcessingError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(AgentExecutionError)
    async def _agent_error(request: Request, exc: AgentExecutionError) -> JSONResponse:
        log.error("api.agent_execution_error", agent=exc.agent_name, detail=exc.detail)
        return JSONResponse(status_code=502, content={"detail": f"{exc.agent_name}: {exc.detail}"})

    @app.exception_handler(ScholarAIError)
    async def _domain_error(request: Request, exc: ScholarAIError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(Exception)
    async def _unhandled_error(request: Request, exc: Exception) -> JSONResponse:
        log.error("api.unhandled_error", path=request.url.path, error=str(exc))
        return JSONResponse(status_code=500, content={"detail": "internal server error"})
