#!/bin/sh
# Crea el esquema y, si se indica SEED_KB y la KB está vacía, la carga. Luego ejecuta el comando.
set -e

alembic upgrade head

if [ -n "$SEED_KB" ]; then
    python -m scripts.seed_tenant "$SEED_KB" || echo "seed omitido (la KB ya tiene bloques o falló)"
fi

exec "$@"
