FROM ollama/ollama:latest

RUN apt-get update && \
    apt-get install -y python3.11 python3.11-venv python3.11-dev python3-pip curl && \
    ln -sf /usr/bin/python3.11 /usr/bin/python && \
    pip install --upgrade pip

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py /app/main.py
COPY start.sh /app/start.sh

RUN chmod +x /app/start.sh

RUN ollama pull llama3

CMD ["bash", "./start.sh"]
