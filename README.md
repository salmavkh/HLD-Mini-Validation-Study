# HLD Mini Validation Study

Streamlit app for a small external validation of HLD descriptor predictions using expert ratings.

## What This App Does
- Loads a fixed set of sampled audio files.
- Shows 6 descriptor-pair questions per audio.
- Saves responses after each `Save & Next`.
- Supports resume by participant ID.
- Shows a thank-you page after completion.

## Expected Data Layout
- `dataset/audio_100_pairs/file_list/sampled_file_ids.csv`
- `dataset/audio_100_pairs_wav/*.wav`

## Quick Start
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install streamlit
streamlit run app.py
```

Participant IDs: use numeric IDs (currently `1` to `5`).

## Output Files
- `outputs/responses.csv`
  - columns: `participant_id,audio_filename,descriptor_pair,selected_choice,timestamp`
- `outputs/progress.csv`
  - stores per-user progress and randomized audio order

## Helper Scripts
- `sample_audio_100_pairs.py`:
  - samples 100 files by VA strata and copies them into `dataset/audio_100_pairs/`
- `convert_sampled_mp3_to_wav.py`:
  - converts sampled MP3 files to WAV in `dataset/audio_100_pairs_wav/`
