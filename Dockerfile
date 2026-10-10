FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.12 /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
COPY prompts ./prompts
COPY evals/recordings ./evals/recordings
RUN uv sync --locked --no-dev
ENV OTEL_CONSOLE=0
EXPOSE 8000
USER nobody
CMD ["/app/.venv/bin/uvicorn", "service.api:app", "--host", "0.0.0.0", "--port", "8000"]
