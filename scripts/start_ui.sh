#!/bin/sh
# Run the local paper UI without putting credentials in arguments or browser URLs.
set -eu
umask 077
cd "$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
if [ ! -x .venv/bin/trading-agent ]; then
    echo 'Install the frozen Python environment first; see docs/how-to-use.md.' >&2
    exit 1
fi
if [ -f .env ]; then
    set -a
    . ./.env
    set +a
fi
session_file=${TRADING_SESSION_FILE:-.env.session-first}
if [ -f "$session_file" ]; then
    set -a
    case "$session_file" in
        /*) . "$session_file" ;;
        *) . "./$session_file" ;;
    esac
    set +a
fi
if [ -z "${TRADING_OPERATOR_TOKEN:-}" ]; then
    echo 'Set TRADING_OPERATOR_TOKEN in your private .env before starting. See docs/ui-setup.md.' >&2
    exit 1
fi
if [ "$#" -gt 1 ]; then
    echo 'Usage: ./scripts/start_ui.sh [ACCOUNT_CONFIG.toml]' >&2
    exit 1
fi
account_config=${1:-${TRADING_CONFIG:-config/paper.toml}}
if [ "$#" -eq 0 ] && [ "${TRADING_CONFIG:-config/paper.toml}" = config/paper.toml ] && [ -f config/first-paper-session.toml ]; then
    account_config=config/first-paper-session.toml
fi
if .venv/bin/python scripts/open_existing_ui.py "$account_config"; then
    exit 0
else
    probe_result=$?
    if [ "$probe_result" -ne 10 ]; then exit "$probe_result"; fi
fi
exec .venv/bin/trading-agent --config "$account_config" serve --open
