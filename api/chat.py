import os
import tempfile
import logging
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
from ollama import embeddings
from google import genai
from google.genai import types
from models import Outlet
from sqlalchemy import text

from utils.embedding import get_query_embedding

router = APIRouter()
logger = logging.getLogger(__name__)


class ChatMessage(BaseModel):
    message: str


# Setup Google Credentials
if "GOOGLE_APPLICATION_CREDENTIALS_JSON" in os.environ:
    creds_json = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    with tempfile.NamedTemporaryFile(
        delete=False, mode="w", suffix=".json"
    ) as creds_file:
        creds_file.write(creds_json)
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_file.name

client = genai.Client(
    vertexai=True,
    project=os.getenv("GCP_PROJECT_ID"),
    location="global",
)


def get_relevant_outlets_for_chat(query: str, db: Session) -> str:
    """Get relevant outlets for chat context using semantic search
    Args:
        query (str): The user's query
        db (Session): The database session

    Returns:
        str: The relevant outlets for the user's query
    """
    try:
        db.begin()
        query_embedding = get_query_embedding(query)

        sql_query = text(
            """
            SELECT o.name, o.address, o.services,
                   (1 - (ov.embedding <=> CAST(:query_embedding AS vector))) as similarity_score
            FROM outlets o
            JOIN outlet_vectors ov ON o.id = ov.outlet_id
            WHERE (1 - (ov.embedding <=> CAST(:query_embedding AS vector))) >= 0.3
            ORDER BY ov.embedding <=> CAST(:query_embedding AS vector)
        """
        )

        result = db.execute(sql_query, {"query_embedding": query_embedding})

        relevant_outlets = []
        for row in result:
            outlet_info = f"{row.name}, Address: {row.address}"
            if row.services:
                outlet_info += f", Services: {', '.join(row.services)}"
            relevant_outlets.append(outlet_info)

        db.commit()
        return (
            "\n".join(relevant_outlets)
            if relevant_outlets
            else "No particularly relevant outlets found."
        )

    except Exception as e:
        db.rollback()
        logger.warning(f"Semantic search failed, falling back. Error: {e}")
        outlets = db.query(Outlet).all()
        return "\n".join(
            f"{o.name}, Address: {o.address}, Services: {', '.join(o.services or [])}"
            for o in outlets
        )


@router.post("")
async def chat_about_outlets(payload: ChatMessage, db: Session = Depends(get_db)):
    """Chat about outlets with semantic context using Gemini
    Args:
        payload (ChatMessage): The message to chat about
        db (Session): The database session

    Returns:
        StreamingResponse: The chat response stream
    """
    relevant_outlets = get_relevant_outlets_for_chat(payload.message, db)

    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part(
                    text=(
                        "You are a helpful assistant that answers questions about McDonald's outlets in Kuala Lumpur.\n"
                        "Here are the most relevant outlets based on the user's question:\n"
                        + relevant_outlets
                        + "\n\n"
                        + "Answer based on this information. If the question is about specific services or locations, "
                        "focus on the outlets that best match the user's needs.\n\n"
                        + "Please use numbering if it multiple outlets are found.\n\n"
                        + "User Question: "
                        + payload.message
                    )
                )
            ],
        )
    ]

    generate_content_config = types.GenerateContentConfig(
        temperature=1,
        top_p=0.95,
        max_output_tokens=8192,
        safety_settings=[
            types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF"),
            types.SafetySetting(
                category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="OFF"
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="OFF"
            ),
            types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="OFF"),
        ],
    )

    def stream_generator():
        try:
            stream = client.models.generate_content_stream(
                model="gemini-2.0-flash-lite-001",
                contents=contents,
                config=generate_content_config,
            )
            for chunk in stream:
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            logger.error(f"Error generating content: {e}")
            yield "An error occurred."

    return StreamingResponse(stream_generator(), media_type="text/plain")
