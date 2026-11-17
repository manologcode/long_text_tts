FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/home/myuser/venv/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --shell /bin/bash myuser && \
    python -m venv /home/myuser/venv && \
    /home/myuser/venv/bin/python -m pip install --no-cache-dir --upgrade pip

WORKDIR /app

COPY app/requirements.txt ./requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=myuser:myuser app /app

RUN mkdir -p /app/audio_files /app/temp_audio && \
    chown -R myuser:myuser /app

USER myuser

EXPOSE 5008

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5008/apidocs.json')" || exit 1

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5008"]
