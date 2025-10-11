FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:/root/.cargo/bin:/usr/local/bin:/usr/bin:/bin:${PATH}"

# Install dependencies first to leverage Docker cache
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen
ENV PATH="/app/.venv/bin:${PATH}"
# Copy the rest of the application code
COPY . .

# Create directories for persistent data (media, static)
RUN mkdir -p /app/data/media /app/data/static
VOLUME ["/app/data"]

# Set environment variables
ENV DJANGO_SETTINGS_MODULE=dmr.settings

EXPOSE 8000

# Run gunicorn through uv for production
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120", "dmr.wsgi:application"]
