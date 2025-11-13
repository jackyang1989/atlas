"""
Webhook API 端点
文件：backend/app/api/webhooks.py
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthCredentials
from sqlalchemy.orm import Session
import logging

from app.database import get_db
from app.models.admin import AdminUser
from app.schemas.webhook import (
    WebhookCreate,
    WebhookUpdate,
    WebhookResponse,
    WebhookListResponse,
    WebhookLogResponse,
    WebhookLogListResponse,
    WebhookStatsResponse,
    WebhookTestRequest,
)
from app.services.webhook_service import WebhookService
from app.utils.security import verify_token

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> str:
    """获取当前登录用户"""
    token = credentials.credentials
    username = verify_token(token)
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    admin = db.query(AdminUser).filter(AdminUser.username == username).first()
    if not admin:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    return username


# ==================== Webhook 管理 ====================

@router.get("/", response_model=WebhookListResponse)
async def list_webhooks(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    enabled_only: bool = Query(False, description="只显示启用的"),
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """列出所有 Webhooks"""
    try:
        webhooks, total = WebhookService.list_webhooks(
            db, skip=skip, limit=limit, enabled_only=enabled_only
        )
        return {
            "total": total,
            "items": [w.to_dict() for w in webhooks]
        }
    except Exception as e:
        logger.error(f"获取 Webhook 列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取列表失败"
        )


@router.post("/", response_model=WebhookResponse, status_code=status.HTTP_201_CREATED)
async def create_webhook(
    request: WebhookCreate,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建 Webhook"""
    try:
        webhook = WebhookService.create_webhook(
            db,
            url=request.url,
            name=request.name,
            events=request.events,
            description=request.description,
            secret=request.secret,
            retry_enabled=request.retry_enabled,
            created_by=current_user,
        )
        return webhook.to_dict()
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"创建 Webhook 失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建失败"
        )


@router.get("/{webhook_id}", response_model=WebhookResponse)
async def get_webhook(
    webhook_id: str,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取 Webhook 详情"""
    webhook = WebhookService.get_webhook(db, webhook_id)
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook 不存在"
        )
    return webhook.to_dict()


@router.put("/{webhook_id}", response_model=WebhookResponse)
async def update_webhook(
    webhook_id: str,
    request: WebhookUpdate,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新 Webhook"""
    try:
        webhook = WebhookService.update_webhook(
            db, webhook_id, **request.model_dump(exclude_unset=True)
        )
        if not webhook:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Webhook 不存在"
            )
        return webhook.to_dict()
    
    except Exception as e:
        logger.error(f"更新 Webhook 失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新失败"
        )


@router.post("/{webhook_id}/toggle", response_model=WebhookResponse)
async def toggle_webhook(
    webhook_id: str,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """启用/禁用 Webhook"""
    webhook = WebhookService.toggle_webhook(db, webhook_id)
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook 不存在"
        )
    return webhook.to_dict()


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(
    webhook_id: str,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除 Webhook"""
    success = WebhookService.delete_webhook(db, webhook_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook 不存在"
        )
    return None


# ==================== Webhook 测试 ====================

@router.post("/{webhook_id}/test")
async def test_webhook(
    webhook_id: str,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """测试 Webhook"""
    try:
        result = WebhookService.test_webhook(db, webhook_id)
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "测试失败")
            )
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"测试 Webhook 失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="测试失败"
        )


# ==================== 日志查询 ====================

@router.get("/{webhook_id}/logs", response_model=WebhookLogListResponse)
async def get_webhook_logs(
    webhook_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取 Webhook 调用日志"""
    try:
        logs, total = WebhookService.get_webhook_logs(
            db, webhook_id, skip=skip, limit=limit
        )
        return {
            "total": total,
            "items": [log.to_dict() for log in logs]
        }
    except Exception as e:
        logger.error(f"获取日志失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取日志失败"
        )


@router.get("/logs/recent", response_model=WebhookLogListResponse)
async def get_recent_logs(
    hours: int = Query(24, ge=1, le=168, description="最近 N 小时"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取最近的 Webhook 日志"""
    try:
        logs, total = WebhookService.get_recent_logs(
            db, hours=hours, skip=skip, limit=limit
        )
        return {
            "total": total,
            "items": [log.to_dict() for log in logs]
        }
    except Exception as e:
        logger.error(f"获取最近日志失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取日志失败"
        )


# ==================== 统计信息 ====================

@router.get("/{webhook_id}/stats", response_model=WebhookStatsResponse)
async def get_webhook_stats(
    webhook_id: str,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取 Webhook 统计信息"""
    try:
        stats = WebhookService.get_webhook_stats(db, webhook_id)
        if not stats:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Webhook 不存在"
            )
        return stats
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取统计失败"
        )


# ==================== 日志清理 ====================

@router.post("/logs/cleanup")
async def cleanup_logs(
    days: int = Query(30, ge=1, le=365, description="保留天数"),
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """清理旧日志"""
    try:
        deleted_count = WebhookService.cleanup_old_logs(db, days)
        return {
            "success": True,
            "message": f"已删除 {deleted_count} 条日志",
            "deleted_count": deleted_count,
        }
    except Exception as e:
        logger.error(f"清理日志失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="清理失败"
        )
