"""Collect a fixed, reviewed URL catalog for local parser tests, never publish it."""

import hashlib
import ipaddress
import json
import re
import socket
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urljoin, urlsplit

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / ".local/public-corpus"
HOSTS = {"congbao.chinhphu.vn", "g7.cdnchinhphu.vn", "xuandinh.dongnai.gov.vn", "moj.gov.vn", "dichvucong.gov.vn", "cdn.dongnai.gov.vn"}
MAXIMUM = 25 * 1024 * 1024


def validate_url(url: str) -> None:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname not in HOSTS or parsed.username or parsed.password or parsed.port not in {None, 443}:
        raise ValueError("URL outside the fixed HTTPS source allowlist")
    for info in socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM):
        if not ipaddress.ip_address(info[4][0]).is_global:
            raise ValueError("Source DNS must resolve to public addresses")


class Redirect(urllib.request.HTTPRedirectHandler):
    max_redirections = 5

    def redirect_request(self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> Any:
        validate_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.links.append(href)


def fetch(url: str) -> tuple[bytes, str, str]:
    validate_url(url)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), Redirect())
    request = urllib.request.Request(url, headers={"User-Agent": "CitizenAI-local-corpus/2.0", "Accept-Encoding": "identity"})
    with opener.open(request, timeout=35) as response:
        validate_url(response.url)
        if int(response.headers.get("Content-Length", "0")) > MAXIMUM:
            raise ValueError("Source exceeds 25 MiB")
        body = response.read(MAXIMUM + 1)
        if len(body) > MAXIMUM:
            raise ValueError("Source exceeds 25 MiB")
        return body, response.url, response.headers.get_content_type()


def collect(source: dict[str, Any]) -> dict[str, Any]:
    if not re.fullmatch(r"[A-Z0-9-]{1,64}", source["id"]) or source["extension"] not in {"pdf", "docx", "xlsx", "html"}:
        raise ValueError("Invalid catalog ID or extension")
    row = {**source, "collected_at": datetime.now(UTC).isoformat(), "approved_for_public": False,
           "issuer": "UBND xã Xuân Định" if source["id"].startswith("XD-") else None,
           "legal_effectivity_verified": False, "fixture": False}
    try:
        url = source.get("url", source["page"])
        if not source["direct"]:
            page, page_url, _ = fetch(source["page"])
            parser = Links()
            parser.feed(page.decode("utf-8", errors="replace"))
            matches = [urljoin(page_url, link) for link in parser.links if "." + source["extension"] in unquote(link).lower()]
            if not matches:
                raise ValueError("No supported attachment on official page")
            url = matches[source.get("attachment_index", 0)]
        data, final_url, mime = fetch(url)
        extension = source["extension"]
        if extension == "pdf" and not data.startswith(b"%PDF-"):
            raise ValueError("PDF magic mismatch")
        if extension in {"docx", "xlsx"} and not data.startswith(b"PK"):
            raise ValueError("Office magic mismatch")
        if extension == "html" and mime not in {"text/html", "application/xhtml+xml"}:
            raise ValueError("HTML content type mismatch")
        digest = hashlib.sha256(data).hexdigest()
        filename = source["id"] + "-" + digest[:12] + "." + extension
        (OUTPUT / filename).write_bytes(data)
        row.update(download_url=final_url, sha256=digest, byte_size=len(data), filename=filename,
                   mime_type=mime, state="downloaded")
    except (OSError, ValueError, urllib.error.URLError) as exc:
        row.update(state="failed", error_type=type(exc).__name__, error_reason=str(exc)[:300])
    return row


def main() -> None:
    sources = json.loads((ROOT / "fixtures/public_sources/catalog.json").read_text(encoding="utf-8"))["sources"]
    if len(sources) > 30:
        raise ValueError("This bounded collector supports at most 30 catalog entries")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(collect, sources))
    manifest = {"label": "Public-source local technical corpus; not approved public knowledge or legal advice",
                "collected_at": datetime.now(UTC).isoformat(), "sources": rows}
    (OUTPUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    good = [r for r in rows if r["state"] == "downloaded"]
    print(json.dumps({"downloaded": len(good), "unique_hashes": len({r["sha256"] for r in good}),
                      "failed": [{"id": r["id"], "error_type": r["error_type"]} for r in rows if r["state"] != "downloaded"]}))


if __name__ == "__main__":
    main()
