from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthCredentials
from sqlalchemy.orm import Session
import logging
import json

from app.database import get_db
from app.models.admin import AdminUser
from app.schemas.user import (
    UserCreate,
    UserUpdate,
    UserTrafficUpdate,
    UserServiceIds,
    UserResponse,
    UserDetailResponse,
    UserListResponse,
    UserConfigResponse
)
from app.services.user_manager import UserManager
from app.utils.security import verify_token

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> str:
    """获取并验证当前用户"""
    token = credentials.credentials
    username = verify_token(token)
    
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 验证用户是否存在
    admin = db.query(AdminUser).filter(AdminUser.username == username).first()
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    
    return username


@router.get("/", response_model=UserListResponse)
async def list_users(
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(10, ge=1, le=100, description="每页记录数"),
    status_filter: str = Query(None, description="状态过滤: active/disabled/expired/over_quota"),
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """列出所有用户"""
    try:
        users, total = UserManager.list_users(db, skip=skip, limit=limit)
        
        # 状态过滤
        if status_filter:
            users = [u for u in users if u.status == status_filter]
            total = len(users)
        
        return {
            "total": total,
            "items": users
        }
    except Exception as e:
        logger.error(f"获取用户列表出错: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取用户列表失败"
        )


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    request: UserCreate,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建新用户"""
    try:
        user = UserManager.create_user(
            db,
            username=request.username,
            traffic_limit_gb=request.traffic_limit_gb,
            speed_limit_kbps=request.speed_limit_kbps,
            device_limit=request.device_limit,
            expiry_date=request.expiry_date,
            preferred_regions=request.preferred_regions,
            notes=request.notes
        )
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"创建用户出错: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建用户失败"
        )


@router.get("/{user_id}", response_model=UserDetailResponse)
async def get_user(
    user_id: str,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取用户详情"""
    user = UserManager.get_user(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    # 计算剩余流量
    traffic_remaining_gb = None
    if user.traffic_limit_gb > 0:
        traffic_remaining_gb = max(0, user.traffic_limit_gb - user.traffic_used_gb)
    
    response = UserDetailResponse(**user.__dict__)
    response.traffic_remaining_gb = traffic_remaining_gb
    return response


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    request: UserUpdate,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新用户"""
    try:
        user = UserManager.update_user(
            db,
            user_id,
            **request.model_dump(exclude_unset=True)
        )
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
        return user
    except Exception as e:
        logger.error(f"更新用户出错: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新用户失败"
        )


@router.post("/{user_id}/traffic", response_model=UserResponse)
async def add_traffic(
    user_id: str,
    request: UserTrafficUpdate,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """增加用户流量"""
    user = UserManager.add_traffic(db, user_id, request.traffic_gb)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    return user


@router.post("/{user_id}/traffic/reset", response_model=UserResponse)
async def reset_traffic(
    user_id: str,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """重置用户流量"""
    user = UserManager.reset_traffic(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    return user


@router.put("/{user_id}/services", response_model=UserResponse)
async def set_service_ids(
    user_id: str,
    request: UserServiceIds,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """设置用户的服务"""
    user = UserManager.set_service_ids(db, user_id, request.service_ids)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    return user


@router.post("/{user_id}/enable", response_model=UserResponse)
async def enable_user(
    user_id: str,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """启用用户"""
    user = UserManager.enable_user(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    return user


@router.post("/{user_id}/disable", response_model=UserResponse)
async def disable_user(
    user_id: str,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """禁用用户"""
    user = UserManager.disable_user(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    return user


@router.get("/{user_id}/config", response_model=UserConfigResponse)
async def get_user_config(
    user_id: str,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取用户配置"""
    config = UserManager.get_user_config(db, user_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    return config


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除用户"""
    if not UserManager.delete_user(db, user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    return None
