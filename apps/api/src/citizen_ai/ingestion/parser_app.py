import asyncio
import json
import os
import signal
import subprocess
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from .formats import MIMES
from .models import Extraction, Limits

app = FastAPI(title="Isolated document parser", docs_url=None, openapi_url=None, redoc_url=None)
gate = asyncio.Semaphore(1)


def parser_limits() -> Limits:
    return Limits(
        max_file_bytes=int(os.getenv("MAX_UPLOAD_MB", "25")) * 1024 * 1024,
        max_pdf_pages=int(os.getenv("MAX_PDF_PAGES", "300")),
    )


def isolated_extract(data: bytes, extension: str, limits: Limits) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as directory:
        source = Path(directory) / ("source" + extension)
        source.write_bytes(data)
        clean_env = {
            "PATH": os.environ.get("PATH", ""),
            "LANG": "C.UTF-8",
            "OMP_THREAD_LIMIT": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": str(Path(__file__).resolve().parents[2]),
        }
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "citizen_ai.ingestion.parse_job",
                str(source),
                extension,
                json.dumps(asdict(limits)),
            ],
            cwd=directory,
            env=clean_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=os.name == "posix",
        )
        try:
            output, _ = process.communicate(timeout=int(os.getenv("EXTRACTION_TIMEOUT_SECONDS", "180")))
        except subprocess.TimeoutExpired:
            if os.name == "posix":
                os.killpg(process.pid, signal.SIGKILL)
            else:
                process.kill()
            process.communicate()
            return {"error_code": "EXTRACTION_TIMEOUT"}
        if process.returncode != 0 or len(output) > limits.max_text_bytes * 3:
            return {"error_code": "EXTRACTION_RESOURCE_LIMIT"}
        try:
            raw = json.loads(output)
            if "error_code" in raw:
                return {"error_code": raw["error_code"]}
            return Extraction.model_validate(raw).model_dump()
        except Exception:
            return {"error_code": "EXTRACTION_FAILED"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ready"}


@app.post("/extract")
async def extract(request: Request, x_file_extension: str = Header()) -> JSONResponse:
    if x_file_extension not in MIMES:
        return JSONResponse({"error_code": "FILE_UNSUPPORTED"}, status_code=422)
    limits = parser_limits()
    data = bytearray()
    async for part in request.stream():
        data.extend(part)
        if len(data) > limits.max_file_bytes:
            return JSONResponse({"error_code": "FILE_TOO_LARGE"}, status_code=413)
    async with gate:
        result = await run_in_threadpool(isolated_extract, bytes(data), x_file_extension, limits)
    return JSONResponse(result, status_code=422 if "error_code" in result else 200)
