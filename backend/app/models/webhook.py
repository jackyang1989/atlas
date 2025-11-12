"""
Webhook 事件系统模型
"""
from sqlalchemy import Column, String, DateTime, Boolean, Integer, Text, ForeignKey
from sqlalchemy.sql import func
from app.database import Base
import json


class Webhook(Base):
    """Webhook 配置"""
    __tablename__ = "webhooks"
    
    id = Column(String(36), primary_key=True)
    url = Column(String(500), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String(255))
    
    # 事件订阅：JSON 格式 ["service.started", "user.created", ...]
    events = Column(Text, default="[]")
    
    # 认证
    secret = Column(String(256))  # 用于签名验证
    
    # 状态
    enabled = Column(Boolean, default=True, index=True)
    
    # 重试配置
    retry_enabled = Column(Boolean, default=True)
    retry_max_attempts = Column(Integer, default=3)
    retry_delay_seconds = Column(Integer, default=60)  # 重试间隔
    
    # 统计
    total_calls = Column(Integer, default=0)
    failed_calls = Column(Integer, default=0)
    last_called_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    
    created_by = Column(String(50))  # 创建者用户名
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<Webhook {self.name}>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "url": self.url,
            "name": self.name,
            "description": self.description,
            "events": json.loads(self.events) if self.events else [],
            "enabled": self.enabled,
            "retry_enabled": self.retry_enabled,
            "retry_max_attempts": self.retry_max_attempts,
            "retry_delay_seconds": self.retry_delay_seconds,
            "total_calls": self.total_calls,
            "failed_calls": self.failed_calls,
            "last_called_at": self.last_called_at.isoformat() if self.last_called_at else None,
            "last_error": self.last_error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
    
    def get_events(self):
        """获取订阅的事件列表"""
        return json.loads(self.events) if self.events else []
    
    def set_events(self, events: list):
        """设置订阅的事件"""
        self.events = json.dumps(events)


class WebhookLog(Base):
    """Webhook 调用日志"""
    __tablename__ = "webhook_logs"
    
    id = Column(String(36), primary_key=True)
    webhook_id = Column(String(36), ForeignKey('webhooks.id'), index=True)
    
    # 事件信息
    event_type = Column(String(100), nullable=False, index=True)
    event_timestamp = Column(DateTime, nullable=False)
    
    # 请求信息
    request_url = Column(String(500))
    request_headers = Column(Text)  # JSON
    request_body = Column(Text)     # JSON
    
    # 响应信息
    status_code = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    response_time_ms = Column(Integer)  # 响应时间，毫秒
    
    # 重试信息
    attempt = Column(Integer, default=1)  # 第几次尝试
    retry_after_seconds = Column(Integer, nullable=True)  # 建议重试间隔
    
    # 状态
    success = Column(Boolean, default=False, index=True)
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    def __repr__(self):
        return f"<WebhookLog {self.event_type} - {self.success}>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "webhook_id": self.webhook_id,
            "event_type": self.event_type,
            "event_timestamp": self.event_timestamp.isoformat() if self.event_timestamp else None,
            "status_code": self.status_code,
            "response_time_ms": self.response_time_ms,
            "attempt": self.attempt,
            "success": self.success,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ==================== 事件定义 ====================

WEBHOOK_EVENTS = {
    # 服务事件
    "service.started": {
        "description": "服务已启动",
        "category": "service",
        "example_payload": {
            "event": "service.started",
            "timestamp": "2025-11-12T10:30:00Z",
            "service": {
                "id": "svc_123",
                "name": "VLESS_HK",
                "protocol": "vless",
                "port": 443,
            }
        }
    },
    "service.stopped": {
        "description": "服务已停止",
        "category": "service",
    },
    "service.created": {
        "description": "服务已创建",
        "category": "service",
    },
    "service.deleted": {
        "description": "服务已删除",
        "category": "service",
    },
    
    # 用户事件
    "user.created": {
        "description": "用户已创建",
        "category": "user",
    },
    "user.deleted": {
        "description": "用户已删除",
        "category": "user",
    },
    "user.disabled": {
        "description": "用户已禁用",
        "category": "user",
    },
    "user.enabled": {
        "description": "用户已启用",
        "category": "user",
    },
    "user.quota_exceeded": {
        "description": "用户流量超限",
        "category": "user",
    },
    "user.expired": {
        "description": "用户已过期",
        "category": "user",
    },
    
    # 域名事件
    "domain.created": {
        "description": "域名已添加",
        "category": "domain",
    },
    "domain.cert_issued": {
        "description": "证书已签发",
        "category": "domain",
    },
    "domain.cert_renewed": {
        "description": "证书已续期",
        "category": "domain",
    },
    "domain.cert_expiring": {
        "description": "证书即将过期",
        "category": "domain",
    },
    "domain.deleted": {
        "description": "域名已删除",
        "category": "domain",
    },
    
    # 备份事件
    "backup.created": {
        "description": "备份已创建",
        "category": "backup",
    },
    "backup.restored": {
        "description": "备份已恢复",
        "category": "backup",
    },
    "backup.deleted": {
        "description": "备份已删除",
        "category": "backup",
    },
    
    # 系统事件
    "system.health_warning": {
        "description": "系统健康告警",
        "category": "system",
    },
    "system.resource_alert": {
        "description": "系统资源告警",
        "category": "system",
    },
    "system.error": {
        "description": "系统错误",
        "category": "system",
    },
}
