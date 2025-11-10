from sqlalchemy import Column, String, Float, Integer, DateTime, Text
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    uuid = Column(String(36), unique=True, nullable=False, index=True)
    service_ids = Column(Text, nullable=True)
    
    traffic_limit_gb = Column(Float, default=0)
    traffic_used_gb = Column(Float, default=0)
    speed_limit_kbps = Column(Integer, default=0)
    device_limit = Column(Integer, default=0)
    devices_online = Column(Integer, default=0)
    
    status = Column(String(20), default="active")
    expiry_date = Column(DateTime, nullable=True)
    
    preferred_regions = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<User {self.username}>"
