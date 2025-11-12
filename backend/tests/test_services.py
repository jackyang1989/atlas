import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app.services.auth_service import AuthService

SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def test_db():
    """创建测试数据库"""
    engine = create_engine(
        SQLALCHEMY_TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    AuthService.create_default_admin(db)
    
    def override_get_db():
        yield db
    
    app.dependency_overrides[get_db] = override_get_db
    yield db
    db.close()


@pytest.fixture
def client(test_db):
    """创建测试客户端"""
    return TestClient(app)


@pytest.fixture
def auth_token(client):
    """获取认证 token"""
    response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123"}
    )
    return response.json()["access_token"]


class TestServices:
    """服务管理测试类"""
    
    def test_create_service(self, client, auth_token):
        """测试创建服务"""
        response = client.post(
            "/api/services/",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "name": "VLESS_Test",
                "protocol": "vless",
                "port": 9001,
                "cert_domain": "example.com"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "VLESS_Test"
        assert data["port"] == 9001
        assert data["status"] == "stopped"
        assert data["protocol"] == "vless"
    
    def test_create_service_port_conflict(self, client, auth_token):
        """测试端口冲突检测"""
        # 创建第一个服务
        client.post(
            "/api/services/",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "name": "Service1",
                "protocol": "vless",
                "port": 9002,
                "cert_domain": "example.com"
            }
        )
        
        # 尝试创建相同端口的服务
        response = client.post(
            "/api/services/",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "name": "Service2",
                "protocol": "vless",
                "port": 9002,
                "cert_domain": "example.com"
            }
        )
        assert response.status_code == 400
        assert "已被占用" in response.json()["detail"]
    
    def test_create_service_duplicate_name(self, client, auth_token):
        """测试服务名重复检测"""
        # 创建第一个服务
        client.post(
            "/api/services/",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "name": "DuplicateName",
                "protocol": "vless",
                "port": 9003,
                "cert_domain": "example.com"
            }
        )
        
        # 尝试创建相同名称的服务
        response = client.post(
            "/api/services/",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "name": "DuplicateName",
                "protocol": "vless",
                "port": 9004,
                "cert_domain": "example.com"
            }
        )
        assert response.status_code == 400
        assert "已存在" in response.json()["detail"]
    
    def test_create_vless_without_domain(self, client, auth_token):
        """测试 VLESS 缺少域名"""
        response = client.post(
            "/api/services/",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "name": "NodomainVLESS",
                "protocol": "vless",
                "port": 9005,
            }
        )
        assert response.status_code == 400
        assert "需要指定证书域名" in response.json()["detail"]
    
    def test_create_hysteria2_service(self, client, auth_token):
        """测试创建 Hysteria2 服务"""
        response = client.post(
            "/api/services/",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "name": "Hysteria2_Test",
                "protocol": "hysteria2",
                "port": 9006,
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["protocol"] == "hysteria2"
        assert data["status"] == "stopped"
    
    def test_list_services(self, client, auth_token):
        """测试列表服务"""
        # 创建多个服务
        for i in range(3):
            client.post(
                "/api/services/",
                headers={"Authorization": f"Bearer {auth_token}"},
                json={
                    "name": f"Service{i}",
                    "protocol": "hysteria2",
                    "port": 9100 + i,
                }
            )
        
        # 获取列表
        response = client.get(
            "/api/services/",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3
    
    def test_list_services_pagination(self, client, auth_token):
        """测试服务列表分页"""
        # 创建 15 个服务
        for i in range(15):
            client.post(
                "/api/services/",
                headers={"Authorization": f"Bearer {auth_token}"},
                json={
                    "name": f"PaginationService{i}",
                    "protocol": "hysteria2",
                    "port": 10000 + i,
                }
            )
        
        # 获取第一页（默认 10 条）
        response = client.get(
            "/api/services/?skip=0&limit=10",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 15
        assert len(data["items"]) == 10
        
        # 获取第二页
        response = client.get(
            "/api/services/?skip=10&limit=10",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 5
    
    def test_get_service(self, client, auth_token):
        """测试获取服务详情"""
        # 创建服务
        create_response = client.post(
            "/api/services/",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "name": "GetServiceTest",
                "protocol": "hysteria2",
                "port": 9200,
            }
        )
        service_id = create_response.json()["id"]
        
        # 获取服务详情
        response = client.get(
            f"/api/services/{service_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == service_id
        assert data["name"] == "GetServiceTest"
    
    def test_get_nonexistent_service(self, client, auth_token):
        """测试获取不存在的服务"""
        response = client.get(
            "/api/services/nonexistent-id",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 404
    
    def test_update_service(self, client, auth_token):
        """测试更新服务"""
        # 创建服务
        create_response = client.post(
            "/api/services/",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "name": "UpdateTest",
                "protocol": "hysteria2",
                "port": 9300,
            }
        )
        service_id = create_response.json()["id"]
        
        # 更新服务
        response = client.put(
            f"/api/services/{service_id}",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "name": "UpdatedName",
                "tags": '["HK"]'
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "UpdatedName"
        assert data["tags"] == '["HK"]'
    
    def test_toggle_service(self, client, auth_token):
        """测试启停服务"""
        # 创建服务
        create_response = client.post(
            "/api/services/",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "name": "ToggleTest",
                "protocol": "hysteria2",
                "port": 9400,
            }
        )
        service_id = create_response.json()["id"]
        
        # 启动服务
        response = client.put(
            f"/api/services/{service_id}/toggle",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        assert response.json()["status"] == "running"
        
        # 停止服务
        response = client.put(
            f"/api/services/{service_id}/toggle",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        assert response.json()["status"] == "stopped"
    
    def test_delete_service(self, client, auth_token):
        """测试删除服务"""
        # 创建服务
        create_response = client.post(
            "/api/services/",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "name": "DeleteTest",
                "protocol": "hysteria2",
                "port": 9500,
            }
        )
        service_id = create_response.json()["id"]
        
        # 删除服务
        response = client.delete(
            f"/api/services/{service_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 204
        
        # 验证服务已删除
        response = client.get(
            f"/api/services/{service_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 404
    
    def test_unauthorized_access(self, client):
        """测试未授权访问"""
        response = client.get("/api/services/")
        assert response.status_code == 403
    
    def test_invalid_protocol(self, client, auth_token):
        """测试无效的协议"""
        response = client.post(
            "/api/services/",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "name": "InvalidProtocol",
                "protocol": "invalid",
                "port": 9600,
            }
        )
        assert response.status_code == 422
