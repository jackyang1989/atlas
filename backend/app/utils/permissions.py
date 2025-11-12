"""
权限检查装饰器和依赖注入
"""
from functools import wraps
from typing import List, Callable, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthCredentials
from sqlalchemy.orm import Session
import logging

from app.database import get_db
from app.models.admin import AdminUser
from app.models.rbac import AdminRole, AdminPermission
from app.services.rbac_service import RBACService
from app.utils.security import verify_token

logger = logging.getLogger(__name__)
security = HTTPBearer()


# ==================== 依赖注入函数 ====================

def get_current_admin_user(
    credentials: HTTPAuthCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> AdminUser:
    """获取当前管理员用户"""
    token = credentials.credentials
    username = verify_token(token)
    
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    admin = db.query(AdminUser).filter(AdminUser.username == username).first()
    
    if not admin or not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    return admin


# ==================== 权限检查装饰器 ====================

def require_permission(*permissions: str):
    """
    权限检查装饰器
    
    用法:
        @app.get("/api/users")
        @require_permission("read:user")
        async def list_users(user: AdminUser = Depends(get_current_admin_user)):
            ...
        
        @app.delete("/api/users/{user_id}")
        @require_permission("delete:user", "write:user")  # 需要任意一个权限
        async def delete_user(user: AdminUser = Depends(get_current_admin_user)):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 从 kwargs 中获取当前用户
            user: AdminUser = kwargs.get('current_user')
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found"
                )
            
            # 检查用户是否激活
            if not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User is inactive"
                )
            
            # 检查权限（需要任意一个权限）
            has_perm = any(
                RBACService.has_permission(user, perm)
                for perm in permissions
            )
            
            if not has_perm:
                logger.warning(
                    f"❌ 权限拒绝: 用户 {user.username} 尝试访问 {func.__name__}，"
                    f"所需权限: {permissions}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"You don't have permission to access this resource. "
                            f"Required: {', '.join(permissions)}"
                )
            
            logger.info(
                f"✅ 权限允许: 用户 {user.username} 访问 {func.__name__}"
            )
            
            return await func(*args, **kwargs)
        
        return wrapper
    
    return decorator


def require_all_permissions(*permissions: str):
    """
    需要所有权限的装饰器
    
    用法:
        @app.put("/api/roles/{role_id}/permissions")
        @require_all_permissions("write:role", "write:admin")
        async def update_role_permissions(
            role_id: str,
            current_user: AdminUser = Depends(get_current_admin_user)
        ):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user: AdminUser = kwargs.get('current_user')
            
            if not user or not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found or inactive"
                )
            
            # 检查所有权限
            has_all_perms = RBACService.has_all_permissions(user, list(permissions))
            
            if not has_all_perms:
                logger.warning(
                    f"❌ 权限拒绝: 用户 {user.username}，"
                    f"所需所有权限: {permissions}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"You need all of these permissions: {', '.join(permissions)}"
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    
    return decorator


# ==================== 路由级别权限检查 ====================

async def check_permission_dependency(
    permission: str,
    current_user: AdminUser = Depends(get_current_admin_user)
):
    """依赖注入函数，用于路由级权限检查"""
    if not RBACService.has_permission(current_user, permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied. Required: {permission}"
        )
    return current_user


async def check_permissions_dependency(
    permissions: List[str],
    current_user: AdminUser = Depends(get_current_admin_user)
):
    """依赖注入函数，检查多个权限中的任意一个"""
    if not any(RBACService.has_permission(current_user, perm) for perm in permissions):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied. Required any of: {permissions}"
        )
    return current_user


# ==================== 上下文权限检查 ====================

class PermissionChecker:
    """权限检查辅助类"""
    
    def __init__(self, user: AdminUser, db: Session):
        self.user = user
        self.db = db
    
    def check(self, permission: str) -> bool:
        """检查权限"""
        return RBACService.has_permission(self.user, permission)
    
    def check_any(self, permissions: List[str]) -> bool:
        """检查任意权限"""
        return RBACService.has_any_permission(self.user, permissions)
    
    def check_all(self, permissions: List[str]) -> bool:
        """检查所有权限"""
        return RBACService.has_all_permissions(self.user, permissions)
    
    def require(self, permission: str):
        """需要权限，否则抛出异常"""
        if not self.check(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission}"
            )
    
    def require_any(self, permissions: List[str]):
        """需要任意权限"""
        if not self.check_any(permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied. Required any of: {permissions}"
            )
    
    def require_all(self, permissions: List[str]):
        """需要所有权限"""
        if not self.check_all(permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied. Required all of: {permissions}"
            )
