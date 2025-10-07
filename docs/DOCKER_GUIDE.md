# Docker Deployment Guide

This guide covers Docker deployment for the DMR Server.

## Docker Run Command

To deploy the DMR Server using Docker:

```bash
docker run -d \
  --name dmrserver \
  -p 8000:8000 \
  -v $(pwd)/media:/app/media \
  -v $(pwd)/static:/app/static \
  -v $(pwd)/db.sqlite3:/app/db.sqlite3 \
  -e DJANGO_SETTINGS_MODULE=dmr.settings \
  -e DJANGO_CONFIGURATION=Production \
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
      - ./media:/app/media
      - ./static:/app/static
      - ./db.sqlite3:/app/db.sqlite3
    environment:
      - DJANGO_SETTINGS_MODULE=dmr.settings
      - DJANGO_CONFIGURATION=Production
    restart: unless-stopped
```

## Volume Mounts

- `./media:/app/media` - For uploaded media files
- `./static:/app/static` - For Django static files (after running `collectstatic`)
- `./db.sqlite3:/app/db.sqlite3` - For the SQLite database

## Environment Variables

- `DJANGO_SETTINGS_MODULE` - Django settings module
- `SECRET_KEY` - Django secret key
- `DEBUG` - Debug mode (True/False)
- `ALLOWED_HOSTS` - Allowed hosts for Django
- `DATABASE_URL` - Database URL (defaults to SQLite)

## Accessing the Application

Once running, the application will be available at:

- Main API: <http://localhost:8000/>
- Admin Interface: <http://localhost:8000/admin/>
- API Documentation: <http://localhost:8000/schema/swagger-ui/>
