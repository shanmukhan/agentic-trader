#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
umask 077
command -v uv >/dev/null || { echo 'Install uv from https://docs.astral.sh/uv/ first.' >&2; exit 1; }
uv sync --frozen --all-extras
uv run trading-agent environment
uv run trading-agent init-db
echo 'Read docs/how-to-use.md; no broker connection or system service was enabled.'
