#!/usr/bin/env python3
"""Convert sampled study MP3 files to WAV.

Default behavior:
- Reads sampled IDs from dataset/audio_100_pairs/file_list/sampled_file_ids.csv
- Converts dataset/audio_100_pairs/<id>.mp3
- Writes WAV files to dataset/audio_100_pairs_wav/<id>.wav

Requires ffmpeg installed and available on PATH.
"""

from __future__ import annotations

import argparse
import csv
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List


def log(msg: str) -> None:
    try:
        print(msg, flush=True)
    except BrokenPipeError:
        raise SystemExit(0)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert sampled MP3 files to WAV.")
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("dataset/audio_100_pairs"),
        help="Directory containing sampled MP3 files.",
    )
    parser.add_argument(
        "--sample-list",
        type=Path,
        default=Path("dataset/audio_100_pairs/file_list/sampled_file_ids.csv"),
        help="CSV containing sampled file IDs (expects column: file_id).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("dataset/audio_100_pairs_wav"),
        help="Directory to write WAV files.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing WAV files.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned conversions without running ffmpeg.",
    )
    return parser.parse_args()


def find_ffmpeg() -> str:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError(
            "ffmpeg not found on PATH. Install ffmpeg first, then rerun this script."
        )
    return ffmpeg


def load_sampled_mp3_files(input_dir: Path, sample_list: Path) -> List[Path]:
    if sample_list.exists():
        files: List[Path] = []
        with sample_list.open("r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                file_id = row.get("file_id", "").strip()
                if file_id:
                    files.append(input_dir / f"{file_id}.mp3")
        if files:
            return files

    return sorted(input_dir.glob("*.mp3"))


def convert_one(ffmpeg: str, src: Path, dst: Path, overwrite: bool, dry_run: bool) -> None:
    cmd = [
        ffmpeg,
        "-v",
        "error",
        "-i",
        str(src),
        "-acodec",
        "pcm_s16le",
        str(dst),
    ]

    if overwrite:
        cmd.insert(1, "-y")
    else:
        cmd.insert(1, "-n")

    if dry_run:
        log(f"[DRY RUN] {' '.join(cmd)}")
        return

    subprocess.run(cmd, check=True)


def main() -> int:
    args = parse_args()

    input_dir = args.input_dir.resolve()
    sample_list = args.sample_list.resolve()
    output_dir = args.output_dir.resolve()

    log("Starting MP3 -> WAV conversion")
    log(f"Input directory : {input_dir}")
    log(f"Sample list     : {sample_list}")
    log(f"Output directory: {output_dir}")

    if not input_dir.exists():
        log(f"ERROR: input directory not found: {input_dir}")
        return 1

    try:
        ffmpeg = find_ffmpeg()
        log(f"Using ffmpeg: {ffmpeg}")
    except RuntimeError as exc:
        log(f"ERROR: {exc}")
        return 1

    mp3_files = load_sampled_mp3_files(input_dir, sample_list)
    if not mp3_files:
        log("ERROR: no MP3 files found to convert.")
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)

    total = len(mp3_files)
    converted = 0
    skipped_missing = 0
    skipped_exists = 0
    failed = 0

    for idx, src in enumerate(mp3_files, start=1):
        dst = output_dir / f"{src.stem}.wav"

        if not src.exists():
            skipped_missing += 1
            log(f"[{idx}/{total}] MISSING: {src.name}")
            continue

        if dst.exists() and not args.overwrite:
            skipped_exists += 1
            log(f"[{idx}/{total}] SKIP (exists): {dst.name}")
            continue

        try:
            convert_one(ffmpeg, src, dst, args.overwrite, args.dry_run)
            converted += 1
            if args.dry_run:
                log(f"[{idx}/{total}] PLAN: {src.name} -> {dst.name}")
            else:
                log(f"[{idx}/{total}] OK: {src.name} -> {dst.name}")
        except subprocess.CalledProcessError:
            failed += 1
            log(f"[{idx}/{total}] FAIL: {src.name}")

    log("---")
    log(
        "Done. "
        f"planned_or_converted={converted}, "
        f"missing={skipped_missing}, "
        f"exists_skipped={skipped_exists}, "
        f"failed={failed}, total={total}"
    )

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
