#!/bin/sh
set -e

TARGET_API_URL="${NEXT_PUBLIC_API_URL:-https://distillnews.nmohan.tech/api}"

echo "Injecting runtime NEXT_PUBLIC_API_URL: ${TARGET_API_URL}"

# Replace placeholders and default URLs in compiled JS/HTML bundles
find /app/.next /app/public -type f \( -name "*.js" -o -name "*.html" -o -name "*.json" \) -exec sed -i \
  -e "s|__NEXT_PUBLIC_API_URL_PLACEHOLDER__|${TARGET_API_URL}|g" \
  -e "s|http://localhost:8000|${TARGET_API_URL}|g" \
  -e "s|http://localhost:4002|${TARGET_API_URL}|g" \
  {} + 2>/dev/null || true

exec "$@"
