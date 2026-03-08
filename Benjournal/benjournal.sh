#!/usr/bin/env bash
set -euo pipefail

PROJECT_PATH="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
export PROJECT_PATH
export APP_ID="benjournal"
export APP_NAME="Benjournal"
export APP_MODULE="benjournal_api.main:app"
export APP_PACKAGE="benjournal_api"
export DEFAULT_PORT="9200"

exec "$PROJECT_PATH/../PROJECT_STANDARDS/scripts/manage_fastapi_site.sh" "$@"
