FROM alpine
RUN apk add py3-pip && pip install discord.py requests --no-cache-dir --break-system-packages
ADD ./subscribot.py /uscitibot/subscribot.py
ADD ./persistence /uscitibot/persistence
ADD ./domain /uscitibot/domain
ADD ./data /uscitibot/data
WORKDIR /uscitibot
ENTRYPOINT python subscribot.py
