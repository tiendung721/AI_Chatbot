FROM python:3.12.10-slim-bookworm@sha256:fd95fa221297a88e1cf49c55ec1828edd7c5a428187e67b5d1805692d11588db AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_LINK_MODE=copy
RUN pip install --no-cache-dir uv==0.13.7
WORKDIR /app/apps/api
COPY apps/api/pyproject.toml apps/api/uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev --no-install-project
COPY apps/api/src ./src
COPY apps/api/migrations ./migrations
COPY apps/api/alembic.ini ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev
ENV PATH="/app/apps/api/.venv/bin:$PATH"
RUN useradd --uid 10001 --create-home citizen
USER citizen
CMD ["uvicorn", "citizen_ai.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]

FROM base AS parser
USER root
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-vie tesseract-ocr-eng fonts-dejavu-core && rm -rf /var/lib/apt/lists/*
USER citizen
CMD ["uvicorn", "citizen_ai.ingestion.parser_app:app", "--host", "0.0.0.0", "--port", "8100", "--no-access-log"]

FROM parser AS test
USER root
COPY apps/api/tests ./tests
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen
USER citizen
CMD ["pytest", "-q", "-p", "no:cacheprovider"]
