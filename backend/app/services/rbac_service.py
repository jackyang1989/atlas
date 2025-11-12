"""
RBAC（基于角色的访问控制）服务
"""
import uuid
import logging
from typing import List, Dict, Optional
from sqlalchemy.orm import Session

from app.models.rbac import AdminRole, AdminPermission, AdminUser, PERMISSIONS, ROLES_CONFIG

logger = logging.getLogger(__name__)


class RBACService:
    """RBAC 权限管理服务"""
    
    # ==================== 权限管理 ====================
    
    @staticmethod
    def init_permissions(db: Session):
        """初始化系统权限"""
        try:
            # 检查是否已初始化
            existing_count = db.query(AdminPermission).count()
            if existing_count >= len(PERMISSIONS):
                logger.info("✅ 权限已初始化")
                return
            
            # 创建所有权限
            for perm_name, description, resource, action in PERMISSIONS:
                perm = db.query(AdminPermission).filter(
                    AdminPermission.name == perm_name
                ).first()
                
                if not perm:
                    perm = AdminPermission(
                        id=str(uuid.uuid4()),
                        name=perm_name,
                        description=description,
                        resource=resource,
                        action=action,
                    )
                    db.add(perm)
            
            db.commit()
            logger.info(f"✅ 已初始化 {len(PERMISSIONS)} 个权限")
        except Exception as e:
            logger.error(f"❌ 权限初始化失败: {e}")
            db.rollback()
    
    # ==================== 角色管理 ====================
    
    @staticmethod
    def init_roles(db: Session):
        """初始化系统角色"""
        try:
            for role_name, role_config in ROLES_CONFIG.items():
                # 检查角色是否存在
                role = db.query(AdminRole).filter(
                    AdminRole.name == role_name
                ).first()
                
                if not role:
                    # 创建角色
                    role = AdminRole(
                        id=str(uuid.uuid4()),
                        name=role_name,
                        description=role_config["description"],
                        is_builtin=True,  # 标记为内置角色
                    )
                    
                    # 分配权限
                    for perm_name in role_config["permissions"]:
                        perm = db.query(AdminPermission).filter(
                            AdminPermission.name == perm_name
                        ).first()
                        if perm:
                            role.permissions.append(perm)
                    
                    db.add(role)
            
            db.commit()
            logger.info(f"✅ 已初始化 {len(ROLES_CONFIG)} 个角色")
        except Exception as e:
            logger.error(f"❌ 角色初始化失败: {e}")
            db.rollback()
    
    @staticmethod
    def create_role(
        db: Session,
        name: str,
        description: str,
        permission_ids: List[str]
    ) -> Optional[AdminRole]:
        """创建自定义角色"""
        try:
            # 检查角色名是否已存在
            existing = db.query(AdminRole).filter(AdminRole.name == name).first()
            if existing:
                logger.warning(f"⚠️ 角色 {name} 已存在")
                return None
            
            # 创建角色
            role = AdminRole(
                id=str(uuid.uuid4()),
                name=name,
                description=description,
                is_builtin=False,
            )
            
            # 添加权限
            for perm_id in permission_ids:
                perm = db.query(AdminPermission).filter(
                    AdminPermission.id == perm_id
                ).first()
                if perm:
                    role.permissions.append(perm)
            
            db.add(role)
            db.commit()
            db.refresh(role)
            
            logger.info(f"✅ 角色创建成功: {name}")
            return role
        except Exception as e:
            logger.error(f"❌ 角色创建失败: {e}")
            db.rollback()
            return None
    
    @staticmethod
    def update_role_permissions(
        db: Session,
        role_id: str,
        permission_ids: List[str]
    ) -> Optional[AdminRole]:
        """更新角色权限"""
        try:
            role = db.query(AdminRole).filter(AdminRole.id == role_id).first()
            if not role:
                logger.warning(f"⚠️ 角色不存在: {role_id}")
                return None
            
            if role.is_builtin:
                logger.warning(f"⚠️ 不能修改内置角色的权限: {role.name}")
                return None
            
            # 清空现有权限
            role.permissions.clear()
            
            # 添加新权限
            for perm_id in permission_ids:
                perm = db.query(AdminPermission).filter(
                    AdminPermission.id == perm_id
                ).first()
                if perm:
                    role.permissions.append(perm)
            
            db.commit()
            db.refresh(role)
            
            logger.info(f"✅ 角色权限已更新: {role.name}")
            return role
        except Exception as e:
            logger.error(f"❌ 角色权限更新失败: {e}")
            db.rollback()
            return None
    
    @staticmethod
    def get_all_roles(db: Session) -> List[AdminRole]:
        """获取所有角色"""
        return db.query(AdminRole).all()
    
    @staticmethod
    def get_role_by_name(db: Session, name: str) -> Optional[AdminRole]:
        """按名称获取角色"""
        return db.query(AdminRole).filter(AdminRole.name == name).first()
    
    @staticmethod
    def delete_role(db: Session, role_id: str) -> bool:
        """删除角色"""
        try:
            role = db.query(AdminRole).filter(AdminRole.id == role_id).first()
            if not role:
                return False
            
            if role.is_builtin:
                logger.warning(f"⚠️ 不能删除内置角色: {role.name}")
                return False
            
            # 检查是否有用户使用此角色
            user_count = db.query(AdminUser).filter(AdminUser.role_id == role_id).count()
            if user_count > 0:
                logger.warning(f"⚠️ 有 {user_count} 个用户使用此角色")
                return False
            
            db.delete(role)
            db.commit()
            logger.info(f"✅ 角色已删除: {role.name}")
            return True
        except Exception as e:
            logger.error(f"❌ 角色删除失败: {e}")
            db.rollback()
            return False
    
    # ==================== 权限检查 ====================
    
    @staticmethod
    def has_permission(user: AdminUser, permission: str) -> bool:
        """检查用户是否有权限"""
        if not user or not user.is_active:
            return False
        
        if not user.role:
            return False
        
        return any(p.name == permission for p in user.role.permissions)
    
    @staticmethod
    def has_any_permission(user: AdminUser, permissions: List[str]) -> bool:
        """检查用户是否有任何一个权限"""
        return any(RBACService.has_permission(user, perm) for perm in permissions)
    
    @staticmethod
    def has_all_permissions(user: AdminUser, permissions: List[str]) -> bool:
        """检查用户是否有所有权限"""
        return all(RBACService.has_permission(user, perm) for perm in permissions)
    
    # ==================== 管理员管理 ====================
    
    @staticmethod
    def assign_role_to_user(
        db: Session,
        user_id: str,
        role_id: str
    ) -> Optional[AdminUser]:
        """为用户分配角色"""
        try:
            user = db.query(AdminUser).filter(AdminUser.id == user_id).first()
            if not user:
                return None
            
            role = db.query(AdminRole).filter(AdminRole.id == role_id).first()
            if not role:
                return None
            
            user.role_id = role_id
            db.commit()
            db.refresh(user)
            
            logger.info(f"✅ 已为用户 {user.username} 分配角色 {role.name}")
            return user
        except Exception as e:
            logger.error(f"❌ 角色分配失败: {e}")
            db.rollback()
            return None
    
    @staticmethod
    def enable_user(db: Session, user_id: str) -> Optional[AdminUser]:
        """启用用户"""
        try:
            user = db.query(AdminUser).filter(AdminUser.id == user_id).first()
            if not user:
                return None
            
            user.is_active = True
            db.commit()
            db.refresh(user)
            
            logger.info(f"✅ 用户已启用: {user.username}")
            return user
        except Exception as e:
            logger.error(f"❌ 启用用户失败: {e}")
            db.rollback()
            return None
    
    @staticmethod
    def disable_user(db: Session, user_id: str) -> Optional[AdminUser]:
        """禁用用户"""
        try:
            user = db.query(AdminUser).filter(AdminUser.id == user_id).first()
            if not user:
                return None
            
            # 不能禁用最后一个 admin
            if user.role and user.role.name == "admin":
                admin_count = db.query(AdminUser).filter(
                    AdminUser.role_id == user.role_id,
                    AdminUser.id != user_id,
                    AdminUser.is_active == True
                ).count()
                
                if admin_count == 0:
                    logger.warning("⚠️ 不能禁用最后一个管理员账户")
                    return None
            
            user.is_active = False
            db.commit()
            db.refresh(user)
            
            logger.info(f"✅ 用户已禁用: {user.username}")
            return user
        except Exception as e:
            logger.error(f"❌ 禁用用户失败: {e}")
            db.rollback()
            return None
    
    # ==================== 审计日志 ====================
    
    @staticmethod
    def log_permission_check(
        db: Session,
        user_id: str,
        permission: str,
        resource_type: str,
        resource_id: str,
        allowed: bool
    ):
        """记录权限检查"""
        try:
            from app.models.admin import AuditLog
            
            log = AuditLog(
                id=str(uuid.uuid4()),
                admin_user=user_id,
                action=f"permission_check:{permission}",
                resource_type=resource_type,
                resource_id=resource_id,
                details={"allowed": allowed},
            )
            db.add(log)
            db.commit()
        except Exception as e:
            logger.error(f"❌ 审计日志记录失败: {e}")
