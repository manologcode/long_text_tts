import os


def _env_float(name: str, default: float) -> float:
    try:
        value = os.getenv(name)
        return float(value) if value not in (None, "") else default
    except (TypeError, ValueError):
        return default


def _env_int(name: str, default: int | None) -> int | None:
    try:
        value = os.getenv(name)
        return int(value) if value not in (None, "") else default
    except (TypeError, ValueError):
        return default


class Config:
    AUDIO_FILES_DIR = os.getenv("AUDIO_FILES_DIR", "audio_files")
    TEMP_DIR = os.getenv("TEMP_DIR", "temp_audio")
    AUDIO_TAGS_DIR = os.getenv("AUDIO_TAGS_DIR", "effects")
    SPEAKERS_JSON_PATH = os.getenv("SPEAKERS_JSON_PATH", "studio_speakers.json")
    CHATTERBOX_VOICES_JSON_PATH = os.getenv(
        "CHATTERBOX_VOICES_JSON_PATH", "chatterbox_voices.json"
    )

    DEFAULT_ENGINE = os.getenv("TTS_ENGINE", "coqui").strip().lower() or "coqui"
    MAX_CHUNK_SIZE = _env_int("TTS_MAX_CHUNK_SIZE", None)
    HTTP_TIMEOUT = _env_float("TTS_HTTP_TIMEOUT", 120.0)

    SERVER_URL_COQUI_XTTS = (
        os.getenv("SERVER_URL_COQUI_XTTS")
        or os.getenv("SERVER_URL_VOICE_XTTS")
        or "http://192.168.1.69:8820"
    ).rstrip("/")

    SERVER_URL_CHATTERBOX = os.getenv(
        "SERVER_URL_CHATTERBOX", "http://192.168.1.69:8020"
    ).rstrip("/")
    CHATTERBOX_REFERENCE_AUDIO = (
        os.getenv("CHATTERBOX_REFERENCE_AUDIO", "").strip() or None
    )
    CHATTERBOX_DEFAULT_VOICE = (
        os.getenv("CHATTERBOX_DEFAULT_VOICE", "default").strip() or "default"
    )
    CHATTERBOX_LANGUAGE_ID = (
        os.getenv("CHATTERBOX_LANGUAGE_ID", "es").strip() or "es"
    )
    CHATTERBOX_EXAGGERATION = _env_float("CHATTERBOX_EXAGGERATION", 0.5)
    CHATTERBOX_TEMPERATURE = _env_float("CHATTERBOX_TEMPERATURE", 0.8)
    CHATTERBOX_SEED = _env_int("CHATTERBOX_SEED", 0)
    CHATTERBOX_CFG_WEIGHT = _env_float("CHATTERBOX_CFG_WEIGHT", 0.5)
