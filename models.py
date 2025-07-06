from sqlalchemy import Column, Integer, String, Float, JSON, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from datetime import datetime
from pgvector.sqlalchemy import Vector

Base = declarative_base()

class Outlet(Base):
    __tablename__ = "outlets"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    address = Column(Text, nullable=False)
    phone = Column(String(20), nullable=True)
    fax = Column(String(20), nullable=True)
    
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    operating_hours = Column(JSON, nullable=True)
    services = Column(JSON, nullable=True)
    waze_link = Column(String(500), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    is_geocoded = Column(Boolean, default=False)
    geocoding_error = Column(String(500), nullable=True)

    # Optional: Relationship to OutletProximity
    catchments = relationship("OutletProximity", foreign_keys="[OutletProximity.outlet_id]", back_populates="source_outlet")
    intersected_by = relationship("OutletProximity", foreign_keys="[OutletProximity.intersecting_outlet_id]", back_populates="intersecting_outlet")

    def __repr__(self):
        return f"<Outlet(name='{self.name}', address='{self.address}')>"

class OutletProximity(Base):
    __tablename__ = "outlet_proximities"
    
    id = Column(Integer, primary_key=True, index=True)

    outlet_id = Column(Integer, ForeignKey("outlets.id", ondelete="CASCADE"), nullable=False, index=True)
    intersecting_outlet_id = Column(Integer, ForeignKey("outlets.id", ondelete="CASCADE"), nullable=False, index=True)
    distance_km = Column(Float, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    source_outlet = relationship("Outlet", foreign_keys=[outlet_id], back_populates="catchments")
    intersecting_outlet = relationship("Outlet", foreign_keys=[intersecting_outlet_id], back_populates="intersected_by")

    def __repr__(self):
        return f"<OutletProximity(outlet_id={self.outlet_id}, intersecting_outlet_id={self.intersecting_outlet_id})>"

class OutletVector(Base):
    __tablename__ = "outlet_vectors"

    id = Column(Integer, primary_key=True, index=True)
    outlet_id = Column(Integer, ForeignKey("outlets.id", ondelete="CASCADE"), unique=True, nullable=False)

    # Vector embedding (e.g., 1536 for OpenAI / nomic models)
    embedding = Column(Vector(768), nullable=False)

    # Optional: textual summary used for embedding generation
    summary = Column(String, nullable=False)

    # Relationship back to outlet
    outlet = relationship("Outlet", backref="vector")

    def __repr__(self):
        return f"<OutletVector(outlet_id={self.outlet_id}, summary={self.summary[:30]}...)>"