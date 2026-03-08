#!/usr/bin/env bash
set -euo pipefail

PROJECT_PATH="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
export PROJECT_PATH
export APP_ID="benself"
export APP_NAME="Benself"
export APP_MODULE="benself_api.main:app"
export APP_PACKAGE="benself_api"
export DEFAULT_PORT="9800"

exec "$PROJECT_PATH/../PROJECT_STANDARDS/scripts/manage_fastapi_site.sh" "$@"
