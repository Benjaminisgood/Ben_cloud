#!/usr/bin/env bash
set -euo pipefail

PROJECT_PATH="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
export PROJECT_PATH
export APP_ID="benreel"
export APP_NAME="Benreel"
export APP_MODULE="benreel_api.main:app"
export APP_PACKAGE="benreel_api"
export DEFAULT_PORT="9500"

exec "$PROJECT_PATH/../PROJECT_STANDARDS/scripts/manage_fastapi_site.sh" "$@"
