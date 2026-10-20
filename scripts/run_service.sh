#!/bin/sh
# launchd wrapper. A private environment file is sourced explicitly; never echo it.
set -eu
umask 077
cd "${TRADING_WORKDIR:?Set TRADING_WORKDIR to the absolute project path}"
if [ -f .env ]; then
    set -a
    . ./.env
    set +a
fi
if [ "${TRADING_STREAM:-0}" = 1 ]; then
    exec .venv/bin/trading-agent serve --stream
fi
exec .venv/bin/trading-agent serve
