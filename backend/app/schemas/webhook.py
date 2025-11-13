"""
Webhook Schema（数据验证）
文件：backend/app/schemas/webhook.py
"""
from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional
from datetime import datetime


# ==================== Webhook ====================

class WebhookCreate(BaseModel):
    """创建 Webhook 请求"""
    url: str = Field(..., description="Webhook URL")
    name: str = Field(..., min_length=1, max_length=100, description="名称")
    description: Optional[str] = Field(None, max_length=255, description="描述")
    events: List[str] = Field(..., min_items=1, description="订阅的事件列表")
    secret: Optional[str] = Field(None, description="签名密钥（自动生成）")
    retry_enabled: bool = Field(True, description="启用重试")


class WebhookUpdate(BaseModel):
    """更新 Webhook 请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=255)
    url: Optional[str] = None
    events: Optional[List[str]] = None
    enabled: Optional[bool] = None
    retry_enabled: Optional[bool] = None
    retry_max_attempts: Optional[int] = Field(None, ge=1, le=10)
    retry_delay_seconds: Optional[int] = Field(None, ge=10, le=3600)


class WebhookResponse(BaseModel):
    """Webhook 响应"""
    id: str
    url: str
    name: str
    description: Optional[str]
    events: List[str]
    enabled: bool
    retry_enabled: bool
    retry_max_attempts: int
    retry_delay_seconds: int
    total_calls: int
    failed_calls: int
    last_called_at: Optional[str]
    last_error: Optional[str]
    created_at: Optional[str]
    
    class Config:
        from_attributes = True


class WebhookListResponse(BaseModel):
    """Webhook 列表响应"""
    total: int
    items: List[WebhookResponse]


class WebhookTestRequest(BaseModel):
    """测试 Webhook 请求"""
    custom_payload: Optional[dict] = Field(None, description="自定义测试负载")


# ==================== Webhook Log ====================

class WebhookLogResponse(BaseModel):
    """Webhook 日志响应"""
    id: str
    webhook_id: str
    event_type: str
    event_timestamp: Optional[str]
    status_code: Optional[int]
    response_time_ms: Optional[int]
    attempt: int
    success: bool
    error_message: Optional[str]
    created_at: Optional[str]
    
    class Config:
        from_attributes = True


class WebhookLogListResponse(BaseModel):
    """Webhook 日志列表响应"""
    total: int
    items: List[WebhookLogResponse]


# ==================== 统计 ====================

class WebhookStatsResponse(BaseModel):
    """Webhook 统计响应"""
    webhook_id: str
    name: str
    total_calls: int
    failed_calls: int
    success_rate: float
    last_called_at: Optional[str]
    last_error: Optional[str]
    recent_calls_24h: int
    recent_failures_24h: int
    avg_response_time_ms: float


# ==================== 事件信息 ====================

class EventInfo(BaseModel):
    """事件信息"""
    event_type: str
    description: str
    category: str
    example_payload: Optional[dict]


class EventListResponse(BaseModel):
    """事件列表响应"""
    total: int
    events: List[EventInfo]
