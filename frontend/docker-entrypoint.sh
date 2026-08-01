#!/bin/sh
set -e

cat <<EOF > /app/public/runtime-env.js
window.__ENV__ = {
  NEXT_PUBLIC_API_URL: "${NEXT_PUBLIC_API_URL:-http://localhost:8000}"
};
EOF

exec "$@"