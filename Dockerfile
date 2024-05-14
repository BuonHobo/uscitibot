FROM alpine
RUN apk add py3-pip && pip install discord.py requests --no-cache-dir --break-system-packages
WORKDIR /uscitibot
ENTRYPOINT python subscribot.py