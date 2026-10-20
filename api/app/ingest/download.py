from __future__ import annotations

import argparse
import hashlib
from datetime import date
from pathlib import Path

import httpx

from .sources import Source, load_sources, raw_path, save_sources

USER_AGENT = "islamic-family-law-assistant/0.1 (corpus builder)"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def download(source: Source, raw_dir: Path, client: httpx.Client) -> Path:
    target = raw_path(source, raw_dir)
    target.parent.mkdir(parents=True, exist_ok=True)
    response = client.get(source.url_sumber, follow_redirects=True, timeout=120)
    response.raise_for_status()
    target.write_bytes(response.content)
    return target


def sync(
    manifest: Path, raw_dir: Path, client: httpx.Client | None = None, *, force: bool = False
) -> list[str]:
    """Download missing raw files, verify/record sha256. Returns doc_ids whose hash changed."""
    sources = load_sources(manifest)
    own_client = client is None
    client = client or httpx.Client(headers={"User-Agent": USER_AGENT})
    changed: list[str] = []
    try:
        for source in sources:
            if source.fetcher != "http" or not source.url_sumber.startswith(("http://", "https://")):
                continue
            target = raw_path(source, raw_dir)
            if force or not target.exists():
                download(source, raw_dir, client)
                source.tanggal_unduh = date.today()
            digest = sha256_file(target)
            if source.sha256 and source.sha256 != digest and not force:
                raise ValueError(f"{source.doc_id}: sha256 mismatch (file changed)")
            if source.sha256 != digest:
                source.sha256 = digest
                changed.append(source.doc_id)
    finally:
        if own_client:
            client.close()
    save_sources(manifest, sources)
    return changed


def main() -> None:
    parser = argparse.ArgumentParser(description="Download raw corpus files")
    parser.add_argument("--manifest", type=Path, default=Path("../data/sources.yaml"))
    parser.add_argument("--raw-dir", type=Path, default=Path("../data/raw"))
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    changed = sync(args.manifest, args.raw_dir, force=args.force)
    print(f"updated hashes: {changed or 'none'}")


if __name__ == "__main__":
    main()
