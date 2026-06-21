# Mootion Docker Deployment Guide

## Architecture Overview

```
┌─────────────┐     ┌──────────────┐
│   Browser    │────▶│   Nginx :80  │
└─────────────┘     └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
       ┌──────────┐ ┌──────────┐ ┌──────────────┐
       │ Frontend │ │ Backend  │ │   Animation  │
       │  :3000   │ │  :8000   │ │   Engine     │
       └──────────┘ └────┬─────┘ │   :8001      │
                         │       └──────────────┘
              ┌──────────┼──────────┐
              ▼          ▼          ▼
       ┌──────────┐ ┌──────────┐ ┌──────────┐
       │PostgreSQL│ │  Redis   │ │  Minio/  │
       │  :5432   │ │  :6379   │ │   R2     │
       └──────────┘ └──────────┘ └──────────┘
```

## Prerequisites

- **Docker** v24+ & **Docker Compose** v2.20+
- **Git**
- At least **4 GB RAM** allocated to Docker (8 GB recommended)
- **30 GB** free disk space

## 1. Clone & Prepare

```bash
git clone <repository-url> mootion
cd mootion
```

## 2. Environment Configuration

### Backend (`backend/.env`)

Required variables:

```env
# Database (uses the docker-compose PostgreSQL if not set)
DATABASE_URL=postgresql://neondb_owner:password123@db:5432/neondb

# OAuth (Google)
GOOGLE_OAUTH_CLIENT_ID=your_client_id
GOOGLE_OAUTH_CLIENT_SECRET=your_client_secret
GOOGLE_OAUTH_REDIRECT_URI=http://localhost/auth/google/callback

# AI / Azure OpenAI
AZURE_OPENAI_API_KEY=your_key
AZURE_OPENAI_ENDPOINT=https://your-resource.cognitiveservices.azure.com/openai/v1/
AZURE_OPENAI_DEPLOYMENT=gpt-5.4-mini

# Gemini (for voice features)
GEMINI_API_KEY=your_key

# Object Storage (MinIO or Cloudflare R2)
R2_BUCKET=mootion
R2_ENDPOINT=https://your-endpoint.r2.cloudflarestorage.com
R2_ACCESS_KEY_ID=your_key_id
R2_SECRET_ACCESS_KEY=your_secret
R2_PUBLIC_URL=https://your-public-url.r2.dev

# Azure Computer Vision (for OCR)
AZURE_VISION_ENDPOINT=https://your-vision-resource.cognitiveservices.azure.com/
AZURE_VISION_API_KEY=your_vision_key

# Redis
REDIS_URL=redis://redis:6379/0
```

### Frontend (`frontend/.env`)

```env
GEMINI_API_KEY=your_key
NEXT_PUBLIC_API_URL=http://localhost/api
```

## 3. Build & Run

```bash
# Build all images
docker compose build

# Start all services in detached mode
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f
```

## 4. First-Time Setup

Once all containers are healthy, run database migrations and seed data:

```bash
docker compose run --rm setup
```

This will:
1. Run Alembic migrations (or auto-create tables via SQLAlchemy)
2. Seed NCERT curriculum data
3. Create default teacher user (`abc` / `abc`)

## 5. Verify Deployment

| Service        | URL                          |
|----------------|------------------------------|
| Frontend       | http://localhost             |
| Backend API    | http://localhost/api         |
| Swagger Docs   | http://localhost/api/docs    |
| Animation API  | http://localhost/video-api   |

### Health checks

```bash
curl http://localhost/api/           # Backend health
curl http://localhost:3000           # Frontend health (direct)
curl http://localhost:8001           # Animation engine health
```

## 6. Useful Commands

### View logs for a specific service

```bash
docker compose logs -f backend
docker compose logs -f worker
docker compose logs -f frontend
```

### Restart a service

```bash
docker compose restart backend
```

### Rebuild a single service

```bash
docker compose build --no-cache backend
docker compose up -d backend
```

### Run database migrations manually

```bash
docker compose run --rm backend python migration.py
```

### Reseed curriculum data

```bash
docker compose run --rm backend python seed_ncert.py
```

### Stop all services

```bash
docker compose down
```

### Stop and remove volumes (destroys all data)

```bash
docker compose down -v
```

### Run ingestion (curriculum vector embeddings)

```bash
docker compose run --rm backend python -m ingestion.ingest_all
```

## 7. Production Hardening

### SSL / TLS

Configure Nginx with Let's Encrypt. Update `nginx/nginx.conf`:

```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    location / {
        proxy_pass http://frontend:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    ...
}
```

Add a certbot sidecar or use a reverse proxy like Caddy for automatic TLS.

### Resource Limits

Add resource constraints to `docker-compose.yml`:

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: "2"
  worker:
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: "2"
  animation-engine:
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: "2"
```

### Database Backups

```bash
# Manual backup
docker exec mootion-postgres pg_dump -U neondb_owner neondb > backup_$(date +%Y%m%d).sql

# Restore
cat backup.sql | docker exec -i mootion-postgres psql -U neondb_owner neondb
```

### Monitoring

```bash
# Container resource usage
docker stats

# Backend logs (structured)
docker compose logs --tail=100 backend | grep -i error
```

## 8. Troubleshooting

### "Backend health check failing"

```bash
# Check backend logs
docker compose logs backend

# Ensure DB is ready
docker compose logs db

# Check env vars
docker compose exec backend env | grep DATABASE_URL
```

### "Frontend shows blank page"

```bash
# Check if assets built correctly
docker compose logs frontend

# Verify nginx config
docker compose exec nginx nginx -t
```

### "OCR returns 501 Not Implemented"

Ensure these are set in `backend/.env`:
```
AZURE_VISION_ENDPOINT=...
AZURE_VISION_API_KEY=...
```

### "OpenAI / AI calls returning errors"

Check that `AZURE_OPENAI_API_KEY` and `AZURE_OPENAI_ENDPOINT` are correct and the deployment name exists in your Azure resource.

### "Port 80 already in use"

Edit `docker-compose.yml` and change the nginx port mapping:

```yaml
ports:
  - "8080:80"   # Access via http://localhost:8080
```

## 9. Service Dependencies

```
nginx
  ├── frontend (needs backend healthy)
  ├── backend (needs db + redis healthy)
  └── animation-engine
backend
  ├── db (healthcheck: pg_isready)
  └── redis (healthcheck: redis-cli ping)
worker
  ├── db
  └── redis
setup (one-time)
  └── db
```

Startup order is enforced via `depends_on` with `condition: service_healthy`.

## 10. File Reference

| File                          | Purpose                                    |
|-------------------------------|--------------------------------------------|
| `backend/Dockerfile`          | Backend multi-stage build                  |
| `backend/.dockerignore`       | Backend build exclusions                   |
| `frontend/Dockerfile`         | Frontend multi-stage build                 |
| `frontend/.dockerignore`      | Frontend build exclusions                  |
| `animation-engine/dockerfile` | Animation engine build                     |
| `docker-compose.yml`          | Full-stack orchestration                   |
| `nginx/nginx.conf`            | Reverse proxy configuration                |
| `docs/deployment.md`          | This document                             |
