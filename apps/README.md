# ScriptGrabber Web Interface

Modern web interface for ScriptGrabber distributed job execution with backend API and frontend dashboard.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Podman Pod                           │
│                                                         │
│  ┌─────────────┐           ┌──────────────┐           │
│  │   Backend   │ ←────────→ │   Frontend   │           │
│  │   (FastAPI) │  :8000     │   (Vite)     │  :5173    │
│  │             │            │              │           │
│  │  File Upload│            │  Job Monitor │           │
│  │  Job API    │            │  Dashboard   │           │
│  └──────┬──────┘            └──────────────┘           │
│         │                                               │
│         ├── Shared Volume: /cluster ──────────────────┤
│         │   ├── queue/          (common queue)         │
│         │   ├── ctrl/<name>/    (control queues)       │
│         │   ├── spool/<name>/   (execution dirs)       │
│         │   ├── log/            (logs)                 │
│         │   └── varlock/        (lock files)           │
│         │                                               │
│  ┌──────┴───────┬─────────────┬─────────────┐         │
│  │  Grabber 1   │  Grabber 2  │  Grabber 3  │         │
│  │              │             │             │         │
│  │  Poll queue  │  Poll       │  Poll       │         │
│  │  Execute     │  Execute    │  Execute    │         │
│  └──────────────┴─────────────┴─────────────┘         │
│                                                         │
│  Network: grabber-net (shared)                         │
└─────────────────────────────────────────────────────────┘
```

## Quick Start

### Option 1: Local Development

Start backend and frontend locally (no containers):

```bash
# 1. Install dependencies
cd apps/backend && uv sync && cd ../..
cd apps/frontend && npm install && cd ../..

# 2. Start both services
./scripts/start.sh
```

Access:
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

### Option 2: Podman Pod

Run complete system in containers with shared volume:

```bash
# 1. Build and create pod
./scripts/create-pod.sh

# 2. In separate terminal, start frontend
cd apps/frontend
npm run dev
```

Access same URLs as above.

## Project Structure

```
apps/
├── backend/                # FastAPI backend
│   ├── core/              # Core modules
│   │   ├── models.py      # Pydantic models
│   │   └── job_manager.py # Job management logic
│   ├── server.py          # FastAPI app
│   └── pyproject.toml     # Python dependencies
│
└── frontend/              # Vite + TypeScript frontend
    ├── src/
    │   ├── api.ts         # API client
    │   ├── types.d.ts     # TypeScript types
    │   └── main.ts        # App entry point
    ├── index.html         # HTML template
    ├── vite.config.ts     # Vite configuration
    └── package.json       # Node dependencies
```

## API Endpoints

- `POST /api/jobs` - Submit job (upload .py file)
- `GET /api/jobs/{job_id}` - Get job status
- `GET /api/jobs` - List jobs (with filtering and pagination)
- `GET /api/status` - Cluster status and metrics
- `GET /api/health` - Health check

## Features

### Backend (FastAPI)
- ✅ File upload with validation
- ✅ Job submission to shared queue
- ✅ Job status tracking
- ✅ Cluster monitoring
- ✅ RESTful API with OpenAPI docs
- ✅ CORS support
- ✅ Async/await for performance

### Frontend (Vite + TypeScript)
- ✅ Drag & drop file upload
- ✅ Real-time job monitoring
- ✅ Auto-refresh every 5 seconds
- ✅ Job filtering by status
- ✅ Detailed job viewer
- ✅ Cluster dashboard with metrics
- ✅ Responsive design

## Development

### Backend

```bash
cd apps/backend

# Install dependencies
uv sync

# Start server (with hot reload)
uv run python server.py

# Run tests
uv run pytest

# Add dependencies
uv add <package>
```

### Frontend

```bash
cd apps/frontend

# Install dependencies
npm install

# Start dev server (with hot reload)
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## Pod Management

### Create and start pod

```bash
./scripts/create-pod.sh
```

### View pod status

```bash
podman pod ps
podman ps --pod
```

### View logs

```bash
# All pod logs
podman pod logs script-grabber-pod

# Specific container logs
podman logs script-grabber-master
podman logs script-grabber-grabber1
podman logs script-grabber-grabber2
podman logs script-grabber-grabber3
```

### Stop pod

```bash
./scripts/stop-pod.sh
# or
podman pod stop script-grabber-pod
```

### Remove pod and volume

```bash
podman pod rm script-grabber-pod
podman volume rm cluster-data
```

## Environment Configuration

Backend environment variables (`apps/backend/.env`):

```bash
CLUSTER_PATH=/cluster        # Path to shared cluster directory
HOST=0.0.0.0                # Server bind address
PORT=8000                   # Server port
MAX_UPLOAD_SIZE=10485760    # Max file size (10MB)
LOG_LEVEL=INFO              # Logging level
```

## Job Submission Flow

1. User uploads Python script via web UI or API
2. Backend validates file (.py extension, size limit)
3. Backend saves file to `/cluster/queue/` with unique ID
4. One of 3 grabbers polls queue and grabs the job
5. Grabber executes job, writes output to spool directory
6. User can view job status and results via web UI or API

## API Examples

### Submit job

```bash
curl -X POST http://localhost:8000/api/jobs \
  -F "file=@example.py"
```

### Get job status

```bash
curl http://localhost:8000/api/jobs/example.py_20231215_123456_000000
```

### List all jobs

```bash
curl http://localhost:8000/api/jobs
```

### Get cluster status

```bash
curl http://localhost:8000/api/status
```

## Troubleshooting

**Backend won't start:**
- Check Python version: `python --version` (requires 3.10+)
- Verify dependencies: `cd apps/backend && uv sync`
- Check ports: `lsof -i :8000`

**Frontend won't start:**
- Check Node version: `node --version` (requires 18+)
- Verify dependencies: `cd apps/frontend && npm install`
- Check ports: `lsof -i :5173`

**Pod won't start:**
- Check Podman: `podman --version`
- View logs: `podman pod logs script-grabber-pod`
- Check volume: `podman volume inspect cluster-data`

**CORS errors:**
- Ensure backend is running on port 8000
- Check vite.config.ts proxy settings
- Verify CORS middleware in server.py

## Security Considerations

- File validation: Only `.py` files accepted
- Size limits: 10MB default (configurable)
- Path traversal: Filenames sanitized
- Resource limits: Set Docker/Podman constraints
- Authentication: Add reverse proxy for production
- HTTPS: Use nginx or Traefik for SSL/TLS

## Performance

- Shared volume: Use fast storage (SSD recommended)
- Polling interval: 10 seconds default per grabber
- Job timeout: 3600 seconds default (1 hour)
- Concurrent jobs: 1 per grabber (sequential execution)
- Auto-refresh: 5 seconds in web UI

## Scaling

Add more grabbers to the pod:

```bash
podman run -dt \
    --pod script-grabber-pod \
    --name script-grabber-grabber4 \
    -v cluster-data:/cluster:Z \
    script-grabber:latest \
    grabber4 /cluster --job-timeout 3600
```

## License

MIT License - see main project LICENSE file
