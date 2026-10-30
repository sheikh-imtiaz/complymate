# One image: API + workers.
#   AWS Lambda: entrypoint detects AWS_LAMBDA_RUNTIME_API and runs awslambdaric with the handler from CMD
#               (api_handler | worker_handler | ws_handler, set per function in Terraform image_config).
#   Azure Container Apps / local: runs uvicorn (API) or the worker loop (CMD "worker").
FROM python:3.12-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# WeasyPrint runtime libraries (pango, harfbuzz) and fonts for PDF export
RUN apt-get update && apt-get install -y --no-install-recommends \
      libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libffi8 fonts-dejavu-core shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /usr/local/bin/uv

WORKDIR /app

FROM base AS builder
COPY pyproject.toml uv.lock* README.md ./
RUN uv sync --frozen --no-dev --no-install-project --extra azure || uv sync --no-dev --no-install-project --extra azure
COPY src ./src
RUN uv sync --frozen --no-dev --extra azure || uv sync --no-dev --extra azure

FROM base AS runtime
RUN useradd --uid 10001 --create-home app
COPY --from=builder /app/.venv /app/.venv
COPY --chown=app:app src ./src
COPY --chown=app:app migrations ./migrations
COPY --chown=app:app alembic.ini ./
COPY --chown=app:app templates ./templates
COPY --chown=app:app seed ./seed
COPY --chown=app:app scripts ./scripts
COPY --chown=app:app docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app/src" \
    TEMPLATES_DIR="/app/templates" \
    PORT=8080

USER app
EXPOSE 8080
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["complymate.lambda_handlers.api_handler"]
