import os
import tempfile
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api import chat, outlet
from utils.credentials import load_credentials

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://mindhive-frontend.vercel.app"],  # Change for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

load_credentials()

app.include_router(chat.router, prefix="/chat", tags=["Chat"])
app.include_router(outlet.router, prefix="/outlets", tags=["Outlets"])


@app.get("/")
def read_root():
    return {"Hello": "World"}
