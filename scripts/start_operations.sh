#!/bin/sh
# Independent local paper supervisor. Default is observation only.
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
account_config=${TRADING_CONFIG:-config/paper.toml}
if [ "$account_config" = config/paper.toml ] && [ -f config/first-paper-session.toml ]; then
    account_config=config/first-paper-session.toml
fi
if [ "$#" -gt 0 ] && [ "${1#--}" = "$1" ]; then
    account_config=$1
    shift
fi
operations_output=${TRADING_OPERATIONS_OUTPUT:-$(.venv/bin/python -c \
    'import sys; from trading_agent.settings import Settings; print(Settings.load(sys.argv[1]).database.with_suffix(".supervisor"))' \
    "$account_config")}
exec .venv/bin/trading-agent --config "$account_config" operations-watch --output "$operations_output" "$@"
