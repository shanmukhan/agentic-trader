#!/bin/bash
# Run on the workstation. No local environment, database or broker session is copied.
set -euo pipefail
if [[ $# -lt 1 || $1 == -* ]]; then
    echo "Usage: $0 USER@PI [PORTFOLIO_ADVISOR_DIRECTORY|--trader-only] [--android-apk SIGNED_APK]" >&2
    exit 2
fi
target=$1
root=$(cd "$(dirname "$0")/../.." && pwd)
shift
advisor=$(dirname "$root")/portfolio-advisor
trader_only=0
advisor_supplied=0
android_apk=
while [[ $# -gt 0 ]]; do
    case $1 in
        --trader-only) trader_only=1; shift ;;
        --android-apk)
            [[ $# -ge 2 && $2 != -* ]] || { echo 'Missing signed APK path.' >&2; exit 2; }
            android_apk=$2; shift 2 ;;
        -*) echo 'Unknown deployment option.' >&2; exit 2 ;;
        *) [[ $advisor_supplied -eq 0 ]] || { echo 'Unexpected deployment argument.' >&2; exit 2; }
           advisor=$1; advisor_supplied=1; shift ;;
    esac
done
[[ $trader_only -eq 0 || $advisor_supplied -eq 0 ]] || { echo 'Trader-only cannot include an Advisor directory.' >&2; exit 2; }
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
bundle_args=(--trader "$root" --output "$bundle")
if [[ $trader_only -eq 0 ]]; then bundle_args+=(--advisor "$advisor"); fi
if [[ -n $android_apk ]]; then bundle_args+=(--android-apk "$android_apk"); fi
"$python" "$root/deployment/rpi/bundle.py" "${bundle_args[@]}"
remote_stage=$(ssh -o BatchMode=yes "$target" 'umask 077; mktemp -d /tmp/trading-services.XXXXXX')
[[ $remote_stage =~ ^/tmp/trading-services\.[a-zA-Z0-9]+$ ]] || exit 1
scp -q "$bundle" "$target:$remote_stage/bundle.tar.gz"
ssh -o BatchMode=yes "$target" "tar -xzf '$remote_stage/bundle.tar.gz' -C '$remote_stage' && sudo -n bash '$remote_stage/rpi/install.sh' '$remote_stage'"
