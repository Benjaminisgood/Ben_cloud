#!/usr/bin/env bash
set -euo pipefail

PROJECT_PATH="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
export PROJECT_PATH
export APP_ID="benprefs"
export APP_NAME="Benprefs"
export APP_MODULE="benprefs_api.main:app"
export APP_PACKAGE="benprefs_api"
export DEFAULT_PORT="8800"

exec "$PROJECT_PATH/../PROJECT_STANDARDS/scripts/manage_fastapi_site.sh" "$@"
