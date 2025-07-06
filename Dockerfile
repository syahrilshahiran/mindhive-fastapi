FROM ollama/ollama:latest

# Install Python 3.11 from deadsnakes PPA
RUN apt-get update && \
    apt-get install -y software-properties-common && \
    add-apt-repository ppa:deadsnakes/ppa -y && \
    apt-get update && \
    apt-get install -y python3.11 python3.11-venv python3.11-dev curl && \
    ln -sf /usr/bin/python3.11 /usr/bin/python && \
    curl -sS https://bootstrap.pypa.io/get-pip.py | python && \
    pip install --upgrade pip

# Set working directory
WORKDIR /app

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app files
COPY . /app
RUN chmod +x /app/start.sh

# Clear Ollama's default ENTRYPOINT to avoid ollama bash error
ENTRYPOINT []

CMD ["bash", "./start.sh"]
