from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthCredentials
from sqlalchemy.orm import Session
import logging

from app.database import get_db
from app.models.admin import AdminUser
from app.schemas.domain import (
    DomainCreate,
    DomainUpdate,
    CertInfoUpdate,
    DomainResponse,
    DomainListResponse,
    DomainConfigResponse,
    DomainStatusResponse,
)
from app.services.domain_manager import DomainManager
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


@router.get("/", response_model=DomainListResponse)
async def list_domains(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """列出所有域名"""
    try:
        domains, total = DomainManager.list_domains(db, skip=skip, limit=limit)
        return {
            "total": total,
            "items": domains
        }
    except Exception as e:
        logger.error(f"获取域名列表出错: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取域名列表失败"
        )


@router.post("/", response_model=DomainResponse, status_code=status.HTTP_201_CREATED)
async def create_domain(
    request: DomainCreate,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建新域名"""
    try:
        domain = DomainManager.create_domain(
            db,
            domain=request.domain,
            email=request.email,
            provider=request.provider,
            api_key=request.api_key,
            api_secret=request.api_secret,
            auto_renew=request.auto_renew,
            renew_before_days=request.renew_before_days,
        )
        return domain
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"创建域名出错: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建域名失败"
        )


@router.get("/{domain_id}", response_model=DomainResponse)
async def get_domain(
    domain_id: str,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取域名详情"""
    domain = DomainManager.get_domain(db, domain_id)
    if not domain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="域名不存在"
        )
    return domain


@router.put("/{domain_id}", response_model=DomainResponse)
async def update_domain(
    domain_id: str,
    request: DomainUpdate,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新域名"""
    try:
        domain = DomainManager.update_domain(
            db,
            domain_id,
            **request.model_dump(exclude_unset=True)
        )
        if not domain:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="域名不存在"
            )
        return domain
    except Exception as e:
        logger.error(f"更新域名出错: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新域名失败"
        )


@router.post("/{domain_id}/cert", response_model=DomainResponse)
async def update_cert_info(
    domain_id: str,
    request: CertInfoUpdate,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新证书信息"""
    domain = DomainManager.update_cert_info(
        db,
        domain_id,
        request.cert_valid_from,
        request.cert_valid_to
    )
    if not domain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="域名不存在"
        )
    return domain


@router.get("/{domain_id}/config", response_model=DomainConfigResponse)
async def get_domain_config(
    domain_id: str,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取域名配置"""
    config = DomainManager.get_domain_config(db, domain_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="域名不存在"
        )
    return config


@router.get("/status/all", response_model=DomainStatusResponse)
async def get_domain_status(
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取域名状态统计"""
    try:
        from app.models.domain import Domain
        
        total = db.query(Domain).count()
        
        expiring = len(DomainManager.check_expiring_domains(db))
        expired = len(DomainManager.check_expired_domains(db))
        active = total - expired
        
        return {
            "total": total,
            "active": active,
            "expiring_soon": expiring,
            "expired": expired,
        }
    except Exception as e:
        logger.error(f"获取域名状态出错: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取域名状态失败"
        )


@router.delete("/{domain_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_domain(
    domain_id: str,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除域名"""
    if not DomainManager.delete_domain(db, domain_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="域名不存在"
        )
    return None
