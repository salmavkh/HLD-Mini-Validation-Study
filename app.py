from __future__ import annotations

import re

import streamlit as st

from storage_backend import get_or_create_progress


st.set_page_config(page_title="HLD Validation Study", layout="centered")

st.markdown(
    """
    <style>
      .stApp {
        background-color: #ffffff;
      }
      .block-container {
        max-width: 860px;
        padding-top: 2.8rem;
        padding-bottom: 1.8rem;
      }
      .hero-title {
        text-align: center;
        font-size: 30px;
        font-weight: 700;
        color: #262938;
        margin: 0.6rem 0 1.2rem 0;
      }
      .intro-text {
        text-align: center;
        font-size: 18px;
        line-height: 1.45;
        color: #303445;
        margin-bottom: 0.85rem;
      }
      .spacer-sm {
        margin-top: 0.25rem;
      }
      .spacer-md {
        margin-top: 0.75rem;
      }
      .id-label {
        text-align: right;
        font-size: 20px;
        color: #2f3344;
        padding-top: 0.35rem;
      }
      .stTextInput > div > div > input {
        font-size: 20px;
      }
      .stButton > button {
        background-color: #000000;
        color: #ffffff;
        border: 1px solid #000000;
        border-radius: 10px;
        font-size: 22px;
        font-weight: 700;
        min-height: 52px;
        width: 220px;
        margin: 0 auto;
        display: block;
      }
      .stButton > button:hover {
        background-color: #111111;
        color: #ffffff;
        border-color: #111111;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="hero-title">Welcome to the HLD Validation Study</div>', unsafe_allow_html=True)

st.markdown('<div class="intro-text">Thank you for participating in this study.</div>', unsafe_allow_html=True)

st.markdown(
    '<div class="intro-text">The purpose of this study is to evaluate whether the model\'s predicted high-level sound descriptors align with expert human judgment.</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="intro-text">You will be asked to listen to 100 audio files. For each audio file, you will answer 6 descriptor-pair questions. For each pair, please choose the descriptor that best matches the sound. You may choose "Neither / unclear" if neither descriptor clearly fits.</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="intro-text">Please judge each descriptor pair independently.</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="intro-text">Click Save & Next to save your progress. If you exit midway, you can return later and continue from where you left off using the same participant ID.</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="intro-text">Before starting, please enter your assigned participant ID. You should have already received this ID. If you do not have a participant ID but would like to participate, please contact [email]</div>',
    unsafe_allow_html=True,
)

st.markdown('<div class="spacer-md"></div>', unsafe_allow_html=True)

existing_pid = st.session_state.get("participant_id", "")

col_left, col_center, col_right = st.columns([1.6, 2.0, 1.6])
with col_center:
    label_col, input_col = st.columns([1.2, 1.0])
    with label_col:
        st.markdown('<div class="id-label">Enter user id:</div>', unsafe_allow_html=True)
    with input_col:
        participant_id_input = st.text_input(
            "participant_id_input",
            value=existing_pid,
            label_visibility="collapsed",
            placeholder="e.g., 1",
        ).strip().upper()

st.markdown('<div class="spacer-sm"></div>', unsafe_allow_html=True)

btn_left, btn_center, btn_right = st.columns([1.8, 1.4, 1.8])
with btn_center:
    submitted = st.button("Submit", type="secondary", use_container_width=False)

if submitted:
    if not participant_id_input:
        st.error("Please enter a participant ID.")
        st.stop()

    if not re.fullmatch(r"[1-5]", participant_id_input):
        st.error("Participant ID must be a number from 1 to 5.")
        st.stop()

    progress = get_or_create_progress(participant_id_input)
    st.session_state["participant_id"] = participant_id_input

    total = len(progress["audio_order"])
    done = int(progress["current_idx"])
    st.success(f"Loaded {participant_id_input}. Progress: {done}/{total} completed.")

    if hasattr(st, "switch_page"):
        st.switch_page("pages/01_rating.py")
    else:
        st.page_link("pages/01_rating.py", label="Go to Rating Page")

if existing_pid and not submitted:
    st.info(f"Current session participant: {existing_pid}")
