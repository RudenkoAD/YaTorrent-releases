#!/usr/bin/env python3
"""Small AIM2 JSON API client. No automatic retries or credential-bearing redirects."""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from http.client import HTTPException
from pathlib import Path
from typing import BinaryIO
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        return None


def endpoint(base: str, path: str, allow_http: bool) -> str:
    parsed = urlsplit(base)
    schemes = {"https", "http"} if allow_http else {"https"}
    if (parsed.scheme not in schemes or not parsed.hostname or parsed.username is not None
            or parsed.password is not None or parsed.query or parsed.fragment):
        raise ValueError("Set AIM2_API_BASE to an HTTPS API root without credentials/query/fragment")
    route = urlsplit(path)
    decoded = unquote(route.path)
    if (not path.startswith("/") or path.startswith("//") or route.scheme or route.netloc
            or route.fragment or "\\" in decoded or ".." in decoded.split("/")
            or any(ord(char) < 32 for char in path)):
        raise ValueError("Use a relative API path beginning with one slash, without traversal")
    return base.rstrip("/") + path


def reject_constant(value: str) -> None:
    raise ValueError("JSON must not contain NaN or Infinity")


def payload(path: Path | None) -> bytes | None:
    if path is None:
        return None
    data = json.loads(path.read_text(encoding="utf-8"), parse_constant=reject_constant)
    return json.dumps(data, ensure_ascii=False, allow_nan=False).encode("utf-8")


def copy_response(response: BinaryIO, target: BinaryIO) -> int:
    size = 0
    while block := response.read(64 * 1024):
        target.write(block)
        size += len(block)
    return size


def execute(args: argparse.Namespace) -> None:
    url = endpoint(os.environ.get("AIM2_API_BASE", ""), args.path, args.allow_http)
    token_path = os.environ.get("AIM2_TOKEN_FILE")
    if not token_path:
        raise ValueError("Set AIM2_TOKEN_FILE to an existing private token file")
    token = Path(token_path).read_text(encoding="utf-8").rstrip("\r\n")
    if not token or any(char.isspace() for char in token):
        raise ValueError("Token file must contain one nonempty token")
    if args.json_file and args.method == "GET":
        raise ValueError("GET does not accept --json-file")
    if args.output and args.output.exists():
        raise ValueError("Output exists; choose a new filename")
    request = Request(url, data=payload(args.json_file), method=args.method,
                      headers={"Authorization": f"Bearer {token}", "Accept": "application/json",
                               "Content-Type": "application/json", "Accept-Encoding": "identity"})
    opener = build_opener(NoRedirects())
    with opener.open(request, timeout=args.timeout) as response:
        if response.headers.get_content_type() != "application/json":
            raise ValueError("Expected JSON response; check API base and endpoint")
        if response.headers.get("Content-Encoding", "identity").lower() != "identity":
            raise ValueError("Unexpected response encoding")
        expected = response.headers.get("Content-Length")
        if args.output:
            # Same-filesystem temporary file; publish atomically without overwriting a result.
            name: str | None = None
            try:
                with tempfile.NamedTemporaryFile(dir=args.output.parent, delete=False) as target:
                    name = target.name
                    size = copy_response(response, target)
                    if expected is not None and size != int(expected):
                        raise ValueError("Incomplete response; output was not published")
                    target.flush()
                    os.fsync(target.fileno())
                os.link(name, args.output)
            finally:
                if name is not None:
                    Path(name).unlink(missing_ok=True)
            print(f"Saved {size} bytes", file=sys.stderr)
        else:
            size = copy_response(response, sys.stdout.buffer)
            if expected is not None and size != int(expected):
                raise ValueError("Incomplete response")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("method", choices=("GET", "POST", "PUT", "PATCH"))
    parser.add_argument("path", help="API path, e.g. /baskets/catalog?limit=100&offset=0")
    parser.add_argument("--json-file", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--allow-http", action="store_true")
    args = parser.parse_args()
    if not 0 < args.timeout <= 900:
        parser.error("--timeout must be between 0 and 900 seconds")
    try:
        execute(args)
    except HTTPError as error:
        print(f"HTTP {error.code}; response body omitted. Check state before retrying a write.",
              file=sys.stderr)
        return 1
    except (OSError, ValueError, URLError, HTTPException):
        # Exceptions may embed response URLs, credential paths or request values.
        print("Request failed (configuration, network or file). Check inputs and server state; "
              "no automatic retry was made.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
