from pydantic import BaseModel, Field
from typing import Dict, Optional


class CPUStatsResponse(BaseModel):
    """CPU 统计"""
    usage_percent: float = Field(..., description="CPU使用率百分比")
    count: int = Field(..., description="CPU核心数")
    count_logical: int = Field(..., description="逻辑CPU数")


class MemoryStatsResponse(BaseModel):
    """内存统计"""
    total_gb: float = Field(..., description="总内存(GB)")
    available_gb: float = Field(..., description="可用内存(GB)")
    used_gb: float = Field(..., description="已用内存(GB)")
    percent: float = Field(..., description="使用率百分比")


class DiskStatsResponse(BaseModel):
    """磁盘统计"""
    total_gb: float = Field(..., description="总容量(GB)")
    used_gb: float = Field(..., description="已用容量(GB)")
    free_gb: float = Field(..., description="可用容量(GB)")
    percent: float = Field(..., description="使用率百分比")


class NetworkStatsResponse(BaseModel):
    """网络统计"""
    bytes_sent_gb: float = Field(..., description="发送数据(GB)")
    bytes_recv_gb: float = Field(..., description="接收数据(GB)")
    packets_sent: int = Field(..., description="发送包数")
    packets_recv: int = Field(..., description="接收包数")
    errin: int = Field(..., description="接收错误")
    errout: int = Field(..., description="发送错误")


class ProcessStatsResponse(BaseModel):
    """进程统计"""
    total_processes: int = Field(..., description="总进程数")
    process_count: int = Field(..., description="进程计数")


class UptimeStatsResponse(BaseModel):
    """运行时间统计"""
    uptime_seconds: int = Field(..., description="运行时间(秒)")
    uptime_days: int = Field(..., description="运行天数")
    uptime_hours: int = Field(..., description="运行小时")
    uptime_minutes: int = Field(..., description="运行分钟")
    boot_time: str = Field(..., description="启动时间")


class SystemStatsResponse(BaseModel):
    """完整系统统计"""
    timestamp: str = Field(..., description="时间戳")
    cpu: CPUStatsResponse
    memory: MemoryStatsResponse
    disk: DiskStatsResponse
    network: NetworkStatsResponse
    process: ProcessStatsResponse
    uptime: UptimeStatsResponse


class DashboardStatsResponse(BaseModel):
    """仪表盘统计"""
    timestamp: str
    services: Dict = Field(..., description="服务统计")
    users: Dict = Field(..., description="用户统计")
    traffic: Dict = Field(..., description="流量统计")
    system: SystemStatsResponse = Field(..., description="系统统计")


class HealthCheckResponse(BaseModel):
    """健康检查"""
    status: str = Field(..., description="系统状态: ok/warning")
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    warnings: Dict[str, bool] = Field(..., description="告警信息")
