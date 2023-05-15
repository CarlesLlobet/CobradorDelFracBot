FROM python:3.9-slim

# Env vars
ENV TELEGRAM_TOKEN ${TELEGRAM_TOKEN}

WORKDIR /app

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

ADD bot.py .

RUN chmod +x bot.py

CMD python3 bot.py
