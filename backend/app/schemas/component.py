from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime


class ComponentBase(BaseModel):
    """组件基础字段"""
    name: str = Field(..., min_length=1, max_length=100, description="组件名称")
    type: str = Field(..., description="组件类型: proxy, tool")
    version: str = Field(..., description="当前版本")


class ComponentCreate(ComponentBase):
    """创建组件"""
    install_method: str = Field(..., description="安装方式: binary, docker, script")
    install_url: Optional[str] = Field(None, description="安装 URL")


class ComponentUpdate(BaseModel):
    """更新组件"""
    status: Optional[str] = None
    version: Optional[str] = None
    latest_version: Optional[str] = None


class ComponentResponse(ComponentBase):
    """组件响应"""
    id: str
    latest_version: Optional[str]
    status: str
    installed_path: Optional[str]
    service_name: Optional[str]
    install_method: str
    sha256_checksum: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class ComponentListResponse(BaseModel):
    """组件列表响应"""
    total: int
    items: List[ComponentResponse]


class ComponentInstallRequest(BaseModel):
    """安装组件请求"""
    force: bool = Field(False, description="强制重新安装")


class ComponentVersionCheckResponse(BaseModel):
    """版本检查响应"""
    current_version: str
    latest_version: str
    update_available: bool
    changelog: Optional[str] = None


# 备份相关 Schema
class BackupCreate(BaseModel):
    """创建备份请求"""
    include_data: bool = Field(True, description="包含数据")
    include_config: bool = Field(True, description="包含配置")
    description: Optional[str] = Field(None, max_length=255, description="备份描述")


class BackupResponse(BaseModel):
    """备份响应"""
    filename: str
    size_mb: float
    created_at: str
    description: Optional[str]


class BackupListResponse(BaseModel):
    """备份列表响应"""
    total: int
    items: List[BackupResponse]


class BackupRestoreRequest(BaseModel):
    """恢复备份请求"""
    filename: str = Field(..., description="备份文件名")
    force: bool = Field(False, description="强制恢复")


# 告警相关 Schema
class AlertTestRequest(BaseModel):
    """测试告警请求"""
    email: str = Field(..., description="测试邮箱地址")


class AlertSendRequest(BaseModel):
    """发送告警请求"""
    type: str = Field(..., description="告警类型")
    params: Dict = Field(..., description="告警参数")
    recipients: List[str] = Field(..., description="接收人邮箱列表")
