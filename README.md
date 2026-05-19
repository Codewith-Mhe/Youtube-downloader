# ClipFetch

> Paste a video link → pick a quality → download. No signup, no ads, no tracking.

ClipFetch is a small, fast, self-hostable video downloader for **YouTube, TikTok,
X/Twitter, and Facebook**. Extraction happens server-side via [yt-dlp](https://github.com/yt-dlp/yt-dlp);
the browser only sees opaque, short-lived download tokens.

```
┌──────────────┐      POST /api/fetch       ┌──────────────────┐
│              │ ─────────────────────────► │                  │
│  Next.js     │                            │  FastAPI         │
│  (frontend)  │ ◄───────────────────────── │  + yt-dlp        │
│              │   { formats: [{token}] }   │                  │
└──────────────┘                            └──────────────────┘
       │                                            │
       │   GET /api/download?token=…   (streamed)   │
       └────────────────────────────────────────────┘
```

---

## Table of contents

1. [Project structure](#project-structure)
2. [Local setup](#local-setup)
3. [API documentation](#api-documentation)
4. [Deployment — Render](#deployment--render)
5. [Deployment — Railway](#deployment--railway)
6. [Deployment — VPS without Docker](#deployment--vps-without-docker)
7. [Optional — Nginx reverse proxy](#optional--nginx-reverse-proxy)
8. [Security notes](#security-notes)
9. [Legal](#legal)
10. [Future improvements](#future-improvements)

---

## Project structure

```
clipfetch/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI entrypoint
│   │   ├── routes/                  # /api/fetch, /api/download, /api/health
│   │   ├── services/                # yt-dlp extractor, token store
│   │   ├── middleware/              # IP-based rate limiter (SlowAPI)
│   │   ├── schemas/                 # Pydantic models
│   │   └── utils/                   # URL validator, format helpers
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── app/                         # Next.js 14 app router
│   │   ├── page.tsx                 # Home page
│   │   ├── layout.tsx               # Root layout, fonts, SEO
│   │   ├── globals.css
│   │   ├── api/fetch/route.ts       # Proxies to FastAPI
│   │   ├── api/download/route.ts    # Streams from FastAPI
│   │   ├── privacy, terms, dmca, contact/
│   │   ├── sitemap.ts, robots.ts, not-found.tsx
│   ├── components/                  # FetcherPanel, header, footer, icons
│   ├── lib/                         # API client, platform detection, types
│   ├── package.json
│   └── .env.example
│
├── nginx.conf.example
└── README.md                        # this file
```

---

## Local setup

You need:

- **Python 3.10+**
- **Node.js 18+** (20 recommended)
- **ffmpeg** on PATH — only required if you plan to download formats that need
  remuxing. Most direct downloads work without it.

### 1. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

Backend is now on `http://127.0.0.1:8000`. Sanity check:

```bash
curl http://127.0.0.1:8000/api/health
# {"status":"ok"}
```

OpenAPI docs are at `http://127.0.0.1:8000/api/docs`.

### 2. Frontend

In a separate terminal:

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

Open <http://localhost:3000>. Paste a video URL and try it.

> The frontend talks to the backend via the `BACKEND_URL` env var. If you change
> the backend port, update `.env.local` and restart `npm run dev`.

---

## API documentation

The backend exposes three endpoints. The frontend's `/api/*` routes proxy to these.

### `POST /api/fetch`

Extract metadata and available formats for a video.

**Request**

```json
{ "url": "https://youtu.be/dQw4w9WgXcQ" }
```

**Success — 200**

```json
{
  "success": true,
  "platform": "youtube",
  "title": "Never Gonna Give You Up",
  "thumbnail": "https://i.ytimg.com/vi/.../maxresdefault.jpg",
  "duration": "03:33",
  "uploader": "Rick Astley",
  "formats": [
    {
      "formatId": "137+140",
      "quality": "1080p",
      "ext": "mp4",
      "size": "45.3MB",
      "hasAudio": true,
      "hasVideo": true,
      "note": null,
      "downloadUrl": "/api/download?token=<opaque-32-byte-token>"
    }
  ]
}
```

**Error — 4xx/5xx**

```json
{ "success": false, "message": "This video is private." }
```

Possible status codes:

| Status | Meaning |
|--------|---------|
| 400 | Invalid URL, unsupported platform, no formats available |
| 403 | Private / age-restricted / login-required |
| 404 | Removed, deleted, or unavailable |
| 429 | Rate-limited (either by us or by the source platform) |
| 451 | Geo-restricted |
| 504 | Extraction timed out |

### `GET /api/download?token=<token>`

Streams the chosen format to the client. The token is opaque and expires after
**30 minutes**. Returns the binary file with `Content-Disposition: attachment` —
the browser saves it automatically.

### `GET /api/health`

Liveness probe. Returns `{"status":"ok"}`.

---

## Deployment — Render

ClipFetch deploys to Render as **two services**. No Docker required.

### Backend (Web Service · Python)

1. **New +** → **Web Service** → connect your repo.
2. **Root Directory**: `backend`
3. **Build Command**: `pip install -r requirements.txt`
4. **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. **Environment variables**:
   ```
   ALLOWED_ORIGINS=https://your-frontend.onrender.com
   TRUST_PROXY=true
   RATE_LIMIT_FETCH=10/minute
   RATE_LIMIT_DOWNLOAD=30/minute
   EXTRACT_TIMEOUT_SECONDS=25
   ```
6. Pick the **Starter** plan or higher — the free tier sleeps and 25s extraction
   timeouts will clip against cold starts.

After deploy, note the backend URL (e.g. `https://clipfetch-api.onrender.com`).

### Frontend (Web Service · Node)

1. **New +** → **Web Service** → same repo.
2. **Root Directory**: `frontend`
3. **Build Command**: `npm install && npm run build`
4. **Start Command**: `npm run start`
5. **Environment variables**:
   ```
   BACKEND_URL=https://clipfetch-api.onrender.com
   NEXT_PUBLIC_SITE_URL=https://your-frontend.onrender.com
   ```

That's it. Visit the frontend URL.

> **ffmpeg on Render**: install it via a build hook. Add a file `backend/build.sh`:
> ```bash
> #!/usr/bin/env bash
> apt-get update && apt-get install -y ffmpeg
> pip install -r requirements.txt
> ```
> and set Build Command to `bash build.sh`. Most direct-URL formats don't need it.

---

## Deployment — Railway

Railway works the same way — two services from one repo.

### Backend

1. **New Project** → **Deploy from GitHub** → select repo.
2. **Settings** → **Root Directory**: `backend`
3. **Settings** → **Start Command**:
   `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. **Variables**: same set as the Render section above.
5. Optionally add a `nixpacks.toml` in `backend/` to pull in ffmpeg:
   ```toml
   [phases.setup]
   aptPkgs = ["ffmpeg"]
   ```

### Frontend

1. New service, same project, same repo.
2. **Root Directory**: `frontend`
3. **Build Command**: `npm install && npm run build`
4. **Start Command**: `npm run start`
5. **Variables**:
   ```
   BACKEND_URL=${{backend.RAILWAY_PUBLIC_DOMAIN}}
   NEXT_PUBLIC_SITE_URL=${{RAILWAY_PUBLIC_DOMAIN}}
   ```
   (Use Railway's reference syntax so the two services find each other.)

---

## Deployment — VPS without Docker

A small VPS (Ubuntu 22.04+, 1–2 vCPU, 2 GB RAM) is the right home for serious
traffic because video extraction is CPU- and bandwidth-heavy.

The plan: backend under **systemd**, frontend under **PM2**, optional **Nginx**
in front for HTTPS.

### 1. System prep

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3.11 python3.11-venv python3-pip git ffmpeg ufw
# Node 20 via NodeSource
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
sudo npm install -g pm2
```

### 2. Clone and configure

```bash
sudo adduser --system --group --home /opt/clipfetch clipfetch
sudo -u clipfetch -H bash <<'EOF'
cd /opt/clipfetch
git clone https://github.com/<you>/clipfetch.git app
cd app/backend
python3.11 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
cp .env.example .env
EOF
sudo -u clipfetch nano /opt/clipfetch/app/backend/.env
```

Set in `.env`:

```
ALLOWED_ORIGINS=https://clipfetch.example.com
TRUST_PROXY=true
RATE_LIMIT_FETCH=10/minute
```

### 3. Backend — systemd unit

Create `/etc/systemd/system/clipfetch-api.service`:

```ini
[Unit]
Description=ClipFetch API
After=network.target

[Service]
Type=simple
User=clipfetch
Group=clipfetch
WorkingDirectory=/opt/clipfetch/app/backend
EnvironmentFile=/opt/clipfetch/app/backend/.env
ExecStart=/opt/clipfetch/app/backend/.venv/bin/uvicorn app.main:app \
  --host 127.0.0.1 --port 8000 --workers 2 --proxy-headers --forwarded-allow-ips="*"
Restart=on-failure
RestartSec=3
# Hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ProtectHome=true
LimitNOFILE=65535

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now clipfetch-api
sudo systemctl status clipfetch-api
curl http://127.0.0.1:8000/api/health
```

### 4. Frontend — build and run with PM2

```bash
sudo -u clipfetch -H bash <<'EOF'
cd /opt/clipfetch/app/frontend
cp .env.example .env.local
# Edit BACKEND_URL=http://127.0.0.1:8000 and NEXT_PUBLIC_SITE_URL=https://clipfetch.example.com
npm install
npm run build
pm2 start npm --name clipfetch-web -- start
pm2 save
EOF

# Make PM2 start on boot (run as root once)
sudo env PATH=$PATH:/usr/bin pm2 startup systemd -u clipfetch --hp /opt/clipfetch
```

The frontend now listens on `127.0.0.1:3000`.

### 5. Firewall

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

You're done — without HTTPS yet. Continue to the Nginx section to put a real
domain and a certificate on it.

---

## Optional — Nginx reverse proxy

Nginx is **not** required for Render or Railway. On a VPS it's strongly
recommended: it gives you HTTPS, hides the internal ports, and handles large
streaming responses gracefully.

```bash
sudo apt install -y nginx certbot python3-certbot-nginx
sudo cp /opt/clipfetch/app/nginx.conf.example /etc/nginx/sites-available/clipfetch
# Edit the file: replace clipfetch.example.com with your domain
sudo ln -s /etc/nginx/sites-available/clipfetch /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d clipfetch.example.com
```

See `nginx.conf.example` in the repo root for the full config (gzip, large
download buffering off, security headers, /api/ → :8000, everything else → :3000).

---

## Security notes

A short rundown of what's already in place and what to think about before
exposing this to the open internet.

**Already in the code**

- **Strict URL allowlist** — only the four supported platforms can reach
  `yt-dlp`. See `backend/app/utils/validators.py`.
- **No shell** — `yt-dlp` is used as a Python library. There is no
  `subprocess.run`, no shell quoting, no command-injection surface.
- **Opaque tokens** — the response from `/api/fetch` carries 32-byte
  `secrets.token_urlsafe` tokens, not raw upstream URLs or format IDs. Tokens
  expire after 30 minutes and the store is bounded to 50k entries with eviction.
- **IP-based rate limits** — 10/min on `/api/fetch`, 30/min on `/api/download`
  by default (configurable). Honors `X-Forwarded-For` only when `TRUST_PROXY=true`.
- **CORS** — explicit allowlist via `ALLOWED_ORIGINS`. No wildcards.
- **No persistent storage** — downloads are streamed; nothing hits disk.
- **Hard timeouts** — 25s extraction, 30s HTTP. Slow upstreams won't pile up.
- **Sanitized exceptions** — the global exception handler returns generic
  messages; only the server log gets the traceback.
- **Security headers** — `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`,
  Referrer-Policy, Permissions-Policy in `next.config.mjs`. Add a CSP in Nginx
  if you want to go further.

**Worth doing for serious traffic**

- **Swap the in-memory token store for Redis** if you run more than one backend
  replica. The interface in `app/services/token_store.py` is small enough to
  port in ~30 lines.
- **Add a captcha** (Turnstile, hCaptcha) on `/api/fetch` if you start getting
  abusive automation. The interface is built to slot one in.
- **Outbound egress controls** — yt-dlp talks to the source platform on your
  server's IP. If you serve at scale, expect occasional 429s from upstream —
  consider rotating residential proxies or simply backing off politely.
- **Logging** — keep logs short-lived (≤14 days) and redact URLs if your
  jurisdiction is strict.

---

## Legal

ClipFetch ships with these pages, all available from the footer:

- **Privacy** (`/privacy`) — what we collect and don't collect.
- **Terms of Use** (`/terms`) — acceptable-use rules.
- **DMCA / Copyright** (`/dmca`) — takedown procedure.
- **Contact** (`/contact`) — general / copyright / security email addresses.

The homepage carries this disclaimer in a dedicated section:

> *This tool is intended only for downloading videos you own, have permission to
> use, or that are legally available for download. Users are responsible for
> respecting copyright laws and platform terms of service.*

Update the email addresses in the legal pages to your real contacts before
launch.

---

## Future improvements

Things deliberately left out to keep the first cut small and shippable:

1. **Redis-backed token store + rate limiter** for horizontal scaling.
2. **Server-side progress events** — stream extraction status over SSE so the
   UI can show "fetching metadata… resolving formats…" instead of one spinner.
3. **Audio-only "Extract MP3" button** — currently audio-only formats appear in
   the list; a one-tap action would be nicer.
4. **Subtitle download** — yt-dlp exposes subtitles trivially.
5. **Playlist support** — currently `noplaylist=true`; for playlists, return a
   chooser instead of the first entry.
6. **Captcha or proof-of-work** on `/api/fetch` to deter abuse without hurting
   real users.
7. **Caching of extraction results** for ~10 minutes — same URL → same formats →
   skip the yt-dlp roundtrip and serve fresh tokens.
8. **i18n** — the UI is structured to swap copy without surgery.
9. **PWA install** — service worker + manifest so it lives on the home screen.
10. **Server-side ffmpeg remux pipeline** for platforms where the highest
    quality requires merging separate video + audio streams. Today users get
    those as two separate downloads if they pick the highest tier.

---

Made with care. PRs welcome.
