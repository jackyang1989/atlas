from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging

from app.config import settings
from app.database import engine, Base, SessionLocal
from app import models

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 导入路由
from app.api import auth, health, services


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动事件
    logger.info("🚀 ATLAS 启动中...")
    Base.metadata.create_all(bind=engine)
    logger.info("✅ 数据库初始化完成")
    
    # 创建默认管理员
    from app.services.auth_service import AuthService
    db = SessionLocal()
    try:
        AuthService.create_default_admin(db)
    finally:
        db.close()
    
    yield
    
    # 关闭事件
    logger.info("👋 ATLAS 关闭")


app = FastAPI(
    title="ATLAS API",
    description="Advanced Traffic & Load Administration System",
    version=settings.PROJECT_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    openapi_url="/openapi.json",
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 路由注册
app.include_router(health.router, tags=["Health"])
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(services.router, prefix="/api/services", tags=["Services"])


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=5000,
        reload=settings.DEBUG,
    )
