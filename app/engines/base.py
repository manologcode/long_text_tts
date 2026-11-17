from abc import ABC, abstractmethod
from dataclasses import dataclass


class TTSError(Exception):
    """Error controlado de un motor de síntesis de voz."""


@dataclass
class TTSOptions:
    reference_audio: str | dict | None = None
    exaggeration: float | None = None
    temperature: float | None = None
    seed: int | None = None
    cfg_weight: float | None = None
    add_wav_header: bool = True
    stream_chunk_size: str = "20"


class TTSEngine(ABC):
    name: str
    output_extension: str = "mp3"
    default_max_chunk_size: int = 230
    default_voice: str | None = None

    def __init__(self):
        from config import Config

        self.max_chunk_size = Config.MAX_CHUNK_SIZE or self.default_max_chunk_size

    @abstractmethod
    def synthesize(
        self,
        text: str,
        voice: str,
        lang: str,
        options: TTSOptions,
        output_path: str,
    ) -> str:
        """Genera el audio de un fragmento y lo guarda en output_path."""

    @abstractmethod
    def synthesize_stream(
        self,
        text: str,
        voice: str,
        lang: str,
        options: TTSOptions,
    ) -> bytes:
        """Genera el audio completo y devuelve sus bytes."""

    def available_voices(self) -> list[str]:
        return []
