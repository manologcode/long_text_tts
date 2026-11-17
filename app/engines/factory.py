from config import Config
from engines.base import TTSEngine
from engines.chatterbox import ChatterboxEngine
from engines.coqui import CoquiEngine

ENGINES = {
    "coqui": CoquiEngine,
    "chatterbox": ChatterboxEngine,
}

_instances: dict[str, TTSEngine] = {}


def get_engine(name: str | None = None) -> TTSEngine:
    requested = (name or Config.DEFAULT_ENGINE or "coqui").strip().lower()
    if requested not in ENGINES:
        raise ValueError(
            f"Motor TTS desconocido: '{requested}'. "
            f"Motores disponibles: {', '.join(sorted(ENGINES))}"
        )

    if requested not in _instances:
        _instances[requested] = ENGINES[requested]()

    return _instances[requested]


def available_engines() -> list[str]:
    return sorted(ENGINES)
