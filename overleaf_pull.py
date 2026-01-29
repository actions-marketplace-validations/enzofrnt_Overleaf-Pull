#!/usr/bin/env python3
"""
Download an Overleaf project as a zip and extract it locally.
Standalone: takes project_id, cookie, base_url; no dependency on the JS bridge.
"""
import argparse
import io
import re
import zipfile
from pathlib import Path
from typing import Optional

import requests


def _normalize_base_url(url: str) -> str:
    return url.rstrip("/")


def _cookie_header(cookie: str) -> str:
    """Build Cookie header: Overleaf expects overleaf.sid= value (same as JS login.js)."""
    if cookie.strip().lower().startswith("overleaf.sid="):
        return cookie.strip()
    return "overleaf.sid=" + cookie.strip()


def get_csrf_token(session: requests.Session, base_url: str, project_id: str) -> Optional[str]:
    """GET project page and extract ol-csrfToken from meta tag."""
    url = f"{base_url}/project/{project_id}"
    r = session.get(url)
    r.raise_for_status()
    match = re.search(r'<meta name="ol-csrfToken" content="([^"]*)"', r.text)
    return match.group(1) if match else None


def download_zip(
    session: requests.Session, base_url: str, project_id: str
) -> bytes:
    """Download project zip; returns raw bytes."""
    url = f"{base_url}/project/{project_id}/download/zip"
    r = session.get(url)
    r.raise_for_status()
    data = r.content
    # Overleaf may return HTML (login/error) instead of zip when auth/CSRF is wrong
    if not data.startswith(b"PK"):
        ct = r.headers.get("Content-Type", "")
        preview = data[:200].decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Server did not return a zip file (got Content-Type: {ct}). "
            f"First bytes: {preview!r}..."
        )
    return data


def _single_root_dir(names: list) -> Optional[str]:
    """If all paths share a single top-level directory, return it; else None."""
    top_dirs = set()
    for name in names:
        parts = [p for p in name.split("/") if p]
        if not parts:
            continue
        top_dirs.add(parts[0])
    if len(top_dirs) != 1:
        return None
    single = next(iter(top_dirs))
    # Must have at least one path like "single/file" (content under that dir)
    if not any(n.startswith(single + "/") for n in names):
        return None
    return single


def extract_zip(zip_bytes: bytes, output_dir: Path, flatten_single_root: bool = True) -> None:
    """Extract zip into output_dir. If one root dir and flatten_single_root, flatten into output_dir."""
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
        names = zf.namelist()
        single_root = _single_root_dir(names) if flatten_single_root else None

        if single_root:
            prefix = single_root + "/"
            for info in zf.infolist():
                if not info.filename.startswith(prefix):
                    continue
                rel = info.filename[len(prefix) :].rstrip("/")
                if not rel:
                    continue
                dest = output_dir / rel
                if info.is_dir():
                    dest.mkdir(parents=True, exist_ok=True)
                else:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(zf.read(info.filename))
        else:
            zf.extractall(str(output_dir))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Pull an Overleaf project (download zip and extract locally)."
    )
    parser.add_argument("project_id", help="Overleaf project ID")
    parser.add_argument(
        "cookie",
        help="Session cookie value (e.g. s%%3A...) or full header (overleaf.sid=...). Same as config.cookie in JS.",
    )
    parser.add_argument("base_url", help="Overleaf base URL (e.g. https://overleaf.example.com)")
    parser.add_argument(
        "--output-dir",
        "-o",
        type=Path,
        default=Path("."),
        help="Output directory (default: current)",
    )
    args = parser.parse_args()

    base_url = _normalize_base_url(args.base_url)
    session = requests.Session()
    session.headers["Cookie"] = _cookie_header(args.cookie)

    # Overleaf requires x-csrf-token for /download/zip (same as JS getProjectPage)
    csrf = get_csrf_token(session, base_url, args.project_id)
    if csrf:
        session.headers["X-CSRF-Token"] = csrf

    zip_bytes = download_zip(session, base_url, args.project_id)
    extract_zip(zip_bytes, args.output_dir)
    print(f"Extracted to {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
