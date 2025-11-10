import uuid
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models.admin import AdminUser
from app.utils.security import hash_password, verify_password, create_access_token

logger = logging.getLogger(__name__)


class AuthService:
    @staticmethod
    def create_default_admin(db: Session):
        """创建默认管理员"""
        try:
            admin = db.query(AdminUser).filter(AdminUser.username == "admin").first()
            
            if not admin:
                admin = AdminUser(
                    id=str(uuid.uuid4()),
                    username="admin",
                    password_hash=hash_password("admin123"),
                    role="admin"
                )
                db.add(admin)
                db.commit()
                logger.info("✅ 默认管理员已创建: admin / admin123")
            else:
                logger.info("ℹ️  管理员已存在")
        except Exception as e:
            logger.error(f"创建默认管理员失败: {e}")
            db.rollback()
    
    @staticmethod
    def authenticate_admin(db: Session, username: str, password: str) -> AdminUser:
        """认证管理员"""
        admin = db.query(AdminUser).filter(AdminUser.username == username).first()
        
        if not admin:
            return None
        
        if admin.locked_until and admin.locked_until > datetime.utcnow():
            return None
        
        if not verify_password(password, admin.password_hash):
            admin.login_attempts += 1
            
            if admin.login_attempts >= 5:
                admin.locked_until = datetime.utcnow() + timedelta(minutes=30)
                logger.warning(f"⚠️  管理员账户已锁定: {username}")
            
            db.commit()
            return None
        
        admin.login_attempts = 0
        admin.locked_until = None
        admin.last_login = datetime.utcnow()
        db.commit()
        
        logger.info(f"✅ 登录成功: {username}")
        return admin
    
    @staticmethod
    def generate_access_token(admin: AdminUser) -> str:
        """生成访问令牌"""
        return create_access_token(data={"sub": admin.username})
    
    @staticmethod
    def change_password(db: Session, username: str, old_password: str, new_password: str) -> bool:
        """修改密码"""
        admin = db.query(AdminUser).filter(AdminUser.username == username).first()
        
        if not admin or not verify_password(old_password, admin.password_hash):
            return False
        
        admin.password_hash = hash_password(new_password)
        db.commit()
        logger.info(f"✅ 密码已修改: {username}")
        return True
