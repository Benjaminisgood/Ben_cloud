#!/usr/bin/env bash
set -euo pipefail

PROJECT_PATH="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
export PROJECT_PATH
export APP_ID="benvinyl"
export APP_NAME="Benvinyl"
export APP_MODULE="benvinyl_api.main:app"
export APP_PACKAGE="benvinyl_api"
export DEFAULT_PORT="9400"

exec "$PROJECT_PATH/../PROJECT_STANDARDS/scripts/manage_fastapi_site.sh" "$@"
