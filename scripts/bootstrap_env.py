"""Create local secrets once; never print them or overwrite an existing .env."""

import os
import secrets
from pathlib import Path

root = Path(__file__).resolve().parents[1]
target = root / ".env"
if target.exists():
    print("Existing .env preserved.")
else:
    values = dict(
        line.split("=", 1)
        for line in (root / ".env.example").read_text().splitlines()
        if line and not line.startswith("#")
    )
    values["POSTGRES_PASSWORD"] = secrets.token_hex(24)
    values["APP_DATABASE_PASSWORD"] = secrets.token_hex(24)
    values["SESSION_SECRET"] = secrets.token_hex(32)
    values["S3_ACCESS_KEY_ID"] = "local-" + secrets.token_hex(8)
    values["S3_SECRET_ACCESS_KEY"] = secrets.token_hex(32)
    values["DATABASE_URL"] = (
        f"postgresql+psycopg://citizen_runtime:{values['APP_DATABASE_PASSWORD']}@postgres:5432/citizen"
    )
    values["MIGRATION_DATABASE_URL"] = (
        f"postgresql+psycopg://citizen_migrator:{values['POSTGRES_PASSWORD']}@postgres:5432/citizen"
    )
    with target.open("x", encoding="utf-8", newline="\n") as output:
        output.write("".join(f"{key}={value}\n" for key, value in values.items()))
    if os.name != "nt":
        target.chmod(0o600)
    print("Created local .env with generated secrets. Keep this file outside Git.")
(root / ".local").mkdir(exist_ok=True)
