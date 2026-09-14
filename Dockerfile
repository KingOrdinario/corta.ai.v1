FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=5000 \
    WHISPER_MODEL=tiny

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg git curl fonts-dejavu && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p uploads outputs

EXPOSE 5000
CMD ["gunicorn","-w","1","-b","0.0.0.0:5000","--timeout","900","app:app"]
