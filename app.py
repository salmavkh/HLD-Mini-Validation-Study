from __future__ import annotations

import csv
import re
from pathlib import Path

import streamlit as st

from storage_backend import get_or_create_progress


PROJECT_ROOT = Path(__file__).resolve().parent
CREDENTIALS_CSV = PROJECT_ROOT / "participant_credentials.csv"


@st.cache_data(show_spinner=False)
def load_credentials() -> dict[str, str]:
    if "participant_credentials" in st.secrets:
        secret_creds = dict(st.secrets["participant_credentials"])
        credentials_from_secrets = {
            str(k).strip(): str(v).strip() for k, v in secret_creds.items()
        }
        if credentials_from_secrets:
            return credentials_from_secrets

    if not CREDENTIALS_CSV.exists():
        raise RuntimeError(
            f"Credentials file not found: {CREDENTIALS_CSV}. "
            "For deployment, add [participant_credentials] in Streamlit secrets."
        )

    credentials: dict[str, str] = {}
    with CREDENTIALS_CSV.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if "participant_id" not in (reader.fieldnames or []) or "password" not in (
            reader.fieldnames or []
        ):
            raise RuntimeError(
                "Invalid participant_credentials.csv header. "
                "Expected columns: participant_id,password"
            )
        for row in reader:
            participant_id = str(row.get("participant_id", "")).strip()
            password = str(row.get("password", "")).strip()
            if participant_id:
                credentials[participant_id] = password

    if not credentials:
        raise RuntimeError(
            "participant_credentials.csv has no credentials. "
            "For deployment, add [participant_credentials] in Streamlit secrets."
        )

    return credentials


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
        text-align: left;
        font-size: 20px;
        color: #2f3344;
        padding-top: 0.35rem;
        white-space: nowrap;
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
    '<div class="intro-text">Before starting, please enter your assigned user ID and password. You should have already received these credentials. If you do not have them but would like to participate, please contact salmavkh@student.ubc.ca</div>',
    unsafe_allow_html=True,
)

st.markdown('<div class="spacer-md"></div>', unsafe_allow_html=True)

existing_pid = st.session_state.get("participant_id", "")

col_left, col_center, col_right = st.columns([1.2, 2.8, 1.2])
with col_center:
    label_col, input_col = st.columns([1.0, 1.15])
    with label_col:
        st.markdown('<div class="id-label">Enter user id:</div>', unsafe_allow_html=True)
    with input_col:
        participant_id_input = st.text_input(
            "participant_id_input",
            value=existing_pid,
            label_visibility="collapsed",
            placeholder="e.g., 1",
        ).strip()

    label_col2, input_col2 = st.columns([1.0, 1.15])
    with label_col2:
        st.markdown('<div class="id-label">Password:</div>', unsafe_allow_html=True)
    with input_col2:
        password_input = st.text_input(
            "password_input",
            value="",
            label_visibility="collapsed",
            type="password",
            placeholder="Enter password",
        ).strip()

st.markdown('<div class="spacer-sm"></div>', unsafe_allow_html=True)

btn_left, btn_center, btn_right = st.columns([1.8, 1.4, 1.8])
with btn_center:
    submitted = st.button("Submit", type="secondary", use_container_width=False)

if submitted:
    if not participant_id_input or not password_input:
        st.error("Please enter both user ID and password.")
        st.stop()

    if not re.fullmatch(r"[0-5]", participant_id_input):
        st.error("User ID or password is incorrect. If you need help, contact the email above.")
        st.stop()

    try:
        credentials = load_credentials()
    except RuntimeError as exc:
        st.error(str(exc))
        st.stop()

    expected_password = credentials.get(participant_id_input)
    if expected_password is None or password_input != expected_password:
        st.error("User ID or password is incorrect. If you need help, contact the email above.")
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
