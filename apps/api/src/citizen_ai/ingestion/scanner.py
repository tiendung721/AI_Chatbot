import socket
import struct

from ..common import AppError
from ..config import settings


def scan_bytes(data: bytes) -> None:
    cfg = settings()
    try:
        with socket.create_connection(
            (cfg.clamav_host, cfg.clamav_port), timeout=cfg.scanner_timeout_seconds
        ) as connection:
            connection.settimeout(cfg.scanner_timeout_seconds)
            connection.sendall(b"zINSTREAM\0")
            for start in range(0, len(data), 65536):
                part = data[start : start + 65536]
                connection.sendall(struct.pack(">I", len(part)) + part)
            connection.sendall(struct.pack(">I", 0))
            response = bytearray()
            while b"\0" not in response and len(response) < 4096:
                part = connection.recv(1024)
                if not part:
                    break
                response.extend(part)
    except OSError as exc:
        raise AppError(
            "SCANNER_UNAVAILABLE", "Bộ quét file chưa sẵn sàng. Vui lòng thử xử lý lại sau.", 503, True
        ) from exc
    status = response.decode("utf-8", errors="replace").strip("\0\r\n ")
    if status.endswith(" FOUND"):
        raise AppError("FILE_QUARANTINED", "File đã bị cách ly do phát hiện nội dung nguy hiểm.", 422)
    if status != "stream: OK":
        raise AppError(
            "SCANNER_UNAVAILABLE", "Bộ quét chưa xác nhận file an toàn. File chưa được xử lý.", 503, True
        )
