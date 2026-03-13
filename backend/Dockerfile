FROM python:3.12-slim

ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY
ARG PIP_INDEX_URL
ARG PIP_TRUSTED_HOST
ENV http_proxy=${HTTP_PROXY} \
    https_proxy=${HTTPS_PROXY} \
    no_proxy=${NO_PROXY} \
    PIP_INDEX_URL=${PIP_INDEX_URL} \
    PIP_TRUSTED_HOST=${PIP_TRUSTED_HOST}

WORKDIR /app

RUN sh -c 'set -e; \
    if [ -n "$HTTP_PROXY" ]; then \
      printf "Acquire::http::Proxy \\"%s\\";\\n" "$HTTP_PROXY" > /etc/apt/apt.conf.d/01proxy; \
      printf "Acquire::https::Proxy \\"%s\\";\\n" "$HTTPS_PROXY" >> /etc/apt/apt.conf.d/01proxy; \
      printf "Acquire::http::Proxy::deb.debian.org \\"DIRECT\\";\\n" >> /etc/apt/apt.conf.d/01proxy; \
      printf "Acquire::https::Proxy::deb.debian.org \\"DIRECT\\";\\n" >> /etc/apt/apt.conf.d/01proxy; \
      printf "Acquire::http::Proxy::security.debian.org \\"DIRECT\\";\\n" >> /etc/apt/apt.conf.d/01proxy; \
      printf "Acquire::https::Proxy::security.debian.org \\"DIRECT\\";\\n" >> /etc/apt/apt.conf.d/01proxy; \
    fi; \
    apt-get update && apt-get install -y \
      gcc \
      libpq-dev \
      curl \
      postgresql-client && \
    rm -rf /var/lib/apt/lists/* && rm -f /etc/apt/apt.conf.d/01proxy || true'

# Install uv
RUN pip install uv

# Copy pyproject.toml, README and install dependencies
COPY pyproject.toml README.md ./
RUN uv pip install --system .

ENV http_proxy= \
    https_proxy= \
    no_proxy=

# Copy application code
COPY backend/app/ ./app/
COPY backend/alembic/ ./alembic/
COPY backend/alembic.ini ./
COPY backend/entrypoint.sh ./

# Make entrypoint executable
RUN chmod +x entrypoint.sh

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 3002

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3002/health || exit 1

# Run the application with entrypoint
ENTRYPOINT ["./entrypoint.sh"]
