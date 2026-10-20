#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
case "$(uname -m)" in aarch64|arm64) ;; *) echo 'Use a 64-bit Raspberry Pi OS.' >&2; exit 1;; esac
umask 077
command -v uv >/dev/null || { echo 'Install uv from https://docs.astral.sh/uv/ first.' >&2; exit 1; }
uv sync --frozen --extra broker
uv run trading-agent environment
uv run trading-agent init-db
echo 'Review deployment/systemd/trading-agent.service and docs/runbook.md before installing.'
