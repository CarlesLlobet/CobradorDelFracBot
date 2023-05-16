FROM python:3.9-slim

# Env vars
ENV TELEGRAM_TOKEN ${TELEGRAM_TOKEN}
ENV TELEGRAM_TOKEN ${TELEGRAM_ADMINS:-[54997365]}
ENV TELEGRAM_TOKEN ${TELEGRAM_CHATS:-[-366683659, -346416650]}

WORKDIR /app

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt
RUN touch members.storage

ADD bot.py .

RUN chmod +x bot.py

CMD python3 bot.py
