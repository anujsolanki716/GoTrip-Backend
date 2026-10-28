#!/bin/sh
set -e
# Apply database migrations before starting the server.
if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
  alembic upgrade head
fi
exec "$@"
