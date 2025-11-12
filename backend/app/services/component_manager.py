import uuid
import logging
import json
import requests
from typing import List, Optional, Tuple, Dict
from sqlalchemy.orm import Session
from datetime import datetime
import hashlib

from app.models.component import Component

logger = logging.getLogger(__name__)


class ComponentManager:
    """组件管理类"""
    
    # 官方组件库
    OFFICIAL_COMPONENTS = {
        "sing-box": {
            "type": "proxy",
            "description": "Sing-Box 通用代理工具",
            "latest_version": "1.8.0",
            "install_url": "https://github.com/SagerNet/sing-box/releases/download/v1.8.0/sing-box-1.8.0-linux-amd64.tar.gz",
            "sha256": "abc123...",
        },
        "xray": {
            "type": "proxy",
            "description": "Xray 代理工具",
            "latest_version": "1.8.0",
            "install_url": "https://github.com/XTLS/Xray-core/releases/download/v1.8.0/Xray-linux-64.zip",
            "sha256": "def456...",
        },
        "acme.sh": {
            "type": "tool",
            "description": "ACME 证书管理工具",
            "latest_version": "3.0.0",
            "install_url": "https://github.com/acmesh-official/acme.sh/archive/refs/tags/3.0.0.tar.gz",
            "sha256": "ghi789...",
        },
        "ddns-go": {
            "type": "tool",
            "description": "DDNS 动态域名工具",
            "latest_version": "5.6.0",
            "install_url": "https://github.com/jeessy2/ddns-go/releases/download/v5.6.0/ddns-go_linux_x86_64.tar.gz",
            "sha256": "jkl012...",
        },
    }
    
    @staticmethod
    def create_component(
        db: Session,
        name: str,
        component_type: str,
        version: str = "0.0.0",
        install_url: Optional[str] = None,
        sha256_checksum: Optional[str] = None,
        meta: Optional[Dict] = None,
    ) -> Component:
        """创建新组件"""
        # 检查组件是否已存在
        existing = db.query(Component).filter(Component.name == name).first()
        if existing:
            raise ValueError(f"组件 {name} 已存在")
        
        component = Component(
            id=str(uuid.uuid4()),
            name=name,
            type=component_type,
            version=version,
            install_url=install_url,
            sha256_checksum=sha256_checksum,
            meta_json=json.dumps(meta) if meta else None,
            status="not-installed",
        )
        
        db.add(component)
        db.commit()
        db.refresh(component)
        
        logger.info(f"✅ 组件创建成功: {name} v{version}")
        return component
    
    @staticmethod
    def list_components(
        db: Session,
        skip: int = 0,
        limit: int = 10,
        component_type: Optional[str] = None,
    ) -> Tuple[List[Component], int]:
        """列出所有组件"""
        query = db.query(Component)
        
        if component_type:
            query = query.filter(Component.type == component_type)
        
        total = query.count()
        components = query.offset(skip).limit(limit).all()
        return components, total
    
    @staticmethod
    def get_component(db: Session, component_id: str) -> Optional[Component]:
        """获取组件详情"""
        return db.query(Component).filter(Component.id == component_id).first()
    
    @staticmethod
    def get_component_by_name(db: Session, name: str) -> Optional[Component]:
        """按名称获取组件"""
        return db.query(Component).filter(Component.name == name).first()
    
    @staticmethod
    def update_component(
        db: Session,
        component_id: str,
        **kwargs
    ) -> Optional[Component]:
        """更新组件"""
        component = db.query(Component).filter(Component.id == component_id).first()
        if not component:
            return None
        
        allowed_fields = ['status', 'version', 'installed_path', 'latest_version']
        
        for key, value in kwargs.items():
            if key in allowed_fields and value is not None:
                setattr(component, key, value)
        
        db.commit()
        db.refresh(component)
        logger.info(f"✅ 组件已更新: {component.name}")
        return component
    
    @staticmethod
    def check_updates(db: Session) -> Dict[str, str]:
        """检查所有组件更新"""
        updates = {}
        
        for name, info in ComponentManager.OFFICIAL_COMPONENTS.items():
            component = db.query(Component).filter(Component.name == name).first()
            
            if component:
                latest = info.get("latest_version")
                if component.version != latest:
                    updates[name] = {
                        "current": component.version,
                        "latest": latest,
                    }
        
        logger.info(f"✅ 发现 {len(updates)} 个可用更新")
        return updates
    
    @staticmethod
    def get_official_components() -> Dict:
        """获取官方组件库"""
        return ComponentManager.OFFICIAL_COMPONENTS
    
    @staticmethod
    def install_component(
        db: Session,
        component_id: str,
        install_path: str,
    ) -> Optional[Component]:
        """安装组件"""
        component = db.query(Component).filter(Component.id == component_id).first()
        if not component:
            return None
        
        try:
            # 这里应该实现实际的下载和安装逻辑
            # 为了演示，我们只更新状态
            component.status = "installed"
            component.installed_path = install_path
            component.version = component.latest_version or component.version
            
            db.commit()
            db.refresh(component)
            
            logger.info(f"✅ 组件已安装: {component.name} -> {install_path}")
            return component
        except Exception as e:
            logger.error(f"❌ 组件安装失败: {e}")
            component.status = "failed"
            db.commit()
            return None
    
    @staticmethod
    def uninstall_component(db: Session, component_id: str) -> Optional[Component]:
        """卸载组件"""
        component = db.query(Component).filter(Component.id == component_id).first()
        if not component:
            return None
        
        try:
            # 这里应该实现实际的卸载逻辑
            component.status = "not-installed"
            component.installed_path = None
            
            db.commit()
            db.refresh(component)
            
            logger.info(f"✅ 组件已卸载: {component.name}")
            return component
        except Exception as e:
            logger.error(f"❌ 组件卸载失败: {e}")
            return None
    
    @staticmethod
    def verify_checksum(file_path: str, checksum: str) -> bool:
        """验证文件校验和"""
        sha256_hash = hashlib.sha256()
        
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        
        return sha256_hash.hexdigest() == checksum
    
    @staticmethod
    def delete_component(db: Session, component_id: str) -> bool:
        """删除组件"""
        component = db.query(Component).filter(Component.id == component_id).first()
        if not component:
            return False
        
        name = component.name
        db.delete(component)
        db.commit()
        logger.info(f"✅ 组件已删除: {name}")
        return True
