import json
import logging
import logging.handlers
import os
import re
from datetime import UTC, datetime
from pathlib import Path


class RedactedJSON(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        message = record.getMessage()
        for key in (
            "KITE_API_KEY",
            "KITE_API_SECRET",
            "KITE_ACCESS_TOKEN",
            "TRADING_OPERATOR_TOKEN",
        ):
            value = os.environ.get(key)
            if value:
                message = message.replace(value, "[REDACTED]")
        message = re.sub(
            r"(?i)authorization[ \t]*[:=][ \t]*(?:bearer|token)[ \t]+[^\s,]+",
            "authorization=[REDACTED]",
            message,
        )
        message = re.sub(
            r"(?i)(access_token|api_key|api_secret|request_token|authorization|checksum)"
            r"[\"']?[ \t]*[:=][ \t]*(?:\"[^\"]*\"|'[^']*'|[^\s,&]+)",
            r"\1=[REDACTED]",
            message,
        )
        return json.dumps(
            {
                "time": datetime.now(UTC).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": message,
                "correlation_id": getattr(record, "correlation_id", "system"),
            }
        )


def configure_logging(directory: Path = Path("logs")) -> None:
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    handler = logging.handlers.RotatingFileHandler(
        directory / "agent.jsonl", maxBytes=5_000_000, backupCount=3
    )
    (directory / "agent.jsonl").chmod(0o600)
    handler.setFormatter(RedactedJSON())
    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)
    # Third-party request/SDK debug output can contain token-bearing URLs.
    for name in ("httpx", "httpcore", "websockets", "uvicorn.access"):
        logging.getLogger(name).disabled = True
