"""
RBAC 权限管理 API 端点
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
import logging

from app.database import get_db
from app.models.admin import AdminUser
from app.models.rbac import AdminRole, AdminPermission
from app.schemas.rbac import (
    RoleResponse,
    RoleListResponse,
    RoleCreateRequest,
    RoleUpdateRequest,
    PermissionResponse,
    PermissionListResponse,
    AdminUserResponse,
    AdminUserListResponse,
    AdminUserCreateRequest,
    AdminUserUpdateRequest,
    AssignRoleRequest,
)
from app.services.rbac_service import RBACService
from app.utils.permissions import (
    get_current_admin_user,
    require_permission,
    PermissionChecker,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ==================== 权限相关端点 ====================

@router.get("/permissions", response_model=PermissionListResponse)
async def list_permissions(
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_admin_user),
):
    """获取所有权限"""
    try:
        permissions = db.query(AdminPermission).all()
        return {
            "total": len(permissions),
            "items": [
                {
                    "id": p.id,
                    "name": p.name,
                    "description": p.description,
                    "resource": p.resource,
                    "action": p.action,
                }
                for p in permissions
            ]
        }
    except Exception as e:
        logger.error(f"❌ 获取权限列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取权限列表失败"
        )


@router.get("/permissions/by-resource/{resource}")
async def get_permissions_by_resource(
    resource: str,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_admin_user),
):
    """获取特定资源的权限"""
    try:
        permissions = db.query(AdminPermission).filter(
            AdminPermission.resource == resource
        ).all()
        
        return {
            "resource": resource,
            "permissions": [p.to_dict() for p in permissions]
        }
    except Exception as e:
        logger.error(f"❌ 获取资源权限失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取权限失败"
        )


# ==================== 角色相关端点 ====================

@router.get("/roles", response_model=RoleListResponse)
async def list_roles(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_admin_user),
):
    """获取所有角色"""
    try:
        query = db.query(AdminRole)
        total = query.count()
        roles = query.offset(skip).limit(limit).all()
        
        return {
            "total": total,
            "items": [r.to_dict() for r in roles]
        }
    except Exception as e:
        logger.error(f"❌ 获取角色列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取角色列表失败"
        )


@router.get("/roles/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: str,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_admin_user),
):
    """获取角色详情"""
    try:
        role = db.query(AdminRole).filter(AdminRole.id == role_id).first()
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="角色不存在"
            )
        return role.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 获取角色失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取角色失败"
        )


@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    request: RoleCreateRequest,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_admin_user),
):
    """创建新角色"""
    try:
        # 检查权限
        checker = PermissionChecker(current_user, db)
        checker.require("write:role")
        
        # 创建角色
        role = RBACService.create_role(
            db,
            name=request.name,
            description=request.description,
            permission_ids=request.permission_ids
        )
        
        if not role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="角色创建失败"
            )
        
        return role.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 创建角色失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建角色失败"
        )


@router.put("/roles/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: str,
    request: RoleUpdateRequest,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_admin_user),
):
    """更新角色"""
    try:
        checker = PermissionChecker(current_user, db)
        checker.require("write:role")
        
        role = db.query(AdminRole).filter(AdminRole.id == role_id).first()
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="角色不存在"
            )
        
        if role.is_builtin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="不能修改内置角色"
            )
        
        # 更新权限
        if request.permission_ids is not None:
            role = RBACService.update_role_permissions(
                db, role_id, request.permission_ids
            )
        
        # 更新描述
        if request.description:
            role.description = request.description
            db.commit()
            db.refresh(role)
        
        return role.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 更新角色失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新角色失败"
        )


@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: str,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_admin_user),
):
    """删除角色"""
    try:
        checker = PermissionChecker(current_user, db)
        checker.require("delete:admin")
        
        success = RBACService.delete_role(db, role_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="角色删除失败（可能是内置角色或有用户使用）"
            )
        
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 删除角色失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除角色失败"
        )


# ==================== 管理员用户相关端点 ====================

@router.get("/users", response_model=AdminUserListResponse)
async def list_admin_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_admin_user),
):
    """获取所有管理员用户"""
    try:
        checker = PermissionChecker(current_user, db)
        checker.require("read:admin")
        
        query = db.query(AdminUser)
        total = query.count()
        users = query.offset(skip).limit(limit).all()
        
        return {
            "total": total,
            "items": [u.to_dict() for u in users]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 获取用户列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取用户列表失败"
        )


@router.post("/users", response_model=AdminUserResponse, status_code=status.HTTP_201_CREATED)
async def create_admin_user(
    request: AdminUserCreateRequest,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_admin_user),
):
    """创建管理员用户"""
    try:
        checker = PermissionChecker(current_user, db)
        checker.require("write:admin")
        
        # 检查用户名是否已存在
        existing = db.query(AdminUser).filter(
            AdminUser.username == request.username
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户名已存在"
            )
        
        # 获取角色
        role = db.query(AdminRole).filter(
            AdminRole.id == request.role_id
        ).first()
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="角色不存在"
            )
        
        # 创建用户
        from app.utils.security import hash_password
        import uuid
        
        user = AdminUser(
            id=str(uuid.uuid4()),
            username=request.username,
            password_hash=hash_password(request.password),
            role_id=request.role_id,
            is_active=True,
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        logger.info(f"✅ 管理员用户创建成功: {user.username}")
        return user.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 创建用户失败: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建用户失败"
        )


@router.put("/users/{user_id}/role", response_model=AdminUserResponse)
async def assign_role(
    user_id: str,
    request: AssignRoleRequest,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_admin_user),
):
    """为用户分配角色"""
    try:
        checker = PermissionChecker(current_user, db)
        checker.require("write:admin")
        
        user = RBACService.assign_role_to_user(db, user_id, request.role_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户或角色不存在"
            )
        
        return user.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 角色分配失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="角色分配失败"
        )


@router.post("/users/{user_id}/enable", response_model=AdminUserResponse)
async def enable_admin_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_admin_user),
):
    """启用用户"""
    try:
        checker = PermissionChecker(current_user, db)
        checker.require("write:admin")
        
        user = RBACService.enable_user(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
        
        return user.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 启用用户失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="启用用户失败"
        )


@router.post("/users/{user_id}/disable", response_model=AdminUserResponse)
async def disable_admin_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_admin_user),
):
    """禁用用户"""
    try:
        checker = PermissionChecker(current_user, db)
        checker.require("write:admin")
        
        user = RBACService.disable_user(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="不能禁用此用户（可能是最后一个管理员）"
            )
        
        return user.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 禁用用户失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="禁用用户失败"
        )
