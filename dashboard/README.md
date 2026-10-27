# NeuroGraph-X dashboard (M7)

React with Vite, JavaScript, Node.js 24. Decided in `docs/decisions/0012-dashboard-stack.md`,
which also holds the Streamlit fallback rule.

The dashboard is a client of the REST API only. It never reads files under `data/`, `runs/`
or `db/`. In development and in `npm run preview`, Vite forwards `/api/...` to the FastAPI
server at `http://127.0.0.1:8000` and removes the `/api` prefix (`vite.config.js`).

## Run it

From the repository root, in one terminal, start the API:

```bash
python -m uvicorn neurographx.api.main:app --reload
```

In a second terminal:

```bash
cd dashboard
npm ci            # first time, and whenever package-lock.json changes
npm run dev       # http://localhost:5173
```

The footer of every page shows the result of `GET /health`. If the API is not running it
says so in plain language instead of leaving a blank page.

## Checks

```bash
npm run lint
npm run build
```

## Layout

```
src/api/client.js      the only module that calls the API
src/components/        layout, research-use notice, API status
src/pages/             Overview, Participants, Analysis, History, Models, Exclusions, About
vite.config.js         dev and preview proxy for /api
.npmrc                 save-exact=true, so versions are pinned like requirements.txt
.nvmrc                 Node.js major version
```

Scaffolded with create-vite 9.3.1 (`--template react --eslint`), then trimmed. Versions are
exact in `package.json`; `package-lock.json` is committed and CI installs with `npm ci`.
