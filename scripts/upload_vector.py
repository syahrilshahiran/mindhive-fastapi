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
    """
    Generate a detailed summary of a McDonald's outlet including all services and contextual information.
    Args:
        outlet (Outlet): The outlet to generate the summary for
    Returns:
        str: The generated summary
    """
    name = outlet.name
    address = outlet.address
    services = outlet.services or []

    summary = f"{name} is a McDonald's restaurant located at {address}."

    # Always list all services
    if services:
        summary += f" It offers the following services: {', '.join(services)}."

    # Add contextual/natural language explanations for key services
    explanations = {
        "24 Hours": "It operates 24 hours, ideal for late-night meals.",
        "Drive-Thru": "Drive-Thru is available for quick service from your vehicle.",
        "McCafe": "You can enjoy coffee and desserts from McCafe.",
        "WiFi": "Free WiFi is provided for customers.",
        "Birthday Party": "Birthday party packages are available for celebrations.",
        "Electric Vehicle": "Electric vehicle charging stations are available.",
        "Surau": "There is a Surau (prayer room) on-site.",
        "Digital Order Kiosk": "It features a digital kiosk for self-service ordering.",
        "Cashless Facility": "Cashless payments are accepted.",
        "Dessert Center": "You can get ice cream and desserts at the Dessert Center.",
        "Breakfast": "Breakfast items are available during morning hours.",
        "McDelivery": "Delivery service is available via McDelivery.",
    }

    for service in services:
        if service in explanations:
            summary += " " + explanations[service]

    return summary

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
    db.query(OutletVector).delete()
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
