# Chore: Create Pod with Shared Network and Volume for 3 Grabbers + Web Master

## Chore Description

Create a Docker/Kubernetes pod configuration with:
- **Master node**: Web server allowing file uploads to temp directory, then moving files to shared queue
- **3 Grabber instances**: Worker nodes polling shared queue and executing jobs
- **Shared network**: All containers communicate on same network
- **Shared volume**: Common filesystem for queue, spool, and log directories

The web server will provide:
- File upload endpoint for submitting Python scripts as jobs
- REST API for job management and status monitoring
- Simple web UI for job submission and cluster monitoring

## Relevant Files

Use these files to resolve the chore:

- `Dockerfile` - Current container image definition for grabber instances
  - Needs modification to support both grabber and master modes
  - Will be used as base for all containers in the pod

- `docker-compose.yaml` - Current docker-compose configuration
  - Needs complete rewrite to support 1 master + 3 grabber instances
  - Must define shared volume and network configuration
  - Will orchestrate the entire pod deployment

- `src/script_grabber/grabmaster.py` - Currently a stub class
  - Needs complete implementation as web server with Flask/FastAPI
  - Must handle file uploads, job submission, and cluster monitoring
  - Will serve as the entry point for the master container

- `src/script_grabber/grabber.py` - Worker implementation
  - Already complete, no changes needed
  - Used by the 3 grabber containers

- `pyproject.toml` - Python package configuration
  - Needs additional dependencies: Flask or FastAPI, Werkzeug, etc.
  - Must add new entry point for master web server

- `README.md` - Project documentation
  - Needs new section on pod deployment and web interface usage
  - Must document API endpoints and deployment instructions

### New Files

- `src/script_grabber/web_master.py` - Web server implementation
  - Flask/FastAPI application with file upload endpoints
  - Job submission API (POST /api/jobs)
  - Job status API (GET /api/jobs, GET /api/jobs/{id})
  - Cluster status API (GET /api/status)
  - Simple HTML UI for job submission and monitoring

- `src/script_grabber/templates/index.html` - Web UI template
  - Simple HTML form for file upload
  - Job list and status display
  - Cluster monitoring dashboard

- `src/script_grabber/static/style.css` - Basic styling for web UI

- `kubernetes/pod.yaml` - Kubernetes pod definition (alternative to docker-compose)
  - Defines 4 containers in single pod
  - Shared volume configuration
  - Network and service definitions

- `tests/integration/test_web_master.py` - Integration tests for web server
  - Test file upload endpoint
  - Test job submission workflow
  - Test API endpoints

- `.env.example` - Environment variable template
  - Cluster path configuration
  - Port configuration for web server
  - Grabber names and settings

## Step by Step Tasks

IMPORTANT: Execute every step in order, top to bottom.

### 1. Update project dependencies for web server

- Add web framework and dependencies to `pyproject.toml`:
  - `flask>=3.0.0` for web server
  - `werkzeug>=3.0.0` for file handling
  - `gunicorn>=21.0.0` for production WSGI server
- Add new entry point for web master: `web-master = "script_grabber.web_master:main"`
- Update `[project.optional-dependencies]` to include web dependencies separately
- Run `uv lock` to update lock file

### 2. Implement web master server

- Create `src/script_grabber/web_master.py` with Flask application:
  - Initialize Flask app with proper configuration
  - Configure upload folder to use `/tmp/uploads` (temporary staging area)
  - Define cluster path from environment variable or command-line argument
  - Implement file upload endpoint `POST /api/jobs`:
    - Accept Python script file upload
    - Validate file extension (.py)
    - Save to temp directory with unique filename
    - Move to shared queue directory atomically
    - Return job ID and submission status
  - Implement job status endpoint `GET /api/jobs/{job_id}`:
    - Search spool directories for job status
    - Return RUNNING, DONE, FAILED, or TIMEOUT status
    - Include log file contents if available
  - Implement cluster status endpoint `GET /api/status`:
    - List all grabbers (check varlock for active grabbers)
    - Count jobs in each state (queued, running, done, failed, timeout)
    - Return cluster health metrics
  - Implement job list endpoint `GET /api/jobs`:
    - List all jobs with their current status
    - Support pagination and filtering by status
  - Implement web UI route `GET /`:
    - Serve HTML template for job submission
    - Include JavaScript for file upload and status updates
- Add proper error handling and logging
- Add CORS support for API endpoints
- Implement `main()` function to start server with configurable host/port

### 3. Create web UI templates and static files

- Create `src/script_grabber/templates/` directory
- Create `src/script_grabber/templates/index.html`:
  - HTML form for file upload with drag-and-drop support
  - Job submission button
  - Real-time job list with auto-refresh (every 5 seconds)
  - Cluster status dashboard showing:
    - Active grabbers count
    - Jobs queued, running, completed
    - Recent job history with status badges
  - Simple, clean UI with responsive design
- Create `src/script_grabber/static/` directory
- Create `src/script_grabber/static/style.css`:
  - Basic styling for form, buttons, and job list
  - Status badges (green=done, red=failed, yellow=running, blue=queued)
  - Responsive grid layout
  - Modern, minimal design

### 4. Update Dockerfile for multi-mode support

- Modify `Dockerfile` to support both grabber and web master modes:
  - Install all dependencies including web server packages
  - Copy entire project structure including templates and static files
  - Set working directory to `/app`
  - Use environment variable `MODE` to determine entry point
  - Default `ENTRYPOINT` should be configurable via CMD
- Build optimized image with proper layer caching
- Ensure uv and Python dependencies are installed correctly

### 5. Create docker-compose configuration for pod

- Rewrite `docker-compose.yaml` to define complete pod:
  - Define shared volume `cluster_data` mapped to `/cluster`
  - Define shared network `grabber_net` with bridge driver
  - Define `master` service:
    - Use same Dockerfile with command `web-master master /cluster`
    - Map port 5000:5000 for web interface
    - Mount shared volume at `/cluster`
    - Set environment variables: `FLASK_APP=script_grabber.web_master`
    - Container name: `script_grabber_master`
  - Define 3 grabber services (`grabber1`, `grabber2`, `grabber3`):
    - Use same Dockerfile with command `grabber <name> /cluster`
    - Mount shared volume at `/cluster`
    - Depend on master service
    - Container names: `script_grabber_grabber1`, `script_grabber_grabber2`, `script_grabber_grabber3`
  - All services on same `grabber_net` network
  - Add healthcheck for master service (HTTP GET on port 5000)
  - Add restart policy: `unless-stopped`

### 6. Create Kubernetes pod configuration (optional)

- Create `kubernetes/` directory
- Create `kubernetes/pod.yaml`:
  - Define Pod with 4 containers (1 master + 3 grabbers)
  - Define shared volume using `emptyDir` or `persistentVolumeClaim`
  - Define volume mounts for `/cluster` in all containers
  - Master container:
    - Command: `["web-master", "master", "/cluster"]`
    - Port: 5000
  - Grabber containers:
    - Commands: `["grabber", "grabber1", "/cluster"]` (unique names)
  - Add liveness and readiness probes
- Create `kubernetes/service.yaml`:
  - Define Service to expose web master on port 5000
  - Type: LoadBalancer or NodePort
- Create `kubernetes/pvc.yaml`:
  - Define PersistentVolumeClaim for cluster storage
  - Request appropriate storage size (e.g., 10Gi)

### 7. Create environment configuration template

- Create `.env.example` file with:
  - `CLUSTER_PATH=/cluster` - Path to shared cluster directory
  - `WEB_PORT=5000` - Port for web server
  - `GRABBER_TIMEOUT=3600` - Default job timeout in seconds
  - `UPLOAD_MAX_SIZE=10485760` - Max upload size (10MB)
  - `LOG_LEVEL=INFO` - Logging level
- Add `.env` to `.gitignore`
- Document environment variables in README

### 8. Add integration tests for web master

- Create `tests/integration/test_web_master.py`:
  - Test Flask app initialization
  - Test file upload endpoint with valid Python script:
    - Upload file via POST to `/api/jobs`
    - Verify job appears in queue directory
    - Verify API returns job ID
  - Test file upload validation:
    - Reject non-Python files
    - Reject files exceeding size limit
  - Test job status endpoint:
    - Create job in various states
    - Query `/api/jobs/{job_id}`
    - Verify correct status returned
  - Test cluster status endpoint:
    - Query `/api/status`
    - Verify response contains grabber info and job counts
  - Test job list endpoint:
    - Query `/api/jobs`
    - Verify pagination works
    - Verify filtering by status works
- Add pytest fixture for Flask test client
- Add pytest fixture for temporary cluster directory
- Use `@pytest.mark.integration` marker

### 9. Update documentation

- Update `README.md` with new "Pod Deployment" section:
  - Prerequisites (Docker, docker-compose, or Kubernetes)
  - Quick start with docker-compose:
    - `docker-compose up -d`
    - Access web UI at `http://localhost:5000`
  - Quick start with Kubernetes:
    - `kubectl apply -f kubernetes/`
    - Access web UI via service endpoint
  - Environment configuration instructions
  - Scaling instructions (adding more grabbers)
- Add "Web Interface" section:
  - Describe web UI features
  - Document API endpoints with examples:
    - `POST /api/jobs` - Submit job
    - `GET /api/jobs` - List jobs
    - `GET /api/jobs/{id}` - Get job status
    - `GET /api/status` - Cluster status
  - Include curl examples for API usage
  - Add screenshots or ASCII diagrams
- Add "Architecture" section:
  - Diagram showing master + grabbers + shared volume
  - Explain job lifecycle in pod environment
  - Describe network communication
- Update `CLAUDE.md` with:
  - Pod deployment commands
  - Web master implementation details
  - Testing web endpoints

### 10. Package web server resources

- Update `pyproject.toml` to include templates and static files:
  - Add `[tool.hatch.build.targets.wheel.force-include]` section
  - Include `src/script_grabber/templates/` directory
  - Include `src/script_grabber/static/` directory
- Ensure `MANIFEST.in` includes web resources (if needed)
- Test package building with `uv build`
- Verify templates and static files are included in wheel

### 11. Run all validation commands

Execute every validation command to ensure zero regressions and complete functionality.

## Validation Commands

Execute every command to validate the chore is complete with zero regressions.

- `uv pip install -e ".[dev]"` - Install package with all dependencies including web server
- `uv run pytest -v` - Run all tests including new web master integration tests
- `uv run pytest -m integration -k "web_master" -v` - Run web master integration tests specifically
- `uv build` - Build package and verify web resources are included
- `docker-compose build` - Build all Docker images successfully
- `docker-compose up -d` - Start pod with all services
- `docker-compose ps` - Verify all 4 containers are running (1 master + 3 grabbers)
- `curl http://localhost:5000/api/status` - Verify web server is responding and returns cluster status
- `curl http://localhost:5000/` - Verify web UI is accessible
- `docker-compose logs master` - Check master logs for errors
- `docker-compose logs grabber1` - Check grabber1 logs for errors
- `docker-compose exec master ls -la /cluster` - Verify shared volume is mounted and accessible
- `docker-compose exec grabber1 ls -la /cluster` - Verify grabbers can access shared volume
- `docker-compose down` - Clean shutdown of pod
- `uv run pytest --cov=src/script_grabber --cov-report=term-missing` - Verify test coverage remains ≥80%

## Notes

### Architecture Overview

The pod consists of 4 containers sharing a network and volume:

```
┌─────────────────────────────────────────────────────────┐
│                    Grabber Pod                          │
│                                                         │
│  ┌───────────────┐                                     │
│  │  Web Master   │ :5000 (HTTP)                        │
│  │               │                                      │
│  │  - File Upload│                                      │
│  │  - Job Submit │                                      │
│  │  - API/UI     │                                      │
│  └───────┬───────┘                                     │
│          │                                              │
│          ├── Shared Volume: /cluster ──────────────────┤
│          │   ├── queue/          (common queue)        │
│          │   ├── ctrl/<name>/    (control queues)      │
│          │   ├── spool/<name>/   (execution dirs)      │
│          │   ├── log/            (logs)                │
│          │   └── varlock/        (lock files)          │
│          │                                              │
│  ┌───────┴────────┬────────────┬────────────┐         │
│  │   Grabber 1    │ Grabber 2  │ Grabber 3  │         │
│  │                │            │            │         │
│  │  - Poll queue  │ - Poll     │ - Poll     │         │
│  │  - Execute jobs│ - Execute  │ - Execute  │         │
│  └────────────────┴────────────┴────────────┘         │
│                                                         │
│  Network: grabber_net (bridge)                         │
└─────────────────────────────────────────────────────────┘
```

### Job Submission Flow

1. User uploads Python script via web UI or API
2. Web master receives file, validates, saves to temp directory
3. Web master moves file atomically to `/cluster/queue/`
4. One of 3 grabbers polls queue and grabs the job
5. Grabber executes job, updates status in spool directory
6. Web master can query job status from spool directory
7. User can view results via web UI or API

### Security Considerations

- **File validation**: Only accept `.py` files, validate content
- **Size limits**: Enforce max upload size (10MB default)
- **Path traversal**: Sanitize filenames to prevent directory traversal attacks
- **Resource limits**: Docker container resource limits (CPU, memory)
- **Authentication**: Consider adding basic auth or API keys for production
- **HTTPS**: Use reverse proxy (nginx) for HTTPS in production

### Performance Considerations

- **Shared volume**: Use fast storage (SSD) for optimal performance
- **File operations**: Atomic moves prevent race conditions
- **Polling interval**: Default 10 seconds, configurable per grabber
- **Job timeout**: Default 3600 seconds (1 hour), configurable
- **Concurrent jobs**: Each grabber processes one job at a time (sequential)
- **Scalability**: Add more grabber containers by extending docker-compose

### Development Workflow

1. Local development: Run web master with `uv run web-master master /tmp/cluster`
2. Test file upload: `curl -F "file=@test.py" http://localhost:5000/api/jobs`
3. Monitor logs: `docker-compose logs -f`
4. Interactive debugging: `docker-compose exec master bash`
5. Hot reload: Mount source code as volume for development

### Known Limitations

- **Storage**: Shared volume size limited by Docker/Kubernetes configuration
- **Job history**: No automatic cleanup of old jobs (manual or scheduled task needed)
- **Authentication**: No built-in authentication (add nginx reverse proxy for production)
- **Job timeout**: Currently not enforced (known bug in grabber.py:140)
- **Lock file cleanup**: No automatic cleanup of stale lock files (known bug)

### Future Enhancements

- Add job priority queues (high, medium, low)
- Implement job dependencies and workflows
- Add job retry mechanisms with exponential backoff
- Implement job scheduling (cron-like syntax)
- Add real-time WebSocket updates for job status
- Implement job history database (SQLite or PostgreSQL)
- Add authentication and authorization (OAuth2, JWT)
- Implement metrics and monitoring (Prometheus, Grafana)
- Add job result caching and artifact storage
- Implement distributed tracing (OpenTelemetry)
