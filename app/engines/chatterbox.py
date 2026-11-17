import base64
import json
import logging
import mimetypes
import os
from urllib.parse import urlparse

import requests

from config import Config
from engines.base import TTSEngine, TTSError, TTSOptions

logger = logging.getLogger(__name__)

AUDIO_EXTENSIONS = (".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aac", ".opus")
REFERENCE_KEYS = ("reference_audio", "path", "url", "name", "value", "data", "file")


class ChatterboxEngine(TTSEngine):
    name = "chatterbox"
    output_extension = "wav"
    default_max_chunk_size = 300
    default_voice = "default"

    def __init__(self):
        super().__init__()
        self.base_url = Config.SERVER_URL_CHATTERBOX
        self.voices_path = Config.CHATTERBOX_VOICES_JSON_PATH
        self.default_voice = Config.CHATTERBOX_DEFAULT_VOICE
        self._references: dict | None = None

    def _load_references(self) -> dict:
        if self._references is None:
            self._references = {}
            if os.path.exists(self.voices_path):
                try:
                    with open(self.voices_path, "r", encoding="utf-8") as archivo:
                        data = json.load(archivo)
                    if isinstance(data, dict):
                        self._references = data
                    else:
                        logger.warning(
                            "El archivo %s no contiene un objeto JSON válido",
                            self.voices_path,
                        )
                except (OSError, json.JSONDecodeError) as exc:
                    logger.warning(
                        "No se pudo cargar el archivo de voces %s: %s",
                        self.voices_path,
                        exc,
                    )
        return self._references

    def available_voices(self) -> list[str]:
        try:
            response = requests.get(
                f"{self.base_url}/voices",
                timeout=Config.HTTP_TIMEOUT,
            )
            if response.status_code == 200:
                voices = self._extract_voices(response.json())
                if voices:
                    return voices
        except (requests.RequestException, ValueError) as exc:
            logger.warning("No se pudo consultar /voices de Chatterbox: %s", exc)

        return list(self._load_references().keys())

    @staticmethod
    def _extract_voices(payload) -> list[str]:
        if isinstance(payload, list):
            voices = []
            for item in payload:
                if isinstance(item, str):
                    voices.append(item)
                elif isinstance(item, dict):
                    voice_id = (
                        item.get("id") or item.get("voice_id") or item.get("name")
                    )
                    if isinstance(voice_id, str):
                        voices.append(voice_id)
            return voices

        if isinstance(payload, dict):
            for key in ("voices", "items", "data"):
                if key in payload:
                    return ChatterboxEngine._extract_voices(payload[key])
            return [key for key in payload if isinstance(key, str)]

        return []

    @staticmethod
    def _looks_like_reference(value: str) -> bool:
        value = value.strip()
        return (
            value.startswith("http://")
            or value.startswith("https://")
            or value.startswith("/")
            or value.startswith("data:audio/")
            or value.lower().endswith(AUDIO_EXTENSIONS)
        )

    def _resolve_reference(
        self, voice: str, options: TTSOptions
    ) -> str | dict | None:
        if isinstance(options.reference_audio, dict):
            return options.reference_audio
        if isinstance(options.reference_audio, str) and options.reference_audio.strip():
            return options.reference_audio.strip()

        references = self._load_references()
        value = references.get(voice)
        if isinstance(value, (str, dict)):
            return value

        if Config.CHATTERBOX_REFERENCE_AUDIO:
            return Config.CHATTERBOX_REFERENCE_AUDIO

        if voice and self._looks_like_reference(voice):
            return voice.strip()

        return None

    @staticmethod
    def _option(value, default):
        return default if value is None else value

    @staticmethod
    def _candidate_references(reference: str | dict | None):
        if isinstance(reference, dict):
            for key in REFERENCE_KEYS:
                value = reference.get(key)
                if isinstance(value, str) and value.strip():
                    yield value.strip()
            return

        if isinstance(reference, str) and reference.strip():
            yield reference.strip()

    def _read_reference(self, value: str) -> tuple[str, bytes]:
        if value.startswith("data:audio/"):
            try:
                header, encoded = value.split(",", 1)
                mime = header[5:].split(";", 1)[0] or "audio/wav"
            except ValueError as exc:
                raise TTSError("Audio de referencia embebido inválido") from exc

            try:
                content = base64.b64decode(encoded)
            except ValueError as exc:
                raise TTSError("Audio de referencia embebido inválido") from exc

            extension = mimetypes.guess_extension(mime) or ".wav"
            return f"reference{extension}", content

        if value.startswith(("http://", "https://")):
            try:
                response = requests.get(value, timeout=Config.HTTP_TIMEOUT)
            except requests.RequestException as exc:
                raise TTSError(
                    f"No se pudo descargar el audio de referencia: {exc}"
                ) from exc

            if response.status_code != 200 or not response.content:
                raise TTSError(
                    "No se pudo descargar el audio de referencia "
                    f"({response.status_code}): {response.text[:300]}"
                )

            filename = os.path.basename(urlparse(value).path) or "reference.wav"
            return filename, response.content

        path = value[5:] if value.startswith("file=") else value
        if not os.path.isfile(path):
            raise TTSError(
                f"El audio de referencia '{path}' no existe o no es accesible "
                "desde este contenedor"
            )

        try:
            with open(path, "rb") as archivo:
                content = archivo.read()
        except OSError as exc:
            raise TTSError(
                f"No se pudo leer el audio de referencia '{path}': {exc}"
            ) from exc

        return os.path.basename(path), content

    def _load_reference_file(self, reference: str | dict | None) -> tuple[str, bytes]:
        errors = []
        for value in self._candidate_references(reference):
            try:
                return self._read_reference(value)
            except TTSError as exc:
                errors.append(str(exc))

        if errors:
            raise TTSError("; ".join(errors))

        raise TTSError("No se pudo interpretar el audio de referencia")

    def _build_form(
        self,
        text: str,
        voice: str,
        lang: str,
        reference: str | dict | None,
        options: TTSOptions,
    ) -> dict:
        voice_value = (voice or "").strip()
        if (
            reference is not None
            or not voice_value
            or self._looks_like_reference(voice_value)
        ):
            voice_value = self.default_voice

        language_id = (lang or "").strip() or Config.CHATTERBOX_LANGUAGE_ID

        form = {
            "text": (None, text),
            "voice": (None, voice_value),
            "exaggeration": (
                None,
                str(self._option(options.exaggeration, Config.CHATTERBOX_EXAGGERATION)),
            ),
            "temperature": (
                None,
                str(self._option(options.temperature, Config.CHATTERBOX_TEMPERATURE)),
            ),
            "cfg_weight": (
                None,
                str(self._option(options.cfg_weight, Config.CHATTERBOX_CFG_WEIGHT)),
            ),
            "seed": (None, str(self._option(options.seed, Config.CHATTERBOX_SEED))),
            "language_id": (None, language_id),
        }

        if reference is not None:
            filename, content = self._load_reference_file(reference)
            content_type = (
                mimetypes.guess_type(filename)[0] or "application/octet-stream"
            )
            form["reference_audio"] = (filename, content, content_type)
            logger.info("Usando audio de referencia para Chatterbox: %s", reference)

        return form

    def _generate(
        self, text: str, voice: str, lang: str, options: TTSOptions
    ) -> bytes:
        reference = self._resolve_reference(voice, options)
        form = self._build_form(text, voice, lang, reference, options)

        try:
            response = requests.post(
                f"{self.base_url}/tts",
                files=form,
                timeout=Config.HTTP_TIMEOUT,
            )
        except requests.RequestException as exc:
            raise TTSError(f"No se pudo conectar con Chatterbox: {exc}") from exc

        if response.status_code != 200:
            raise TTSError(
                f"Error en la API Chatterbox ({response.status_code}): "
                f"{response.text[:500]}"
            )

        if not response.content:
            raise TTSError("Chatterbox devolvió una respuesta de audio vacía")

        return response.content

    def synthesize(
        self,
        text: str,
        voice: str,
        lang: str,
        options: TTSOptions,
        output_path: str,
    ) -> str:
        audio = self._generate(text, voice, lang, options)
        with open(output_path, "wb") as f:
            f.write(audio)
        return output_path

    def synthesize_stream(
        self,
        text: str,
        voice: str,
        lang: str,
        options: TTSOptions,
    ) -> bytes:
        return self._generate(text, voice, lang, options)
