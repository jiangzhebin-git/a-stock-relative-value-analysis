import hashlib
import json
import os
from pathlib import Path


if __name__ == "__main__":
    pin = os.environ.get("WEB_ACCESS_PIN", "")
    if not (pin.isdigit() and len(pin) in {4, 6}):
        raise SystemExit("WEB_ACCESS_PIN 必须是4位或6位数字")
    digest = hashlib.sha256(pin.encode("utf-8")).hexdigest()
    target = Path(__file__).resolve().parent / "web" / "config.js"
    target.write_text(
        f"window.DASHBOARD_CONFIG = {json.dumps({'pinHash': digest})};\n",
        encoding="utf-8",
    )

