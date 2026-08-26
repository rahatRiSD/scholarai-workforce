"""In-process background workflow runtime with cooperative controls.

The LangGraph remains the source of workflow truth.  This runtime only owns
the lifecycle of each asynchronous graph stream so the API can return
immediately and operators can poll, pause between nodes, resume, cancel, or
launch a targeted retry.  Production deployments should run a single API
worker or replace this adapter with a Redis/Celery-backed implementation.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class RunStatus(StrEnum):
    IDLE = "idle"
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class RunControl:
    application_id: str
    status: RunStatus = RunStatus.QUEUED
    current_actor: str = "supervisor"
    current_step: int = 0
    total_steps: int = 0
    error: str = ""
    started_at: datetime | None = None
    finished_at: datetime | None = None
    pause_gate: asyncio.Event = field(default_factory=asyncio.Event, repr=False)
    cancel_requested: bool = False
    task: asyncio.Task[Any] | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        self.pause_gate.set()

    async def checkpoint(self) -> None:
        """Pause only at safe graph-node boundaries; cancellation is immediate."""
        await self.pause_gate.wait()
        if self.cancel_requested:
            raise asyncio.CancelledError

    def snapshot(self) -> dict[str, Any]:
        return {
            "application_id": self.application_id,
            "run_status": self.status.value,
            "current_actor": self.current_actor,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "progress": round(self.current_step / self.total_steps, 3) if self.total_steps else 0.0,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
        }


Runner = Callable[[RunControl], Awaitable[dict[str, Any]]]


class WorkflowRunManager:
    """Owns background graph tasks for one API process."""

    def __init__(self) -> None:
        self._runs: dict[str, RunControl] = {}

    async def start(self, application_id: str, runner: Runner) -> dict[str, Any]:
        existing = self._runs.get(application_id)
        if existing and existing.status in {
            RunStatus.QUEUED,
            RunStatus.RUNNING,
            RunStatus.PAUSED,
            RunStatus.CANCELLING,
        }:
            raise RuntimeError(f"application {application_id!r} already has an active workflow run")

        control = RunControl(application_id=application_id)
        self._runs[application_id] = control

        async def wrapped() -> None:
            control.status = RunStatus.RUNNING
            control.started_at = datetime.now(UTC)
            try:
                await runner(control)
            except asyncio.CancelledError:
                control.status = RunStatus.CANCELLED
                control.finished_at = datetime.now(UTC)
                return
            except Exception as exc:  # noqa: BLE001 - surfaced through status and persisted state
                control.status = RunStatus.FAILED
                control.error = str(exc)
                control.finished_at = datetime.now(UTC)
                return
            control.status = RunStatus.COMPLETED
            control.finished_at = datetime.now(UTC)

        control.task = asyncio.create_task(wrapped(), name=f"scholarai-{application_id}")
        await asyncio.sleep(0)
        return control.snapshot()

    def status(self, application_id: str) -> dict[str, Any]:
        control = self._runs.get(application_id)
        if control is None:
            return RunControl(application_id=application_id, status=RunStatus.IDLE).snapshot()
        return control.snapshot()

    def pause(self, application_id: str) -> dict[str, Any]:
        control = self._active(application_id)
        if control.status is not RunStatus.RUNNING:
            raise RuntimeError("only a running workflow can be paused")
        control.status = RunStatus.PAUSED
        control.pause_gate.clear()
        return control.snapshot()

    def resume(self, application_id: str) -> dict[str, Any]:
        control = self._active(application_id)
        if control.status is not RunStatus.PAUSED:
            raise RuntimeError("only a paused workflow can be resumed")
        control.status = RunStatus.RUNNING
        control.pause_gate.set()
        return control.snapshot()

    def cancel(self, application_id: str) -> dict[str, Any]:
        control = self._active(application_id)
        control.status = RunStatus.CANCELLING
        control.cancel_requested = True
        control.pause_gate.set()
        if control.task and not control.task.done():
            control.task.cancel()
        return control.snapshot()

    def _active(self, application_id: str) -> RunControl:
        control = self._runs.get(application_id)
        if control is None or control.status in {
            RunStatus.IDLE,
            RunStatus.COMPLETED,
            RunStatus.CANCELLED,
            RunStatus.FAILED,
        }:
            raise RuntimeError(f"application {application_id!r} has no active workflow run")
        return control
