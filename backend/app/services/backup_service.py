"""
备份服务 - 修复版本
包含全局实例初始化
"""
import os
import shutil
import logging
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pathlib import Path
from sqlalchemy.orm import Session

from app.config import settings
from app.models.admin import AdminUser

logger = logging.getLogger(__name__)


class BackupService:
    """备份管理服务"""
    
    def __init__(self, backup_dir: str, retention_days: int = 30):
        """初始化备份服务"""
        self.backup_dir = backup_dir
        self.retention_days = retention_days
        
        # 创建备份目录
        Path(self.backup_dir).mkdir(parents=True, exist_ok=True)
        logger.info(f"✅ 备份目录已初始化: {self.backup_dir}")
    
    def create_backup(
        self,
        db: Session,
        include_data: bool = True,
        include_config: bool = True,
        description: Optional[str] = None,
    ) -> Dict:
        """创建完整备份"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"atlas_backup_{timestamp}.tar.gz"
        backup_path = os.path.join(self.backup_dir, backup_name)
        
        try:
            import tempfile
            import tarfile
            
            # 临时目录存放要备份的文件
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # 1. 备份数据库
                if include_data:
                    db_file = getattr(settings, 'DATABASE_URL', 'sqlite:///./atlas.db')
                    if 'sqlite' in db_file:
                        db_path = db_file.replace('sqlite:///', '').replace('sqlite://', '')
                        if os.path.exists(db_path):
                            shutil.copy2(db_path, temp_path / 'atlas.db')
                            logger.info(f"✅ 数据库备份: {db_path}")
                
                # 2. 备份配置文件
                if include_config:
                    certs_dir = getattr(settings, 'CERTS_DIR', '/opt/atlas/certs')
                    config_dir = getattr(settings, 'SING_BOX_CONFIG_PATH', '/etc/sing-box/config.json')
                    
                    if os.path.exists(certs_dir):
                        shutil.copytree(certs_dir, temp_path / 'certs', dirs_exist_ok=True)
                        logger.info(f"✅ 证书备份: {certs_dir}")
                    
                    if os.path.exists(config_dir):
                        shutil.copy2(config_dir, temp_path / 'sing-box-config.json')
                        logger.info(f"✅ 配置文件备份: {config_dir}")
                
                # 3. 添加备份元数据
                metadata = {
                    'timestamp': timestamp,
                    'description': description or '自动备份',
                    'include_data': include_data,
                    'include_config': include_config,
                    'version': '1.0.0',
                }
                (temp_path / 'backup_metadata.json').write_text(json.dumps(metadata, indent=2))
                
                # 4. 压缩备份
                with tarfile.open(backup_path, 'w:gz') as tar:
                    for item in temp_path.iterdir():
                        tar.add(item, arcname=item.name)
                
                file_size = os.path.getsize(backup_path)
                
                return {
                    'success': True,
                    'filename': backup_name,
                    'path': backup_path,
                    'size_bytes': file_size,
                    'size_mb': round(file_size / (1024 * 1024), 2),
                    'created_at': datetime.now().isoformat(),
                    'type': 'full',
                }
        
        except Exception as e:
            logger.error(f"❌ 备份失败: {e}")
            return {
                'success': False,
                'error': str(e),
            }
    
    def list_backups(self) -> List[Dict]:
        """列出所有备份"""
        backups = []
        
        if not os.path.exists(self.backup_dir):
            return backups
        
        try:
            for filename in sorted(os.listdir(self.backup_dir), reverse=True):
                filepath = os.path.join(self.backup_dir, filename)
                
                if os.path.isfile(filepath) and filename.endswith('.tar.gz'):
                    file_stat = os.stat(filepath)
                    
                    backup_info = {
                        'filename': filename,
                        'path': filepath,
                        'size_bytes': file_stat.st_size,
                        'size_mb': round(file_stat.st_size / (1024 * 1024), 2),
                        'created_at': datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
                        'type': 'full',
                    }
                    
                    # 尝试读取元数据
                    try:
                        import tarfile
                        with tarfile.open(filepath, 'r:gz') as tar:
                            if 'backup_metadata.json' in tar.getnames():
                                meta = tar.extractfile('backup_metadata.json').read()
                                metadata = json.loads(meta)
                                backup_info['description'] = metadata.get('description', '')
                    except Exception:
                        backup_info['description'] = '未知'
                    
                    backups.append(backup_info)
        
        except Exception as e:
            logger.error(f"❌ 列表备份失败: {e}")
        
        return backups
    
    def restore_backup(
        self,
        db: Session,
        filename: str,
        force: bool = False,
    ) -> Dict:
        """恢复备份"""
        backup_path = os.path.join(self.backup_dir, filename)
        
        if not os.path.exists(backup_path):
            return {'success': False, 'error': '备份文件不存在'}
        
        try:
            import tarfile
            import tempfile
            
            with tempfile.TemporaryDirectory() as temp_dir:
                # 解压备份
                with tarfile.open(backup_path, 'r:gz') as tar:
                    tar.extractall(temp_dir)
                
                temp_path = Path(temp_dir)
                
                # 恢复数据库
                db_backup = temp_path / 'atlas.db'
                if db_backup.exists():
                    db_file = getattr(settings, 'DATABASE_URL', 'sqlite:///./atlas.db')
                    if 'sqlite' in db_file:
                        db_path = db_file.replace('sqlite:///', '').replace('sqlite://', '')
                        
                        # 备份当前数据库
                        if os.path.exists(db_path):
                            backup_current = f"{db_path}.before_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                            shutil.copy2(db_path, backup_current)
                            logger.info(f"✅ 当前数据库已备份: {backup_current}")
                        
                        # 恢复备份
                        shutil.copy2(db_backup, db_path)
                        logger.info(f"✅ 数据库已恢复: {db_path}")
                
                # 恢复配置文件
                certs_backup = temp_path / 'certs'
                if certs_backup.exists():
                    certs_dir = getattr(settings, 'CERTS_DIR', '/opt/atlas/certs')
                    os.makedirs(certs_dir, exist_ok=True)
                    shutil.copytree(certs_backup, certs_dir, dirs_exist_ok=True)
                    logger.info(f"✅ 证书已恢复: {certs_dir}")
                
                config_backup = temp_path / 'sing-box-config.json'
                if config_backup.exists():
                    config_dir = getattr(settings, 'SING_BOX_CONFIG_PATH', '/etc/sing-box/config.json')
                    os.makedirs(os.path.dirname(config_dir), exist_ok=True)
                    shutil.copy2(config_backup, config_dir)
                    logger.info(f"✅ 配置已恢复: {config_dir}")
            
            return {
                'success': True,
                'message': '备份恢复成功',
                'restored_at': datetime.now().isoformat(),
            }
        
        except Exception as e:
            logger.error(f"❌ 恢复失败: {e}")
            return {
                'success': False,
                'error': str(e),
            }
    
    def delete_backup(self, filename: str) -> bool:
        """删除备份"""
        backup_path = os.path.join(self.backup_dir, filename)
        
        try:
            if os.path.exists(backup_path):
                os.remove(backup_path)
                logger.info(f"✅ 备份已删除: {filename}")
                return True
            return False
        except Exception as e:
            logger.error(f"❌ 删除备份失败: {e}")
            return False
    
    def cleanup_old_backups(self, days: int = 30) -> Dict:
        """清理过期备份"""
        deleted_count = 0
        freed_space = 0
        cutoff_date = datetime.now() - timedelta(days=days)
        
        if not os.path.exists(self.backup_dir):
            return {'success': False, 'error': '备份目录不存在'}
        
        try:
            for filename in os.listdir(self.backup_dir):
                filepath = os.path.join(self.backup_dir, filename)
                
                if os.path.isfile(filepath):
                    file_mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                    
                    if file_mtime < cutoff_date:
                        try:
                            file_size = os.path.getsize(filepath)
                            os.remove(filepath)
                            freed_space += file_size
                            deleted_count += 1
                            logger.info(f"✅ 删除过期备份: {filename}")
                        except Exception as e:
                            logger.error(f"❌ 删除备份失败: {e}")
            
            return {
                'success': True,
                'deleted_count': deleted_count,
                'freed_space_mb': round(freed_space / (1024 * 1024), 2),
                'message': f'已删除 {deleted_count} 个过期备份',
            }
        
        except Exception as e:
            logger.error(f"❌ 清理备份失败: {e}")
            return {
                'success': False,
                'error': str(e),
            }


# 全局实例 - 在应用启动时初始化
backup_service: Optional[BackupService] = None


def init_backup_service():
    """初始化备份服务（在应用启动时调用）"""
    global backup_service
    backup_dir = getattr(settings, 'BACKUPS_DIR', '/opt/atlas/backups')
    backup_service = BackupService(backup_dir, retention_days=30)
    return backup_service


def get_backup_service() -> BackupService:
    """获取备份服务实例"""
    global backup_service
    if backup_service is None:
        backup_service = init_backup_service()
    return backup_service
