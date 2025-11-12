import os
import shutil
import logging
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class BackupManager:
    """备份管理类"""
    
    def __init__(self, backup_dir: str, retention_days: int = 30):
        """初始化备份管理器"""
        self.backup_dir = backup_dir
        self.retention_days = retention_days
        
        # 创建备份目录
        Path(self.backup_dir).mkdir(parents=True, exist_ok=True)
    
    @staticmethod
    def create_database_backup(
        db_path: str,
        backup_dir: str,
        backup_name: Optional[str] = None,
    ) -> Dict:
        """创建数据库备份"""
        if not backup_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"database_backup_{timestamp}.db"
        
        backup_path = os.path.join(backup_dir, backup_name)
        
        try:
            # 复制数据库文件
            shutil.copy2(db_path, backup_path)
            
            # 获取备份信息
            file_size = os.path.getsize(backup_path)
            
            backup_info = {
                "name": backup_name,
                "path": backup_path,
                "size_bytes": file_size,
                "size_mb": round(file_size / (1024 * 1024), 2),
                "timestamp": datetime.now().isoformat(),
                "type": "database",
            }
            
            logger.info(f"✅ 数据库备份成功: {backup_name}")
            return backup_info
        except Exception as e:
            logger.error(f"❌ 数据库备份失败: {e}")
            raise
    
    @staticmethod
    def create_config_backup(
        config_dir: str,
        backup_dir: str,
        backup_name: Optional[str] = None,
    ) -> Dict:
        """创建配置文件备份"""
        if not backup_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"config_backup_{timestamp}.tar.gz"
        
        backup_path = os.path.join(backup_dir, backup_name)
        
        try:
            # 压缩配置目录
            shutil.make_archive(
                backup_path.replace('.tar.gz', ''),
                'gztar',
                config_dir
            )
            
            file_size = os.path.getsize(backup_path)
            
            backup_info = {
                "name": backup_name,
                "path": backup_path,
                "size_bytes": file_size,
                "size_mb": round(file_size / (1024 * 1024), 2),
                "timestamp": datetime.now().isoformat(),
                "type": "config",
            }
            
            logger.info(f"✅ 配置备份成功: {backup_name}")
            return backup_info
        except Exception as e:
            logger.error(f"❌ 配置备份失败: {e}")
            raise
    
    @staticmethod
    def list_backups(backup_dir: str) -> List[Dict]:
        """列出所有备份"""
        backups = []
        
        if not os.path.exists(backup_dir):
            return backups
        
        for filename in sorted(os.listdir(backup_dir), reverse=True):
            filepath = os.path.join(backup_dir, filename)
            
            if os.path.isfile(filepath):
                file_stat = os.stat(filepath)
                
                # 判断备份类型
                backup_type = "database" if filename.endswith(".db") else "config"
                
                backup_info = {
                    "name": filename,
                    "path": filepath,
                    "size_bytes": file_stat.st_size,
                    "size_mb": round(file_stat.st_size / (1024 * 1024), 2),
                    "timestamp": datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
                    "type": backup_type,
                }
                backups.append(backup_info)
        
        return backups
    
    @staticmethod
    def restore_database(
        backup_path: str,
        db_path: str,
    ) -> bool:
        """恢复数据库"""
        try:
            # 备份当前数据库
            if os.path.exists(db_path):
                backup_current = db_path + ".before_restore"
                shutil.copy2(db_path, backup_current)
                logger.info(f"当前数据库备份: {backup_current}")
            
            # 恢复备份
            shutil.copy2(backup_path, db_path)
            
            logger.info(f"✅ 数据库恢复成功: {backup_path}")
            return True
        except Exception as e:
            logger.error(f"❌ 数据库恢复失败: {e}")
            return False
    
    @staticmethod
    def restore_config(
        backup_path: str,
        extract_dir: str,
    ) -> bool:
        """恢复配置文件"""
        try:
            # 创建恢复目录
            os.makedirs(extract_dir, exist_ok=True)
            
            # 解压备份
            shutil.unpack_archive(backup_path, extract_dir)
            
            logger.info(f"✅ 配置恢复成功: {extract_dir}")
            return True
        except Exception as e:
            logger.error(f"❌ 配置恢复失败: {e}")
            return False
    
    @staticmethod
    def cleanup_old_backups(
        backup_dir: str,
        retention_days: int = 30,
    ) -> int:
        """清理过期备份"""
        deleted_count = 0
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        
        if not os.path.exists(backup_dir):
            return 0
        
        for filename in os.listdir(backup_dir):
            filepath = os.path.join(backup_dir, filename)
            
            if os.path.isfile(filepath):
                file_mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                
                if file_mtime < cutoff_date:
                    try:
                        os.remove(filepath)
                        logger.info(f"✅ 删除过期备份: {filename}")
                        deleted_count += 1
                    except Exception as e:
                        logger.error(f"❌ 删除备份失败: {e}")
        
        if deleted_count > 0:
            logger.info(f"✅ 清理完成: 删除 {deleted_count} 个过期备份")
        
        return deleted_count
    
    @staticmethod
    def delete_backup(backup_path: str) -> bool:
        """删除指定备份"""
        try:
            if os.path.exists(backup_path):
                os.remove(backup_path)
                logger.info(f"✅ 备份已删除: {backup_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"❌ 删除备份失败: {e}")
            return False
    
    @staticmethod
    def get_backup_stats(backup_dir: str) -> Dict:
        """获取备份统计"""
        backups = BackupManager.list_backups(backup_dir)
        
        total_size = sum(b["size_bytes"] for b in backups)
        
        db_backups = [b for b in backups if b["type"] == "database"]
        config_backups = [b for b in backups if b["type"] == "config"]
        
        return {
            "total_backups": len(backups),
            "database_backups": len(db_backups),
            "config_backups": len(config_backups),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "oldest_backup": min(b["timestamp"] for b in backups) if backups else None,
            "newest_backup": max(b["timestamp"] for b in backups) if backups else None,
        }
