#!/usr/bin/env python3
"""Replace sampled WAV files by copying same-named files from corpus.

Default behavior:
- Reads all .wav files currently in dataset/audio_100_pairs_wav
- For each target file <name>.wav, copies from dataset/corpus/<name>.wav
- Overwrites target files in place
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


def log(msg: str) -> None:
    try:
        print(msg, flush=True)
    except BrokenPipeError:
        raise SystemExit(0)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Refresh dataset/audio_100_pairs_wav from dataset/corpus."
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=Path("dataset/corpus"),
        help="Directory containing source WAV files.",
    )
    parser.add_argument(
        "--target-dir",
        type=Path,
        default=Path("dataset/audio_100_pairs_wav"),
        help="Directory containing target WAV files to replace.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned copy actions without writing files.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    source_dir = args.source_dir.resolve()
    target_dir = args.target_dir.resolve()

    log("Starting WAV refresh from corpus")
    log(f"Source directory: {source_dir}")
    log(f"Target directory: {target_dir}")

    if not source_dir.exists():
        log(f"ERROR: source directory not found: {source_dir}")
        return 1
    if not target_dir.exists():
        log(f"ERROR: target directory not found: {target_dir}")
        return 1

    target_files = sorted(target_dir.glob("*.wav"))
    if not target_files:
        log("ERROR: no .wav files found in target directory.")
        return 1

    total = len(target_files)
    copied = 0
    missing_source = 0
    failed = 0

    for idx, target_path in enumerate(target_files, start=1):
        source_path = source_dir / target_path.name

        if not source_path.exists():
            missing_source += 1
            log(f"[{idx}/{total}] MISSING SOURCE: {source_path.name}")
            continue

        if args.dry_run:
            copied += 1
            log(f"[{idx}/{total}] PLAN: {source_path.name} -> {target_path.name}")
            continue

        try:
            shutil.copy2(source_path, target_path)
            copied += 1
            log(f"[{idx}/{total}] OK: {source_path.name} -> {target_path.name}")
        except OSError as exc:
            failed += 1
            log(f"[{idx}/{total}] FAIL: {source_path.name} ({exc})")

    log("---")
    log(
        "Done. "
        f"copied_or_planned={copied}, "
        f"missing_source={missing_source}, "
        f"failed={failed}, total={total}"
    )

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
