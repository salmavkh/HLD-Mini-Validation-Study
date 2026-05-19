from __future__ import annotations

from pathlib import Path

import streamlit as st

from storage_backend import (
    AUDIO_DIR,
    get_or_create_progress,
    get_question_order,
    get_saved_audio_answers,
    update_progress_index,
    upsert_audio_responses,
)


st.set_page_config(page_title="Rate Audio", layout="centered")

st.markdown(
    """
    <style>
      .stApp {
        background-color: #ffffff;
      }
      .block-container {
        max-width: 680px;
        padding-top: 3rem;
        padding-bottom: 2rem;
      }
      .top-meta {
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 16px;
        font-weight: 400;
        color: #1f2230;
        margin-top: 0.25rem;
        margin-bottom: 0.45rem;
      }
      .btn-row {
        margin-top: 1rem;
      }
      .row-sep {
        border-top: 1px solid #e6e8ef;
        margin: 0;
      }
      .table-gap-top {
        margin-top: 0.05rem;
      }
      .table-gap-bottom {
        margin-bottom: 0.05rem;
      }
      .row-content {
        padding: 0;
        margin-top: 0;
        margin-bottom: 0;
      }
      .descriptor-label {
        margin: 0;
        line-height: 1.05;
        font-size: 14px;
        font-weight: 500;
      }
      .stButton > button {
        min-height: 46px;
        border-radius: 10px;
        font-weight: 600;
      }
      .stButton > button[kind="primary"] {
        background-color: #000000;
        color: #ffffff;
        border: 1px solid #000000;
      }
      .stButton > button[kind="primary"]:hover {
        background-color: #111111;
        color: #ffffff;
        border-color: #111111;
      }
      .stButton > button[kind="secondary"] {
        background-color: #ffffff;
        color: #000000;
        border: 1px solid #000000;
      }
      .stButton > button[kind="secondary"]:hover {
        background-color: #f7f7f7;
        color: #000000;
        border-color: #000000;
      }
      .stButton > button[kind="secondary"]:disabled,
      .stButton > button[kind="secondary"]:disabled:hover {
        background-color: #ffffff !important;
        color: #8a8a8a !important;
        border: 1px solid #b8b8b8 !important;
        opacity: 1 !important;
        cursor: not-allowed !important;
      }
      .stButton > button[kind="primary"]:disabled,
      .stButton > button[kind="primary"]:disabled:hover {
        background-color: #d3d3d3 !important;
        color: #9a9a9a !important;
        border: 1px solid #d3d3d3 !important;
        opacity: 1 !important;
        cursor: not-allowed !important;
      }
      .stRadio [role="radiogroup"] input[type="radio"] {
        accent-color: #000000;
      }
      .stRadio [role="radiogroup"] {
        display: grid !important;
        grid-template-columns: 12rem 12rem;
        justify-content: start !important;
        align-items: center !important;
        margin-left: 3rem !important;
        column-gap: 1.1rem !important;
        row-gap: 0 !important;
      }
      .stRadio [role="radiogroup"] > label {
        display: flex !important;
        align-items: center !important;
        margin: 0 !important;
        min-width: 0;
        padding-top: 0 !important;
        padding-bottom: 0 !important;
        line-height: 1.05 !important;
        justify-self: start;
        width: 100%;
        text-align: left !important;
        white-space: nowrap !important;
      }
      div[data-testid="stRadio"] {
        margin-top: -0.5rem !important;
        margin-bottom: -1.5rem !important;
      }
      div[data-testid="stRadio"] > div {
        margin-bottom: 0 !important;
      }
      div[data-testid="stRadio"] label p {
        margin: 0 !important;
        font-size: 14px !important;
        line-height: 1.05 !important;
      }
      .stRadio [role="radiogroup"] > label span {
        font-size: 14px !important;
        line-height: 1.05 !important;
      }
      div[data-testid="stRadio"] label > div:first-child {
        margin-top: 0 !important;
        margin-bottom: 0 !important;
      }
      div[data-testid="stRadio"] label {
        transform: none !important;
      }
      div[data-testid="stRadio"] label span {
        vertical-align: middle !important;
      }
      @media (max-width: 768px) {
        .block-container {
          padding-top: 1.4rem;
          padding-left: 0.95rem;
          padding-right: 0.95rem;
        }
        .top-meta {
          font-size: 14px;
          flex-wrap: wrap;
          row-gap: 0.2rem;
        }
        .stRadio [role="radiogroup"] {
          grid-template-columns: max-content max-content !important;
          margin-left: 0.2rem !important;
          column-gap: 0.9rem !important;
        }
        div[data-testid="stRadio"] {
          margin-top: -0.25rem !important;
          margin-bottom: -1.0rem !important;
        }
      }
    </style>
    """,
    unsafe_allow_html=True,
)

participant_id = st.session_state.get("participant_id")
if not participant_id:
    st.warning("No participant ID found. Start from the home page first.")
    st.page_link("app.py", label="Go to Home")
    st.stop()

progress = get_or_create_progress(participant_id)
audio_order = progress["audio_order"]
current_idx = int(progress["current_idx"])
total = len(audio_order)

if current_idx >= total:
    if hasattr(st, "switch_page"):
        st.switch_page("pages/02_thank_you.py")
    st.success(f"All done, user {participant_id}. You completed all {total} audio files.")
    st.page_link("pages/02_thank_you.py", label="Go to Thank You Page")
    st.stop()

audio_filename = audio_order[current_idx]
audio_stem = Path(audio_filename).stem
display_audio_filename = f"{audio_stem}.wav"
wav_dir = AUDIO_DIR.parent / "audio_100_pairs_wav"
wav_path = wav_dir / f"{audio_stem}.wav"

if not wav_path.exists():
    st.error(f"Audio WAV file not found: {wav_path}")
    st.stop()
audio_path = wav_path

st.markdown(
    f'<div class="top-meta"><span>User id : {participant_id}</span><span>{display_audio_filename}</span><span>Audio {current_idx + 1} of {total}</span></div>',
    unsafe_allow_html=True,
)

st.progress((current_idx + 1) / total)
st.audio(str(audio_path), format="audio/mp3")

question_order = get_question_order(participant_id, audio_filename)
saved_answers = get_saved_audio_answers(participant_id, audio_filename)

st.markdown('<div class="table-gap-top"></div>', unsafe_allow_html=True)
st.markdown('<div class="row-sep"></div>', unsafe_allow_html=True)

answers = {}
for idx, (left, right) in enumerate(question_order, start=1):
    left_value = left.lower()
    right_value = right.lower()
    valid_options = {left_value, right_value}
    descriptor_key = f"{left_value}|{right_value}"
    widget_key = f"choice::{participant_id}::{audio_filename}::{descriptor_key}"

    if widget_key in st.session_state and st.session_state[widget_key] not in valid_options:
        del st.session_state[widget_key]

    if widget_key not in st.session_state and descriptor_key in saved_answers:
        saved_value = saved_answers[descriptor_key]
        if saved_value == "left":
            saved_value = left_value
        elif saved_value == "right":
            saved_value = right_value
        if saved_value in valid_options:
            st.session_state[widget_key] = saved_value

    st.markdown('<div class="row-content">', unsafe_allow_html=True)
    row_label_col, row_choice_col = st.columns([1.0, 3.2], vertical_alignment="center")
    with row_label_col:
        st.markdown(f'<p class="descriptor-label">Descriptor {idx}</p>', unsafe_allow_html=True)
    with row_choice_col:
        response = st.radio(
            label=f"Descriptor {idx} choice",
            options=[left_value, right_value],
            format_func=lambda x, l=left, r=right: {
                l.lower(): l,
                r.lower(): r,
            }[x],
            horizontal=True,
            index=None,
            key=widget_key,
            label_visibility="collapsed",
        )
    st.markdown("</div>", unsafe_allow_html=True)

    answers[descriptor_key] = response
    if idx < len(question_order):
        st.markdown('<div class="row-sep"></div>', unsafe_allow_html=True)

st.markdown('<div class="row-sep"></div>', unsafe_allow_html=True)
st.markdown('<div class="table-gap-bottom"></div>', unsafe_allow_html=True)

st.markdown('<div class="btn-row"></div>', unsafe_allow_html=True)
prev_col, next_col = st.columns([1, 1])
all_answered = all(value is not None for value in answers.values())

with prev_col:
    prev_clicked = st.button(
        "Previous",
        use_container_width=True,
        disabled=(current_idx == 0),
    )

with next_col:
    save_clicked = st.button(
        "Save & Next",
        use_container_width=True,
        type="primary",
        disabled=not all_answered,
    )

if prev_clicked and current_idx > 0:
    update_progress_index(participant_id, current_idx - 1)
    st.rerun()

if save_clicked:
    upsert_audio_responses(
        participant_id=participant_id,
        audio_filename=audio_filename,
        answers=answers,
    )

    next_idx = current_idx + 1
    update_progress_index(participant_id, next_idx)

    if next_idx >= total and hasattr(st, "switch_page"):
        st.switch_page("pages/02_thank_you.py")

    st.success("Saved. Loading next audio...")
    st.rerun()
