#!/bin/bash
# Publish the existing shanmukhan.com Investing tab and private app routes.
# Deploy the current application source with deploy.sh first.
set -euo pipefail
if [[ $# -lt 1 || $# -gt 2 || $1 == -* ]]; then
    echo "Usage: $0 USER@PI [RPI_SETUP_DIRECTORY]" >&2
    exit 2
fi
target=$1
root=$(cd "$(dirname "$0")/../.." && pwd)
setup=${2:-$(dirname "$root")/rpi-setup}
stage=$(ssh -o BatchMode=yes "$target" 'umask 077; mktemp -d /tmp/trading-web.XXXXXX')
[[ $stage =~ ^/tmp/trading-web\.[a-zA-Z0-9]+$ ]] || exit 1
trap 'ssh -o BatchMode=yes "$target" "rm -rf '\''$stage'\''" || true' EXIT
scp -q "$setup/scripts/configure-trading-web.sh" "$setup/scripts/trading-web-auth.py" \
    "$setup/scripts/apache-templates/trading-apps.conf" \
    "$setup/scripts/site-content/shanmukhan/index.html" "$target:$stage/"
ssh -o BatchMode=yes "$target" "sudo -n bash '$stage/configure-trading-web.sh' '$stage'"
