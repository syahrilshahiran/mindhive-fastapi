FROM ollama/ollama:latest

# 🐍 Install Python 3.11 and pip
RUN apt-get update && \
    apt-get install -y python3.11 python3-pip && \
    ln -sf /usr/bin/python3.11 /usr/bin/python && \
    pip install --upgrade pip

# Set workdir
WORKDIR /app

# 📦 Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 📁 Copy app files
COPY main.py /app/main.py
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# 🚫 Prevent Ollama from overriding CMD with its ENTRYPOINT
ENTRYPOINT []

# 🚀 Start Ollama and FastAPI server
CMD ["bash", "./start.sh"]
