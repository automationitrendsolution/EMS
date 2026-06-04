# Production Deployment Guide — iTrendTASKS

This guide covers deploying iTrendTASKS with Docker Compose behind Nginx. The
same images run on a single VM, or you can split services across hosts /
managed services (MongoDB Atlas, managed Redis).

---

## 1. Prerequisites

- A Linux host with Docker Engine ≥ 24 and the Docker Compose plugin.
- A domain name pointing at the host (for TLS).
- Open ports **80** and **443**.

---

## 2. Configure environment

```bash
git clone <your-repo> itrendtasks && cd itrendtasks
cp .env.example .env
```

Edit `.env` and set **strong, unique** values:

```ini
DEBUG=False
SECRET_KEY=<64+ random chars>
JWT_SECRET=<another 64+ random chars>
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

MONGO_USERNAME=<db user>
MONGO_PASSWORD=<strong db password>

OPENAI_API_KEY=<your key>     # optional; AI degrades to heuristics if blank
```

Generate secrets quickly:

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

> With `DEBUG=False` the app auto-enables secure cookies, HSTS, nosniff, and
> `SECURE_PROXY_SSL_HEADER`. Set `SECURE_SSL_REDIRECT=True` once TLS is live.

---

## 3. First boot

```bash
docker compose up -d --build
docker compose logs -f django      # watch it wait for Mongo, migrate, seed
```

On first boot the entrypoint:
1. waits for MongoDB,
2. runs Django-internal migrations (Celery beat tables),
3. runs `collectstatic`,
4. seeds demo data **only if `RUN_SEED=1`**.

**Disable seeding for a real deployment** — set `RUN_SEED=0` in `.env`, then
create your first admin:

```bash
docker compose exec django python manage.py shell -c "
from accounts.services import create_user
create_user(full_name='Owner', email='owner@yourco.com', password='CHANGE_ME', role='super_admin')
"
```

---

## 4. TLS / HTTPS

The bundled `docker/nginx.conf` serves plain HTTP on port 80. For production TLS,
either:

**Option A — Certbot sidecar.** Add a `certbot` service and a `443` server block
that references the issued certs, then mount `/etc/letsencrypt`.

**Option B — Terminate TLS upstream** (cloud load balancer / Cloudflare) and keep
Nginx on 80 inside the private network. Ensure the proxy sets
`X-Forwarded-Proto: https` (already honored via `SECURE_PROXY_SSL_HEADER`).

Minimal 443 block to add to `docker/nginx.conf`:

```nginx
server {
    listen 443 ssl;
    server_name yourdomain.com;
    ssl_certificate     /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    # ...copy the location blocks from the port-80 server...
}
```

---

## 5. Scaling

- **Web (Daphne):** run multiple `django` replicas behind Nginx `upstream`.
  Channels uses Redis as the shared layer, so WebSockets work across replicas.
- **Celery:** scale `celery` workers with `docker compose up -d --scale celery=3`.
- **MongoDB:** for HA use a replica set or **MongoDB Atlas** — set `MONGO_HOST`
  to the SRV host and `MONGO_USERNAME/PASSWORD` accordingly (the connection
  helper passes them through). For Atlas use `mongodb+srv://` style host.
- **Redis:** point `REDIS_URL` / `CELERY_BROKER_URL` at a managed Redis.

---

## 6. Backups

```bash
# MongoDB dump
docker compose exec mongodb mongodump --username $MONGO_USERNAME \
  --password $MONGO_PASSWORD --authenticationDatabase admin --archive | \
  gzip > backup-$(date +%F).archive.gz

# Restore
gunzip -c backup-YYYY-MM-DD.archive.gz | \
  docker compose exec -T mongodb mongorestore --username $MONGO_USERNAME \
  --password $MONGO_PASSWORD --authenticationDatabase admin --archive
```

Persisted volumes: `mongodb_data`, `media_data`, `static_data`, `redis_data`.
Back up `media_data` (uploaded files) alongside the database.

---

## 7. Operations

```bash
docker compose ps                       # service health
docker compose logs -f celery-beat      # reminder scheduler
docker compose restart django           # rolling restart
docker compose pull && docker compose up -d --build   # deploy update
```

**Health checks:**
- App: `GET /login/` → 200
- API: `GET /api/swagger.json` → 200
- Mongo/Redis: compose healthchecks (`docker compose ps`)

---

## 8. Hardening checklist

- [ ] `DEBUG=False`, unique `SECRET_KEY` and `JWT_SECRET`.
- [ ] `ALLOWED_HOSTS` / `CSRF_TRUSTED_ORIGINS` restricted to your domains.
- [ ] `RUN_SEED=0`; demo accounts removed.
- [ ] MongoDB auth enabled with a strong password; port not exposed publicly.
- [ ] Redis not exposed publicly (only on the compose network).
- [ ] TLS enabled; `SECURE_SSL_REDIRECT=True`.
- [ ] Secrets stored outside the repo; any leaked key rotated.
- [ ] Regular automated backups of `mongodb_data` + `media_data`.
```
