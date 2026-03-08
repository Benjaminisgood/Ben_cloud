#!/usr/bin/env bash
set -euo pipefail

PROJECT_PATH="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
export PROJECT_PATH
export APP_ID="benlink"
export APP_NAME="Benlink"
export APP_MODULE="benlink_api.main:app"
export APP_PACKAGE="benlink_api"
export DEFAULT_PORT="9700"

exec "$PROJECT_PATH/../PROJECT_STANDARDS/scripts/manage_fastapi_site.sh" "$@"
