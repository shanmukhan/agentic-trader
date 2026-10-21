"""Open a matching authenticated running UI; return 10 only when no server listens."""

import errno
import hashlib
import json
import sys
import urllib.error
import urllib.request
import webbrowser

from trading_agent.settings import Settings


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def main() -> int:
    settings = Settings.load(sys.argv[1])
    host = "[::1]" if settings.host == "::1" else "127.0.0.1"
    url = f"http://{host}:{settings.port}/"
    request = urllib.request.Request(
        url + "api/setup",
        headers={"Authorization": "Bearer " + settings.operator_token.get_secret_value()},
    )
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    try:
        with opener.open(request, timeout=3) as response:
            state = json.loads(response.read(65536))
        expected = hashlib.sha256(str(settings.database.resolve()).encode()).hexdigest()
        if state.get("account_id") != expected:
            raise ValueError
    except urllib.error.URLError as exc:
        if getattr(exc.reason, "errno", None) == errno.ECONNREFUSED:
            return 10
        print(
            "Port is occupied or unavailable. Stop the prior UI in its terminal; "
            "do not start a second account owner.",
            file=sys.stderr,
        )
        return 1
    except Exception:
        print(
            "Running UI does not match this account/version. Review its terminal "
            "and config before restarting.",
            file=sys.stderr,
        )
        return 1
    print("Opening the existing paper dashboard; no second account process was started.")
    webbrowser.open(url)
    return 0


if __name__ == "__main__":
    sys.exit(main())
