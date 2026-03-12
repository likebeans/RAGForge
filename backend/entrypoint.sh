#!/bin/bash
set -e

echo "=== YaoYan Backend Startup ==="

# Wait for database to be ready
if [[ "$DATABASE_URL" == *"sqlite"* ]]; then
    echo "Using SQLite database, skipping PG network wait."
else
    echo "Waiting for database at ${DB_HOST:-host.docker.internal}:${DB_PORT:-5435}..."
    MAX_RETRIES=30
    RETRY_COUNT=0
    while ! pg_isready -h ${DB_HOST:-host.docker.internal} -p ${DB_PORT:-5435} -U ${DB_USER:-kb} -q; do
        RETRY_COUNT=$((RETRY_COUNT + 1))
        if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
            echo "Database connection failed after $MAX_RETRIES attempts, starting anyway..."
            break
        fi
        echo "Database is not ready, waiting... (attempt $RETRY_COUNT/$MAX_RETRIES)"
        sleep 2
    done
    echo "Database connection check completed!"
fi

# Run database migrations
echo "Running database migrations..."
alembic upgrade head
echo "Migrations completed!"

# Start the application
echo "Starting FastAPI application..."
exec uvicorn app.main:app --host 0.0.0.0 --port 3002
