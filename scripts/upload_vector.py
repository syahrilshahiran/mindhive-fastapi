import logging
from sqlalchemy.orm import Session
from database import get_db 
from models import Outlet, OutletVector
from ollama import embeddings
from sqlalchemy.exc import IntegrityError
from tqdm import tqdm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "nomic-embed-text"

def generate_outlet_summary(outlet: Outlet) -> str:
    """Generate a summary of an outlet using its name, address, and services
        Args:
            outlet (Outlet): The outlet to generate the summary for

        Returns:
            str: The generated summary
    """
    name = outlet.name
    address = outlet.address
    services = outlet.services or []

    summary_lines = [
        f"{name} is a McDonald's outlet located at {address}.",
    ]

    if services:
        summary_lines.append("It offers the following services: " + ", ".join(services) + ".")

    if "24 Hours" in services:
        summary_lines.append("This outlet is open 24 hours.")
    if "Drive-Thru" in services:
        summary_lines.append("This outlet has a drive-thru.")
    if "Birthday Party" in services:
        summary_lines.append("This outlet supports birthday party hosting.")
    if "McCafe" in services:
        summary_lines.append("This outlet includes a McCafe.")
    if "WiFi" in services:
        summary_lines.append("WiFi is available at this outlet.")

    return " ".join(summary_lines)

def generate_embedding(text: str) -> list[float]:
    """Generate embedding for a given text using the specified embedding model"""
    response = embeddings(
        model=EMBEDDING_MODEL,
        prompt=text
    )
    return response["embedding"]

def upload_outlet_vectors():
    """Upload outlet vectors to the database"""
    db: Session = next(get_db())
    outlets = db.query(Outlet).all()
    logger.info(f"Processing {len(outlets)} outlets...")
    for outlet in tqdm(outlets, desc="Processing Outlets"):
        # Skip if vector already exists
        if db.query(OutletVector).filter_by(outlet_id=outlet.id).first():
            continue

        summary = generate_outlet_summary(outlet)
        try:
            embedding = generate_embedding(summary)
        except Exception as e:
            logger.error(f"Embedding failed for {outlet.name}: {e}")
            continue

        vector_record = OutletVector(
            outlet_id=outlet.id,
            summary=summary,
            embedding=embedding
        )

        db.add(vector_record)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            logger.error(f"Failed to insert vector for outlet_id={outlet.id}")

    logger.info("Vector upload complete.")

if __name__ == "__main__":
    """Main function to run the script
        Command to run: python -m scripts.upload_vector
    """
    upload_outlet_vectors()
