# syntax=docker/dockerfile:1

# ---- builder: install runtime deps + the app package into a venv ----
FROM python:3.12-slim AS builder

# Override at build time (compose passes a China mirror on the ECS host).
# Defaults to the official index so CI / overseas builds are unaffected.
ARG PIP_INDEX_URL=https://pypi.org/simple

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /src

# Copy only what the package needs to build (keeps cache stable across test-only edits).
COPY pyproject.toml ./
COPY app ./app

# Non-editable install: pulls in fastapi/uvicorn/neo4j/pydantic and installs the `app`
# package into the venv. dev extras (pytest/httpx) are intentionally excluded.
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --index-url "${PIP_INDEX_URL}" --upgrade pip \
    && /opt/venv/bin/pip install --index-url "${PIP_INDEX_URL}" .

# ---- runtime: only the venv, run as non-root ----
FROM python:3.12-slim AS runtime

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN groupadd -r app && useradd -r -g app app

COPY --from=builder /opt/venv /opt/venv

USER app

EXPOSE 8000

# FastAPI serves /openapi.json once the app is up; use it as a cheap liveness probe.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/openapi.json').status==200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
