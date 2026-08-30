# ScholarAI Workforce - backend API image.
#
# Multi-stage build: a `builder` stage resolves dependencies into a virtual
# environment, and the final stage copies only that venv + the source tree,
# so the shipped image doesn't carry build toolchains.

FROM python:3.12-slim AS builder

WORKDIR /build

RUN pip install --no-cache-dir --upgrade pip

COPY pyproject.toml README.md ./
COPY src ./src

# Editable-less install: resolve real dependencies into a venv we can copy
# forward whole into the runtime stage.
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir .


FROM python:3.12-slim AS runtime

RUN useradd --create-home --uid 1000 scholarai
WORKDIR /app

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY --from=builder /opt/venv /opt/venv
COPY src ./src
COPY data ./data
COPY ui ./ui
COPY pyproject.toml README.md ./

RUN mkdir -p /app/data/uploads && chown -R scholarai:scholarai /app

USER scholarai
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import os, httpx; httpx.get('http://localhost:' + os.getenv('PORT', '8000') + '/health', timeout=3).raise_for_status()"

CMD ["sh", "-c", "exec uvicorn scholarai.interfaces.api.app:app --host 0.0.0.0 --port ${PORT:-8000}"]
