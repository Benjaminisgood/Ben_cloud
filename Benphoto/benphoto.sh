#!/usr/bin/env bash
set -euo pipefail

PROJECT_PATH="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
export PROJECT_PATH
export APP_ID="benphoto"
export APP_NAME="Benphoto"
export APP_MODULE="benphoto_api.main:app"
export APP_PACKAGE="benphoto_api"
export DEFAULT_PORT="9300"

exec "$PROJECT_PATH/../PROJECT_STANDARDS/scripts/manage_fastapi_site.sh" "$@"
