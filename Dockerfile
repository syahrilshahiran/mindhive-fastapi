FROM python:3.11-slim


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
