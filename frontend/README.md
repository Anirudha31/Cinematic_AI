# ReelForge Frontend

Plain HTML, CSS, and JavaScript — no build step, no framework, no
npm install required. Open it directly or serve it with any static
file server.

## Quick start

The frontend needs the backend running first (see `../backend/README.md`).

**Option A — just open the file:**
Double-click `index.html`, or open it in a browser directly.
(Note: some browsers restrict `fetch` from `file://` origins — if you
hit issues, use Option B instead.)

**Option B — serve it locally (recommended):**
```bash
cd frontend
python3 -m http.server 8080
```
Then visit `http://localhost:8080`.

**Option C — Docker:**
Already wired up in the project root's `docker-compose.yml`:
```bash
docker compose up --build
```
Frontend will be on port 8080, backend on port 8000.

## Configuring the backend URL

By default, the frontend auto-detects the backend:
- If served from port 8000 itself, it uses the same origin.
- Otherwise it assumes the backend is on the same hostname, port 8000.

To point at a different backend (e.g. a deployed server), add this
before the script tags in `index.html`:

```html
<script>window.REELFORGE_API_BASE = "https://your-backend.example.com";</script>
<script src="js/api.js"></script>
<script src="js/app.js"></script>
```

## File structure

```
frontend/
  index.html         Page structure
  css/styles.css      All styling (single file, CSS variables for theming)
  js/api.js           Backend API client (fetch wrappers)
  js/app.js           UI logic: composer, polling, result rendering
```

## Customizing

- **Colors / fonts**: edit the CSS variables at the top of `css/styles.css`.
- **Platform list**: pulled live from the backend's `/api/platforms` — add
  a new platform spec in the backend's `app/models/schemas.py` and it will
  automatically appear here, no frontend changes needed.
