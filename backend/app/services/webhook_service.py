"""
Webhook 事件系统服务
文件：backend/app/services/webhook_service.py
"""
import uuid
import hmac
import hashlib
import logging
import json
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import requests
from requests.exceptions import RequestException, Timeout

from app.models.webhook import Webhook, WebhookLog, WEBHOOK_EVENTS

logger = logging.getLogger(__name__)


class WebhookService:
    """Webhook 管理服务"""
    
    # ==================== Webhook 管理 ====================
    
    @staticmethod
    def create_webhook(
        db: Session,
        url: str,
        name: str,
        events: List[str],
        description: str = None,
        secret: str = None,
        retry_enabled: bool = True,
        created_by: str = None,
    ) -> Webhook:
        """创建 Webhook"""
        try:
            # 验证事件类型
            invalid_events = [e for e in events if e not in WEBHOOK_EVENTS]
            if invalid_events:
                raise ValueError(f"无效的事件类型: {invalid_events}")
            
            # 生成密钥
            if not secret:
                secret = str(uuid.uuid4())
            
            webhook = Webhook(
                id=str(uuid.uuid4()),
                url=url,
                name=name,
                description=description,
                events=json.dumps(events),
                secret=secret,
                enabled=True,
                retry_enabled=retry_enabled,
                created_by=created_by,
            )
            
            db.add(webhook)
            db.commit()
            db.refresh(webhook)
            
            logger.info(f"✅ Webhook 创建成功: {name} -> {url}")
            return webhook
        
        except Exception as e:
            logger.error(f"❌ Webhook 创建失败: {e}")
            db.rollback()
            raise
    
    @staticmethod
    def list_webhooks(
        db: Session,
        skip: int = 0,
        limit: int = 10,
        enabled_only: bool = False,
    ) -> tuple[List[Webhook], int]:
        """列出 Webhooks"""
        query = db.query(Webhook)
        
        if enabled_only:
            query = query.filter(Webhook.enabled == True)
        
        total = query.count()
        webhooks = query.offset(skip).limit(limit).all()
        return webhooks, total
    
    @staticmethod
    def get_webhook(db: Session, webhook_id: str) -> Optional[Webhook]:
        """获取 Webhook 详情"""
        return db.query(Webhook).filter(Webhook.id == webhook_id).first()
    
    @staticmethod
    def update_webhook(
        db: Session,
        webhook_id: str,
        **kwargs
    ) -> Optional[Webhook]:
        """更新 Webhook"""
        webhook = db.query(Webhook).filter(Webhook.id == webhook_id).first()
        if not webhook:
            return None
        
        allowed_fields = [
            'name', 'description', 'url', 'events', 'enabled',
            'retry_enabled', 'retry_max_attempts', 'retry_delay_seconds'
        ]
        
        for key, value in kwargs.items():
            if key in allowed_fields and value is not None:
                if key == 'events' and isinstance(value, list):
                    setattr(webhook, key, json.dumps(value))
                else:
                    setattr(webhook, key, value)
        
        db.commit()
        db.refresh(webhook)
        logger.info(f"✅ Webhook 已更新: {webhook.name}")
        return webhook
    
    @staticmethod
    def delete_webhook(db: Session, webhook_id: str) -> bool:
        """删除 Webhook"""
        webhook = db.query(Webhook).filter(Webhook.id == webhook_id).first()
        if not webhook:
            return False
        
        name = webhook.name
        db.delete(webhook)
        db.commit()
        logger.info(f"✅ Webhook 已删除: {name}")
        return True
    
    @staticmethod
    def toggle_webhook(db: Session, webhook_id: str) -> Optional[Webhook]:
        """启用/禁用 Webhook"""
        webhook = db.query(Webhook).filter(Webhook.id == webhook_id).first()
        if not webhook:
            return None
        
        webhook.enabled = not webhook.enabled
        db.commit()
        db.refresh(webhook)
        
        status = "启用" if webhook.enabled else "禁用"
        logger.info(f"✅ Webhook 已{status}: {webhook.name}")
        return webhook
    
    # ==================== 事件发送 ====================
    
    @staticmethod
    def generate_signature(payload: dict, secret: str) -> str:
        """生成 HMAC-SHA256 签名"""
        message = json.dumps(payload, sort_keys=True).encode('utf-8')
        signature = hmac.new(
            secret.encode('utf-8'),
            message,
            hashlib.sha256
        ).hexdigest()
        return signature
    
    @staticmethod
    def send_event(
        db: Session,
        event_type: str,
        payload: dict,
        source: str = "system",
    ):
        """发送事件到所有订阅的 Webhooks（同步版本）"""
        try:
            # 查找订阅此事件的 Webhooks
            webhooks = db.query(Webhook).filter(
                Webhook.enabled == True
            ).all()
            
            sent_count = 0
            for webhook in webhooks:
                events = webhook.get_events()
                if event_type in events:
                    WebhookService._send_to_webhook(
                        db, webhook, event_type, payload, source
                    )
                    sent_count += 1
            
            if sent_count > 0:
                logger.info(f"✅ 事件已发送: {event_type} -> {sent_count} 个 Webhook")
            
        except Exception as e:
            logger.error(f"❌ 发送事件失败: {e}")
    
    @staticmethod
    def _send_to_webhook(
        db: Session,
        webhook: Webhook,
        event_type: str,
        payload: dict,
        source: str,
        attempt: int = 1,
    ):
        """发送到单个 Webhook"""
        start_time = datetime.now()
        
        # 构建请求体
        event_data = {
            "event": event_type,
            "timestamp": datetime.now().isoformat(),
            "source": source,
            "payload": payload,
        }
        
        # 生成签名
        signature = WebhookService.generate_signature(event_data, webhook.secret)
        
        headers = {
            "Content-Type": "application/json",
            "X-ATLAS-Event": event_type,
            "X-ATLAS-Signature": signature,
            "User-Agent": "ATLAS-Webhook/1.0",
        }
        
        try:
            # 发送请求
            response = requests.post(
                webhook.url,
                json=event_data,
                headers=headers,
                timeout=10,  # 10 秒超时
            )
            
            response_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            success = response.status_code < 400
            
            # 记录日志
            log = WebhookLog(
                id=str(uuid.uuid4()),
                webhook_id=webhook.id,
                event_type=event_type,
                event_timestamp=datetime.now(),
                request_url=webhook.url,
                request_headers=json.dumps(headers),
                request_body=json.dumps(event_data),
                status_code=response.status_code,
                response_body=response.text[:1000],  # 限制长度
                response_time_ms=response_time,
                attempt=attempt,
                success=success,
            )
            db.add(log)
            
            # 更新统计
            webhook.total_calls += 1
            webhook.last_called_at = datetime.now()
            
            if not success:
                webhook.failed_calls += 1
                webhook.last_error = f"HTTP {response.status_code}"
                
                # 重试逻辑
                if webhook.retry_enabled and attempt < webhook.retry_max_attempts:
                    logger.warning(f"⚠️ Webhook 调用失败，将重试: {webhook.name}")
                    # 这里可以添加延迟重试逻辑
            else:
                webhook.last_error = None
            
            db.commit()
            
            if success:
                logger.info(f"✅ Webhook 调用成功: {webhook.name} ({response_time}ms)")
            else:
                logger.error(f"❌ Webhook 调用失败: {webhook.name} - HTTP {response.status_code}")
        
        except Timeout:
            # 超时
            log = WebhookLog(
                id=str(uuid.uuid4()),
                webhook_id=webhook.id,
                event_type=event_type,
                event_timestamp=datetime.now(),
                request_url=webhook.url,
                attempt=attempt,
                success=False,
                error_message="请求超时",
            )
            db.add(log)
            
            webhook.total_calls += 1
            webhook.failed_calls += 1
            webhook.last_error = "请求超时"
            webhook.last_called_at = datetime.now()
            db.commit()
            
            logger.error(f"❌ Webhook 请求超时: {webhook.name}")
        
        except RequestException as e:
            # 其他请求错误
            log = WebhookLog(
                id=str(uuid.uuid4()),
                webhook_id=webhook.id,
                event_type=event_type,
                event_timestamp=datetime.now(),
                request_url=webhook.url,
                attempt=attempt,
                success=False,
                error_message=str(e)[:500],
            )
            db.add(log)
            
            webhook.total_calls += 1
            webhook.failed_calls += 1
            webhook.last_error = str(e)[:500]
            webhook.last_called_at = datetime.now()
            db.commit()
            
            logger.error(f"❌ Webhook 请求失败: {webhook.name} - {e}")
    
    # ==================== 测试 Webhook ====================
    
    @staticmethod
    def test_webhook(db: Session, webhook_id: str) -> Dict:
        """测试 Webhook"""
        webhook = db.query(Webhook).filter(Webhook.id == webhook_id).first()
        if not webhook:
            return {"success": False, "error": "Webhook 不存在"}
        
        test_payload = {
            "event": "test",
            "timestamp": datetime.now().isoformat(),
            "message": "这是一条测试消息",
        }
        
        try:
            WebhookService._send_to_webhook(
                db, webhook, "test", test_payload, "manual_test"
            )
            return {"success": True, "message": "测试消息已发送"}
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ==================== 日志管理 ====================
    
    @staticmethod
    def get_webhook_logs(
        db: Session,
        webhook_id: str,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[List[WebhookLog], int]:
        """获取 Webhook 调用日志"""
        query = db.query(WebhookLog).filter(
            WebhookLog.webhook_id == webhook_id
        ).order_by(WebhookLog.created_at.desc())
        
        total = query.count()
        logs = query.offset(skip).limit(limit).all()
        return logs, total
    
    @staticmethod
    def get_recent_logs(
        db: Session,
        hours: int = 24,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[List[WebhookLog], int]:
        """获取最近的日志"""
        cutoff = datetime.now() - timedelta(hours=hours)
        
        query = db.query(WebhookLog).filter(
            WebhookLog.created_at >= cutoff
        ).order_by(WebhookLog.created_at.desc())
        
        total = query.count()
        logs = query.offset(skip).limit(limit).all()
        return logs, total
    
    @staticmethod
    def cleanup_old_logs(db: Session, days: int = 30) -> int:
        """清理旧日志"""
        cutoff = datetime.now() - timedelta(days=days)
        
        deleted_count = db.query(WebhookLog).filter(
            WebhookLog.created_at < cutoff
        ).delete()
        
        db.commit()
        
        logger.info(f"✅ 清理 Webhook 日志: 删除 {deleted_count} 条")
        return deleted_count
    
    # ==================== 统计信息 ====================
    
    @staticmethod
    def get_webhook_stats(db: Session, webhook_id: str) -> Dict:
        """获取 Webhook 统计信息"""
        webhook = db.query(Webhook).filter(Webhook.id == webhook_id).first()
        if not webhook:
            return None
        
        # 最近 24 小时的调用次数
        last_24h = datetime.now() - timedelta(hours=24)
        recent_calls = db.query(WebhookLog).filter(
            WebhookLog.webhook_id == webhook_id,
            WebhookLog.created_at >= last_24h,
        ).count()
        
        recent_failures = db.query(WebhookLog).filter(
            WebhookLog.webhook_id == webhook_id,
            WebhookLog.created_at >= last_24h,
            WebhookLog.success == False,
        ).count()
        
        # 平均响应时间
        avg_response_time = db.query(
            db.func.avg(WebhookLog.response_time_ms)
        ).filter(
            WebhookLog.webhook_id == webhook_id,
            WebhookLog.success == True,
            WebhookLog.created_at >= last_24h,
        ).scalar() or 0
        
        return {
            "webhook_id": webhook_id,
            "name": webhook.name,
            "total_calls": webhook.total_calls,
            "failed_calls": webhook.failed_calls,
            "success_rate": (
                (webhook.total_calls - webhook.failed_calls) / webhook.total_calls * 100
                if webhook.total_calls > 0 else 0
            ),
            "last_called_at": webhook.last_called_at.isoformat() if webhook.last_called_at else None,
            "last_error": webhook.last_error,
            "recent_calls_24h": recent_calls,
            "recent_failures_24h": recent_failures,
            "avg_response_time_ms": round(avg_response_time, 2),
        }


# ==================== 全局事件触发器（便捷函数）====================

def trigger_webhook_event(
    db: Session,
    event_type: str,
    payload: dict,
    source: str = "system",
):
    """全局事件触发器"""
    try:
        WebhookService.send_event(db, event_type, payload, source)
    except Exception as e:
        logger.error(f"❌ Webhook 事件触发失败: {e}")
