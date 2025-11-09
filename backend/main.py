"""
VUI Pro Panel - 完整后端系统
Version: 2.0.0
合并所有功能的完整版本 - 可直接使用

部署方式：
1. 保存此文件为 main.py
2. 安装依赖：pip install -r requirements.txt
3. 运行：python main.py
"""

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, JSON, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
import subprocess
import json
import os
import psutil
import qrcode
import io
import base64
import yaml
import uuid
import hashlib
import jwt
import asyncio
import secrets
import logging
from pathlib import Path

# ============= 配置 =============
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_hex(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE = 7

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./vui_pro.db")

BASE_DIR = Path("/opt/vui-pro")
DATA_DIR = BASE_DIR / "data"
BACKUP_DIR = BASE_DIR / "backups"
CERT_DIR = BASE_DIR / "certs"

XRAY_CONFIG = Path("/usr/local/etc/xray/config.json")
XRAY_BIN = Path("/usr/local/bin/xray")
HYSTERIA_CONFIG = Path("/etc/hysteria/config.yaml")
HYSTERIA_BIN = Path("/usr/local/bin/hysteria")

for dir_path in [DATA_DIR, BACKUP_DIR, CERT_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# ============= 数据库模型 =============
Base = declarative_base()
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Protocol(Base):
    __tablename__ = "protocols"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    type = Column(String(50), nullable=False)
    port = Column(Integer, nullable=False)
    status = Column(String(20), default="stopped")
    config = Column(JSON, nullable=False)
    enabled = Column(Boolean, default=True)
    traffic_total = Column(Float, default=0.0)
    user_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False)
    uuid = Column(String(36), default=lambda: str(uuid.uuid4()))
    password = Column(String(100))
    email = Column(String(100), nullable=True)
    protocol_ids = Column(JSON, default=list)
    traffic_limit = Column(Float, default=100.0)
    traffic_used = Column(Float, default=0.0)
    speed_limit = Column(Integer, default=100)
    expiry_date = Column(DateTime, nullable=True)
    status = Column(String(20), default="active")
    last_login = Column(DateTime, nullable=True)
    device_limit = Column(Integer, default=3)
    created_at = Column(DateTime, default=datetime.utcnow)

class AdminUser(Base):
    __tablename__ = "admin_users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    role = Column(String(20), default="admin")
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

# ============= Pydantic 模型 =============
class ProtocolCreate(BaseModel):
    name: str
    type: str
    port: int
    config: Dict[str, Any] = {}

class UserCreate(BaseModel):
    username: str
    password: Optional[str] = None
    protocol_ids: List[int] = []
    traffic_limit: float = 100
    speed_limit: int = 100
    expiry_days: Optional[int] = None
    device_limit: int = 3

class LoginRequest(BaseModel):
    username: str
    password: str

# ============= 工具函数 =============
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def get_server_ip() -> str:
    try:
        result = subprocess.run(["curl", "-s4", "ifconfig.me"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return result.stdout.strip()
    except:
        pass
    return "127.0.0.1"

async def run_command(cmd: List[str], timeout: int = 30) -> tuple:
    try:
        process = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        return process.returncode, stdout.decode(), stderr.decode()
    except:
        return -1, "", "Command failed"

# ============= 协议管理 =============
def generate_x25519_keypair() -> dict:
    try:
        if XRAY_BIN.exists():
            result = subprocess.run([str(XRAY_BIN), "x25519"], capture_output=True, text=True, timeout=5)
            lines = result.stdout.strip().split('\n')
            return {"private": lines[0].split(': ')[1], "public": lines[1].split(': ')[1]}
    except:
        pass
    return {"private": secrets.token_urlsafe(32), "public": secrets.token_urlsafe(32)}

def create_vless_config(port: int, custom: dict) -> dict:
    keys = generate_x25519_keypair()
    return {
        "log": {"loglevel": "warning"},
        "inbounds": [{
            "port": port,
            "protocol": "vless",
            "settings": {"clients": [], "decryption": "none"},
            "streamSettings": {
                "network": "tcp",
                "security": "reality",
                "realitySettings": {
                    "show": False,
                    "dest": custom.get("dest", "www.microsoft.com:443"),
                    "serverNames": [custom.get("serverName", "www.microsoft.com")],
                    "privateKey": keys["private"],
                    "publicKey": keys["public"],
                    "shortIds": ["", secrets.token_hex(8)]
                }
            }
        }],
        "outbounds": [{"protocol": "freedom", "tag": "direct"}]
    }

def create_hysteria2_config(port: int, custom: dict) -> dict:
    return {
        "listen": f":{port}",
        "auth": {"type": "password", "password": custom.get("password", secrets.token_urlsafe(16))},
        "masquerade": {
            "type": "proxy",
            "proxy": {"url": custom.get("masquerade_url", "https://news.ycombinator.com"), "rewriteHost": True}
        }
    }

def generate_vless_link(config: dict, user_uuid: str, server_ip: str) -> str:
    inbound = config["inbounds"][0]
    reality = inbound["streamSettings"]["realitySettings"]
    return f"vless://{user_uuid}@{server_ip}:{inbound['port']}?type=tcp&security=reality&sni={reality['serverNames'][0]}&pbk={reality['publicKey']}&flow=xtls-rprx-vision#VLESS-REALITY"

def generate_hysteria2_link(config: dict, server_ip: str) -> str:
    port = config["listen"].strip(":")
    return f"hysteria2://{config['auth']['password']}@{server_ip}:{port}#Hysteria2"

# ============= FastAPI 应用 =============
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("VUI Pro Panel 启动中...")
    db = SessionLocal()
    admin = db.query(AdminUser).filter(AdminUser.username == "admin").first()
    if not admin:
        admin = AdminUser(username="admin", password_hash=hash_password(os.getenv("ADMIN_PASSWORD", "admin")), role="admin")
        db.add(admin)
        db.commit()
        logger.info("默认管理员账号已创建")
    db.close()
    yield
    logger.info("VUI Pro Panel 关闭中...")

app = FastAPI(title="VUI Pro Panel API", version="2.0.0", lifespan=lifespan)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

security = HTTPBearer()

async def get_current_admin(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        admin = db.query(AdminUser).filter(AdminUser.username == payload.get("username")).first()
        if not admin:
            raise HTTPException(401, "管理员不存在")
        return admin
    except:
        raise HTTPException(401, "认证失败")

# ============= 认证 API =============
@app.post("/api/auth/login")
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    admin = db.query(AdminUser).filter(AdminUser.username == request.username).first()
    if not admin or admin.password_hash != hash_password(request.password):
        raise HTTPException(401, "用户名或密码错误")
    admin.last_login = datetime.utcnow()
    db.commit()
    token = create_access_token({"username": admin.username, "role": admin.role})
    return {"access_token": token, "token_type": "bearer", "expires_in": ACCESS_TOKEN_EXPIRE * 86400}

@app.get("/api/auth/me")
async def get_current_user_info(admin: AdminUser = Depends(get_current_admin)):
    return {"username": admin.username, "role": admin.role, "last_login": admin.last_login}

# ============= 系统 API =============
@app.get("/api/system/stats")
async def get_system_stats():
    cpu = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    net = psutil.net_io_counters()
    await asyncio.sleep(1)
    net2 = psutil.net_io_counters()
    return {
        "cpu": round(cpu, 1),
        "memory": {"total": round(memory.total/1024/1024/1024, 2), "used": round(memory.used/1024/1024/1024, 2), "percent": round(memory.percent, 1)},
        "disk": {"total": round(disk.total/1024/1024/1024, 2), "used": round(disk.used/1024/1024/1024, 2), "percent": round(disk.percent, 1)},
        "network": {"upload_speed": round((net2.bytes_sent-net.bytes_sent)/1024/1024*8, 2), "download_speed": round((net2.bytes_recv-net.bytes_recv)/1024/1024*8, 2)},
        "uptime": round((datetime.now()-datetime.fromtimestamp(psutil.boot_time())).total_seconds())
    }

@app.get("/api/system/info")
async def get_system_info():
    import platform
    return {
        "hostname": platform.node(),
        "os": f"{platform.system()} {platform.release()}",
        "cpu_count": psutil.cpu_count(),
        "python_version": platform.python_version(),
        "xray_installed": XRAY_BIN.exists(),
        "hysteria_installed": HYSTERIA_BIN.exists(),
        "server_ip": get_server_ip()
    }

# ============= 协议 API =============
@app.get("/api/protocols")
async def list_protocols(db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    return db.query(Protocol).all()

@app.post("/api/protocols")
async def create_protocol(protocol: ProtocolCreate, db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    if db.query(Protocol).filter(Protocol.port == protocol.port).first():
        raise HTTPException(400, f"端口 {protocol.port} 已被占用")
    if db.query(Protocol).filter(Protocol.name == protocol.name).first():
        raise HTTPException(400, f"名称 {protocol.name} 已存在")
    
    if protocol.type == "vless-reality":
        config = create_vless_config(protocol.port, protocol.config)
    elif protocol.type == "hysteria2":
        config = create_hysteria2_config(protocol.port, protocol.config)
    else:
        raise HTTPException(400, "不支持的协议类型")
    
    db_protocol = Protocol(name=protocol.name, type=protocol.type, port=protocol.port, config=config, status="stopped")
    db.add(db_protocol)
    db.commit()
    db.refresh(db_protocol)
    return db_protocol

@app.put("/api/protocols/{protocol_id}/toggle")
async def toggle_protocol(protocol_id: int, db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    protocol = db.query(Protocol).filter(Protocol.id == protocol_id).first()
    if not protocol:
        raise HTTPException(404, "协议不存在")
    
    protocol.status = "stopped" if protocol.status == "running" else "running"
    db.commit()
    return {"status": protocol.status, "message": "操作成功"}

@app.get("/api/protocols/{protocol_id}/link")
async def get_protocol_link(protocol_id: int, db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    protocol = db.query(Protocol).filter(Protocol.id == protocol_id).first()
    if not protocol:
        raise HTTPException(404, "协议不存在")
    
    server_ip = get_server_ip()
    users = db.query(User).filter(User.protocol_ids.contains([protocol_id])).all()
    links = []
    
    for user in users:
        if protocol.type == "vless-reality":
            link = generate_vless_link(protocol.config, user.uuid, server_ip)
        elif protocol.type == "hysteria2":
            link = generate_hysteria2_link(protocol.config, server_ip)
        else:
            link = ""
        links.append({"user_id": user.id, "username": user.username, "link": link})
    
    return {"links": links}

@app.get("/api/protocols/{protocol_id}/qrcode")
async def get_protocol_qrcode(protocol_id: int, user_id: Optional[int] = None, db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    protocol = db.query(Protocol).filter(Protocol.id == protocol_id).first()
    if not protocol:
        raise HTTPException(404, "协议不存在")
    
    users = [db.query(User).filter(User.id == user_id).first()] if user_id else db.query(User).filter(User.protocol_ids.contains([protocol_id])).all()
    server_ip = get_server_ip()
    qrcodes = []
    
    for user in users:
        if not user:
            continue
        if protocol.type == "vless-reality":
            link = generate_vless_link(protocol.config, user.uuid, server_ip)
        elif protocol.type == "hysteria2":
            link = generate_hysteria2_link(protocol.config, server_ip)
        else:
            continue
        
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(link)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        qrcodes.append({"user_id": user.id, "username": user.username, "qrcode": f"data:image/png;base64,{base64.b64encode(buffer.getvalue()).decode()}", "link": link})
    
    return {"qrcodes": qrcodes}

@app.delete("/api/protocols/{protocol_id}")
async def delete_protocol(protocol_id: int, db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    protocol = db.query(Protocol).filter(Protocol.id == protocol_id).first()
    if not protocol:
        raise HTTPException(404, "协议不存在")
    db.delete(protocol)
    db.commit()
    return {"message": "删除成功"}

# ============= 用户 API =============
@app.get("/api/users")
async def list_users(db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    return db.query(User).all()

@app.post("/api/users")
async def create_user(user: UserCreate, db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    if db.query(User).filter(User.username == user.username).first():
        raise HTTPException(400, f"用户名 {user.username} 已存在")
    
    expiry_date = datetime.utcnow() + timedelta(days=user.expiry_days) if user.expiry_days else None
    db_user = User(username=user.username, uuid=str(uuid.uuid4()), password=user.password or secrets.token_urlsafe(12), 
                   protocol_ids=user.protocol_ids, traffic_limit=user.traffic_limit, speed_limit=user.speed_limit, 
                   expiry_date=expiry_date, device_limit=user.device_limit, status="active")
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.get("/api/users/{user_id}")
async def get_user(user_id: int, db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "用户不存在")
    return user

@app.delete("/api/users/{user_id}")
async def delete_user(user_id: int, db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "用户不存在")
    db.delete(user)
    db.commit()
    return {"message": "删除成功"}

@app.get("/api/users/{user_id}/links")
async def get_user_links(user_id: int, db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "用户不存在")
    
    server_ip = get_server_ip()
    links = []
    
    for protocol_id in user.protocol_ids:
        protocol = db.query(Protocol).filter(Protocol.id == protocol_id).first()
        if not protocol:
            continue
        
        if protocol.type == "vless-reality":
            link = generate_vless_link(protocol.config, user.uuid, server_ip)
        elif protocol.type == "hysteria2":
            link = generate_hysteria2_link(protocol.config, server_ip)
        else:
            link = ""
        
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(link)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        
        links.append({"protocol_id": protocol.id, "protocol_name": protocol.name, "protocol_type": protocol.type, 
                     "link": link, "qrcode": f"data:image/png;base64,{base64.b64encode(buffer.getvalue()).decode()}"})
    
    return {"links": links}

# ============= 备份 API =============
@app.post("/api/backup")
async def create_backup(db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    import tarfile, shutil
    try:
        BACKUP_DIR.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"vui_backup_{timestamp}"
        backup_path = BACKUP_DIR / backup_name
        backup_tar = BACKUP_DIR / f"{backup_name}.tar.gz"
        
        backup_path.mkdir(exist_ok=True)
        db_file = Path("vui_pro.db")
        if db_file.exists():
            shutil.copy2(db_file, backup_path / "database.db")
        if XRAY_CONFIG.exists():
            shutil.copy2(XRAY_CONFIG, backup_path / "xray_config.json")
        if HYSTERIA_CONFIG.exists():
            shutil.copy2(HYSTERIA_CONFIG, backup_path / "hysteria_config.yaml")
        
        with tarfile.open(backup_tar, "w:gz") as tar:
            tar.add(backup_path, arcname=backup_name)
        shutil.rmtree(backup_path)
        
        return {"message": "备份创建成功", "file": backup_name, "size": round(backup_tar.stat().st_size/1024/1024, 2)}
    except Exception as e:
        raise HTTPException(500, f"备份失败: {e}")

@app.get("/api/backups")
async def list_backups(admin: AdminUser = Depends(get_current_admin)):
    if not BACKUP_DIR.exists():
        return []
    backups = []
    for file in BACKUP_DIR.glob("*.tar.gz"):
        stat = file.stat()
        backups.append({"filename": file.name, "size": round(stat.st_size/1024/1024, 2), "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat()})
    return sorted(backups, key=lambda x: x['created_at'], reverse=True)

# ============= 健康检查 =============
@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "2.0.0", "timestamp": datetime.utcnow().isoformat()}

@app.get("/")
async def root():
    return {"message": "VUI Pro Panel API", "version": "2.0.0", "docs": "/docs"}

# ============= 启动 =============
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
