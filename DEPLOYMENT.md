# Deploying PitWall

PitWall is a Streamlit multi-page app backed by a local SQLite database. It is
stateful only in that one file (`data/pitwall.db`) plus generated
`exports/` and `reports/`. Deployment therefore comes down to: run the app, and
persist the `data/` directory.

Pick the option that matches where you want it to live:

| Option | Best for | Effort | Cost |
|--------|----------|--------|------|
| 1. Local | Development, personal use | none | free |
| 2. Streamlit Community Cloud | Sharing a hosted link, no ops | low | free |
| 3. Docker (any host) | Production, full control | medium | varies |

---

## 1. Local

```bash
conda env create -f environment.yml      # or: pip install -r requirements.txt
conda activate f1-analytics
streamlit run app.py
```

Open http://localhost:8501. The database is created automatically on first
launch. Import Ergast CSVs on the **Settings** page (or via
`database.seed.seed_database`).

---

## 2. Streamlit Community Cloud (easiest hosted)

Free hosting straight from GitHub — good for a shareable demo.

1. Push this repo to GitHub (already done: `NikhilRCoder/f1-betting-app`).
2. Go to <https://share.streamlit.io> and sign in with GitHub.
3. **New app** → pick the repo, branch, and `app.py` as the entry point.
4. Deploy. Streamlit installs `requirements.txt` automatically and serves the
   app at a public `*.streamlit.app` URL.

**Caveats on Community Cloud:**
- The filesystem is **ephemeral** — the SQLite DB resets when the app is rebuilt
  or goes to sleep. Re-import CSVs after a cold start, or move persistence to a
  hosted database (see *Persisting data* below) for anything long-lived.
- `xgboost` needs the OpenMP runtime. Add a `packages.txt` file at the repo root
  containing a single line — `libgomp1` — so the platform installs it. (Included
  in this repo.)

---

## 3. Docker (production, any host)

A `Dockerfile` and `.dockerignore` are included. The image installs
`requirements.txt`, exposes port 8501, and has a health check on Streamlit's
`/_stcore/health` endpoint.

### Build & run

```bash
docker build -t pitwall .

# Persist the database/exports/reports in a named volume.
docker run -d --name pitwall -p 8501:8501 -v pitwall_data:/app/data pitwall
```

Open http://localhost:8501. Because `data/` is a mounted volume, your imported
data and generated files survive restarts and image rebuilds.

### Deploy the image to a host

The same image runs anywhere that accepts a container. Common paths:

- **Fly.io** — `fly launch` (detects the Dockerfile), add a volume mounted at
  `/app/data`, then `fly deploy`.
- **Render / Railway** — create a *Web Service* from the repo, Docker runtime,
  attach a persistent disk mounted at `/app/data`.
- **A VPS (any cloud VM)** — install Docker, `git clone`, `docker build`, then
  `docker run` as above behind a reverse proxy (see below).

### Put it behind HTTPS

For anything public, terminate TLS in front of the container. Minimal
`docker-compose.yml` with Caddy (automatic HTTPS):

```yaml
services:
  pitwall:
    build: .
    volumes:
      - pitwall_data:/app/data
    expose: ["8501"]
  caddy:
    image: caddy:2
    ports: ["80:80", "443:443"]
    command: caddy reverse-proxy --from your-domain.com --to pitwall:8501
    volumes:
      - caddy_data:/data
volumes:
  pitwall_data:
  caddy_data:
```

---

## Configuration

- **`.streamlit/config.toml`** (included) sets headless mode, binds `0.0.0.0`,
  disables usage stats, and applies the dark theme. Override any value with an
  environment variable, e.g. `STREAMLIT_SERVER_PORT=9000`.
- **Log level** — set `LOG_LEVEL=DEBUG` (read by `config/settings.py`).
- **Database location** — defaults to `data/pitwall.db`; keep that path on the
  persistent volume.

---

## Persisting data

The default SQLite file is perfect for single-user and small-team use. To make
data durable in ephemeral/hosted environments you have two clean options:

1. **Mount a persistent volume** at `/app/data` (Docker / Fly / Render) — no code
   change; the SQLite file simply lives on durable storage.
2. **Back up the DB** — copy `data/pitwall.db` out on a schedule (it is a single
   file), or use the **Settings** page's database section.

The architecture already isolates data access behind `database/connection.py` and
the repositories, so a future move to Postgres would only touch that layer — the
services, models and pages are unaffected.

---

## Operational checklist

- [ ] `pytest` green before deploy (`pytest -q`).
- [ ] `requirements.txt` (and `packages.txt` for `libgomp1`) present.
- [ ] Persistent volume mounted at `/app/data`.
- [ ] TLS/reverse proxy in front of the container for public access.
- [ ] Ergast CSVs imported once via **Settings**, or a seed step in your deploy.
- [ ] `LOG_LEVEL` and any port overrides set as environment variables.
