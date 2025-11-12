import json
import uuid
import logging
from typing import List, Optional, Dict, Tuple
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.service import Service
from app.config import settings

logger = logging.getLogger(__name__)


class ServiceManager:
    """VPN 服务管理类"""
    
    @staticmethod
    def generate_vless_config(port: int, cert_domain: str) -> Dict:
        """生成 VLESS+REALITY 配置"""
        return {
            "type": "vless",
            "tag": f"vless-{port}",
            "listen": "0.0.0.0",
            "listen_port": port,
            "users": [],
            "tls": {
                "enabled": True,
                "server_name": cert_domain,
                "certificate_path": f"{settings.CERTS_DIR}/{cert_domain}/fullchain.pem",
                "key_path": f"{settings.CERTS_DIR}/{cert_domain}/privkey.pem",
            },
            "transport": {
                "type": "tcp",
                "reality": {
                    "enabled": True,
                    "handshake": {"server": cert_domain, "epoch": 0},
                }
            }
        }
    
    @staticmethod
    def generate_hysteria2_config(port: int, password: str) -> Dict:
        """生成 Hysteria2 配置"""
        return {
            "type": "hysteria2",
            "tag": f"hysteria2-{port}",
            "listen": "0.0.0.0",
            "listen_port": port,
            "users": [
                {
                    "name": "default",
                    "password": password
                }
            ],
            "masquerade": "https://www.bing.com",
            "tls": {
                "enabled": False
            }
        }
    
    @staticmethod
    def create_service(
        db: Session,
        name: str,
        protocol: str,
        port: int,
        cert_domain: Optional[str] = None,
        tags: Optional[str] = None
    ) -> Service:
        """创建新服务"""
        # 检查端口是否已被占用
        existing = db.query(Service).filter(Service.port == port).first()
        if existing:
            raise ValueError(f"端口 {port} 已被占用")
        
        # 检查服务名是否重复
        existing_name = db.query(Service).filter(Service.name == name).first()
        if existing_name:
            raise ValueError(f"服务名 {name} 已存在")
        
        # 生成配置
        if protocol == 'vless':
            if not cert_domain:
                raise ValueError("VLESS 协议需要指定证书域名")
            config = ServiceManager.generate_vless_config(port, cert_domain)
        elif protocol == 'hysteria2':
            password = str(uuid.uuid4())[:8]
            config = ServiceManager.generate_hysteria2_config(port, password)
        else:
            raise ValueError(f"不支持的协议: {protocol}")
        
        # 创建服务
        service = Service(
            id=str(uuid.uuid4()),
            name=name,
            component="sing-box",
            protocol=protocol,
            port=port,
            config_json=json.dumps(config),
            cert_domain=cert_domain,
            tags=tags,
            status="stopped"
        )
        
        db.add(service)
        db.commit()
        db.refresh(service)
        
        logger.info(f"✅ 服务创建成功: {name}@{port}")
        return service
    
    @staticmethod
    def list_services(
        db: Session,
        skip: int = 0,
        limit: int = 10
    ) -> Tuple[List[Service], int]:
        """列出所有服务"""
        query = db.query(Service)
        total = query.count()
        services = query.offset(skip).limit(limit).all()
        return services, total
    
    @staticmethod
    def get_service(db: Session, service_id: str) -> Optional[Service]:
        """获取服务详情"""
        return db.query(Service).filter(Service.id == service_id).first()
    
    @staticmethod
    def update_service(
        db: Session,
        service_id: str,
        **kwargs
    ) -> Optional[Service]:
        """更新服务"""
        service = db.query(Service).filter(Service.id == service_id).first()
        if not service:
            return None
        
        # 更新允许的字段
        allowed_fields = ['name', 'status', 'tags', 'error_msg']
        for key, value in kwargs.items():
            if key in allowed_fields and value is not None:
                setattr(service, key, value)
        
        service.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(service)
        logger.info(f"✅ 服务已更新: {service.name}")
        return service
    
    @staticmethod
    def delete_service(db: Session, service_id: str) -> bool:
        """删除服务"""
        service = db.query(Service).filter(Service.id == service_id).first()
        if not service:
            return False
        
        db.delete(service)
        db.commit()
        logger.info(f"✅ 服务已删除: {service.name}")
        return True
    
    @staticmethod
    def toggle_service(db: Session, service_id: str) -> Optional[Service]:
        """启停服务"""
        service = db.query(Service).filter(Service.id == service_id).first()
        if not service:
            return None
        
        if service.status == 'running':
            service.status = 'stopped'
            logger.info(f"⏹ 服务已停止: {service.name}")
        else:
            service.status = 'running'
            logger.info(f"▶ 服务已启动: {service.name}")
        
        service.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(service)
        return service
