"""Short-lived parser process: file content never becomes executable instructions."""

import json
import os
import sys
from pathlib import Path

from .models import Limits, ParseFailure


def main() -> None:
    if os.name == "posix":
        import resource

        resource.setrlimit(resource.RLIMIT_AS, (1536 * 1024 * 1024, 1536 * 1024 * 1024))
        resource.setrlimit(resource.RLIMIT_CPU, (150, 150))
        resource.setrlimit(resource.RLIMIT_FSIZE, (128 * 1024 * 1024, 128 * 1024 * 1024))
        resource.setrlimit(resource.RLIMIT_NOFILE, (128, 128))
    from .parsers import parse_file

    try:
        limits = Limits(**json.loads(sys.argv[3]))
        data = Path(sys.argv[1]).read_bytes()
        result = parse_file(data, sys.argv[2], limits)
        print(result.model_dump_json())
    except ParseFailure as exc:
        print(json.dumps({"error_code": exc.code}))
    except Exception:
        print(json.dumps({"error_code": "EXTRACTION_FAILED"}))


if __name__ == "__main__":
    main()
