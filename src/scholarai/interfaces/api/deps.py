"""FastAPI dependency: fetch the composition ``Container`` off app state."""

from __future__ import annotations

from typing import cast

from fastapi import Request

from scholarai.composition import Container


def get_container(request: Request) -> Container:
    return cast(Container, request.app.state.container)
