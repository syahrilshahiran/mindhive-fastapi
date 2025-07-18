from fastapi import APIRouter, Query, Depends, Path
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
from models import Outlet, OutletProximity
from pydantic import BaseModel

router = APIRouter()


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


@router.get("/", response_model=List[OutletResponse])
def get_outlets(
    lat: Optional[float] = Query(None),
    lon: Optional[float] = Query(None),
    db: Session = Depends(get_db),
):
    return (
        db.query(Outlet).filter(Outlet.latitude != None, Outlet.longitude != None).all()
    )


@router.get("/{outlet_id}/catchment")
def get_catchment(outlet_id: int = Path(...), db: Session = Depends(get_db)):
    proximities = db.query(OutletProximity).filter_by(outlet_id=outlet_id).all()
    outlet_ids = [p.intersecting_outlet_id for p in proximities]
    nearby_outlets = db.query(Outlet).filter(Outlet.id.in_(outlet_ids)).all()

    return [
        {
            "id": o.id,
            "name": o.name,
            "latitude": o.latitude,
            "longitude": o.longitude,
            "distance_km": next(
                (
                    p.distance_km
                    for p in proximities
                    if p.intersecting_outlet_id == o.id
                ),
                None,
            ),
        }
        for o in nearby_outlets
        if o.latitude is not None and o.longitude is not None
    ]
