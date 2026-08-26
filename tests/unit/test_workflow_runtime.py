import asyncio

import pytest

from scholarai.application.orchestration.runtime import RunStatus, WorkflowRunManager


@pytest.mark.asyncio
async def test_background_run_can_pause_and_resume() -> None:
    manager = WorkflowRunManager()
    reached_pause = asyncio.Event()
    release_step = asyncio.Event()

    async def runner(control):
        control.total_steps = 2
        control.current_step = 1
        reached_pause.set()
        await release_step.wait()
        await control.checkpoint()
        control.current_step = 2
        return {"done": True}

    await manager.start("APP-PAUSE", runner)
    await reached_pause.wait()
    paused = manager.pause("APP-PAUSE")
    assert paused["run_status"] == RunStatus.PAUSED

    release_step.set()
    await asyncio.sleep(0)
    assert manager.status("APP-PAUSE")["current_step"] == 1

    manager.resume("APP-PAUSE")
    await asyncio.sleep(0.01)
    assert manager.status("APP-PAUSE")["run_status"] == RunStatus.COMPLETED
    assert manager.status("APP-PAUSE")["progress"] == 1.0


@pytest.mark.asyncio
async def test_background_run_can_be_cancelled() -> None:
    manager = WorkflowRunManager()
    started = asyncio.Event()

    async def runner(control):
        started.set()
        await asyncio.Event().wait()
        return {}

    await manager.start("APP-CANCEL", runner)
    await started.wait()
    cancelling = manager.cancel("APP-CANCEL")
    assert cancelling["run_status"] == RunStatus.CANCELLING
    await asyncio.sleep(0)
    assert manager.status("APP-CANCEL")["run_status"] == RunStatus.CANCELLED


@pytest.mark.asyncio
async def test_failed_run_is_retryable() -> None:
    manager = WorkflowRunManager()

    async def fail(_control):
        raise ValueError("agent failed")

    await manager.start("APP-RETRY", fail)
    await asyncio.sleep(0)
    assert manager.status("APP-RETRY")["run_status"] == RunStatus.FAILED

    async def succeed(_control):
        return {"ok": True}

    await manager.start("APP-RETRY", succeed)
    await asyncio.sleep(0)
    assert manager.status("APP-RETRY")["run_status"] == RunStatus.COMPLETED
