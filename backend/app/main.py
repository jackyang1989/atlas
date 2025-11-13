from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging

from app.config import settings
from app.database import engine, Base, SessionLocal
from app import models

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 导入所有路由
from app.api import auth, health, services, users, monitor, domains, components, backups, alerts
from app.api import rbac  # ✨ RBAC 路由
from app.api import webhooks  # ✨ Webhook 路由


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ==================== 启动事件 ====================
    logger.info("🚀 ATLAS 启动中...")
    
    # 1. 创建数据库表
    Base.metadata.create_all(bind=engine)
    logger.info("✅ 数据库初始化完成")
    
    # 2. 初始化备份服务
    from app.services.backup_service import init_backup_service
    init_backup_service()
    logger.info("✅ 备份服务初始化完成")
    
    # 3. ✨ 初始化 RBAC 系统
    from app.services.rbac_service import RBACService
    db = SessionLocal()
    try:
        RBACService.init_permissions(db)
        RBACService.init_roles(db)
        logger.info("✅ RBAC 权限系统已初始化")
    finally:
        db.close()
    
    # 4. 创建默认管理员
    from app.services.auth_service import AuthService
    db = SessionLocal()
    try:
        AuthService.create_default_admin(db)
    finally:
        db.close()
    
    # 5. 注册和启动定时任务
    from app.tasks.scheduled_tasks import register_scheduled_tasks, start_scheduler
    db_factory = SessionLocal
    register_scheduled_tasks(db_factory)
    start_scheduler()
    logger.info("✅ 定时任务已启动")
    
    logger.info("✅ 应用启动完成")
    yield
    
    # ==================== 关闭事件 ====================
    logger.info("👋 ATLAS 关闭中...")
    
    from app.tasks.scheduled_tasks import stop_scheduler
    stop_scheduler()
    logger.info("✅ 定时任务已停止")


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
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost",
        "https://your-domain.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== 注册路由 ====================
app.include_router(health.router, tags=["Health"])
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(rbac.router, prefix="/api/rbac", tags=["RBAC"])  # ✨ RBAC 权限管理
app.include_router(webhooks.router, prefix="/api/webhooks", tags=["Webhooks"])  # ✨ Webhook 事件系统
app.include_router(services.router, prefix="/api/services", tags=["Services"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(monitor.router, prefix="/api/monitor", tags=["Monitor"])
app.include_router(domains.router, prefix="/api/domains", tags=["Domains"])
app.include_router(components.router, prefix="/api/components", tags=["Components"])
app.include_router(backups.router, prefix="/api/backups", tags=["Backups"])
app.include_router(alerts.router, prefix="/api/alerts", tags=["Alerts"])


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.PROJECT_VERSION,
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """系统健康检查（无需认证）"""
    return {
        "status": "ok",
        "service": "atlas"
    }


@app.get("/api/tasks/status")
async def get_tasks_status():
    """获取定时任务状态（仅用于调试）"""
    from app.tasks.scheduled_tasks import get_scheduler_status
    return get_scheduler_status()


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=5000,
        reload=settings.DEBUG,
    )
