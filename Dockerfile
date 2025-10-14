FROM python:3.12

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy source code
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Install script_grabber from local source with dev dependencies
RUN uv pip install --system --no-cache .[dev]

ENTRYPOINT ["grabber"]