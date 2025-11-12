import { useEffect, useState } from 'react';
import {
  Table,
  Button,
  Modal,
  Form,
  Input,
  Select,
  Switch,
  InputNumber,
  message,
  Space,
  Card,
  Row,
  Col,
  Tag,
  Tooltip,
  Alert,
  Statistic,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  SyncOutlined,
  WarningOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import { domainsAPI } from '../services/api';

export default function Domains() {
  const [domains, setDomains] = useState([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [pagination, setPagination] = useState({ current: 1, pageSize: 10 });
  const [stats, setStats] = useState(null);
  
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [form] = Form.useForm();

  useEffect(() => {
    fetchDomains();
    fetchStats();
  }, [pagination]);

  const fetchDomains = async () => {
    setLoading(true);
    try {
      const skip = (pagination.current - 1) * pagination.pageSize;
      const response = await domainsAPI.list(skip, pagination.pageSize);
      setDomains(response.data.items);
      setTotal(response.data.total);
    } catch (error) {
      message.error('获取域名列表失败');
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await domainsAPI.stats();
      setStats(response.data);
    } catch (error) {
      console.error('获取统计信息失败:', error);
    }
  };

  const handleCreateOrUpdate = async (values) => {
    try {
      if (editingId) {
        await domainsAPI.update(editingId, values);
        message.success('域名已更新');
      } else {
        await domainsAPI.create(values);
        message.success('域名已添加');
      }
      setIsModalVisible(false);
      form.resetFields();
      setEditingId(null);
      fetchDomains();
      fetchStats();
    } catch (error) {
      const errorMsg =
        error.response?.data?.detail ||
        error.response?.data?.message ||
        '操作失败';
      message.error(errorMsg);
    }
  };

  const handleDeleteDomain = (domainId) => {
    Modal.confirm({
      title: '删除域名',
      content: '确定要删除此域名吗？此操作不可撤销。',
      okText: '确定',
      cancelText: '取消',
      okType: 'danger',
      onOk: async () => {
        try {
          await domainsAPI.delete(domainId);
          message.success('域名已删除');
          fetchDomains();
          fetchStats();
        } catch (error) {
          message.error('删除失败');
        }
      },
    });
  };

  const handleShowModal = (record = null) => {
    if (record) {
      setEditingId(record.id);
      form.setFieldsValue({
        domain: record.domain,
        email: record.email,
        provider: record.provider,
        auto_renew: record.auto_renew,
        renew_before_days: record.renew_before_days,
      });
    } else {
      setEditingId(null);
      form.resetFields();
    }
    setIsModalVisible(true);
  };

  const getCertStatus = (record) => {
    if (!record.cert_valid_to) {
      return { color: 'default', text: '无证书', icon: '-' };
    }

    const now = new Date();
    const expiry = new Date(record.cert_valid_to);
    const daysRemaining = Math.ceil((expiry - now) / (1000 * 60 * 60 * 24));

    if (daysRemaining < 0) {
      return { color: 'red', text: '已过期', icon: '✗', days: 0 };
    } else if (daysRemaining < 30) {
      return { color: 'orange', text: '即将过期', icon: '⚠️', days: daysRemaining };
    } else {
      return { color: 'green', text: '有效', icon: '✓', days: daysRemaining };
    }
  };

  const columns = [
    {
      title: '域名',
      dataIndex: 'domain',
      key: 'domain',
      width: 150,
      ellipsis: true,
    },
    {
      title: '邮箱',
      dataIndex: 'email',
      key: 'email',
      width: 180,
      ellipsis: true,
    },
    {
      title: '证书提供商',
      dataIndex: 'provider',
      key: 'provider',
      width: 120,
      render: (provider) => provider || '独立',
    },
    {
      title: '证书状态',
      dataIndex: 'cert_valid_to',
      key: 'cert_status',
      width: 150,
      render: (_, record) => {
        const status = getCertStatus(record);
        return (
          <Tooltip
            title={
              status.days
                ? `${status.days} 天后过期`
                : record.cert_valid_to
                ? '已过期'
                : '无证书'
            }
          >
            <Tag color={status.color}>{status.icon} {status.text}</Tag>
          </Tooltip>
        );
      },
    },
    {
      title: '自动续期',
      dataIndex: 'auto_renew',
      key: 'auto_renew',
      width: 100,
      render: (autoRenew) => (
        <Tag color={autoRenew ? 'green' : 'red'}>
          {autoRenew ? '启用' : '禁用'}
        </Tag>
      ),
    },
    {
      title: '续期天数',
      dataIndex: 'renew_before_days',
      key: 'renew_before_days',
      width: 100,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (date) => new Date(date).toLocaleString('zh-CN'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 180,
      fixed: 'right',
      render: (_, record) => (
        <Space wrap>
          <Tooltip title="编辑">
            <Button
              size="small"
              icon={<EditOutlined />}
              onClick={() => handleShowModal(record)}
            />
          </Tooltip>

          <Tooltip title="删除">
            <Button
              size="small"
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDeleteDomain(record.id)}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  return (
    <div>
      {/* 统计卡片 */}
      {stats && (
        <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="总域名数"
                value={stats.total}
                valueStyle={{ color: '#1890ff' }}
              />
            </Card>
          </Col>

          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="有效域名"
                value={stats.active}
                valueStyle={{ color: '#52c41a' }}
              />
            </Card>
          </Col>

          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="即将过期"
                value={stats.expiring_soon}
                valueStyle={{ color: '#faad14' }}
                prefix={<WarningOutlined />}
              />
            </Card>
          </Col>

          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="已过期"
                value={stats.expired}
                valueStyle={{ color: '#ff4d4f' }}
              />
            </Card>
          </Col>
        </Row>
      )}

      {/* 告警信息 */}
      {stats && stats.expired > 0 && (
        <Alert
          message="有已过期的域名，建议立即更新证书"
          type="error"
          showIcon
          style={{ marginBottom: 24 }}
        />
      )}

      {stats && stats.expiring_soon > 0 && (
        <Alert
          message={`有 ${stats.expiring_soon} 个域名证书即将过期`}
          type="warning"
          showIcon
          style={{ marginBottom: 24 }}
        />
      )}

      <Card>
        <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
          <Col>
            <h2>域名证书管理</h2>
          </Col>
          <Col>
            <Space>
              <Button
                icon={<SyncOutlined />}
                onClick={() => {
                  fetchDomains();
                  fetchStats();
                }}
                loading={loading}
              >
                刷新
              </Button>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => handleShowModal()}
              >
                添加域名
              </Button>
            </Space>
          </Col>
        </Row>

        <Table
          columns={columns}
          dataSource={domains}
          rowKey="id"
          loading={loading}
          scroll={{ x: 1200 }}
          pagination={{
            current: pagination.current,
            pageSize: pagination.pageSize,
            total: total,
            showSizeChanger: true,
            pageSizeOptions: ['10', '20', '50'],
            showTotal: (total) => `共 ${total} 个域名`,
            onChange: (page, pageSize) => {
              setPagination({ current: page, pageSize });
            },
          }}
        />
      </Card>

      <Modal
        title={editingId ? '编辑域名' : '添加域名'}
        open={isModalVisible}
        onOk={() => form.submit()}
        onCancel={() => {
          setIsModalVisible(false);
          form.resetFields();
          setEditingId(null);
        }}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleCreateOrUpdate}
        >
          <Form.Item
            name="domain"
            label="域名"
            rules={[
              { required: true, message: '请输入域名' },
              { min: 1, max: 100, message: '域名长度 1-100 字符' },
            ]}
          >
            <Input
              placeholder="例如：example.com"
              disabled={!!editingId}
            />
          </Form.Item>

          <Form.Item
            name="email"
            label="邮箱地址"
            rules={[
              { required: true, message: '请输入邮箱' },
              { type: 'email', message: '请输入有效的邮箱地址' },
            ]}
          >
            <Input placeholder="用于证书相关通知" />
          </Form.Item>

          <Form.Item
            name="provider"
            label="证书提供商"
            initialValue="standalone"
          >
            <Select
              options={[
                { label: '独立管理', value: 'standalone' },
                { label: 'Let\\'s Encrypt', value: 'letsencrypt' },
                { label: '阿里云', value: 'aliyun' },
                { label: '腾讯云', value: 'tencentcloud' },
              ]}
            />
          </Form.Item>

          <Form.Item
            name="auto_renew"
            label="自动续期"
            initialValue={true}
            valuePropName="checked"
          >
            <Switch />
          </Form.Item>

          <Form.Item
            name="renew_before_days"
            label="提前续期天数"
            initialValue={30}
          >
            <InputNumber min={1} max={90} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
