import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Optional
from datetime import datetime

from app.config import settings

logger = logging.getLogger(__name__)


class AlertManager:
    """告警管理类"""
    
    def __init__(self):
        self.smtp_server = getattr(settings, 'SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = getattr(settings, 'SMTP_PORT', 587)
        self.smtp_user = getattr(settings, 'SMTP_USER', '')
        self.smtp_password = getattr(settings, 'SMTP_PASSWORD', '')
        self.from_email = self.smtp_user
    
    def send_email(
        self,
        to_emails: List[str],
        subject: str,
        body: str,
        html_body: Optional[str] = None
    ) -> bool:
        """发送邮件告警"""
        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = self.from_email
            msg['To'] = ', '.join(to_emails)
            msg['Subject'] = subject
            
            # 添加文本和 HTML 内容
            msg.attach(MIMEText(body, 'plain'))
            if html_body:
                msg.attach(MIMEText(html_body, 'html'))
            
            # 发送邮件
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"✅ 邮件已发送至: {', '.join(to_emails)}")
            return True
        
        except Exception as e:
            logger.error(f"❌ 发送邮件失败: {e}")
            return False
    
    def send_service_down_alert(
        self,
        service_name: str,
        service_port: int,
        admin_emails: List[str]
    ) -> bool:
        """发送服务停止告警"""
        subject = f"⚠️ [ATLAS] 服务停止告警 - {service_name}"
        
        body = f"""
ATLAS 系统告警通知

服务名称: {service_name}
服务端口: {service_port}
告警时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
告警类型: 服务停止

请立即检查服务状态并采取必要措施。
        """
        
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2 style="color: #ff4d4f;">⚠️ ATLAS 系统告警通知</h2>
            <table style="border-collapse: collapse; width: 100%;">
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>服务名称</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{service_name}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>服务端口</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{service_port}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>告警时间</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>告警类型</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd; color: #ff4d4f;">服务停止</td>
                </tr>
            </table>
            <p style="margin-top: 20px; color: #666;">请立即检查服务状态并采取必要措施。</p>
        </body>
        </html>
        """
        
        return self.send_email(admin_emails, subject, body, html_body)
    
    def send_user_quota_alert(
        self,
        username: str,
        traffic_used_gb: float,
        traffic_limit_gb: float,
        admin_emails: List[str]
    ) -> bool:
        """发送用户配额告警"""
        usage_percent = (traffic_used_gb / traffic_limit_gb * 100) if traffic_limit_gb > 0 else 0
        
        subject = f"⚠️ [ATLAS] 用户流量告警 - {username}"
        
        body = f"""
ATLAS 用户流量告警

用户名: {username}
已用流量: {traffic_used_gb:.2f} GB
流量限额: {traffic_limit_gb:.2f} GB
使用率: {usage_percent:.1f}%
告警时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

建议立即检查用户流量使用情况。
        """
        
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2 style="color: #faad14;">⚠️ ATLAS 用户流量告警</h2>
            <table style="border-collapse: collapse; width: 100%;">
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>用户名</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{username}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>已用流量</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{traffic_used_gb:.2f} GB</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>流量限额</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{traffic_limit_gb:.2f} GB</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>使用率</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd; color: #faad14;">{usage_percent:.1f}%</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>告警时间</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</td>
                </tr>
            </table>
            <p style="margin-top: 20px; color: #666;">建议立即检查用户流量使用情况。</p>
        </body>
        </html>
        """
        
        return self.send_email(admin_emails, subject, body, html_body)
    
    def send_cert_expiry_alert(
        self,
        domain: str,
        days_until_expiry: int,
        admin_emails: List[str]
    ) -> bool:
        """发送证书过期告警"""
        subject = f"⚠️ [ATLAS] 证书即将过期 - {domain}"
        
        body = f"""
ATLAS 证书过期告警

域名: {domain}
剩余天数: {days_until_expiry} 天
告警时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

请及时续签证书以避免服务中断。
        """
        
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2 style="color: #ff4d4f;">⚠️ ATLAS 证书过期告警</h2>
            <table style="border-collapse: collapse; width: 100%;">
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>域名</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{domain}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>剩余天数</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd; color: #ff4d4f;">{days_until_expiry} 天</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>告警时间</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</td>
                </tr>
            </table>
            <p style="margin-top: 20px; color: #666;">请及时续签证书以避免服务中断。</p>
        </body>
        </html>
        """
        
        return self.send_email(admin_emails, subject, body, html_body)
    
    def send_system_resource_alert(
        self,
        resource_type: str,
        usage_percent: float,
        admin_emails: List[str]
    ) -> bool:
        """发送系统资源告警"""
        subject = f"⚠️ [ATLAS] 系统资源告警 - {resource_type}"
        
        body = f"""
ATLAS 系统资源告警

资源类型: {resource_type}
使用率: {usage_percent:.1f}%
告警时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

系统资源使用率过高，请及时检查。
        """
        
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2 style="color: #ff4d4f;">⚠️ ATLAS 系统资源告警</h2>
            <table style="border-collapse: collapse; width: 100%;">
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>资源类型</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{resource_type}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>使用率</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd; color: #ff4d4f;">{usage_percent:.1f}%</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>告警时间</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</td>
                </tr>
            </table>
            <p style="margin-top: 20px; color: #666;">系统资源使用率过高，请及时检查。</p>
        </body>
        </html>
        """
        
        return self.send_email(admin_emails, subject, body, html_body)


# 全局实例
alert_manager = AlertManager()
