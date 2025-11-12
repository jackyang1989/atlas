from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime


class DomainBase(BaseModel):
    """域名基础字段"""
    domain: str = Field(..., min_length=1, max_length=100, description="域名")
    email: EmailStr = Field(..., description="邮箱地址")
    provider: str = Field(default="standalone", description="证书提供商")
    api_key: Optional[str] = Field(None, description="API密钥")
    api_secret: Optional[str] = Field(None, description="API密钥")
    auto_renew: bool = Field(default=True, description="自动续期")
    renew_before_days: int = Field(default=30, description="提前续期天数")


class DomainCreate(DomainBase):
    """创建域名请求"""
    pass


class DomainUpdate(BaseModel):
    """更新域名请求"""
    email: Optional[EmailStr] = None
    provider: Optional[str] = None
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    auto_renew: Optional[bool] = None
    renew_before_days: Optional[int] = None


class CertInfoUpdate(BaseModel):
    """证书信息更新"""
    cert_valid_from: datetime = Field(..., description="证书生效时间")
    cert_valid_to: datetime = Field(..., description="证书失效时间")


class DomainResponse(DomainBase):
    """域名响应"""
    id: str
    cert_valid_from: Optional[datetime]
    cert_valid_to: Optional[datetime]
    last_renew_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class DomainListResponse(BaseModel):
    """域名列表响应"""
    total: int
    items: List[DomainResponse]


class DomainConfigResponse(BaseModel):
    """域名配置响应"""
    id: str
    domain: str
    email: str
    provider: str
    auto_renew: bool
    renew_before_days: int
    cert_valid_from: Optional[str]
    cert_valid_to: Optional[str]
    days_remaining: Optional[int]
    last_renew_at: Optional[str]
    created_at: str


class DomainStatusResponse(BaseModel):
    """域名状态响应"""
    total: int
    active: int
    expiring_soon: int
    expired: int
