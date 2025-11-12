from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthCredentials
from sqlalchemy.orm import Session
import logging

from app.database import get_db
from app.models.admin import AdminUser
from app.schemas.component import AlertTestRequest, AlertSendRequest
from app.services.alert_manager import alert_manager
from app.utils.security import verify_token

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> str:
    """获取当前登录用户"""
    token = credentials.credentials
    username = verify_token(token)
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    admin = db.query(AdminUser).filter(AdminUser.username == username).first()
    if not admin:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    return username


@router.post("/test")
async def test_alert(
    request: AlertTestRequest,
    current_user: str = Depends(get_current_user)
):
    """测试告警邮件"""
    try:
        success = alert_manager.send_email(
            to_emails=[request.email],
            subject="🧪 ATLAS 告警测试",
            body="这是一封测试邮件，用于验证 ATLAS 告警系统是否正常工作。",
            html_body="""
            <html>
            <body style="font-family: Arial, sans-serif;">
                <h2 style="color: #1890ff;">🧪 ATLAS 告警测试</h2>
                <p>这是一封测试邮件，用于验证 ATLAS 告警系统是否正常工作。</p>
                <p style="color: #666; margin-top: 20px;">如果您收到此邮件，说明告警系统配置正确。</p>
            </body>
            </html>
            """
        )
        
        if success:
            return {"message": "测试邮件已发送", "success": True}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="发送测试邮件失败，请检查 SMTP 配置"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"发送测试邮件失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"发送失败: {str(e)}"
        )


@router.post("/send")
async def send_alert(
    request: AlertSendRequest,
    current_user: str = Depends(get_current_user)
):
    """发送告警"""
    try:
        alert_type = request.type
        params = request.params
        recipients = request.recipients
        
        if alert_type == "service_down":
            success = alert_manager.send_service_down_alert(
                service_name=params.get("service_name"),
                service_port=params.get("service_port"),
                admin_emails=recipients
            )
        
        elif alert_type == "user_quota":
            success = alert_manager.send_user_quota_alert(
                username=params.get("username"),
                traffic_used_gb=params.get("traffic_used_gb"),
                traffic_limit_gb=params.get("traffic_limit_gb"),
                admin_emails=recipients
            )
        
        elif alert_type == "cert_expiry":
            success = alert_manager.send_cert_expiry_alert(
                domain=params.get("domain"),
                days_until_expiry=params.get("days_until_expiry"),
                admin_emails=recipients
            )
        
        elif alert_type == "system_resource":
            success = alert_manager.send_system_resource_alert(
                resource_type=params.get("resource_type"),
                usage_percent=params.get("usage_percent"),
                admin_emails=recipients
            )
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的告警类型: {alert_type}"
            )
        
        if success:
            return {"message": "告警已发送", "success": True}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="发送告警失败"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"发送告警失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"发送失败: {str(e)}"
        )


@router.get("/config")
async def get_alert_config(
    current_user: str = Depends(get_current_user)
):
    """获取告警配置"""
    return {
        "smtp_server": alert_manager.smtp_server,
        "smtp_port": alert_manager.smtp_port,
        "from_email": alert_manager.from_email,
        "configured": bool(alert_manager.smtp_user and alert_manager.smtp_password)
    }
