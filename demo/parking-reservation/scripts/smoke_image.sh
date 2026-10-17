#!/usr/bin/env bash
# Builds the image and runs it against a throwaway Postgres on a host port in 55432-55499.
set -euo pipefail
PORT_DB=${SMOKE_DB_PORT:-55441}
PORT_APP=${SMOKE_APP_PORT:-55442}
cleanup() { docker rm -f pr-smoke-pg pr-smoke-app >/dev/null 2>&1 || true; }
trap cleanup EXIT
cleanup
docker build -q -t parking-reservation:smoke "$(dirname "$0")/.." >/dev/null
docker run -d --name pr-smoke-pg -e POSTGRES_PASSWORD=pw -p "$PORT_DB:5432" postgres:18.6 >/dev/null
for _ in $(seq 1 30); do docker exec pr-smoke-pg pg_isready -U postgres >/dev/null 2>&1 && break; sleep 1; done
sleep 2
ENV=(-e "DATABASE_URL=postgresql://postgres:pw@127.0.0.1:$PORT_DB/postgres" -e IDENTITY_HEADER=x-claims
     -e GCP_PROJECT=proj -e SCHEDULER_SERVICE_ACCOUNT=s@proj.iam.gserviceaccount.com
     -e RELAY_AUDIENCE=https://svc -e PUBSUB_EMULATOR_HOST=127.0.0.1:1 -e "PORT=$PORT_APP")
docker run --rm --network host "${ENV[@]}" parking-reservation:smoke python -m parking_reservation.migrate_main
docker run -d --name pr-smoke-app --network host "${ENV[@]}" parking-reservation:smoke >/dev/null
for _ in $(seq 1 20); do curl -sf "localhost:$PORT_APP/healthz" >/dev/null && break; sleep 1; done
curl -sf "localhost:$PORT_APP/healthz" | grep -q '"ok"'
test "$(curl -s -o /dev/null -w '%{http_code}' -X POST "localhost:$PORT_APP/internal/relay")" = 401
echo "image smoke test passed"
