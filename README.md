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

### 3. Database Setup

```bash
# Run database migrations
uv run python manage.py migrate

# Create a superuser (optional)
uv run python manage.py createsuperuser
```

### 4. Start the Development Server

```bash
# Start the Django development server
uv run python manage.py runserver

# Server will be available at http://127.0.0.1:8000/
```

## Development Commands

### Running with uv (Recommended)

```bash
# Run Django management commands
uv run python manage.py <command>

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

## Dependency Management

This project uses [uv](https://docs.astral.sh/uv/) for fast and reliable dependency management.

### Adding Dependencies

```bash
# Add a new dependency
uv add package-name

# Add a development dependency
uv add --dev package-name

# Add a specific version
uv add "package-name==1.0.0"
```

### Updating Dependencies

```bash
# Update all dependencies
uv lock --upgrade

# Update a specific package
uv lock --upgrade-package package-name

# Sync dependencies after updates
uv sync
```

### Removing Dependencies

```bash
# Remove a dependency
uv remove package-name
```

## API Documentation

Once the server is running, you can access:

- **API Documentation**: `http://127.0.0.1:8000/api/schema/swagger-ui/`
- **Admin Interface**: `http://127.0.0.1:8000/admin/`

## Environment Variables

Create a `.env` file in the project root for environment-specific settings:

```env
DEBUG=True
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///db.sqlite3
```

## Contributing

1. Create a new branch for your feature
2. Make your changes
3. Add dependencies with `uv add` if needed
4. Run tests with `uv run python manage.py test`
5. Submit a pull request

## Troubleshooting

### Common Issues

1. **Python version mismatch**: Ensure you have Python 3.12+ installed
2. **uv not found**: Make sure uv is installed and in your PATH
3. **Dependencies not syncing**: Try `uv sync --reinstall` to force reinstall

### Getting Help

- Check the [uv documentation](https://docs.astral.sh/uv/)
- Django documentation: https://docs.djangoproject.com/
- DRF documentation: https://www.django-rest-framework.org/
