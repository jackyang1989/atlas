"""
创建 Webhook 数据库表
文件：backend/scripts/create_webhook_tables.py

运行方式：
    cd backend
    python scripts/create_webhook_tables.py
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import engine, Base
from app.models.webhook import Webhook, WebhookLog
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_webhook_tables():
    """创建 Webhook 相关表"""
    try:
        logger.info("🚀 开始创建 Webhook 数据库表...")
        
        # 创建表
        Base.metadata.create_all(bind=engine)
        
        logger.info("✅ Webhook 表创建成功！")
        logger.info("   - webhooks")
        logger.info("   - webhook_logs")
        
        return True
    
    except Exception as e:
        logger.error(f"❌ 创建表失败: {e}")
        return False


if __name__ == "__main__":
    success = create_webhook_tables()
    sys.exit(0 if success else 1)
