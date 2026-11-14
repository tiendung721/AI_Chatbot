"""Opt-in real public-source extraction, without publishing or sending to AI."""

import hashlib
import io
import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest

from citizen_ai.ingestion import pipeline
from citizen_ai.ingestion.formats import MIMES

from .test_m1 import Ward
from .test_m1 import wards as wards
from .test_m2 import read_version, upload

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_DB_TESTS") != "1" or not os.getenv("PUBLIC_CORPUS_DIR"),
        reason="Opt-in downloaded public corpus and real local services required",
    ),
]


def test_public_corpus_through_private_storage_scan_parser_and_metadata(
    wards: list[Ward], monkeypatch: pytest.MonkeyPatch
) -> None:
    import pypdfium2 as pdfium

    corpus = Path(os.environ["PUBLIC_CORPUS_DIR"])
    manifest = json.loads((corpus / "manifest.json").read_text(encoding="utf-8"))
    sources = [s for s in manifest["sources"] if s["state"] == "downloaded"]
    assert len({s["sha256"] for s in sources}) >= 20
    assert len({s["topic"] for s in sources}) >= 5
    rows = []
    # Avoid racing this measured extraction with the general background scheduler.
    monkeypatch.setattr(pipeline, "enqueue", lambda *args: None)

    def measure(source: dict, data: bytes, extension: str) -> None:
        ward = wards[0 if source["tenant_fixture"] == "public-test-a" else 1]
        start = time.monotonic()
        item = upload(ward, source["id"] + extension, data, MIMES[extension])
        if item["state"] != "uploaded":
            rows.append(
                {
                    "id": source["id"],
                    "state": "rejected",
                    "format": extension,
                    "error_code": item["error_code"],
                    "source_page": source["page"],
                    "sha256": hashlib.sha256(data).hexdigest(),
                    "seconds": round(time.monotonic() - start, 3),
                }
            )
            print(source["id"], "rejected", item["error_code"], flush=True)
            return
        pipeline.process_ingestion(ward.tenant_id, item["job_id"])
        version = read_version(ward, item)
        assert version["sha256"] == hashlib.sha256(data).hexdigest()
        if source["id"] == "CB-01":
            original = ward.client.get(f"/api/v1/admin/knowledge/versions/{item['version_id']}/original")
            assert original.status_code == 200
            assert hashlib.sha256(original.content).hexdigest() == source["sha256"]
        metadata = version["metadata_json"]
        row = {
            "id": source["id"],
            "topic": source["topic"],
            "tenant_fixture": source["tenant_fixture"],
            "source_page": source["page"],
            "sha256": hashlib.sha256(data).hexdigest(),
            "format": extension,
            "state": version["parse_status"],
            "scan_status": version["scan_status"],
            "seconds": round(time.monotonic() - start, 3),
            "sections": len(version["sections"]),
            "warnings": metadata.get("warnings", []),
            "pages_total": metadata.get("pages_total"),
            "pages_read": metadata.get("pages_read"),
            "sheets": metadata.get("sheets"),
            "derived_scan_fixture": source.get("derived_scan_fixture", False),
        }
        if version["parse_status"] in {"ready", "needs_review"}:
            response = ward.client.patch(
                f"/api/v1/admin/knowledge/versions/{item['version_id']}/metadata",
                json={
                    "revision": version["extraction_revision"],
                    "source_url": source["page"],
                    "classification": "internal",
                    "jurisdiction": source["jurisdiction"],
                    "topic_tags": ["technical-corpus", source["topic"]],
                },
                headers={"X-CSRF-Token": ward.csrf},
            )
            assert response.status_code == 200, response.text
        else:
            row["error_code"] = ward.client.get(f"/api/v1/admin/knowledge/jobs/{item['job_id']}").json()[
                "error_code"
            ]
        assert not version["approved_for_public"]
        other = wards[1] if ward is wards[0] else wards[0]
        assert other.client.get(f"/api/v1/admin/knowledge/versions/{item['version_id']}").status_code == 404
        rows.append(row)
        print(source["id"], row["state"], row["seconds"], flush=True)

    for source in sources:
        filename = (corpus / source["filename"]).resolve()
        assert filename.is_relative_to(corpus.resolve())
        data = filename.read_bytes()
        assert hashlib.sha256(data).hexdigest() == source["sha256"]
        measure(source, data, "." + source["extension"])
    parent = next(s for s in sources if s["extension"] == "pdf")
    pdf = pdfium.PdfDocument((corpus / parent["filename"]).read_bytes())
    page = pdf[0]
    bitmap = page.render(scale=2)
    image = bitmap.to_pil()
    stream = io.BytesIO()
    image.save(stream, format="PNG")
    image.close()
    bitmap.close()
    page.close()
    pdf.close()
    measure({**parent, "id": "DERIVED-SCAN-01", "derived_scan_fixture": True}, stream.getvalue(), ".png")
    report = {
        "date": datetime.now(UTC).isoformat(),
        "label": "Technical extraction only; no public approval, no AI or legal quality acceptance",
        "original_unique_documents": len({s["sha256"] for s in sources}),
        "rows": rows,
    }
    report_path = Path(os.getenv("PUBLIC_CORPUS_REPORT", "/tmp/public-corpus-report.json"))
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    expected_errors = {s["id"]: s["expected_error"] for s in sources if s.get("expected_error")}
    assert all(
        (r["state"] in {"ready", "needs_review"} and r["scan_status"] == "clean")
        or (
            r["state"] == "failed"
            and r.get("error_code") == expected_errors.get(r["id"])
            and r["id"] in expected_errors
        )
        for r in rows
    ), [(r["id"], r.get("error_code")) for r in rows if r["state"] not in {"ready", "needs_review"}]
    assert rows[-1]["state"] == "needs_review"
