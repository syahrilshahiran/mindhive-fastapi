FROM ollama/ollama

# Install Python & pip
RUN apt-get update && \
    apt-get install -y python3 python3-pip curl && \
    pip3 install --upgrade pip

# Create app directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip3 install -r requirements.txt

# Copy app code
COPY app /app/app
COPY start.sh /app/start.sh

RUN chmod +x /app/start.sh

# Pull the model (optional: remove this for smaller image)
RUN ollama pull llama3.2

# Set entrypoint
CMD ["bash", "./start.sh"]
