
import json
import logging
from models import Outlet
from database import SessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_FILE = "mcdonalds_outlets.json"

def load_data():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def insert_outlets(data):
    db = SessionLocal()
    try:
        db.query(Outlet).delete()
        db.commit()
        for outlet in data:
            outlet_obj = Outlet(
                name=outlet.get("name"),
                address=outlet.get("address"),
                phone=outlet.get("phone"),
                fax=outlet.get("fax"),
                latitude=outlet.get("latitude"),
                longitude=outlet.get("longitude"),
                operating_hours=outlet.get("operating_hours") or {},
                services=outlet.get("services") or [],
                waze_link=outlet.get("waze_link"),
                is_geocoded=False,
                geocoding_error=None,
            )
            db.add(outlet_obj)

        db.commit()
        logger.info(f"✅ Inserted {len(data)} outlets into the database.")
    except Exception as e:
        db.rollback()
        logger.warning(f"❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    data = load_data()
    insert_outlets(data)
