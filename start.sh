#!/bin/bash

# Start Ollama in background
ollama serve &

# Wait a few seconds for the server to be ready
sleep 3

# Pull model (only once — Ollama caches it)
ollama pull llama3

# Start FastAPI
uvicorn main:app --host 0.0.0.0 --port 8000
