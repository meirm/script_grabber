# ScriptGrabber Backend

FastAPI backend for job management and cluster monitoring.

## Setup

```bash
cd apps/backend
uv sync
cp .env.sample .env
```

## Development

```bash
# Start server with hot reload
uv run python server.py

# Run tests
uv run pytest

# Add dependencies
uv add <package>
```

## API Endpoints

- `GET /` - API information
- `GET /api/health` - Health check
- `POST /api/jobs` - Submit job (upload .py file)
- `GET /api/jobs/{job_id}` - Get job status
- `GET /api/jobs` - List jobs (with pagination and filtering)
- `GET /api/status` - Cluster status

## Interactive Docs

Visit http://localhost:8000/docs for interactive API documentation.

## Environment Variables

See `.env.sample` for configuration options.
