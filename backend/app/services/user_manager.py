import uuid
import logging
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import json

from app.models.user import User
from app.config import settings

logger = logging.getLogger(__name__)


class UserManager:
    """用户管理类"""
    
    @staticmethod
    def create_user(
        db: Session,
        username: str,
        traffic_limit_gb: float = 0,
        speed_limit_kbps: int = 0,
        device_limit: int = 0,
        expiry_date: Optional[datetime] = None,
        preferred_regions: Optional[str] = None,
        notes: Optional[str] = None
    ) -> User:
        """创建新用户"""
        # 检查用户名是否已存在
        existing = db.query(User).filter(User.username == username).first()
        if existing:
            raise ValueError(f"用户名 {username} 已存在")
        
        # 生成唯一的 UUID
        user_uuid = str(uuid.uuid4())
        
        # 创建用户
        user = User(
            id=str(uuid.uuid4()),
            username=username,
            uuid=user_uuid,
            traffic_limit_gb=traffic_limit_gb,
            speed_limit_kbps=speed_limit_kbps,
            device_limit=device_limit,
            expiry_date=expiry_date,
            preferred_regions=preferred_regions,
            notes=notes,
            status="active"
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        logger.info(f"✅ 用户创建成功: {username} (UUID: {user_uuid})")
        return user
    
    @staticmethod
    def list_users(
        db: Session,
        skip: int = 0,
        limit: int = 10
    ) -> Tuple[List[User], int]:
        """列出所有用户"""
        query = db.query(User)
        total = query.count()
        users = query.offset(skip).limit(limit).all()
        return users, total
    
    @staticmethod
    def get_user(db: Session, user_id: str) -> Optional[User]:
        """获取用户详情（按 ID）"""
        return db.query(User).filter(User.id == user_id).first()
    
    @staticmethod
    def get_user_by_username(db: Session, username: str) -> Optional[User]:
        """获取用户详情（按用户名）"""
        return db.query(User).filter(User.username == username).first()
    
    @staticmethod
    def get_user_by_uuid(db: Session, user_uuid: str) -> Optional[User]:
        """获取用户详情（按 UUID）"""
        return db.query(User).filter(User.uuid == user_uuid).first()
    
    @staticmethod
    def update_user(
        db: Session,
        user_id: str,
        **kwargs
    ) -> Optional[User]:
        """更新用户"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        
        # 更新允许的字段
        allowed_fields = [
            'traffic_limit_gb',
            'speed_limit_kbps',
            'device_limit',
            'status',
            'expiry_date',
            'preferred_regions',
            'notes'
        ]
        
        for key, value in kwargs.items():
            if key in allowed_fields and value is not None:
                setattr(user, key, value)
        
        user.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(user)
        logger.info(f"✅ 用户已更新: {user.username}")
        return user
    
    @staticmethod
    def add_traffic(
        db: Session,
        user_id: str,
        traffic_gb: float
    ) -> Optional[User]:
        """增加用户流量使用量"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        
        user.traffic_used_gb += traffic_gb
        user.updated_at = datetime.utcnow()
        
        # 检查是否超过配额
        if user.traffic_limit_gb > 0 and user.traffic_used_gb >= user.traffic_limit_gb:
            user.status = "over_quota"
            logger.warning(f"⚠️ 用户 {user.username} 已超过流量配额")
        
        db.commit()
        db.refresh(user)
        return user
    
    @staticmethod
    def reset_traffic(
        db: Session,
        user_id: str
    ) -> Optional[User]:
        """重置用户流量"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        
        user.traffic_used_gb = 0
        if user.status == "over_quota":
            user.status = "active"
        user.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(user)
        logger.info(f"✅ 用户流量已重置: {user.username}")
        return user
    
    @staticmethod
    def set_service_ids(
        db: Session,
        user_id: str,
        service_ids: List[str]
    ) -> Optional[User]:
        """设置用户可用的服务"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        
        user.service_ids = json.dumps(service_ids)
        user.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(user)
        logger.info(f"✅ 用户服务已更新: {user.username}")
        return user
    
    @staticmethod
    def check_expiry(db: Session) -> Tuple[int, int]:
        """检查过期用户并自动禁用"""
        now = datetime.utcnow()
        
        # 查找过期用户
        expired_users = db.query(User).filter(
            User.expiry_date <= now,
            User.status == "active"
        ).all()
        
        expired_count = 0
        for user in expired_users:
            user.status = "expired"
            expired_count += 1
        
        # 查找即将过期的用户（7 天内）
        soon_expire = db.query(User).filter(
            User.expiry_date > now,
            User.expiry_date <= now + timedelta(days=7),
            User.status == "active"
        ).count()
        
        if expired_count > 0:
            db.commit()
            logger.info(f"✅ 发现 {expired_count} 个过期用户已禁用")
        
        return expired_count, soon_expire
    
    @staticmethod
    def delete_user(db: Session, user_id: str) -> bool:
        """删除用户"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        
        username = user.username
        db.delete(user)
        db.commit()
        logger.info(f"✅ 用户已删除: {username}")
        return True
    
    @staticmethod
    def enable_user(db: Session, user_id: str) -> Optional[User]:
        """启用用户"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        
        user.status = "active"
        user.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(user)
        logger.info(f"✅ 用户已启用: {user.username}")
        return user
    
    @staticmethod
    def disable_user(db: Session, user_id: str) -> Optional[User]:
        """禁用用户"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        
        user.status = "disabled"
        user.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(user)
        logger.info(f"✅ 用户已禁用: {user.username}")
        return user
    
    @staticmethod
    def get_user_config(db: Session, user_id: str) -> Optional[dict]:
        """获取用户配置信息"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        
        service_ids = []
        if user.service_ids:
            try:
                service_ids = json.loads(user.service_ids)
            except json.JSONDecodeError:
                service_ids = []
        
        return {
            "uuid": user.uuid,
            "username": user.username,
            "status": user.status,
            "traffic_limit_gb": user.traffic_limit_gb,
            "traffic_used_gb": user.traffic_used_gb,
            "traffic_remaining_gb": max(0, user.traffic_limit_gb - user.traffic_used_gb),
            "speed_limit_kbps": user.speed_limit_kbps,
            "device_limit": user.device_limit,
            "devices_online": user.devices_online,
            "expiry_date": user.expiry_date.isoformat() if user.expiry_date else None,
            "service_ids": service_ids,
            "preferred_regions": user.preferred_regions,
        }
