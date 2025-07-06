import json
import logging
from fastapi import FastAPI, Query, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from database import get_db
from models import Outlet
from math import radians, cos, sin, asin, sqrt
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from ollama import chat, embeddings

app = FastAPI()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Outlet response model ---
class OutletResponse(BaseModel):
    id: int
    name: str
    address: str
    latitude: Optional[float]
    longitude: Optional[float]
    phone: Optional[str]
    fax: Optional[str]
    services: List[str]

    class Config:
        orm_mode = True

@app.get("/")
def read_root():
    return {"Hello": "World"}

# --- Haversine formula for distance ---
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    return R * c

@app.get("/outlets", response_model=List[OutletResponse])
def get_outlets(
    lat: Optional[float] = Query(None, description="Latitude to filter by proximity"),
    lon: Optional[float] = Query(None, description="Longitude to filter by proximity"),
    radius_km: float = Query(5.0, description="Radius in km"),
    db: Session = Depends(get_db),
):
    """Get outlets from the database"""
    query = db.query(Outlet).filter(Outlet.latitude != None, Outlet.longitude != None)
    
    if lat is not None and lon is not None:
        results = []
        for outlet in query.all():
            distance = haversine(lat, lon, outlet.latitude, outlet.longitude)
            if distance <= radius_km:
                results.append(outlet)
        return results

    return query.all()

class ChatMessage(BaseModel):
    message: str

def get_all_outlet_data(db: Session):
    """Get all outlet data from the database"""
    outlets = db.query(Outlet).all()
    return "\n".join(
        f"{o.name}, Address: {o.address}, Services: {', '.join(o.services or [])}"
        for o in outlets
    )
# Get embedding for user question
def get_query_embedding(query: str) -> List[float]:
    """Get embedding for user question"""
    result = embeddings(model="nomic-embed-text", prompt=query)
    return result["embedding"]


def get_relevant_outlets_for_chat(query: str, db: Session) -> str:
    """Get relevant outlets for chat context using semantic search"""
    try:
        db.begin()
        query_embedding = get_query_embedding(query)

        sql_query = text("""
            SELECT
                o.name, o.address, o.services,
                (1 - (ov.embedding <=> CAST(:query_embedding AS vector))) as similarity_score
            FROM outlets o
            JOIN outlet_vectors ov ON o.id = ov.outlet_id
            WHERE (1 - (ov.embedding <=> CAST(:query_embedding AS vector))) >= 0.3
            ORDER BY ov.embedding <=> CAST(:query_embedding AS vector)

        """)

        result = db.execute(sql_query, {
            'query_embedding': query_embedding
        })

        relevant_outlets = []
        for row in result:
            outlet_info = f"{row.name}, Address: {row.address}"
            if row.services:
                outlet_info += f", Services: {', '.join(row.services)}"
            relevant_outlets.append(outlet_info)

        db.commit()
        return "\n".join(relevant_outlets) if relevant_outlets else "No particularly relevant outlets found."

    except Exception as e:
        db.rollback()
        logger.info(f"Error getting relevant outlets: {e}")

        # Fallback to regular outlet list
        outlets = db.query(Outlet).all()
        return "\n".join(
            f"{o.name}, Address: {o.address}, Services: {', '.join(o.services or [])}"
            for o in outlets
        )


@app.post("/chat")
async def chat_about_outlets(payload: ChatMessage, db: Session = Depends(get_db)):
    """Chat about outlets with semantic context"""
    # Get relevant outlets based on the user's question
    relevant_outlets = get_relevant_outlets_for_chat(payload.message, db)
    
    messages = [
        {
            "role": "system",
            "content": (
                "You are a helpful assistant that answers questions about McDonald's outlets in Kuala Lumpur.\n"
                "Here are the most relevant outlets based on the user's question:\n" + 
                relevant_outlets + "\n\n" +
                "Answer based on this information. If the question is about specific services or locations, "
                "focus on the outlets that best match the user's needs."
            )
        },
        {"role": "user", "content": payload.message}
    ]
    
    def stream_generator():
        stream = chat(model="llama3.2", messages=messages, stream=True)
        for chunk in stream:
            yield chunk["message"]["content"]
    
    return StreamingResponse(stream_generator(), media_type="text/plain")