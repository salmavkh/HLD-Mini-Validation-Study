from __future__ import annotations

import csv
import hashlib
import json
import random
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Sequence, Tuple
from zoneinfo import ZoneInfo


PROJECT_ROOT = Path(__file__).resolve().parent
AUDIO_LIST_CSV = PROJECT_ROOT / "dataset" / "audio_100_pairs" / "file_list" / "sampled_file_ids.csv"
AUDIO_DIR = PROJECT_ROOT / "dataset" / "audio_100_pairs"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
PROGRESS_CSV = OUTPUT_DIR / "progress.csv"
RESPONSES_CSV = OUTPUT_DIR / "responses.csv"
RESPONSE_FIELDS = [
    "participant_id",
    "audio_filename",
    "descriptor_pair",
    "selected_choice",
    "timestamp",
]

DESCRIPTOR_PAIRS: List[Tuple[str, str]] = [
    ("Aggressive", "Peaceful"),
    ("Alarming", "Soothing"),
    ("Dangerous", "Safe"),
    ("Blunt", "Sharp"),
    ("Digital", "Analogue"),
    ("Electronic", "Acoustic"),
]


VANCOUVER_TZ = ZoneInfo("America/Vancouver")


def utc_now_iso() -> str:
    return datetime.now(VANCOUVER_TZ).isoformat()


def ensure_output_files() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not PROGRESS_CSV.exists():
        with PROGRESS_CSV.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["participant_id", "current_idx", "audio_order_json", "last_updated"],
            )
            writer.writeheader()

    if not RESPONSES_CSV.exists():
        with RESPONSES_CSV.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=RESPONSE_FIELDS,
            )
            writer.writeheader()


def _seed_from_text(text: str) -> int:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def deterministic_shuffle(items: Sequence[str], seed_text: str) -> List[str]:
    shuffled = list(items)
    rng = random.Random(_seed_from_text(seed_text))
    rng.shuffle(shuffled)
    return shuffled


def load_audio_filenames() -> List[str]:
    if AUDIO_LIST_CSV.exists():
        filenames: List[str] = []
        with AUDIO_LIST_CSV.open("r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                file_id = row["file_id"].strip()
                filenames.append(f"{file_id}.mp3")
        if filenames:
            return filenames

    return sorted(p.name for p in AUDIO_DIR.glob("*.mp3"))


def _read_progress_rows() -> List[Dict[str, str]]:
    ensure_output_files()
    with PROGRESS_CSV.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _write_progress_rows(rows: List[Dict[str, str]]) -> None:
    with PROGRESS_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["participant_id", "current_idx", "audio_order_json", "last_updated"],
        )
        writer.writeheader()
        writer.writerows(rows)


def get_or_create_progress(participant_id: str) -> Dict[str, object]:
    rows = _read_progress_rows()
    for row in rows:
        if row["participant_id"] == participant_id:
            try:
                order = json.loads(row["audio_order_json"])
            except json.JSONDecodeError:
                order = []
            return {
                "participant_id": participant_id,
                "current_idx": int(row["current_idx"]),
                "audio_order": order,
            }

    audio_files = load_audio_filenames()
    if not audio_files:
        raise RuntimeError(
            f"No audio files found. Expected list CSV at {AUDIO_LIST_CSV} "
            f"or mp3 files in {AUDIO_DIR}."
        )

    randomized_order = deterministic_shuffle(audio_files, f"audio-order::{participant_id}")
    rows.append(
        {
            "participant_id": participant_id,
            "current_idx": "0",
            "audio_order_json": json.dumps(randomized_order),
            "last_updated": utc_now_iso(),
        }
    )
    _write_progress_rows(rows)

    return {
        "participant_id": participant_id,
        "current_idx": 0,
        "audio_order": randomized_order,
    }


def update_progress_index(participant_id: str, next_idx: int) -> None:
    rows = _read_progress_rows()
    updated = False
    for row in rows:
        if row["participant_id"] == participant_id:
            row["current_idx"] = str(next_idx)
            row["last_updated"] = utc_now_iso()
            updated = True
            break

    if not updated:
        raise RuntimeError(
            f"Participant {participant_id} not found in {PROGRESS_CSV}. "
            "Start from app.py first."
        )

    _write_progress_rows(rows)


def get_question_order(participant_id: str, audio_filename: str) -> List[Tuple[str, str]]:
    indexed = list(enumerate(DESCRIPTOR_PAIRS))
    rng = random.Random(_seed_from_text(f"question-order::{participant_id}::{audio_filename}"))
    rng.shuffle(indexed)
    return [pair for _, pair in indexed]


def upsert_audio_responses(
    participant_id: str,
    audio_filename: str,
    answers: Dict[str, str],
) -> None:
    ensure_output_files()

    existing_rows: List[Dict[str, str]] = []
    with RESPONSES_CSV.open("r", newline="", encoding="utf-8") as f:
        existing_rows = list(csv.DictReader(f))

    filtered_rows = []
    for row in existing_rows:
        if (
            row["participant_id"] == participant_id
            and row["audio_filename"] == audio_filename
        ):
            continue
        filtered_rows.append(
            {
                "participant_id": row.get("participant_id", ""),
                "audio_filename": row.get("audio_filename", ""),
                "descriptor_pair": row.get("descriptor_pair", ""),
                "selected_choice": row.get("selected_choice", ""),
                "timestamp": row.get("timestamp", ""),
            }
        )

    now = utc_now_iso()
    for descriptor_pair, selected_choice in answers.items():
        filtered_rows.append(
            {
                "participant_id": participant_id,
                "audio_filename": audio_filename,
                "descriptor_pair": descriptor_pair,
                "selected_choice": selected_choice,
                "timestamp": now,
            }
        )

    with RESPONSES_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=RESPONSE_FIELDS,
        )
        writer.writeheader()
        writer.writerows(filtered_rows)


def get_saved_audio_answers(participant_id: str, audio_filename: str) -> Dict[str, str]:
    ensure_output_files()
    saved: Dict[str, str] = {}
    with RESPONSES_CSV.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if (
                row["participant_id"] == participant_id
                and row["audio_filename"] == audio_filename
            ):
                saved[row["descriptor_pair"]] = row["selected_choice"]
    return saved
