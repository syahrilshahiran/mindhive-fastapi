#!/bin/bash

# Start Ollama in the background
ollama serve &

# Wait a bit to make sure Ollama is up
sleep 3

# Start FastAPI with uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8000
