FROM python:3.10.8-alpine

LABEL org.opencontainers.image.authors="Dominic Hock <d.hock@it-hock.de>, ShiniGandhi <@ShiniGandhi>"
LABEL org.opencontainers.image.description="An automated system to download trailers."
LABEL org.opencontainers.image.url="https://github.com/subtixx/Backdroppr"
LABEL org.opencontainers.image.source="https://github.com/subtixx/Backdroppr"

RUN apk add --no-cache ffmpeg=5.1.4-r0

WORKDIR /app

COPY main.py /app/main.py
COPY requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python3", "/app/main.py"]