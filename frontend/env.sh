#!/bin/sh
# PaymentMate AI - Environment Variable Injection Script
# This script runs at container startup to inject runtime environment variables

# Create env-config.js with environment variables
cat <<EOF > /usr/share/nginx/html/env-config.js
window._env_ = {
  VITE_API_BASE_URL: "${VITE_API_BASE_URL:-http://localhost:8000}",
  VITE_API_VERSION: "${VITE_API_VERSION:-v1}",
  VITE_POLL_INTERVAL: "${VITE_POLL_INTERVAL:-2000}",
  VITE_DEBUG: "${VITE_DEBUG:-false}"
};
EOF

echo "Environment variables injected successfully"
