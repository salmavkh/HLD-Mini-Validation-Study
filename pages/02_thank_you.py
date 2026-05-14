from __future__ import annotations

import streamlit as st

from study_utils import get_or_create_progress


st.set_page_config(page_title="Thank You", layout="centered")

st.markdown(
    """
    <style>
      .stApp {
        background-color: #ffffff;
      }
      .block-container {
        max-width: 760px;
        padding-top: clamp(4rem, 18vh, 12rem);
        padding-bottom: 3rem;
      }
      .thank-title {
        text-align: center;
        font-size: 34px;
        font-weight: 700;
        color: #1f2230;
        margin-bottom: 1rem;
      }
      .thank-body {
        text-align: center;
        font-size: 18px;
        line-height: 1.5;
        color: #303445;
        margin-bottom: 1.6rem;
      }
      .stButton > button {
        min-height: 46px;
        border-radius: 10px;
        font-weight: 600;
        background-color: #ffffff;
        color: #000000;
        border: 1px solid #000000;
      }
      .stButton > button:hover {
        background-color: #f7f7f7;
        color: #000000;
        border-color: #000000;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

participant_id = st.session_state.get("participant_id")
if not participant_id:
    st.warning("No participant session found.")
    if st.button("Back to Home"):
        if hasattr(st, "switch_page"):
            st.switch_page("app.py")
    st.stop()

progress = get_or_create_progress(participant_id)
current_idx = int(progress["current_idx"])
total = len(progress["audio_order"])

if current_idx < total:
    st.warning(f"You still have {total - current_idx} audio files left.")
    if st.button("Continue Rating"):
        if hasattr(st, "switch_page"):
            st.switch_page("pages/01_rating.py")
    st.stop()

st.markdown('<div class="thank-title">Thank You!</div>', unsafe_allow_html=True)
st.markdown(
    f'<div class="thank-body">You have completed all {total} audio files.<br/>Your responses have been saved successfully.<br/><br/>Participant ID: {participant_id}</div>',
    unsafe_allow_html=True,
)

left, center, right = st.columns([1.8, 1.4, 1.8])
with center:
    if st.button("Back to Home", use_container_width=True):
        if hasattr(st, "switch_page"):
            st.switch_page("app.py")
