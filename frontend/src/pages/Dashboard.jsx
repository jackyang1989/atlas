import { useEffect, useState } from 'react';
import {
  Row,
  Col,
  Card,
  Statistic,
  Spin,
  message,
  Progress,
  Divider,
  Space,
  Alert,
  Tag,
} from 'antd';
import {
  ServerOutlined,
  UserOutlined,
  DatabaseOutlined,
  ThunderboltOutlined,
  CloudOutlined,
  CheckCircleOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import { systemAPI } from '../services/api';
import '../styles/Dashboard.css';

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [health, setHealth] = useState(null);

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 30000); // 每30秒刷新
    return () => clearInterval(interval);
  }, []);

  const fetchStats = async () => {
    try {
      // 获取完整仪表盘数据
      const response = await systemAPI.stats();
      setStats(response.data);
      
      // 获取健康检查信息
      const healthResponse = await systemAPI.health();
      setHealth(healthResponse.data);
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

  const getHealthStatus = () => {
    if (!health) return null;
    
    return health.status === 'ok' ? (
      <Alert
        message="系统状态正常"
        type="success"
        icon={<CheckCircleOutlined />}
        showIcon
      />
    ) : (
      <Alert
        message="系统存在告警"
        type="warning"
        icon={<WarningOutlined />}
        description={`CPU: ${health.warnings.cpu ? '⚠️' : '✓'} 内存: ${health.warnings.memory ? '⚠️' : '✓'} 磁盘: ${health.warnings.disk ? '⚠️' : '✓'}`}
        showIcon
      />
    );
  };

  return (
    <div className="dashboard-container">
      <h2>系统仪表盘</h2>

      {/* 系统健康状态 */}
      <div style={{ marginBottom: 24 }}>
        {getHealthStatus()}
      </div>

      {/* 服务和用户概览 */}
      <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="运行中的服务"
              value={stats?.services?.running || 0}
              prefix={<ServerOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="活跃用户"
              value={stats?.users?.active || 0}
              prefix={<UserOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="总流量使用"
              value={stats?.traffic?.used_gb || 0}
              suffix="GB"
              prefix={<CloudOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="流量使用率"
              value={stats?.traffic?.usage_percent || 0}
              suffix="%"
              valueStyle={{ color: '#f5222d' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 系统资源使用 */}
      <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
        <Col xs={24} lg={8}>
          <Card title="CPU 使用率">
            <Progress
              type="circle"
              percent={Math.round(stats?.system?.cpu?.usage_percent || 0)}
              status={stats?.system?.cpu?.usage_percent > 80 ? 'exception' : 'normal'}
            />
            <p style={{ marginTop: 16, textAlign: 'center', color: '#666' }}>
              {stats?.system?.cpu?.count} 个核心
            </p>
          </Card>
        </Col>

        <Col xs={24} lg={8}>
          <Card title="内存使用率">
            <Progress
              type="circle"
              percent={Math.round(stats?.system?.memory?.percent || 0)}
              status={stats?.system?.memory?.percent > 80 ? 'exception' : 'normal'}
            />
            <p style={{ marginTop: 16, textAlign: 'center', color: '#666' }}>
              {stats?.system?.memory?.used_gb}GB / {stats?.system?.memory?.total_gb}GB
            </p>
          </Card>
        </Col>

        <Col xs={24} lg={8}>
          <Card title="磁盘使用率">
            <Progress
              type="circle"
              percent={Math.round(stats?.system?.disk?.percent || 0)}
              status={stats?.system?.disk?.percent > 80 ? 'exception' : 'normal'}
            />
            <p style={{ marginTop: 16, textAlign: 'center', color: '#666' }}>
              {stats?.system?.disk?.used_gb}GB / {stats?.system?.disk?.total_gb}GB
            </p>
          </Card>
        </Col>
      </Row>

      {/* 详细信息 */}
      <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
        <Col xs={24} lg={12}>
          <Card title="服务统计">
            <Row gutter={[16, 16]}>
              <Col xs={12}>
                <Statistic
                  title="总服务数"
                  value={stats?.services?.total || 0}
                  valueStyle={{ fontSize: '24px', color: '#1890ff' }}
                />
              </Col>
              <Col xs={12}>
                <Statistic
                  title="已停止"
                  value={stats?.services?.stopped || 0}
                  valueStyle={{ fontSize: '24px', color: '#f5222d' }}
                />
              </Col>
            </Row>
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card title="用户统计">
            <Space direction="vertical" style={{ width: '100%' }}>
              <div>
                <span>总用户数: </span>
                <Tag color="blue">{stats?.users?.total || 0}</Tag>
              </div>
              <div>
                <span>活跃: </span>
                <Tag color="green">{stats?.users?.distribution?.active || 0}</Tag>
                <span style={{ marginLeft: 16 }}>禁用: </span>
                <Tag color="red">{stats?.users?.distribution?.disabled || 0}</Tag>
              </div>
              <div>
                <span>已过期: </span>
                <Tag color="orange">{stats?.users?.distribution?.expired || 0}</Tag>
                <span style={{ marginLeft: 16 }}>超配额: </span>
                <Tag color="volcano">{stats?.users?.distribution?.over_quota || 0}</Tag>
              </div>
            </Space>
          </Card>
        </Col>
      </Row>

      {/* 系统信息 */}
      <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
        <Col xs={24}>
          <Card title="系统信息">
            <Row gutter={[16, 16]}>
              <Col xs={24} sm={12} lg={6}>
                <Statistic
                  title="运行时间"
                  value={stats?.system?.uptime?.uptime_days || 0}
                  suffix="天"
                />
              </Col>
              <Col xs={24} sm={12} lg={6}>
                <Statistic
                  title="总进程数"
                  value={stats?.system?.process?.total_processes || 0}
                />
              </Col>
              <Col xs={24} sm={12} lg={6}>
                <Statistic
                  title="数据接收"
                  value={stats?.system?.network?.bytes_recv_gb || 0}
                  suffix="GB"
                />
              </Col>
              <Col xs={24} sm={12} lg={6}>
                <Statistic
                  title="数据发送"
                  value={stats?.system?.network?.bytes_sent_gb || 0}
                  suffix="GB"
                />
              </Col>
            </Row>
            <Divider />
            <p style={{ color: '#999', fontSize: '12px' }}>
              最后更新: {new Date(stats?.timestamp).toLocaleString('zh-CN')}
            </p>
          </Card>
        </Col>
      </Row>
    </div>
  );
}
