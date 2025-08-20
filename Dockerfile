
FROM python:3.12-slim

# Cache busting argument
ARG CACHE_BUST
RUN echo "Cache bust: $CACHE_BUST"

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

RUN apt-get update -y \
 && apt-get install -y build-essential \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ADD . /app

RUN uv sync

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]