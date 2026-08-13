#!/bin/sh
# Render sets PORT; Grafana defaults to 3000. Map PRA_PG_* for provisioning.
set -e

if [ -n "${PORT:-}" ]; then
  export GF_SERVER_HTTP_PORT="$PORT"
fi

# Prefer SQLite on Render free (no separate Grafana meta-DB required).
export GF_DATABASE_TYPE="${GF_DATABASE_TYPE:-sqlite3}"
export GF_PATHS_DATA="${GF_PATHS_DATA:-/var/lib/grafana}"
export GF_UNIFIED_ALERTING_ENABLED="${GF_UNIFIED_ALERTING_ENABLED:-false}"
export GF_ANALYTICS_REPORTING_ENABLED="${GF_ANALYTICS_REPORTING_ENABLED:-false}"
export GF_CHECK_FOR_UPDATES="${GF_CHECK_FOR_UPDATES:-false}"

# Public Insights: anonymous Viewer (admin login still available).
export GF_AUTH_ANONYMOUS_ENABLED="${GF_AUTH_ANONYMOUS_ENABLED:-true}"
export GF_AUTH_ANONYMOUS_ORG_ROLE="${GF_AUTH_ANONYMOUS_ORG_ROLE:-Viewer}"
export GF_USERS_DEFAULT_THEME="${GF_USERS_DEFAULT_THEME:-dark}"
# Allow Product hub to embed Insights in an iframe.
export GF_SECURITY_ALLOW_EMBEDDING="${GF_SECURITY_ALLOW_EMBEDDING:-true}"
export GF_SECURITY_COOKIE_SAMESITE="${GF_SECURITY_COOKIE_SAMESITE:-disabled}"

# Allow DATABASE_URL → PRA_PG_* (optional convenience on Render).
if [ -n "${DATABASE_URL:-}" ] && [ -z "${PRA_PG_HOST:-}" ]; then
  rest="${DATABASE_URL#*://}"
  creds="${rest%@*}"
  after_at="${rest##*@}"
  hostport="${after_at%%/*}"
  path="${after_at#*/}"
  case "$creds" in
    *:*) user="${creds%%:*}"; password="${creds#*:}" ;;
    *)   user="$creds"; password="" ;;
  esac
  case "$hostport" in
    *:*) host="${hostport%%:*}"; port="${hostport##*:}" ;;
    *)   host="$hostport"; port="5432" ;;
  esac
  db="${path%%\?*}"
  query="${path#*\?}"
  case "$query" in
    *sslmode=*) sslmode="${query#*sslmode=}"; sslmode="${sslmode%%&*}" ;;
    *)          sslmode="require" ;;
  esac
  export PRA_PG_HOST="${host}:${port}"
  export PRA_PG_USER="$user"
  export PRA_PG_PASSWORD="$password"
  export PRA_PG_DB="$db"
  export PRA_PG_SSLMODE="$sslmode"
fi

exec /run.sh
