from __future__ import annotations

import csv
import hashlib
import json
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import gspread
import streamlit as st
from gspread.exceptions import WorksheetNotFound


PROJECT_ROOT = Path(__file__).resolve().parent
AUDIO_LIST_CSV = PROJECT_ROOT / "dataset" / "audio_100_pairs" / "file_list" / "sampled_file_ids.csv"
AUDIO_DIR = PROJECT_ROOT / "dataset" / "audio_100_pairs"

PROGRESS_FIELDS = ["participant_id", "current_idx", "audio_order_json", "last_updated"]
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


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _seed_from_text(text: str) -> int:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def deterministic_shuffle(items: Sequence[str], seed_text: str) -> List[str]:
    shuffled = list(items)
    rng = random.Random(_seed_from_text(seed_text))
    rng.shuffle(shuffled)
    return shuffled


def load_audio_filenames() -> List[str]:
    if not AUDIO_LIST_CSV.exists():
        raise RuntimeError(
            f"Sample list not found: {AUDIO_LIST_CSV}. "
            "Generate it first before running the study app."
        )

    filenames: List[str] = []
    with AUDIO_LIST_CSV.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            file_id = row.get("file_id", "").strip()
            if file_id:
                filenames.append(f"{file_id}.mp3")

    if not filenames:
        raise RuntimeError(
            f"No file_id rows found in sample list: {AUDIO_LIST_CSV}"
        )

    return filenames


def _get_storage_config() -> Tuple[str, str, str]:
    if "gcp_service_account" not in st.secrets:
        raise RuntimeError(
            "Missing [gcp_service_account] in Streamlit secrets. "
            "Add service account credentials before running this app."
        )

    if "study_storage" not in st.secrets:
        raise RuntimeError(
            "Missing [study_storage] in Streamlit secrets. "
            "Add sheet_id/responses_tab/progress_tab before running this app."
        )

    cfg = st.secrets["study_storage"]
    sheet_id = str(cfg.get("sheet_id", "")).strip()
    responses_tab = str(cfg.get("responses_tab", "")).strip()
    progress_tab = str(cfg.get("progress_tab", "")).strip()

    if not sheet_id or not responses_tab or not progress_tab:
        raise RuntimeError(
            "Invalid study_storage config in secrets. "
            "Required keys: sheet_id, responses_tab, progress_tab."
        )

    return sheet_id, responses_tab, progress_tab


@st.cache_resource(show_spinner=False)
def _get_spreadsheet() -> gspread.Spreadsheet:
    sheet_id, _, _ = _get_storage_config()
    service_account_info = dict(st.secrets["gcp_service_account"])
    client = gspread.service_account_from_dict(service_account_info)
    return client.open_by_key(sheet_id)


def _get_or_create_worksheet(spreadsheet: gspread.Spreadsheet, title: str, rows: int, cols: int) -> gspread.Worksheet:
    try:
        return spreadsheet.worksheet(title)
    except WorksheetNotFound:
        return spreadsheet.add_worksheet(title=title, rows=rows, cols=cols)


def _ensure_headers(ws: gspread.Worksheet, expected_fields: List[str]) -> None:
    header = ws.row_values(1)
    if not header:
        ws.append_row(expected_fields, value_input_option="RAW")
        return

    if header[: len(expected_fields)] != expected_fields:
        raise RuntimeError(
            f"Header mismatch in worksheet '{ws.title}'. "
            f"Expected: {expected_fields}. Found: {header}."
        )


@st.cache_resource(show_spinner=False)
def _get_worksheets() -> Tuple[gspread.Worksheet, gspread.Worksheet]:
    _, responses_tab, progress_tab = _get_storage_config()
    spreadsheet = _get_spreadsheet()

    progress_ws = _get_or_create_worksheet(spreadsheet, progress_tab, rows=2000, cols=8)
    responses_ws = _get_or_create_worksheet(spreadsheet, responses_tab, rows=10000, cols=8)

    _ensure_headers(progress_ws, PROGRESS_FIELDS)
    _ensure_headers(responses_ws, RESPONSE_FIELDS)

    return progress_ws, responses_ws


def _read_sheet_rows(ws: gspread.Worksheet, expected_fields: List[str]) -> List[Dict[str, str]]:
    values = ws.get_all_values()
    if not values:
        return []

    header = values[0]
    if header[: len(expected_fields)] != expected_fields:
        raise RuntimeError(
            f"Header mismatch in worksheet '{ws.title}'. "
            f"Expected: {expected_fields}. Found: {header}."
        )

    rows: List[Dict[str, str]] = []
    for raw_row in values[1:]:
        padded = raw_row + [""] * (len(expected_fields) - len(raw_row))
        row = {field: padded[idx] for idx, field in enumerate(expected_fields)}
        if any(row.values()):
            rows.append(row)
    return rows


def _find_progress_row_index(ws: gspread.Worksheet, participant_id: str) -> int | None:
    values = ws.get_all_values()
    for sheet_row_idx, row in enumerate(values[1:], start=2):
        if row and row[0] == participant_id:
            return sheet_row_idx
    return None


def get_or_create_progress(participant_id: str) -> Dict[str, object]:
    progress_ws, _ = _get_worksheets()
    rows = _read_sheet_rows(progress_ws, PROGRESS_FIELDS)

    for row in rows:
        if row["participant_id"] == participant_id:
            try:
                order = json.loads(row["audio_order_json"])
            except json.JSONDecodeError:
                order = []
            return {
                "participant_id": participant_id,
                "current_idx": int(row["current_idx"] or 0),
                "audio_order": order,
            }

    audio_files = load_audio_filenames()
    randomized_order = deterministic_shuffle(audio_files, f"audio-order::{participant_id}")

    progress_ws.append_row(
        [
            participant_id,
            "0",
            json.dumps(randomized_order),
            utc_now_iso(),
        ],
        value_input_option="RAW",
    )

    return {
        "participant_id": participant_id,
        "current_idx": 0,
        "audio_order": randomized_order,
    }


def update_progress_index(participant_id: str, next_idx: int) -> None:
    progress_ws, _ = _get_worksheets()
    row_index = _find_progress_row_index(progress_ws, participant_id)

    if row_index is None:
        raise RuntimeError(
            f"Participant {participant_id} not found in progress worksheet. "
            "Start from app.py first."
        )

    row_values = progress_ws.row_values(row_index)
    existing_audio_order_json = row_values[2] if len(row_values) > 2 else "[]"

    progress_ws.update(
        range_name=f"B{row_index}:D{row_index}",
        values=[[str(next_idx), existing_audio_order_json, utc_now_iso()]],
        value_input_option="RAW",
    )


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
    _, responses_ws = _get_worksheets()
    existing_rows = _read_sheet_rows(responses_ws, RESPONSE_FIELDS)

    filtered_rows: List[Dict[str, str]] = [
        row
        for row in existing_rows
        if not (
            row["participant_id"] == participant_id
            and row["audio_filename"] == audio_filename
        )
    ]

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

    table = [RESPONSE_FIELDS]
    for row in filtered_rows:
        table.append([row.get(field, "") for field in RESPONSE_FIELDS])

    responses_ws.clear()
    responses_ws.update(range_name="A1", values=table, value_input_option="RAW")


def get_saved_audio_answers(participant_id: str, audio_filename: str) -> Dict[str, str]:
    _, responses_ws = _get_worksheets()
    rows = _read_sheet_rows(responses_ws, RESPONSE_FIELDS)

    saved: Dict[str, str] = {}
    for row in rows:
        if (
            row["participant_id"] == participant_id
            and row["audio_filename"] == audio_filename
        ):
            saved[row["descriptor_pair"]] = row["selected_choice"]
    return saved
