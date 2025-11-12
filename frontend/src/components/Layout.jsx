import { Layout, Menu, Avatar, Dropdown, Space } from 'antd';
import {
  DashboardOutlined,
  ServerOutlined,
  UserOutlined,
  GlobeOutlined,
  ToolOutlined,
  SettingOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
} from '@ant-design/icons';
import { useNavigate, useLocation, Outlet } from 'react-router-dom';
import { useState } from 'react';
import '../styles/Layout.css';

export default function MainLayout({ user, onLogout }) {
  const navigate = useNavigate();
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(false);

  const menuItems = [
    { key: '/dashboard', icon: <DashboardOutlined />, label: '仪表盘' },
    { key: '/services', icon: <ServerOutlined />, label: '服务管理' },
    { key: '/users', icon: <UserOutlined />, label: '用户管理' },
    { key: '/domains', icon: <GlobeOutlined />, label: '域名证书' },
    { key: '/components', icon: <ToolOutlined />, label: '组件中心' },
    { key: '/settings', icon: <SettingOutlined />, label: '系统设置' },
  ];

  const userMenuItems = [
    {
      label: '修改密码',
      key: 'change-password',
      onClick: () => navigate('/change-password'),
    },
    {
      type: 'divider',
    },
    {
      label: '退出登录',
      key: 'logout',
      danger: true,
      onClick: onLogout,
    },
  ];

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Layout.Sider
        trigger={null}
        collapsible
        collapsed={collapsed}
        width={200}
        theme="dark"
        style={{
          overflow: 'auto',
          height: '100vh',
          position: 'fixed',
          left: 0,
          top: 0,
          bottom: 0,
        }}
      >
        <div className="logo">
          <h1>{collapsed ? 'A' : 'ATLAS'}</h1>
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={(e) => navigate(e.key)}
        />
      </Layout.Sider>

      <Layout style={{ marginLeft: collapsed ? 80 : 200 }}>
        <Layout.Header
          style={{
            background: '#fff',
            padding: '0 24px',
            boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <span
              className="layout-trigger"
              onClick={() => setCollapsed(!collapsed)}
            >
              {collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            </span>
            <h2 style={{ margin: 0, marginLeft: 16 }}>ATLAS 管理面板</h2>
          </div>
          <Dropdown menu={{ items: userMenuItems }}>
            <Space style={{ cursor: 'pointer' }}>
              <Avatar icon={<UserOutlined />} />
              <span>{user?.username}</span>
            </Space>
          </Dropdown>
        </Layout.Header>

        <Layout.Content style={{ padding: '24px', background: '#f0f2f5' }}>
          <Outlet />
        </Layout.Content>

        <Layout.Footer style={{ textAlign: 'center', color: '#999' }}>
          ATLAS ©2025. 企业级基础设施管理面板
        </Layout.Footer>
      </Layout>
    </Layout>
  );
}
