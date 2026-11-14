import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "apps/api/src"))
from citizen_ai.main import app

target = root / ".local/openapi.json"
target.parent.mkdir(exist_ok=True)
target.write_text(
    json.dumps(app.openapi(), ensure_ascii=False, indent=2), encoding="utf-8"
)
print("OpenAPI exported (no runtime credentials).")
