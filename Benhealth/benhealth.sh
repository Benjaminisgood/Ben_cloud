#!/usr/bin/env bash
set -euo pipefail

PROJECT_PATH="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
export PROJECT_PATH
export APP_ID="benhealth"
export APP_NAME="Benhealth"
export APP_MODULE="benhealth_api.main:app"
export APP_PACKAGE="benhealth_api"
export DEFAULT_PORT="8900"

exec "$PROJECT_PATH/../PROJECT_STANDARDS/scripts/manage_fastapi_site.sh" "$@"
