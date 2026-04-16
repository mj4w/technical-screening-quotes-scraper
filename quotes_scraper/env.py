from __future__ import annotations

import os
from pathlib import Path


# This lightweight loader avoids another dependency while still letting the EC2
# runner and cron job read a local `.env` file in a predictable way.
def load_dotenv(env_path: Path | None = None) -> None:
    path = env_path or Path(".env")
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())
