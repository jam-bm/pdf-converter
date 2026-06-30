# Deploying to a VPS

Run the PDF Converter on a Linux VPS you own, with **Nginx** in front terminating HTTPS.
The app stack (API, Celery worker, Postgres, Redis, Flower) runs under Docker Compose and
is built directly on the server. Nginx runs on the host and proxies to the API.

```
Internet ──► Nginx (host, :80/:443, TLS) ──► api container (127.0.0.1:8000)
                                                  │
                                   postgres ◄─────┤  (internal Docker network only)
                                   redis    ◄─────┘
```

Files involved:

| File | Purpose |
|------|---------|
| `docker-compose.prod.yml` | Production stack (no host-exposed DB/Redis; API bound to localhost) |
| `deploy/nginx.conf` | Nginx reverse-proxy site config |
| `.env.prod.example` | Template for the server's `.env` (real `.env` is never committed) |

---

## 1. Get a server and point your domain at it

- Provision a VPS (DigitalOcean / Hetzner / Linode / EC2…). **2 GB RAM minimum** —
  building the image (it compiles PyMuPDF and installs Tesseract) needs headroom.
- In your DNS provider, create an **A record** for your domain (e.g. `yourdomain.com`)
  pointing to the server's public IP. Do this first so HTTPS can be issued later.

## 2. Install Docker

SSH in as a sudo user:

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER     # run docker without sudo
# log out and back in for the group change to take effect
```

## 3. Open the firewall

Only SSH and HTTP/HTTPS reach the internet. The DB/Redis/API ports stay private.

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

## 4. Clone the repo and create `.env`

```bash
sudo mkdir -p /opt/pdf-converter
sudo chown $USER:$USER /opt/pdf-converter
git clone https://github.com/<your-username>/pdf-converter.git /opt/pdf-converter
cd /opt/pdf-converter

cp .env.prod.example .env
nano .env
```

Set real values:

- `ALLOWED_ORIGINS` — `https://yourdomain.com` (your frontend origin(s))
- `POSTGRES_PASSWORD` — a strong password; put the **same** password into both
  `DATABASE_URL` and `DATABASE_SYNC_URL`

`.env` is gitignored — it won't be committed.

## 5. Build and start the stack

```bash
cd /opt/pdf-converter
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml run --rm api alembic upgrade head
```

Verify the API is up locally (it's bound to `127.0.0.1:8000`, not public yet):

```bash
docker compose -f docker-compose.prod.yml ps
curl http://127.0.0.1:8000/health        # -> {"status":"healthy"}
```

## 6. Install and configure Nginx

```bash
sudo apt update && sudo apt install -y nginx

# Install the site config
sudo cp /opt/pdf-converter/deploy/nginx.conf /etc/nginx/sites-available/pdf-converter
sudo nano /etc/nginx/sites-available/pdf-converter   # replace yourdomain.com with your domain

# Enable it, disable the default site
sudo ln -s /etc/nginx/sites-available/pdf-converter /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

sudo nginx -t          # test config
sudo systemctl reload nginx
```

Now `http://yourdomain.com/health` should return `{"status":"healthy"}`.

## 7. Enable HTTPS with Let's Encrypt

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

Certbot obtains a certificate, rewrites the Nginx config to add the HTTPS (443) server
block plus an HTTP→HTTPS redirect, and reloads Nginx. Renewal is automatic (a systemd
timer). Test renewal with:

```bash
sudo certbot renew --dry-run
```

Visit `https://yourdomain.com/health` — done.

---

## Updating after code changes

```bash
cd /opt/pdf-converter
git pull
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml run --rm api alembic upgrade head
```

## Operations

**Logs**

```bash
docker compose -f docker-compose.prod.yml logs -f api worker
```

**Scale workers** (each worker container runs 2 conversions in parallel)

```bash
docker compose -f docker-compose.prod.yml up -d --scale worker=3
```

**Flower dashboard** (bound to localhost). From your laptop:

```bash
ssh -L 5555:localhost:5555 <user>@<server>
# open http://localhost:5555
```

**Back up the database**

```bash
docker compose -f docker-compose.prod.yml exec postgres \
  pg_dump -U pdfuser pdfconverter > backup-$(date +%F).sql
```

---

## Security notes

- Postgres (`5432`) and Redis (`6379`) are **not** published to the host — internal
  Docker network only. (The dev `docker-compose.yml` does expose them; the prod file
  deliberately does not.)
- The API is bound to `127.0.0.1:8000`, reachable only by the host's Nginx.
- Secrets live only in the server's gitignored `.env`.

### Worth doing next

- Automate DB backups (cron + `pg_dump`).
- Put basic auth in front of Flower, or keep it tunnel-only as above.
- Consider a managed Postgres for production durability.
