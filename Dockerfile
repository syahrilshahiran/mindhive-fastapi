FROM python:3.11-slim

RUN apt-get update

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py /app/main.py
COPY start.sh /app/start.sh

RUN chmod +x /app/start.sh
FROM ollama/ollama:latest
RUN ollama serve
RUN ollama pull llama3

CMD ["bash", "./start.sh"]
