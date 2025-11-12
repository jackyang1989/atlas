import { useEffect, useState } from 'react';
import { Row, Col, Card, Statistic, Spin, message } from 'antd';
import {
  ServerOutlined,
  UserOutlined,
  DatabaseOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { systemAPI } from '../services/api';
import '../styles/Dashboard.css';

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      // 这个端点将在后续实现
      // const response = await systemAPI.stats();
      // setStats(response.data);
      
      // 临时数据用于展示
      setStats({
        cpu_percent: 24.5,
        memory_percent: 45.2,
        disk_percent: 32.1,
        service_count: 3,
        user_count: 12,
      });
    } catch (error) {
      message.error('获取系统信息失败');
      console.error('Error:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin tip="加载中..." />
      </div>
    );
  }

  return (
    <div className="dashboard-container">
      <h2>系统概览</h2>
      <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="CPU 使用率"
              value={stats?.cpu_percent || 0}
              prefix={<ThunderboltOutlined />}
              suffix="%"
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="内存使用率"
              value={stats?.memory_percent || 0}
              prefix={<DatabaseOutlined />}
              suffix="%"
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="磁盘使用率"
              value={stats?.disk_percent || 0}
              prefix={<DatabaseOutlined />}
              suffix="%"
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="活跃用户"
              value={stats?.user_count || 0}
              prefix={<UserOutlined />}
              valueStyle={{ color: '#f5222d' }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
        <Col xs={24} lg={12}>
          <Card>
            <h3>运行中的服务</h3>
            <Statistic
              value={stats?.service_count || 0}
              prefix={<ServerOutlined />}
              valueStyle={{ color: '#1890ff', fontSize: '28px' }}
            />
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card>
            <h3>系统信息</h3>
            <p>项目版本: v1.0.0</p>
            <p>运行状态: 正常</p>
            <p>最后更新: {new Date().toLocaleString()}</p>
          </Card>
        </Col>
      </Row>
    </div>
  );
}
