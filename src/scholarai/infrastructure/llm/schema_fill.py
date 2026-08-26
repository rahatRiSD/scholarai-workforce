"""Generic "best-effort" instance construction for a Pydantic model.

Used only by the offline LLM client (see ``offline_client.py``) to turn a
context dict into a schema-valid object without calling any network API.
Field values are copied from the context dict when the names match; anything
left over gets a type-appropriate, clearly-inert default. This is what lets
one offline client serve every agent's response schema without per-agent
special-casing.
"""

from __future__ import annotations

import enum
import typing
from typing import Any, get_args, get_origin

from pydantic import BaseModel


def _default_for_annotation(annotation: Any) -> Any:
    origin = get_origin(annotation)

    if origin is typing.Union:
        args = [a for a in get_args(annotation) if a is not type(None)]
        return _default_for_annotation(args[0]) if args else None

    if origin in (tuple, list):
        return () if origin is tuple else []

    if origin is dict:
        return {}

    if isinstance(annotation, type):
        if issubclass(annotation, enum.Enum):
            return next(iter(annotation))
        if issubclass(annotation, BaseModel):
            return fill_model(annotation, {})
        if annotation is bool:
            return False
        if annotation is int:
            return 0
        if annotation is float:
            return 0.0
        if annotation is str:
            return ""

    return None


def fill_model(model_cls: type[BaseModel], context: dict[str, Any]) -> BaseModel:
    """Build a valid instance of ``model_cls`` from whatever matches in ``context``."""
    values: dict[str, Any] = {}
    for name, field in model_cls.model_fields.items():
        if name in context:
            values[name] = context[name]
        elif not field.is_required():
            continue  # let Pydantic apply the model's own default
        else:
            values[name] = _default_for_annotation(field.annotation)
    return model_cls.model_validate(values)
