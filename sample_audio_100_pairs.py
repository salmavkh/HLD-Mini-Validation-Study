#!/usr/bin/env python3
"""Sample 100 audio IDs from VA quadrants and copy matching mp3 files.

Workflow:
1) Read predicted VA scores from SQLite DB.
2) Build 4 quadrants with median splits for valence/arousal.
3) Randomly sample 25 file IDs from each quadrant (100 total),
   using only IDs that have a matching mp3 file.
4) Save sampled list CSV to dataset/audio_100_pairs/file_list/.
5) Read CSV back and copy matching dataset/mp3_corpus/<file_id>.mp3
   into dataset/audio_100_pairs/.
"""

from __future__ import annotations

import argparse
import csv
import random
import shutil
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


DB_RELATIVE_PATH = "dataset/audio_predictions_lightgbm_new_va_2.db"
SOURCE_MP3_DIR = "dataset/mp3_corpus"
TARGET_DIR = "dataset/audio_100_pairs"
FILE_LIST_DIR = "dataset/audio_100_pairs/file_list"
FILE_LIST_CSV = "sampled_file_ids.csv"


def print_step(message: str) -> None:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"[{timestamp}] {message}")


def median(values: List[float]) -> float:
    if not values:
        raise ValueError("Cannot compute median of empty list.")
    sorted_values = sorted(values)
    n = len(sorted_values)
    mid = n // 2
    if n % 2 == 1:
        return sorted_values[mid]
    return (sorted_values[mid - 1] + sorted_values[mid]) / 2.0


def load_scores(db_path: Path) -> List[Tuple[int, float, float]]:
    query = """
        SELECT file_id, valence, arousal
        FROM predicted_va_scores
    """
    print_step(f"Connecting to DB: {db_path}")
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(query).fetchall()
    cleaned: List[Tuple[int, float, float]] = []
    for row in rows:
        file_id, valence, arousal = row
        cleaned.append((int(file_id), float(valence), float(arousal)))
    print_step(f"Loaded {len(cleaned)} rows from predicted_va_scores")
    return cleaned


def classify_quadrant(
    valence: float,
    arousal: float,
    valence_median: float,
    arousal_median: float,
) -> str:
    valence_side = "low" if valence < valence_median else "high"
    arousal_side = "low" if arousal < arousal_median else "high"
    return f"{valence_side}_valence_{arousal_side}_arousal"


def stratified_sample(
    rows: Iterable[Tuple[int, float, float]],
    seed: int,
    n_per_quadrant: int,
    source_dir: Path,
) -> Dict[str, List[Tuple[int, float, float]]]:
    rows_list = list(rows)
    valences = [v for _, v, _ in rows_list]
    arousals = [a for _, _, a in rows_list]

    v_med = median(valences)
    a_med = median(arousals)

    print_step(
        "Using median split thresholds: "
        f"valence_median={v_med:.6f}, arousal_median={a_med:.6f}"
    )

    buckets: Dict[str, List[Tuple[int, float, float]]] = defaultdict(list)
    for file_id, valence, arousal in rows_list:
        quadrant = classify_quadrant(valence, arousal, v_med, a_med)
        buckets[quadrant].append((file_id, valence, arousal))

    expected = [
        "low_valence_low_arousal",
        "low_valence_high_arousal",
        "high_valence_high_arousal",
        "high_valence_low_arousal",
    ]

    available_buckets: Dict[str, List[Tuple[int, float, float]]] = defaultdict(list)
    for quadrant in expected:
        for file_id, valence, arousal in buckets[quadrant]:
            mp3_path = source_dir / f"{file_id}.mp3"
            if mp3_path.exists():
                available_buckets[quadrant].append((file_id, valence, arousal))

        raw_count = len(buckets[quadrant])
        available_count = len(available_buckets[quadrant])
        print_step(
            f"Quadrant {quadrant}: {raw_count} DB candidates, "
            f"{available_count} with mp3"
        )
        if available_count < n_per_quadrant:
            raise RuntimeError(
                f"Not enough available samples in {quadrant}: "
                f"need {n_per_quadrant}, found {available_count}."
            )

    rng = random.Random(seed)
    sampled: Dict[str, List[Tuple[int, float, float]]] = {}
    for quadrant in expected:
        sampled[quadrant] = rng.sample(available_buckets[quadrant], n_per_quadrant)
        print_step(
            f"Sampled {n_per_quadrant} from {quadrant} "
            f"(seed={seed})"
        )

    return sampled


def write_sample_csv(sampled: Dict[str, List[Tuple[int, float, float]]], csv_path: Path) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    print_step(f"Writing sampled file list CSV to: {csv_path}")

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["file_id", "valence", "arousal", "quadrant"])
        total = 0
        for quadrant, rows in sampled.items():
            for file_id, valence, arousal in rows:
                writer.writerow([file_id, valence, arousal, quadrant])
                total += 1

    print_step(f"Saved {total} sampled rows to CSV")


def read_file_ids_from_csv(csv_path: Path) -> List[int]:
    print_step(f"Reading sampled file IDs from: {csv_path}")
    file_ids: List[int] = []
    with csv_path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            file_ids.append(int(row["file_id"]))
    print_step(f"Read {len(file_ids)} file IDs from CSV")
    return file_ids


def copy_matches(file_ids: Iterable[int], source_dir: Path, target_dir: Path) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    missing = 0
    copied = 0

    file_ids_list = list(file_ids)
    total = len(file_ids_list)

    old_mp3_files = sorted(target_dir.glob("*.mp3"))
    if old_mp3_files:
        print_step(f"Removing {len(old_mp3_files)} old mp3 files in target folder")
        for old_file in old_mp3_files:
            old_file.unlink()

    print_step(f"Copying matched files from {source_dir} to {target_dir}")
    for idx, file_id in enumerate(file_ids_list, start=1):
        src = source_dir / f"{file_id}.mp3"
        dst = target_dir / f"{file_id}.mp3"

        if not src.exists():
            missing += 1
            print_step(f"[{idx}/{total}] Missing source file: {src.name}")
            continue

        shutil.copy2(src, dst)
        copied += 1
        print_step(f"[{idx}/{total}] Copied: {src.name}")

    print_step(
        f"Copy complete. copied={copied}, missing={missing}, requested={total}"
    )
    if copied != total:
        raise RuntimeError(
            f"Expected to copy {total} files, but copied {copied} "
            f"(missing {missing})."
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sample 100 files by VA quadrants and copy matching mp3 files."
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible sampling (default: 42)",
    )
    parser.add_argument(
        "--n-per-quadrant",
        type=int,
        default=25,
        help="Number of samples per quadrant (default: 25)",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=Path(DB_RELATIVE_PATH),
        help=f"SQLite DB path (default: {DB_RELATIVE_PATH})",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    project_root = Path.cwd()
    db_path = project_root / args.db_path
    source_mp3_dir = project_root / SOURCE_MP3_DIR
    target_dir = project_root / TARGET_DIR
    file_list_csv = project_root / FILE_LIST_DIR / FILE_LIST_CSV

    print_step("Starting VA stratified sampling workflow")
    print_step(f"Project root: {project_root}")

    if not db_path.exists():
        print_step(f"ERROR: DB file not found: {db_path}")
        return 1
    if not source_mp3_dir.exists():
        print_step(f"ERROR: Source mp3 directory not found: {source_mp3_dir}")
        return 1

    try:
        rows = load_scores(db_path)
        sampled = stratified_sample(
            rows=rows,
            seed=args.seed,
            n_per_quadrant=args.n_per_quadrant,
            source_dir=source_mp3_dir,
        )
        write_sample_csv(sampled, file_list_csv)

        sampled_file_ids = read_file_ids_from_csv(file_list_csv)
        copy_matches(sampled_file_ids, source_mp3_dir, target_dir)

        print_step("Workflow finished successfully")
        print_step(f"Sample list CSV: {file_list_csv}")
        print_step(f"Copied files folder: {target_dir}")
        return 0
    except Exception as exc:  # pylint: disable=broad-except
        print_step(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
