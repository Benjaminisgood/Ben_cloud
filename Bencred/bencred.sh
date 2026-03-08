#!/usr/bin/env bash
set -euo pipefail

PROJECT_PATH="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
export PROJECT_PATH
export APP_ID="bencred"
export APP_NAME="Bencred"
export APP_MODULE="bencred_api.main:app"
export APP_PACKAGE="bencred_api"
export DEFAULT_PORT="9600"

exec "$PROJECT_PATH/../PROJECT_STANDARDS/scripts/manage_fastapi_site.sh" "$@"
