"""Validate v2 traceability without rewriting curated acceptance evidence."""

import re
from pathlib import Path


def validate(root: Path) -> None:
    spec = (root / "CODEX_CHATBOT_DA_PHUONG_MASTER_SPEC.md").read_text(encoding="utf-8")
    plan = (root / "docs/IMPLEMENTATION_PLAN.md").read_text(encoding="utf-8")
    checklist = (root / "docs/REQUIREMENTS_CHECKLIST.md").read_text(encoding="utf-8")
    expected: dict[str, set[str]] = {}
    for prefix, document in (("FR", spec), ("NFR", spec), ("W", plan), ("AT", checklist)):
        identifiers = re.findall(r"^\| (" + prefix + r"-\d{2})\b", document, re.MULTILINE)
        if not identifiers or len(identifiers) != len(set(identifiers)):
            raise ValueError(f"Missing or duplicate {prefix} definitions")
        expected[prefix] = set(identifiers)
    for prefix in ("FR", "NFR"):
        mapped = set(re.findall(r"^\| (" + prefix + r"-\d{2})\b", checklist, re.MULTILINE))
        if mapped != expected[prefix]:
            raise ValueError(f"Unmapped requirements: {prefix}")
    for prefix in ("W", "AT"):
        references = set(re.findall(r"\b" + prefix + r"-\d{2}\b", checklist))
        unknown = references - expected[prefix]
        if unknown:
            raise ValueError(f"Unknown references: {sorted(unknown)}")
    print("Traceability valid. Curated evidence and status were not changed.")


if __name__ == "__main__":
    validate(Path(__file__).resolve().parents[1])
