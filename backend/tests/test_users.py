import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta

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


class TestUsers:
    """用户管理测试类"""
    
    def test_create_user(self, client, auth_token):
        """测试创建用户"""
        response = client.post(
            "/api/users/",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "username": "testuser",
                "traffic_limit_gb": 100,
                "speed_limit_kbps": 1024,
                "device_limit": 5,
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "testuser"
        assert data["status"] == "active"
        assert data["traffic_limit_gb"] == 100
        assert "uuid" in data
    
    def test_create_user_duplicate_username(self, client, auth_token):
        """测试重复用户名"""
        # 创建第一个用户
        client.post(
            "/api/users/",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"username": "duplicate"}
        )
        
        # 尝试创建相同用户名
        response = client.post(
            "/api/users/",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"username": "duplicate"}
        )
        assert response.status_code == 400
        assert "已存在" in response.json()["detail"]
    
    def test_list_users(self, client, auth_token):
        """测试列表用户"""
        # 创建多个用户
        for i in range(3):
            client.post(
                "/api/users/",
                headers={"Authorization": f"Bearer {auth_token}"},
                json={"username": f"user{i}"}
            )
        
        # 获取列表
        response = client.get(
            "/api/users/",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3
    
    def test_list_users_pagination(self, client, auth_token):
        """测试用户列表分页"""
        # 创建 15 个用户
        for i in range(15):
            client.post(
                "/api/users/",
                headers={"Authorization": f"Bearer {auth_token}"},
                json={"username": f"pageuser{i}"}
            )
        
        # 获取第一页
        response = client.get(
            "/api/users/?skip=0&limit=10",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 15
        assert len(data["items"]) == 10
        
        # 获取第二页
        response = client.get(
            "/api/users/?skip=10&limit=10",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 5
    
    def test_get_user(self, client, auth_token):
        """测试获取用户详情"""
        # 创建用户
        create_response = client.post(
            "/api/users/",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "username": "gettest",
                "traffic_limit_gb": 50,
            }
        )
        user_id = create_response.json()["id"]
        
        # 获取用户
        response = client.get(
            f"/api/users/{user_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "gettest"
        assert data["traffic_limit_gb"] == 50
    
    def test_update_user(self, client, auth_token):
        """测试更新用户"""
        # 创建用户
        create_response = client.post(
            "/api/users/",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"username": "updatetest"}
        )
        user_id = create_response.json()["id"]
        
        # 更新用户
        response = client.put(
            f"/api/users/{user_id}",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "traffic_limit_gb": 200,
                "speed_limit_kbps": 2048,
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["traffic_limit_gb"] == 200
        assert data["speed_limit_kbps"] == 2048
    
    def test_add_traffic(self, client, auth_token):
        """测试增加流量"""
        # 创建用户
        create_response = client.post(
            "/api/users/",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "username": "traffictest",
                "traffic_limit_gb": 100,
            }
        )
        user_id = create_response.json()["id"]
        
        # 增加流量
        response = client.post(
            f"/api/users/{user_id}/traffic",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"traffic_gb": 50}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["traffic_used_gb"] == 50
    
    def test_traffic_over_quota(self, client, auth_token):
        """测试流量超限"""
        # 创建用户
        create_response = client.post(
            "/api/users/",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "username": "overquota",
                "traffic_limit_gb": 100,
            }
        )
        user_id = create_response.json()["id"]
        
        # 增加超过限制的流量
        response = client.post(
            f"/api/users/{user_id}/traffic",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"traffic_gb": 100}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "over_quota"
    
    def test_reset_traffic(self, client, auth_token):
        """测试重置流量"""
        # 创建用户
        create_response = client.post(
            "/api/users/",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "username": "resettest",
                "traffic_limit_gb": 100,
            }
        )
        user_id = create_response.json()["id"]
        
        # 增加流量
        client.post(
            f"/api/users/{user_id}/traffic",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"traffic_gb": 50}
        )
        
        # 重置流量
        response = client.post(
            f"/api/users/{user_id}/traffic/reset",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["traffic_used_gb"] == 0
    
    def test_set_service_ids(self, client, auth_token):
        """测试设置用户服务"""
        # 创建用户
        create_response = client.post(
            "/api/users/",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"username": "servicetest"}
        )
        user_id = create_response.json()["id"]
        
        # 设置服务
        response = client.put(
            f"/api/users/{user_id}/services",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "service_ids": ["service1", "service2"]
            }
        )
        assert response.status_code == 200
    
    def test_enable_disable_user(self, client, auth_token):
        """测试启用/禁用用户"""
        # 创建用户
        create_response = client.post(
            "/api/users/",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"username": "statustest"}
        )
        user_id = create_response.json()["id"]
        
        # 禁用用户
        response = client.post(
            f"/api/users/{user_id}/disable",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        assert response.json()["status"] == "disabled"
        
        # 启用用户
        response = client.post(
            f"/api/users/{user_id}/enable",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        assert response.json()["status"] == "active"
    
    def test_get_user_config(self, client, auth_token):
        """测试获取用户配置"""
        # 创建用户
        create_response = client.post(
            "/api/users/",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "username": "configtest",
                "traffic_limit_gb": 100,
                "speed_limit_kbps": 1024,
            }
        )
        user_id = create_response.json()["id"]
        
        # 获取配置
        response = client.get(
            f"/api/users/{user_id}/config",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "configtest"
        assert data["traffic_limit_gb"] == 100
        assert "uuid" in data
    
    def test_delete_user(self, client, auth_token):
        """测试删除用户"""
        # 创建用户
        create_response = client.post(
            "/api/users/",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"username": "deletetest"}
        )
        user_id = create_response.json()["id"]
        
        # 删除用户
        response = client.delete(
            f"/api/users/{user_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 204
        
        # 验证用户已删除
        response = client.get(
            f"/api/users/{user_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 404
    
    def test_unauthorized_access(self, client):
        """测试未授权访问"""
        response = client.get("/api/users/")
        assert response.status_code == 403
