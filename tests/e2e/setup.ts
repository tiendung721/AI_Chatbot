import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
export default function setup() {
  execFileSync(
    "docker",
    [
      "compose",
      "run",
      "--rm",
      "--no-deps",
      "ops",
      "python",
      "-c",
      "from citizen_ai.config import settings; c=settings(); assert c.app_env in {'local','test'} and c.ai_provider=='mock' and c.embedding_provider=='disabled', 'E2E requires local Mock AI and disabled embeddings'",
    ],
    { stdio: "pipe" },
  );
  const env = readFileSync(".env", "utf8");
  const value = (key: string, fallback: string) =>
    env
      .match(new RegExp(`^${key}=(.*)$`, "m"))?.[1]
      .trim()
      .replace(/^["']|["']$/g, "") ?? fallback;
  if (
    value("AI_PROVIDER", "mock") !== "mock" ||
    value("EMBEDDING_PROVIDER", "disabled") !== "disabled"
  )
    throw new Error(
      "E2E cần local Mock AI và embeddings disabled để không gọi API tính phí.",
    );
  execFileSync(
    "docker",
    [
      "compose",
      "run",
      "--rm",
      "ops",
      "python",
      "-m",
      "citizen_ai.cli",
      "ops",
      "prepare-e2e",
      "--credentials-path",
      "/app/.local/e2e-admins.json",
    ],
    { stdio: "pipe" },
  );
  execFileSync(
    "docker",
    [
      "compose",
      "run",
      "--rm",
      "--no-deps",
      "--volume",
      `${process.cwd()}/apps/api/tests:/app/apps/api/tests:ro`,
      "--volume",
      `${process.cwd()}/.local:/app/.local`,
      "tests",
      "python",
      "-c",
      "from pathlib import Path; from tests.fixture_files import file_fixture; p=Path('/app/.local/e2e-files'); p.mkdir(exist_ok=True); (p/'review.xlsx').write_bytes(file_fixture('.xlsx'))",
    ],
    { stdio: "pipe" },
  );
}
