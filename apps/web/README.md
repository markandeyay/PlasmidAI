# PlasmidAI Web

Next.js frontend for the Phase 4 design workspace. It provides a chat-style interface, plasmid map rendering, and export actions against the FastAPI backend.

## Development

Install dependencies from this directory:

```powershell
npm ci
```

Run the web dev server:

```powershell
npm run dev
```

From the repository root, the same command is available through:

```powershell
make serve-web
```

The web server defaults to `http://127.0.0.1:3000`.

## Environment

`NEXT_PUBLIC_API_URL` points the browser at the FastAPI backend.

```powershell
$env:NEXT_PUBLIC_API_URL = "http://127.0.0.1:8000"
```

If unset, the app uses `http://127.0.0.1:8000`.

## Tests

Run the production build:

```powershell
npm run build
```

Run browser integration tests:

```powershell
npx playwright install chromium
npm run test:e2e
```

The default Playwright test mocks the API routes in-browser, so it does not require Docker, Redis, a running FastAPI process, or model inference.
