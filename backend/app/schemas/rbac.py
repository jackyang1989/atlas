"""
RBAC Schema（数据验证）
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


# ==================== 权限相关 ====================

class PermissionResponse(BaseModel):
    """权限响应"""
    id: str
    name: str
    description: Optional[str]
    resource: str
    action: str
    
    class Config:
        from_attributes = True


class PermissionListResponse(BaseModel):
    """权限列表响应"""
    total: int
    items: List[PermissionResponse]


# ==================== 角色相关 ====================

class RoleResponse(BaseModel):
    """角色响应"""
    id: str
    name: str
    description: Optional[str]
    is_builtin: bool
    permissions: List[PermissionResponse]
    created_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class RoleListResponse(BaseModel):
    """角色列表响应"""
    total: int
    items: List[RoleResponse]


class RoleCreateRequest(BaseModel):
    """创建角色请求"""
    name: str = Field(..., min_length=1, max_length=50, description="角色名称")
    description: Optional[str] = Field(None, max_length=255, description="角色描述")
    permission_ids: List[str] = Field(..., description="权限 ID 列表")


class RoleUpdateRequest(BaseModel):
    """更新角色请求"""
    description: Optional[str] = Field(None, max_length=255)
    permission_ids: Optional[List[str]] = None


# ==================== 管理员用户相关 ====================

class AdminUserResponse(BaseModel):
    """管理员用户响应"""
    id: str
    username: str
    role_id: Optional[str]
    role: Optional[RoleResponse]
    totp_enabled: bool
    is_active: bool
    last_login: Optional[datetime]
    created_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class AdminUserListResponse(BaseModel):
    """管理员用户列表响应"""
    total: int
    items: List[AdminUserResponse]


class AdminUserCreateRequest(BaseModel):
    """创建管理员用户请求"""
    username: str = Field(..., min_length=1, max_length=50, description="用户名")
    password: str = Field(..., min_length=8, description="密码（至少 8 位）")
    role_id: str = Field(..., description="角色 ID")


class AdminUserUpdateRequest(BaseModel):
    """更新管理员用户请求"""
    password: Optional[str] = Field(None, min_length=8, description="新密码")
    role_id: Optional[str] = None
    is_active: Optional[bool] = None


class AssignRoleRequest(BaseModel):
    """分配角色请求"""
    role_id: str = Field(..., description="角色 ID")


# ==================== 权限检查请求/响应 ====================

class PermissionCheckRequest(BaseModel):
    """权限检查请求"""
    user_id: str = Field(..., description="用户 ID")
    permission: str = Field(..., description="权限名称")


class PermissionCheckResponse(BaseModel):
    """权限检查响应"""
    user_id: str
    permission: str
    allowed: bool
    reason: Optional[str]
