import logging
from sqlalchemy.orm import Session
from database import get_db
from models import Outlet, OutletProximity
from math import radians, cos, sin, asin, sqrt
from tqdm import tqdm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CATCHMENT_RADIUS_KM = 5.0

def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in km
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    return R * c

def compute_and_store_catchments():
    db: Session = next(get_db())
    outlets = db.query(Outlet).filter(Outlet.latitude != None, Outlet.longitude != None).all()

    logger.info(f"Calculating catchments for {len(outlets)} outlets...")
    inserted_count = 0

    for source in tqdm(outlets, desc="Computing catchments"):
        for target in outlets:
            if source.id == target.id:
                continue
            distance = haversine(source.latitude, source.longitude, target.latitude, target.longitude)
            if distance <= CATCHMENT_RADIUS_KM:
                exists = db.query(OutletProximity).filter_by(
                    outlet_id=source.id,
                    intersecting_outlet_id=target.id
                ).first()
                if not exists:
                    db.add(OutletProximity(
                        outlet_id=source.id,
                        intersecting_outlet_id=target.id,
                        distance_km=distance
                    ))
                    inserted_count += 1

    db.commit()
    logger.info(f"Inserted {inserted_count} outlet proximity records.")

if __name__ == "__main__":
    """Main function to run the script
        Command to run: python -m scripts.process_proximity
    """
    compute_and_store_catchments()
