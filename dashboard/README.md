Application Tracker dashboard: a Next.js App Router frontend for the local FastAPI backend.

## Local setup

1. Start the backend with Docker Compose and set a local API key in the root `.env`.
2. Copy `.env.example` to `.env.local`.
3. Set `API_BASE_URL` to the backend's host URL and `API_KEY` to the same key used by the backend.
4. Install dependencies and start Next.js:

```powershell
npm ci
npm run dev -- --port 3002
```

Open `http://localhost:3002`. If the backend host port is not 8000, update `API_BASE_URL` to match it.

The API key is read only by server-side Route Handlers. Never add it to a `NEXT_PUBLIC_` variable.

The proxy validates the configured backend's `/health` response before forwarding credentials. When the backend is unavailable or misconfigured, the dashboard shows an explicit connection state instead of placeholder data.
