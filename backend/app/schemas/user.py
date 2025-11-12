from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class UserBase(BaseModel):
    """用户基础字段"""
    username: str = Field(..., min_length=1, max_length=100, description="用户名")
    traffic_limit_gb: float = Field(default=0, ge=0, description="流量限制（GB），0表示无限")
    speed_limit_kbps: int = Field(default=0, ge=0, description="速度限制（Kbps），0表示无限")
    device_limit: int = Field(default=0, ge=0, description="设备限制，0表示无限")
    expiry_date: Optional[datetime] = Field(None, description="过期时间")
    preferred_regions: Optional[str] = Field(None, description="首选地区，JSON格式")
    notes: Optional[str] = Field(None, description="备注")


class UserCreate(UserBase):
    """创建用户请求"""
    pass


class UserUpdate(BaseModel):
    """更新用户请求"""
    traffic_limit_gb: Optional[float] = Field(None, ge=0)
    speed_limit_kbps: Optional[int] = Field(None, ge=0)
    device_limit: Optional[int] = Field(None, ge=0)
    status: Optional[str] = Field(None, description="active/disabled/expired/over_quota")
    expiry_date: Optional[datetime] = None
    preferred_regions: Optional[str] = None
    notes: Optional[str] = None


class UserTrafficUpdate(BaseModel):
    """流量更新请求"""
    traffic_gb: float = Field(..., gt=0, description="增加的流量（GB）")


class UserServiceIds(BaseModel):
    """用户服务 ID 更新"""
    service_ids: List[str] = Field(..., description="服务 ID 列表")


class UserResponse(UserBase):
    """用户响应"""
    id: str
    uuid: str
    status: str
    traffic_used_gb: float
    devices_online: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class UserDetailResponse(UserResponse):
    """用户详情响应"""
    service_ids: Optional[str] = None
    traffic_remaining_gb: Optional[float] = None
    
    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """用户列表响应"""
    total: int
    items: List[UserResponse]


class UserConfigResponse(BaseModel):
    """用户配置响应"""
    uuid: str
    username: str
    status: str
    traffic_limit_gb: float
    traffic_used_gb: float
    traffic_remaining_gb: float
    speed_limit_kbps: int
    device_limit: int
    devices_online: int
    expiry_date: Optional[str]
    service_ids: List[str]
    preferred_regions: Optional[str]
