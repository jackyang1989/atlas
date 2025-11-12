from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthCredentials
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import logging
import os

from app.database import get_db
from app.models.admin import AdminUser
from app.schemas.component import (
    BackupCreate,
    BackupResponse,
    BackupListResponse,
    BackupRestoreRequest
)
from app.services.backup_manager import BackupManager
from app.utils.security import verify_token
from app.config import settings

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


@router.get("/", response_model=BackupListResponse)
async def list_backups(
    current_user: str = Depends(get_current_user)
):
    """列出所有备份"""
    try:
        backup_manager = BackupManager()
        backups = backup_manager.list_backups()
        return {
            "total": len(backups),
            "items": backups
        }
    except Exception as e:
        logger.error(f"获取备份列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取备份列表失败"
        )


@router.post("/", response_model=BackupResponse, status_code=status.HTTP_201_CREATED)
async def create_backup(
    request: BackupCreate,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建备份"""
    try:
        backup_manager = BackupManager()
        result = backup_manager.create_backup(
            db,
            include_data=request.include_data,
            include_config=request.include_config,
            description=request.description
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "创建备份失败")
            )
        
        return {
            "filename": result["filename"],
            "size_mb": result["size_mb"],
            "created_at": result["created_at"],
            "description": request.description
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建备份失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建备份失败: {str(e)}"
        )


@router.post("/restore")
async def restore_backup(
    request: BackupRestoreRequest,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """恢复备份"""
    try:
        backup_manager = BackupManager()
        result = backup_manager.restore_backup(
            db,
            filename=request.filename,
            force=request.force
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "恢复备份失败")
            )
        
        return {
            "message": "备份恢复成功",
            "restored_at": result["restored_at"]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"恢复备份失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"恢复备份失败: {str(e)}"
        )


@router.get("/download/{filename}")
async def download_backup(
    filename: str,
    current_user: str = Depends(get_current_user)
):
    """下载备份文件"""
    try:
        backup_dir = getattr(settings, 'BACKUPS_DIR', '/opt/atlas/backups')
        filepath = os.path.join(backup_dir, filename)
        
        if not os.path.exists(filepath):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="备份文件不存在"
            )
        
        # 安全检查：确保文件在备份目录内
        if not os.path.abspath(filepath).startswith(os.path.abspath(backup_dir)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无效的文件路径"
            )
        
        return FileResponse(
            path=filepath,
            filename=filename,
            media_type='application/gzip'
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"下载备份失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="下载备份失败"
        )


@router.delete("/{filename}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_backup(
    filename: str,
    current_user: str = Depends(get_current_user)
):
    """删除备份文件"""
    try:
        backup_manager = BackupManager()
        result = backup_manager.delete_backup(filename)
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result.get("error", "备份文件不存在")
            )
        
        return None
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除备份失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除备份失败"
        )


@router.post("/cleanup")
async def cleanup_old_backups(
    days: int = 30,
    current_user: str = Depends(get_current_user)
):
    """清理旧备份（保留最近 N 天）"""
    try:
        backup_manager = BackupManager()
        result = backup_manager.cleanup_old_backups(days)
        
        return {
            "message": f"已删除 {result['deleted_count']} 个过期备份",
            "deleted_count": result["deleted_count"],
            "freed_space_mb": result.get("freed_space_mb", 0)
        }
    
    except Exception as e:
        logger.error(f"清理备份失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="清理备份失败"
        )
