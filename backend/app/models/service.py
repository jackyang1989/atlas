from sqlalchemy import Column, String, Integer, DateTime, Text
from sqlalchemy.sql import func
from app.database import Base


class Service(Base):
    __tablename__ = "services"
    
    id = Column(String(36), primary_key=True)
    name = Column(String(100), nullable=False, index=True)
    component = Column(String(50), default="sing-box")
    protocol = Column(String(50))
    port = Column(Integer, unique=True, nullable=False, index=True)
    status = Column(String(20), default="stopped")
    config_json = Column(Text)
    cert_domain = Column(String(100), nullable=True)
    bind_address = Column(String(20), default="0.0.0.0")
    tags = Column(Text, nullable=True)
    error_msg = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<Service {self.name}@{self.port}>"
