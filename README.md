# Digital Medical Records (DMR) Backend

A Django REST API backend for digital medical record simulation.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) - Fast Python package installer and resolver

## Quick Start

### 1. Install uv (if not already installed)

```bash
# On macOS and Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# On Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or via pip
pip install uv
```

### 2. Setup the Project

```bash
# Clone the repository
git clone https://github.com/UWA-CITS5206-DMR/dmrserver
cd dmrserver

# Install dependencies and create virtual environment
uv sync

# Activate the virtual environment
source .venv/bin/activate  # On Unix/macOS
# or
.venv\Scripts\activate     # On Windows
```

### 3. Environment Configuration

You must configure the `.env` file before running database migrations, otherwise the setup will fail.

```bash
# Copy the example environment file
cp .env.example .env
```

**Important:**

- The `.env` file is ignored by git and should never be committed
- For production, generate a secure `SECRET_KEY` using:

  ```bash
  python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
  ```

- Set `DEBUG=False` in production
- Configure `ALLOWED_HOSTS` appropriately for your deployment environment

### 4. Database Setup

The project automatically creates the necessary `data/` directory for the database, media files, and static files when Django initializes. You don't need to create this directory manually.

```bash
# Run database migrations
# This will create the SQLite database in the data/ directory
uv run python manage.py migrate

# Create a superuser (optional but recommended)
uv run python manage.py createsuperuser
```

**Note:** The database file will be created at `data/db.sqlite3` by default. The `data/` directory is automatically created on first run if it doesn't exist.

### 5. Start the Development Server

```bash
# Start the Django development server
uv run python manage.py runserver

# Server will be available at http://127.0.0.1:8000/
```

## Development Commands

### Running with uv (Recommended)

```bash
# Start development server
uv run python manage.py runserver

# Run tests
uv run python manage.py test

# Create migrations
uv run python manage.py makemigrations

# Apply migrations
uv run python manage.py migrate

# Collect static files
uv run python manage.py collectstatic
```

### Traditional Virtual Environment

If you prefer using a traditional virtual environment:

```bash
# Activate the virtual environment created by uv
source .venv/bin/activate

# Now you can run commands directly
python manage.py runserver
python manage.py test
```

## API Documentation

Once the server is running, you can access:

- **API Documentation**: `http://127.0.0.1:8000/schema/swagger-ui/`
- **Admin Interface**: `http://127.0.0.1:8000/admin/`

## Docker Deployment

For production deployment using Docker:

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

For detailed Docker setup and configuration, see **[Docker Guide](docs/DOCKER_GUIDE.md)**.

## Documentation

For comprehensive development guides and documentation, see the [`docs/`](docs/) directory:

- **[Project Summary](docs/PROJECT_SUMMARY.md)** - Overview of the project architecture
- **[Development Standards](docs/DEVELOPMENT_STANDARDS.md)** - Coding standards and best practices
- **[Development Guide](docs/DEVELOPMENT_GUIDE.md)** - Complete setup and development workflow
- **[Testing Guide](docs/TESTING_GUIDE.md)** - Testing strategies and best practices
- **[Docker Guide](docs/DOCKER_GUIDE.md)** - Instructions for Docker deployment

For detailed troubleshooting, see the [Development Guide](docs/DEVELOPMENT_GUIDE.md#troubleshooting).

## Contributing

1. Create a new branch for your feature
2. Follow the coding standards outlined in the documentation
3. Write tests following the [Testing Guide](docs/TESTING_GUIDE.md)
4. Run tests with `uv run python manage.py test`
5. Submit a pull request

### Getting Help

- Check the uv documentation: <https://docs.astral.sh/uv/>
- Django documentation: <https://docs.djangoproject.com/>
- DRF documentation: <https://www.django-rest-framework.org/>
