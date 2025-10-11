# Docker Deployment Guide

This guide covers Docker deployment for the DMR Server.

## Docker Run Command

To deploy the DMR Server using Docker:

```bash
docker run -d \
  --name dmrserver \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  -e DJANGO_SETTINGS_MODULE=dmr.settings \
  dmrserver
```

## Docker Compose

For easier management, you can use Docker Compose:

```yaml
version: '3.8'

services:
  dmrserver:
    image: dmrserver
    container_name: dmrserver
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
    environment:
      - DJANGO_SETTINGS_MODULE=dmr.settings
    restart: unless-stopped
```

## Volume Mounts

- `./data:/app/data` - For all persistent data (media files, static files, SQLite database)

## Environment Variables

- `DJANGO_SETTINGS_MODULE` - Django settings module (default: dmr.settings)
- `SECRET_KEY` - Django secret key
- `DEBUG` - Debug mode (default: False)
- `ALLOWED_HOSTS` - Comma-separated list of allowed hosts
- `DATABASE_URL` - Database URL (default: sqlite://db.sqlite3)
- `CORS_ALLOWED_ORIGINS` - Comma-separated list of CORS allowed origins
- `CORS_ALLOW_ALL_ORIGINS` - Allow all origins for CORS (True/False, default: True)
- `CSRF_TRUSTED_ORIGINS` - Comma-separated list of CSRF trusted origins

## Accessing the Application

Once running, the application will be available at:

- Main API: <http://localhost:8000/>
- Admin Interface: <http://localhost:8000/admin/>
- API Documentation: <http://localhost:8000/schema/swagger-ui/>
