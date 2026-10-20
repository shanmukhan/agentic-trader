#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
.venv/bin/trading-agent environment
.venv/bin/python -c 'import sqlite3,ssl; print("SQLite",sqlite3.sqlite_version,"TLS",ssl.OPENSSL_VERSION)'
df -h .
case "$(uname -s)" in Darwin) sysctl -n hw.memsize;; Linux) head -n 3 /proc/meminfo;; esac
