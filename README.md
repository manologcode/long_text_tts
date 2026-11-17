# Long Text TTS

**Long Text TTS** recibe textos largos, los limpia y trocea, envía cada fragmento a un generador de voz y une los audios parciales en un único MP3.

Actualmente soporta dos motores:

- **Coqui / XTTS** mediante el servicio `xtts-streaming-server`.
- **Chatterbox** mediante su API REST.

El motor se selecciona con la variable de entorno `TTS_ENGINE` y también se puede forzar por petición con el campo `engine`.

## Características

- Convierte textos largos a voz.
- Trocea automáticamente textos que superan el límite del motor.
- Limpia emojis, iconos y caracteres especiales.
- Convierte números a palabras en español.
- Permite insertar silencios y efectos con etiquetas como `<silence1>`, `<click1>` o `<click2>`.
- Une todos los fragmentos en un solo MP3.
- Selección de motor mediante Docker Compose o por petición.

## Servicios externos de dependencia

Los servicios se ejecutan fuera de esta aplicación. Según el motor elegido:

- **Coqui**: [xtts-streaming-server](https://github.com/manologcode/xtts-streaming-server)
  - Endpoints usados: `/tts` y `/tts_stream`.
- **Chatterbox**: servidor con API REST.
  - Endpoints usados: `/tts` y `/voices`.

## Selección del motor

### Coqui

```bash
TTS_ENGINE=coqui docker compose up -d
```

Variables relacionadas:

- `SERVER_URL_COQUI_XTTS`: URL del servidor Coqui. Por defecto `http://192.168.1.69:8820`.
- `SERVER_URL_VOICE_XTTS`: nombre antiguo, se mantiene como compatibilidad.

### Chatterbox

```bash
TTS_ENGINE=chatterbox docker compose up -d
```

Variables relacionadas:

- `SERVER_URL_CHATTERBOX`: URL del servidor Chatterbox. Por defecto `http://192.168.1.69:8020`.
- `CHATTERBOX_DEFAULT_VOICE`: ID de voz usado cuando la petición no indica `voice`. Por defecto `default`.
- `CHATTERBOX_LANGUAGE_ID`: idioma enviado cuando la petición no indica `lang`. Por defecto `es`.
- `CHATTERBOX_REFERENCE_AUDIO`: ruta o URL del audio de referencia por defecto. Opcional.
- `CHATTERBOX_EXAGGERATION`: por defecto `0.5`.
- `CHATTERBOX_TEMPERATURE`: por defecto `0.8`.
- `CHATTERBOX_SEED`: por defecto `0` (aleatoria).
- `CHATTERBOX_CFG_WEIGHT`: por defecto `0.5`.

### Variables comunes

- `TTS_MAX_CHUNK_SIZE`: tamaño máximo de los fragmentos. Si se omite, Coqui usa 230 y Chatterbox 300.
- `TTS_HTTP_TIMEOUT`: timeout HTTP en segundos. Por defecto `120`.

## Voces y audio de referencia

### Coqui

Las voces se leen de `app/studio_speakers.json`. El campo `voice` de la petición debe coincidir con una de sus claves.

### Chatterbox

El servidor Chatterbox gestiona sus propias voces. El campo `voice` debe ser un ID devuelto por `GET /voices`; si se omite, se usa `default`.

Para clonar una voz concreta se puede enviar `reference_audio`. La aplicación lo resuelve en este orden:

1. Campo `reference_audio` de la petición.
2. Entrada de `app/chatterbox_voices.json` para el valor de `voice`.
3. Variable `CHATTERBOX_REFERENCE_AUDIO`.
4. El propio valor de `voice`, si parece una ruta o URL.
5. Sin audio de referencia, usando la voz indicada en `voice`.

`reference_audio` puede ser una ruta local accesible desde este contenedor, una URL o un data URI `data:audio/...`. El contenido se envía a Chatterbox como archivo en el formulario de `/tts`.

Ejemplo de `app/chatterbox_voices.json`:

```json
{
  "Xavier Hayasaka": "/ruta/local/referencia.wav",
  "Narrador": "https://servidor/referencia.wav"
}
```

## API

### 1. POST /text-to-speech - Conversión asincrónica

Convierte texto a voz en segundo plano.

**Body:**

```json
{
  "text": "Tu texto aquí",
  "voice": "default",
  "lang": "es",
  "engine": "chatterbox",
  "reference_audio": "/ruta/local/referencia.wav"
}
```

Todos los campos excepto `text` son opcionales.

**Respuesta:**

```json
{
  "job_id": "uuid-del-trabajo",
  "status": "queued",
  "audio_url": "/status/uuid-del-trabajo"
}
```

### 2. GET /status/{job_id} - Estado del trabajo

Obtiene el estado actual de una tarea de síntesis. Incluye el motor utilizado.

### 3. GET /audio/{job_id} - Descargar audio

Descarga el MP3 generado cuando el estado es `completed`.

### 4. POST /tts_stream - Streaming directo

Con Coqui devuelve el stream real del servicio XTTS. Con Chatterbox genera el audio completo y lo devuelve troceado, ya que la API REST no ofrece streaming real.

**Body:**

```json
{
  "text": "Tu texto aquí",
  "voice": "Xavier Hayasaka",
  "language": "es",
  "engine": "coqui",
  "add_wav_header": true,
  "stream_chunk_size": "20"
}
```

Con Chatterbox, `lang` se envía como `language_id` y el texto se trocea automáticamente para respetar el máximo de 300 caracteres por petición.

```json
{
  "text": "Tu texto aquí",
  "voice": "default",
  "language": "es",
  "engine": "chatterbox"
}
```

### Parámetros específicos de Chatterbox

Se pueden enviar en ambos endpoints:

- `reference_audio`
- `exaggeration`
- `temperature`
- `seed`
- `cfg_weight`

Si se omiten, se usan los valores de las variables de entorno.

## Ejecutar con Docker

La imagen publicada está en Docker Hub como `manologcode/long_text_tts:latest`.

### Solo con la imagen (sin clonar el repositorio)

```bash
docker run -d \
  --name long_text_tts \
  --restart unless-stopped \
  -p 5008:5008 \
  -e TTS_ENGINE=chatterbox \
  -e SERVER_URL_CHATTERBOX=http://192.168.1.69:8020 \
  --tmpfs /app/audio_files:mode=1777 \
  --tmpfs /app/temp_audio:mode=1777 \
  manologcode/long_text_tts:latest
```

La API queda disponible en `http://localhost:5008/docs`.

### Con Docker Compose (recomendado)

Guarda este `docker-compose.yml` en cualquier carpeta; no hace falta el código:

```yaml
services:
  app:
    image: manologcode/long_text_tts:latest
    pull_policy: always
    restart: always
    container_name: long_text_tts
    ports:
      - "5008:5008"
    tmpfs:
      - /app/audio_files:mode=1777
      - /app/temp_audio:mode=1777
    environment:
      - TTS_ENGINE=chatterbox
      - SERVER_URL_CHATTERBOX=http://192.168.1.69:8020
```

```bash
docker compose up -d
```

En producción no se usan volúmenes: los MP3 generados y los temporales se guardan en `tmpfs` dentro del contenedor y se eliminan al reiniciarlo. Los efectos (`app/effects`) y la configuración forman parte de la imagen y permanecen constantes. Para actualizar:

```bash
docker compose pull
docker compose up -d
```

### Configuración y audios de referencia

La configuración y los audios de referencia deben ir dentro de la imagen (por ejemplo, copiándolos en `app/` antes de `docker build`), ya que el despliegue de producción no monta volúmenes del host.

En desarrollo sí se puede montar el repositorio completo:

```yaml
    volumes:
      - ./app:/app
```

Las rutas de `chatterbox_voices.json` deben ser accesibles dentro del contenedor, por ejemplo `/app/referencias/mi_voz.wav`.

### Desarrollo (con el repositorio clonado)

```bash
docker compose -f docker-compose.dev.yml up -d --build
```

También se puede forzar el motor:

```bash
TTS_ENGINE=coqui docker compose -f docker-compose.dev.yml up -d --build
```

### Publicar una nueva imagen

```bash
docker build -t manologcode/long_text_tts:latest .
docker push manologcode/long_text_tts:latest
```

El workflow de GitHub Actions (`.github/workflows/image.yml`) también publica la imagen al hacer push a `main`.

## Probar la conversión

```bash
docker exec long_text_tts python test.py "esto es un texto de prueba para que lo leas"
```

También se puede indicar el motor y la voz:

```bash
docker exec \
  -e TTS_ENGINE=chatterbox \
  -e TTS_VOICE=Narrador \
  long_text_tts python test.py "texto de prueba"
```

## Etiquetas de efectos

Se pueden insertar etiquetas en el texto para forzar efectos y silencios:

- `<silence1>`
- `<click1>`
- `<click2>`

Los archivos correspondientes están en `app/effects/`. Esta función es independiente del motor TTS elegido.
