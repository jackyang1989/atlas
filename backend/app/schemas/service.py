from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime


class ServiceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="服务名称")
    protocol: str = Field(..., description="协议类型")
    port: int = Field(..., ge=1, le=65535, description="监听端口")
    cert_domain: Optional[str] = Field(None, description="证书域名（VLESS 必需）")
    tags: Optional[str] = Field(None, description="地域标签，JSON 格式")


class ServiceCreate(ServiceBase):
    """创建服务请求"""
    
    @field_validator('protocol')
    @classmethod
    def validate_protocol(cls, v):
        allowed = ['vless', 'hysteria2', 'tuic', 'trojan']
        if v not in allowed:
            raise ValueError(f'协议必须是: {", ".join(allowed)}')
        return v


class ServiceUpdate(BaseModel):
    """更新服务请求"""
    name: Optional[str] = Field(None, max_length=100)
    status: Optional[str] = None
    tags: Optional[str] = None


class ServiceResponse(ServiceBase):
    """服务响应"""
    id: str
    component: str
    status: str
    error_msg: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ServiceListResponse(BaseModel):
    """服务列表响应"""
    total: int
    items: List[ServiceResponse]
