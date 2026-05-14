"""Storage backend switch for study data.

Flip USE_GOOGLE_SHEETS to choose where progress/responses are stored.
"""

from __future__ import annotations

# True -> use Google Sheets backend; False -> use local CSV backend.
USE_GOOGLE_SHEETS = True

if USE_GOOGLE_SHEETS:
    from study_utils_gsheet import (  # noqa: F401
        AUDIO_DIR,
        get_or_create_progress,
        get_question_order,
        get_saved_audio_answers,
        update_progress_index,
        upsert_audio_responses,
    )
else:
    from study_utils import (  # noqa: F401
        AUDIO_DIR,
        get_or_create_progress,
        get_question_order,
        get_saved_audio_answers,
        update_progress_index,
        upsert_audio_responses,
    )

