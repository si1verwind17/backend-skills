#!/usr/bin/env bash
# Creates or updates the Cloud Scheduler jobs that drive the internal
# endpoints. Run once per environment, and again when a schedule changes:
#   PROJECT_ID=... SERVICE_URL=https://... deploy/scheduler-jobs.sh
set -euo pipefail

: "${PROJECT_ID:?}"
: "${SERVICE_URL:?}"
REGION="${REGION:-europe-west4}"
TOKEN="$(gcloud secrets versions access latest --secret=parking-internal-endpoint-token --project="$PROJECT_ID")"

upsert() {
  local name="$1" schedule="$2" path="$3"
  local args=(
    --project="$PROJECT_ID" --location="$REGION"
    --schedule="$schedule" --time-zone="Etc/UTC"
    --uri="${SERVICE_URL}${path}" --http-method=POST
    --headers="X-Internal-Token=${TOKEN}"
    --attempt-deadline=120s
  )
  if gcloud scheduler jobs describe "$name" --project="$PROJECT_ID" --location="$REGION" >/dev/null 2>&1; then
    gcloud scheduler jobs update http "$name" "${args[@]}"
  else
    gcloud scheduler jobs create http "$name" "${args[@]}"
  fi
}

upsert parking-outbox-publish        "* * * * *"    /internal/outbox/publish
upsert parking-settle-charges        "*/5 * * * *"  /internal/pricing/settle
upsert parking-schedule-reminders    "*/15 * * * *" /internal/notifications/schedule-reminders
upsert parking-dispatch-reminders    "* * * * *"    /internal/notifications/dispatch
