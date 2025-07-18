import logging
import os
from google import genai

from utils.credentials import load_credentials

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_credentials()

client = genai.Client(
    vertexai=True,
    project=os.getenv("GCP_PROJECT_ID"),
    location="global",
)


def get_query_embedding(query: str) -> list[float]:
    """
    Generate vector embedding from user query using Google Gemini embedding model.

    Args:
        query (str): The user's text query

    Returns:
        List[float]: The embedding vector
    """
    try:
        embedding_response = client.models.embed_content(
            model="gemini-embedding-001",
            contents=[query],
            config={"output_dimensionality": 768},
        )
        embedding_response_json = embedding_response.model_dump()
        embedding = embedding_response_json["embeddings"][0]["values"]
        return embedding
    except Exception as e:
        logger.error(f"Failed to get embedding from Gemini: {e}")
        return []
