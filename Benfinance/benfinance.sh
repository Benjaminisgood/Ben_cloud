#!/usr/bin/env bash
set -euo pipefail

PROJECT_PATH="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
export PROJECT_PATH
export APP_ID="benfinance"
export APP_NAME="Benfinance"
export APP_MODULE="benfinance_api.main:app"
export APP_PACKAGE="benfinance_api"
export DEFAULT_PORT="9100"

exec "$PROJECT_PATH/../PROJECT_STANDARDS/scripts/manage_fastapi_site.sh" "$@"
