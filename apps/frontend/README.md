# ScriptGrabber Frontend

Modern web interface for ScriptGrabber job management built with Vite + TypeScript.

## Setup

```bash
cd apps/frontend
npm install
```

## Development

```bash
# Start dev server (with hot reload)
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## Features

- 📁 Drag & drop file upload
- 📊 Real-time cluster status monitoring
- 🔄 Auto-refresh every 5 seconds
- 📋 Job list with filtering
- 🔍 Job details viewer
- 📱 Responsive design

## Environment

The frontend proxies API requests to the backend (http://localhost:8000) via Vite proxy configuration.

For production deployment, configure NGINX or similar to proxy `/api` requests to the backend service.
