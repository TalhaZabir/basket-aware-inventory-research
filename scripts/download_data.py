"""Download the public source files used by the basket-aware inventory study.

The script is intentionally source-pinned and checksum-aware. It never invents
or silently substitutes a missing source file.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


UCI_URL = "https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip"
UCI_SOURCE = "https://archive.ics.uci.edu/dataset/502/online+retail+ii"
M5_SOURCE = "https://doi.org/10.5281/zenodo.10203108"
M5_OFFICIAL = "https://www.kaggle.com/competitions/m5-forecasting-accuracy/data"
M5_FILES = {
    "sales_train_validation.csv": (120007726, "26a366a25beb57b0a8f4c7b148758f94", "https://zenodo.org/api/records/10203108/files/sales_train_validation.csv/content"),
    "sales_train_evaluation.csv": (121736518, "b806dfc9f30a745102b708c09951f6aa", "https://zenodo.org/api/records/10203108/files/sales_train_evaluation.csv/content"),
    "sell_prices.csv": (203395785, "08c591caa99e55daf3e0ccac913f7c85", "https://zenodo.org/api/records/10203108/files/sell_prices.csv/content"),
    "calendar.csv": (103469, "3ffeab2991b0c8e861d008b39ea4c95c", "https://zenodo.org/api/records/10203108/files/calendar.csv/content"),
    "sample_submission.csv": (5228786, "c281a69d7c011274899d92020a66e25b", "https://zenodo.org/api/records/10203108/files/sample_submission.csv/content"),
}


def md5_file(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(url: str, destination: Path) -> tuple[str, int, str]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_name(destination.name + ".part")
    request = urllib.request.Request(url, headers={"User-Agent": "basket-aware-inventory-research/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=120) as response, partial.open("wb") as handle:
            total = 0
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                handle.write(chunk)
                total += len(chunk)
        partial.replace(destination)
    except Exception:
        partial.unlink(missing_ok=True)
        raise
    return "downloaded", total, sha256_file(destination)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--datasets", default="uci,m5", help="Comma-separated subset of uci,m5")
    parser.add_argument("--root", default=None, help="Package root; defaults to the parent of this script")
    args = parser.parse_args()

    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parents[1]
    raw = root / "data" / "raw"
    manifest_path = root / "metadata" / "source_manifest.csv"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    rows: list[dict[str, object]] = []

    requested = {part.strip().lower() for part in args.datasets.split(",") if part.strip()}
    if "uci" in requested:
        destination = raw / "uci_online_retail_ii.zip"
        entry: dict[str, object] = {"dataset": "UCI Online Retail II", "file": destination.relative_to(root).as_posix(), "source_url": UCI_SOURCE, "download_url": UCI_URL, "status": "pending", "bytes": "", "sha256": "", "md5": "", "retrieved_at_utc": now, "notes": "Official UCI repository download; checksum recorded locally after transfer."}
        try:
            if destination.exists() and destination.stat().st_size > 0:
                status = "already_present"
                size = destination.stat().st_size
                digest = sha256_file(destination)
            else:
                status, size, digest = download(UCI_URL, destination)
            entry.update({"status": status, "bytes": size, "sha256": digest})
        except Exception as exc:
            entry.update({"status": "download_failed", "notes": f"{entry['notes']} Error: {exc}"})
        rows.append(entry)

    if "m5" in requested:
        for filename, (expected_size, expected_md5, url) in M5_FILES.items():
            destination = raw / "m5" / filename
            entry = {"dataset": "M5 Forecasting Accuracy", "file": destination.relative_to(root).as_posix(), "source_url": M5_SOURCE, "download_url": url, "status": "pending", "bytes": "", "sha256": "", "md5": "", "retrieved_at_utc": now, "notes": f"Public Zenodo copy of the Kaggle release; expected bytes={expected_size}; expected md5={expected_md5}. Official competition page: {M5_OFFICIAL}"}
            try:
                if destination.exists() and destination.stat().st_size == expected_size and md5_file(destination) == expected_md5:
                    status = "already_present_verified"
                    size = destination.stat().st_size
                    digest = sha256_file(destination)
                else:
                    status, size, digest = download(url, destination)
                    actual_md5 = md5_file(destination)
                    if size != expected_size or actual_md5 != expected_md5:
                        raise IOError(f"checksum mismatch: size={size}, md5={actual_md5}")
                entry.update({"status": status, "bytes": size, "sha256": digest, "md5": md5_file(destination)})
            except Exception as exc:
                entry.update({"status": "download_failed", "notes": f"{entry['notes']} Error: {exc}"})
            rows.append(entry)

    with manifest_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["dataset", "file", "source_url", "download_url", "status", "bytes", "sha256", "md5", "retrieved_at_utc", "notes"])
        writer.writeheader()
        writer.writerows(rows)

    failures = [row for row in rows if str(row["status"]).endswith("failed")]
    print(json.dumps({"manifest": str(manifest_path), "files": len(rows), "failures": len(failures)}, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
