FROM python:3.12.0-slim-buster

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install script_grabber using uv
RUN uv pip install --system --no-cache script-grabber

ENTRYPOINT ["grabber"]