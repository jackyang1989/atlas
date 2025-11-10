from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """健康检查"""
    try:
        db.execute("SELECT 1")
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "error", "database": "disconnected"}
