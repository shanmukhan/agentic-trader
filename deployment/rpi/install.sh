#!/bin/bash
# Root-only installer on the Pi. Source and dependencies are prepared before downtime.
set -euo pipefail
umask 077
[[ $EUID -eq 0 && $# -eq 1 && $(uname -m) == aarch64 ]] || {
    echo 'Run as root on a 64-bit Raspberry Pi with an extracted bundle path.' >&2
    exit 2
}
stage=$(realpath "$1")
monitor=/opt/rpi-monitor/backend
rule=/etc/polkit-1/rules.d/10-rpi-monitor-systemctl.rules
[[ -f $monitor/.env && -f $rule ]] || { echo 'Existing RPi Monitor setup required.' >&2; exit 1; }
python3 - "$stage" <<'PY'
import hashlib, json, re, sys
from pathlib import Path
root = Path(sys.argv[1])
manifest = json.loads((root / 'manifest.json').read_text())
if set(manifest['projects']) not in ({'trader'}, {'trader', 'advisor'}):
    raise SystemExit('Unsupported deployment projects')
if not re.fullmatch(r'\d+\.\d+\.\d+', manifest['versions']['trader']):
    raise SystemExit('Invalid Trader release version')
for name, expected in manifest['sha256'].items():
    path = root / name
    if not path.resolve().is_relative_to(root) or path.is_symlink():
        raise SystemExit('Unsafe bundle path')
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise SystemExit('Bundle checksum mismatch: ' + name)
print('Bundle checksums verified')
PY
command -v curl >/dev/null
python3.13 --version
version=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["versions"]["trader"])' "$stage/manifest.json")
apps=(agentic-trader)
if python3 -c 'import json,sys; sys.exit("advisor" not in json.load(open(sys.argv[1]))["projects"])' "$stage/manifest.json"; then
    apps+=(portfolio-advisor)
fi
trader_only=0
if [[ ${#apps[@]} -eq 1 ]]; then
    trader_only=1
    [[ -L /opt/agentic-trader/current && -f /etc/agentic-trader.env ]] || {
        echo 'Trader-only updates require an existing installed Trader service.' >&2
        exit 1
    }
fi
release=v$version-$(date -u +%Y%m%dT%H%M%S)-$(sha256sum "$stage/manifest.json" | cut -c1-12)
backup=/var/backups/trading-services-$release
install -d -m 700 "$backup"
cp -a "$monitor/.env" "$backup/monitor.env"
cp -a "$rule" "$backup/monitor.rules"
cp "$stage/manifest.json" "$backup/manifest.json"
for app in "${apps[@]}"; do
    [[ $app == agentic-trader ]] && account=trading-agent || account=portfolio-advisor
    id "$account" >/dev/null 2>&1 || useradd --system --home-dir "/var/lib/$app" --no-create-home --shell /usr/sbin/nologin "$account"
    install -d -m 755 "/opt/$app" "/opt/$app/releases"
    install -d -m 700 -o "$account" -g "$account" "/var/lib/$app" "/var/lib/$app/data" "/var/lib/$app/config" "/var/lib/$app/logs"
    readlink -f "/opt/$app/current" > "$backup/$app.previous" || true
    systemctl is-active "$app" > "$backup/$app.active" || true
    systemctl is-enabled "$app" > "$backup/$app.enabled" || true
    if [[ -f /etc/systemd/system/$app.service ]]; then
        cp -a "/etc/systemd/system/$app.service" "$backup/$app.service"
    fi
done
[[ ! -f /etc/agentic-trader.env ]] || cp -a /etc/agentic-trader.env "$backup/agentic-trader.env"

# Use the distro's patched Python 3.13.5 (Debian security backports); do not replace
# the interpreter shared by existing applications. uv is private to this deployment.
if [[ ! -x /opt/trading-deploy-tools/bin/uv ]]; then
    python3.13 -m venv /opt/trading-deploy-tools
    /opt/trading-deploy-tools/bin/pip install 'uv==0.13.5'
fi
trader=/opt/agentic-trader/releases/$release
advisor=/opt/portfolio-advisor/releases/$release
mkdir "$trader"
cp -a "$stage/trader/." "$trader/"
chmod -R u=rwX,go=rX "$trader"
cp "$stage/manifest.json" "$trader/deployment-manifest.json"
(
    cd "$trader"
    UV_CACHE_DIR=/var/cache/trading-deploy /opt/trading-deploy-tools/bin/uv sync \
        --python /usr/bin/python3.13 --frozen --no-dev --extra broker --extra ml --no-editable
)
if [[ $trader_only -eq 0 ]]; then
    mkdir "$advisor"
    cp -a "$stage/advisor/." "$advisor/"
    cp "$stage/manifest.json" "$advisor/deployment-manifest.json"
    python3.13 -m venv "$advisor/.venv"
    UV_CACHE_DIR=/var/cache/trading-deploy /opt/trading-deploy-tools/bin/uv pip install \
        --python "$advisor/.venv/bin/python" --requirement "$advisor/requirements.lock"
    "$advisor/.venv/bin/pip" check
    chmod -R u=rwX,go=rX "$advisor"
fi
chmod -R u=rwX,go=rX "$trader"
# Code is immutable to the service; config/database/credential writes use /var/lib.
ln -s /var/lib/agentic-trader/data "$trader/data"
ln -s /var/lib/agentic-trader/logs "$trader/logs"

changed=0
monitor_changed=0
rollback() {
    result=$?
    if [[ $result -ne 0 && $changed -eq 1 ]]; then
        trap - EXIT
        set +e
        echo "Deployment failed; restoring service links/units and monitor config. Backup: $backup" >&2
        systemctl stop "${apps[@]}"
        for app in "${apps[@]}"; do
            previous=$(cat "$backup/$app.previous")
            if [[ -n $previous && -d $previous ]]; then
                ln -sfn "$previous" "/opt/$app/current"
            else
                rm -f "/opt/$app/current"
            fi
            if [[ -f $backup/$app.service ]]; then
                cp -a "$backup/$app.service" "/etc/systemd/system/$app.service"
            else
                systemctl disable "$app"
                rm -f "/etc/systemd/system/$app.service"
            fi
        done
        if [[ $monitor_changed -eq 1 ]]; then
            cp -a "$backup/monitor.env" "$monitor/.env"
            cp -a "$backup/monitor.rules" "$rule"
            systemctl restart polkit rpi-monitor
        fi
        systemctl daemon-reload
        for app in "${apps[@]}"; do
            if [[ $(cat "$backup/$app.enabled") != enabled ]]; then systemctl disable "$app"; fi
            if [[ $(cat "$backup/$app.active") == active ]]; then systemctl start "$app"; fi
        done
        echo 'Persistent account state was retained; never automatically restore a financial database.' >&2
    fi
    exit "$result"
}
trap rollback EXIT
changed=1
systemctl stop "${apps[@]}"
# Selected owning services are stopped: capture consistent private state before startup.
tar -C /var/lib -cpf "$backup/state.tar" "${apps[@]}"

if [[ ! -f /var/lib/agentic-trader/config/paper.toml ]]; then
    "$trader/.venv/bin/python" - "$trader/config/paper.toml" <<'PY'
import sys
from pathlib import Path
import tomlkit
settings = tomlkit.parse(Path(sys.argv[1]).read_text())
settings['database'] = '/var/lib/agentic-trader/data/paper.sqlite3'
settings['calendar'] = '/var/lib/agentic-trader/config/sessions.csv'
settings['host'], settings['port'] = '127.0.0.1', 8010
Path('/var/lib/agentic-trader/config/paper.toml').write_text(tomlkit.dumps(settings))
PY
fi
if [[ ! -f /var/lib/agentic-trader/config/sessions.csv ]]; then
    cp "$trader/config/sessions.csv" /var/lib/agentic-trader/config/sessions.csv
fi
if [[ ! -f /etc/agentic-trader.env ]]; then
    python3 - <<'PY'
import secrets
from pathlib import Path
Path('/etc/agentic-trader.env').write_text(
    'TRADING_MODE=paper\nTRADING_CONFIG=/var/lib/agentic-trader/config/paper.toml\n'
    + 'TRADING_OPERATOR_TOKEN=' + secrets.token_urlsafe(32) + '\n')
PY
    chmod 600 /etc/agentic-trader.env
fi
if [[ $trader_only -eq 0 && ! -f /var/lib/portfolio-advisor/config/.env ]]; then
    cat > /var/lib/portfolio-advisor/config/.env <<'ENV'
ADVISOR_MODE=demo
ADVISOR_DB=/var/lib/portfolio-advisor/data/advisor.sqlite3
KITE_API_KEY=
KITE_API_SECRET=
KITE_ACCESS_TOKEN=
ENV
fi
for app in "${apps[@]}"; do
    [[ $app == agentic-trader ]] && account=trading-agent || account=portfolio-advisor
    chown -R "$account:$account" "/var/lib/$app"
    find "/var/lib/$app" -type f -exec chmod 600 {} +
done
for app in "${apps[@]}"; do
    [[ $app == agentic-trader ]] && next=$trader || next=$advisor
    ln -s "$next" "/opt/$app/.current-$release"
    mv -Tf "/opt/$app/.current-$release" "/opt/$app/current"
    install -m 644 "$stage/rpi/$app.service" "/etc/systemd/system/$app.service"
done
systemctl daemon-reload
systemctl reset-failed "${apps[@]}"
systemctl enable --now "${apps[@]}"
advisor_health=http://127.0.0.1:8501/_stcore/health
if systemctl show portfolio-advisor --property=Environment --value | grep -q 'STREAMLIT_SERVER_BASE_URL_PATH=portfolio-advisor'; then
    advisor_health=http://127.0.0.1:8501/portfolio-advisor/_stcore/health
fi
endpoints=(http://127.0.0.1:8010/health)
if [[ $trader_only -eq 0 ]]; then endpoints+=("$advisor_health"); fi
for endpoint in "${endpoints[@]}"; do
    healthy=0
    for attempt in {1..30}; do
        if curl -fsS --max-time 2 "$endpoint" >/dev/null; then healthy=1; break; fi
        sleep 1
    done
    [[ $healthy -eq 1 ]] || { echo "Health check failed: $endpoint" >&2; exit 1; }
done
curl -fsS --max-time 5 http://127.0.0.1:8010/health | python3 -c 'import json,sys; assert json.load(sys.stdin)["version"] == sys.argv[1], "Backend version mismatch"' "$version"
# Set before calling the helper so a partial failure/restart restores both backups.
if [[ $trader_only -eq 0 ]]; then
    monitor_changed=1
    "$monitor/.venv/bin/python" "$stage/rpi/register_monitor.py" "$monitor" "$rule"
    if cmp -s "$backup/monitor.env" "$monitor/.env" && cmp -s "$backup/monitor.rules" "$rule"; then
        monitor_changed=0
    else
        systemctl restart polkit
        systemctl restart rpi-monitor
    fi
fi
systemctl is-active --quiet rpi-monitor
for attempt in {1..30}; do
    if curl -fsS --max-time 2 http://127.0.0.1:8000/health >/dev/null; then break; fi
    sleep 1
done
curl -fsS --max-time 2 http://127.0.0.1:8000/health >/dev/null
systemctl is-active "${apps[@]}"
echo "Deployed $release; private backup: $backup"
echo 'Browser access: ssh -N -L 8010:127.0.0.1:8010 -L 8501:127.0.0.1:8501 USER@PI'
changed=0
