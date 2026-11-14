import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
const python =
  process.platform === "win32"
    ? "apps/api/.venv/Scripts/python.exe"
    : "apps/api/.venv/bin/python";
if (!existsSync(python))
  throw new Error("Run uv sync --project apps/api first.");
const exported = spawnSync(python, ["scripts/export_openapi.py"], {
  stdio: "inherit",
});
if (exported.status !== 0) process.exit(exported.status ?? 1);
const generated = spawnSync(
  process.platform === "win32"
    ? "openapi-typescript.cmd"
    : "openapi-typescript",
  [".local/openapi.json", "-o", "packages/api-client/schema.d.ts"],
  { stdio: "inherit", shell: process.platform === "win32" },
);
process.exit(generated.status ?? 1);
