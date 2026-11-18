FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim
WORKDIR /app/backend
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --locked --no-dev --no-install-project
COPY backend/ ./
COPY rules.yaml /app/rules.yaml
RUN uv sync --locked --no-dev && uv run python -m atc.seed
EXPOSE 8000
CMD ["uv", "run", "--no-dev", "uvicorn", "atc.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
