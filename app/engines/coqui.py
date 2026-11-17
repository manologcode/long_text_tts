import base64
import json

import requests

from config import Config
from engines.base import TTSEngine, TTSError, TTSOptions


def _decode_audio(content: bytes) -> bytes:
    try:
        return base64.b64decode(content, validate=True)
    except Exception:
        return content


class CoquiEngine(TTSEngine):
    name = "coqui"
    output_extension = "mp3"
    default_max_chunk_size = 230
    default_voice = "Xavier Hayasaka"

    def __init__(self):
        super().__init__()
        self.base_url = Config.SERVER_URL_COQUI_XTTS
        self.speakers_path = Config.SPEAKERS_JSON_PATH
        self._speakers: dict | None = None

    def _load_speakers(self) -> dict:
        if self._speakers is None:
            try:
                with open(self.speakers_path, "r", encoding="utf-8") as archivo:
                    self._speakers = json.load(archivo)
            except (OSError, json.JSONDecodeError) as exc:
                raise TTSError(
                    f"No se pudo cargar el archivo de voces '{self.speakers_path}': {exc}"
                ) from exc
        return self._speakers

    def available_voices(self) -> list[str]:
        return list(self._load_speakers().keys())

    def _get_speaker(self, voice: str) -> dict:
        speakers = self._load_speakers()
        speaker_embeddings = speakers.get(voice)
        if not speaker_embeddings:
            raise TTSError(
                f"Voz '{voice}' no encontrada. Voces disponibles: {list(speakers.keys())}"
            )
        return speaker_embeddings

    def _payload(self, text: str, voice: str, lang: str) -> dict:
        speaker = self._get_speaker(voice)
        return {
            "text": text,
            "language": lang,
            "speaker_embedding": speaker["speaker_embedding"],
            "gpt_cond_latent": speaker["gpt_cond_latent"],
        }

    def synthesize(
        self,
        text: str,
        voice: str,
        lang: str,
        options: TTSOptions,
        output_path: str,
    ) -> str:
        payload = self._payload(text, voice, lang)
        try:
            response = requests.post(
                f"{self.base_url}/tts",
                json=payload,
                timeout=Config.HTTP_TIMEOUT,
            )
        except requests.RequestException as exc:
            raise TTSError(f"No se pudo conectar con Coqui: {exc}") from exc

        if response.status_code != 200:
            raise TTSError(
                f"Error en la API Coqui ({response.status_code}): {response.text[:500]}"
            )

        with open(output_path, "wb") as f:
            f.write(_decode_audio(response.content))

        return output_path

    def synthesize_stream(
        self,
        text: str,
        voice: str,
        lang: str,
        options: TTSOptions,
    ) -> bytes:
        payload = self._payload(text, voice, lang)
        payload.update(
            {
                "add_wav_header": options.add_wav_header,
                "stream_chunk_size": options.stream_chunk_size,
            }
        )

        try:
            response = requests.post(
                f"{self.base_url}/tts_stream",
                json=payload,
                timeout=Config.HTTP_TIMEOUT,
            )
        except requests.RequestException as exc:
            raise TTSError(f"No se pudo conectar con Coqui: {exc}") from exc

        if response.status_code != 200:
            raise TTSError(
                f"Error en la API Coqui ({response.status_code}): {response.text[:500]}"
            )

        return _decode_audio(response.content)
