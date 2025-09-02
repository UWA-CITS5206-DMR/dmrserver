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

## Environment Variables

Create a `.env` file in the project root for environment-specific settings:

```env
DEBUG=True
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///db.sqlite3
```

## Documentation

For comprehensive development guides and documentation, see the [`docs/`](docs/) directory:

- **[📚 Documentation Index](docs/README.md)** - Overview of all available guides
- **[🚀 Development Guide](docs/DEVELOPMENT_GUIDE.md)** - Complete setup and development workflow
- **[🔌 API Guide](docs/API_GUIDE.md)** - Comprehensive API documentation
- **[🏗️ Project Structure](docs/PROJECT_STRUCTURE.md)** - Architecture and codebase organization
- **[🧪 Testing Guide](docs/TESTING_GUIDE.md)** - Testing strategies and best practices

### Quick Links
- **API Documentation**: http://127.0.0.1:8000/schema/swagger-ui/ (when server is running)
- **Admin Interface**: http://127.0.0.1:8000/admin/

## Contributing

1. Read the [Development Guide](docs/DEVELOPMENT_GUIDE.md) for detailed setup instructions
2. Create a new branch for your feature
3. Follow the coding standards outlined in the documentation
4. Write tests following the [Testing Guide](docs/TESTING_GUIDE.md)
5. Run tests with `./start.sh test`
6. Submit a pull request

## Troubleshooting

### Common Issues

1. **Python version mismatch**: Ensure you have Python 3.12+ installed
2. **uv not found**: Make sure uv is installed and in your PATH
3. **Dependencies not syncing**: Try `uv sync --reinstall` to force reinstall

For detailed troubleshooting, see the [Development Guide](docs/DEVELOPMENT_GUIDE.md#troubleshooting).

### Getting Help

- Check the [Documentation](docs/) for comprehensive guides
- Review the [Troubleshooting section](docs/DEVELOPMENT_GUIDE.md#troubleshooting)
- Check the uv documentation: <https://docs.astral.sh/uv/>
- Django documentation: <https://docs.djangoproject.com/>
- DRF documentation: <https://www.django-rest-framework.org/>
