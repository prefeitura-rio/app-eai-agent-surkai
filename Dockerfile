
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

RUN apt-get update -y \
 && apt-get install -y build-essential \
 && rm -rf /var/lib/apt/lists/*

# Set up non-root user
RUN useradd --create-home --shell /bin/bash app
USER app
WORKDIR /home/app

# Copy project files
COPY --chown=app:app . .

# Cache busting argument - placed here to invalidate all subsequent layers
ARG CACHE_BUST=1
RUN echo "Cache bust: $CACHE_BUST"

# Install dependencies and verify uvicorn is available
RUN uv sync --frozen && \
    uv run python -c "import uvicorn; print('uvicorn imported successfully')"

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]