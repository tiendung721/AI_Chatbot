"""Read-only snapshots proving a second bootstrap preserves local secrets and demo data."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("phase", choices=["before", "after"])
args = parser.parse_args()
query = """import json
from citizen_ai.db import transaction, many
with transaction(privileged=True) as db:
    rows=many(db, \"SELECT t.slug,(SELECT count(*) FROM accounts a WHERE a.tenant_id=t.id) AS accounts,(SELECT count(*) FROM documents d WHERE d.tenant_id=t.id) AS documents,(SELECT count(*) FROM content_releases r WHERE r.tenant_id=t.id) AS releases FROM tenants t WHERE t.slug IN ('ward-demo-a','ward-demo-b') ORDER BY t.slug\")
print(json.dumps(rows,sort_keys=True))
"""
result = subprocess.run(
    ["docker", "compose", "run", "--rm", "--no-deps", "ops", "python", "-c", query],
    cwd=root,
    capture_output=True,
    text=True,
    check=True,
)
snapshot = {
    "data": json.loads(result.stdout),
    "hashes": {
        name: hashlib.sha256((root / name).read_bytes()).hexdigest()
        for name in (".env", ".local/provisioned-admins.json")
    },
}
baseline = root / ".local/bootstrap-before.json"
if args.phase == "before":
    baseline.write_text(json.dumps(snapshot, sort_keys=True), encoding="utf-8")
    print("Captured bootstrap preservation baseline (hashes/counts only).")
else:
    assert json.loads(baseline.read_text(encoding="utf-8")) == snapshot, (
        "Second bootstrap changed secrets or demo data"
    )
    print(
        "PASS: second bootstrap preserved .env, credentials, accounts, documents and releases for both demo tenants."
    )
