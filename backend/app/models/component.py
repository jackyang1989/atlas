from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.sql import func
from app.database import Base


class Component(Base):
    __tablename__ = "components"
    
    id = Column(String(36), primary_key=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    type = Column(String(50), nullable=False)  # proxy, tool
    version = Column(String(50), default="0.0.0")
    latest_version = Column(String(50), nullable=True)
    status = Column(String(50), default="not-installed")  # not-installed, installed, installing, error
    
    install_method = Column(String(50))  # binary, docker, script
    install_url = Column(String(255), nullable=True)
    installed_path = Column(String(255), nullable=True)
    service_name = Column(String(100), nullable=True)
    sha256_checksum = Column(String(64), nullable=True)
    meta_json = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<Component {self.name}>"
