#!/bin/bash
# Run on the workstation. No local environment, database or broker session is copied.
set -euo pipefail
if [[ $# -lt 1 || $# -gt 2 || $1 == -* ]]; then
    echo "Usage: $0 USER@PI [PORTFOLIO_ADVISOR_DIRECTORY]" >&2
    exit 2
fi
target=$1
root=$(cd "$(dirname "$0")/../.." && pwd)
advisor=${2:-$(dirname "$root")/portfolio-advisor}
python=${DEPLOY_PYTHON:-$root/.venv/bin/python}
bundle=$(mktemp /tmp/trading-services.XXXXXX)
remote_stage=
cleanup() {
    rm -f "$bundle"
    if [[ -n $remote_stage ]]; then
        ssh -o BatchMode=yes "$target" "rm -rf '$remote_stage'" || true
    fi
}
trap cleanup EXIT
"$python" "$root/deployment/rpi/bundle.py" --trader "$root" --advisor "$advisor" --output "$bundle"
remote_stage=$(ssh -o BatchMode=yes "$target" 'umask 077; mktemp -d /tmp/trading-services.XXXXXX')
[[ $remote_stage =~ ^/tmp/trading-services\.[a-zA-Z0-9]+$ ]] || exit 1
scp -q "$bundle" "$target:$remote_stage/bundle.tar.gz"
ssh -o BatchMode=yes "$target" "tar -xzf '$remote_stage/bundle.tar.gz' -C '$remote_stage' && sudo -n bash '$remote_stage/rpi/install.sh' '$remote_stage'"
