import { useEffect, useState } from 'react';
import {
  Table,
  Button,
  Modal,
  Form,
  Input,
  InputNumber,
  Select,
  DatePicker,
  message,
  Space,
  Card,
  Row,
  Col,
  Tag,
  Tooltip,
  Drawer,
  Statistic,
  Progress,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  CopyOutlined,
  LockOutlined,
  UnlockOutlined,
  ReloadOutlined,
  EyeOutlined,
  ClearOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { usersAPI } from '../services/api';
import '../styles/Users.css';

export default function Users() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [pagination, setPagination] = useState({ current: 1, pageSize: 10 });
  const [statusFilter, setStatusFilter] = useState(null);
  
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [form] = Form.useForm();
  
  const [detailDrawer, setDetailDrawer] = useState(false);
  const [selectedUser, setSelectedUser] = useState(null);

  useEffect(() => {
    fetchUsers();
  }, [pagination, statusFilter]);

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const skip = (pagination.current - 1) * pagination.pageSize;
      const response = await usersAPI.list(skip, pagination.pageSize, statusFilter);
      setUsers(response.data.items);
      setTotal(response.data.total);
    } catch (error) {
      message.error('获取用户列表失败');
      console.error('Error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateOrUpdate = async (values) => {
    try {
      const payload = { ...values };
      if (payload.expiry_date) {
        payload.expiry_date = payload.expiry_date.toISOString();
      }
      
      if (editingId) {
        await usersAPI.update(editingId, payload);
        message.success('用户已更新');
      } else {
        await usersAPI.create(payload);
        message.success('用户创建成功');
      }
      setIsModalVisible(false);
      form.resetFields();
      setEditingId(null);
      fetchUsers();
    } catch (error) {
      const errorMsg =
        error.response?.data?.detail ||
        error.response?.data?.message ||
        '操作失败';
      message.error(errorMsg);
    }
  };

  const handleToggleUser = async (userId, currentStatus) => {
    try {
      if (currentStatus === 'disabled') {
        await usersAPI.enable(userId);
        message.success('用户已启用');
      } else {
        await usersAPI.disable(userId);
        message.success('用户已禁用');
      }
      fetchUsers();
    } catch (error) {
      message.error('操作失败');
    }
  };

  const handleDeleteUser = (userId) => {
    Modal.confirm({
      title: '删除用户',
      content: '确定要删除此用户吗？此操作不可撤销。',
      okText: '确定',
      cancelText: '取消',
      okType: 'danger',
      onOk: async () => {
        try {
          await usersAPI.delete(userId);
          message.success('用户已删除');
          fetchUsers();
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
        username: record.username,
        traffic_limit_gb: record.traffic_limit_gb,
        speed_limit_kbps: record.speed_limit_kbps,
        device_limit: record.device_limit,
        expiry_date: record.expiry_date ? dayjs(record.expiry_date) : null,
        preferred_regions: record.preferred_regions,
        notes: record.notes,
      });
    } else {
      setEditingId(null);
      form.resetFields();
    }
    setIsModalVisible(true);
  };

  const handleCopyUUID = (uuid) => {
    navigator.clipboard.writeText(uuid);
    message.success('UUID 已复制');
  };

  const handleShowDetails = async (userId) => {
    try {
      const response = await usersAPI.getConfig(userId);
      setSelectedUser(response.data);
      setDetailDrawer(true);
    } catch (error) {
      message.error('获取用户配置失败');
    }
  };

  const handleResetTraffic = async (userId) => {
    Modal.confirm({
      title: '重置流量',
      content: '确定要重置此用户的流量吗？',
      okText: '确定',
      cancelText: '取消',
      onOk: async () => {
        try {
          await usersAPI.resetTraffic(userId);
          message.success('流量已重置');
          fetchUsers();
        } catch (error) {
          message.error('重置失败');
        }
      },
    });
  };

  const columns = [
    {
      title: '用户名',
      dataIndex: 'username',
      key: 'username',
      width: 120,
      ellipsis: true,
    },
    {
      title: 'UUID',
      dataIndex: 'uuid',
      key: 'uuid',
      width: 180,
      render: (uuid) => (
        <Tooltip title="点击复制">
          <span
            className="user-uuid"
            onClick={() => handleCopyUUID(uuid)}
            style={{ cursor: 'pointer' }}
          >
            {uuid.substring(0, 12)}...
          </span>
        </Tooltip>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status) => {
        const colors = {
          active: 'green',
          disabled: 'red',
          expired: 'orange',
          over_quota: 'volcano',
        };
        const labels = {
          active: '活跃',
          disabled: '禁用',
          expired: '已过期',
          over_quota: '超配额',
        };
        return <Tag color={colors[status] || 'default'}>{labels[status] || status}</Tag>;
      },
    },
    {
      title: '流量使用',
      dataIndex: 'traffic_used_gb',
      key: 'traffic',
      width: 150,
      render: (_, record) => {
        const used = record.traffic_used_gb || 0;
        const limit = record.traffic_limit_gb || 0;
        const percentage = limit > 0 ? (used / limit) * 100 : 0;
        
        if (limit === 0) {
          return <span className="traffic-info">无限制</span>;
        }
        
        return (
          <Tooltip title={`${used}GB / ${limit}GB`}>
            <Progress
              percent={Math.min(100, percentage)}
              size="small"
              status={percentage >= 100 ? 'exception' : percentage >= 80 ? 'normal' : 'success'}
            />
          </Tooltip>
        );
      },
    },
    {
      title: '设备限制',
      dataIndex: 'device_limit',
      key: 'device_limit',
      width: 100,
      render: (limit) => limit === 0 ? '无限制' : limit,
    },
    {
      title: '过期时间',
      dataIndex: 'expiry_date',
      key: 'expiry_date',
      width: 150,
      render: (date) => date ? new Date(date).toLocaleDateString('zh-CN') : '-',
    },
    {
      title: '操作',
      key: 'actions',
      width: 280,
      fixed: 'right',
      render: (_, record) => (
        <Space wrap size="small">
          <Tooltip title="查看详情">
            <Button
              size="small"
              icon={<EyeOutlined />}
              onClick={() => handleShowDetails(record.id)}
            />
          </Tooltip>
          
          <Tooltip title={record.status === 'disabled' ? '启用' : '禁用'}>
            <Button
              size="small"
              icon={record.status === 'disabled' ? <UnlockOutlined /> : <LockOutlined />}
              onClick={() => handleToggleUser(record.id, record.status)}
            />
          </Tooltip>
          
          <Tooltip title="重置流量">
            <Button
              size="small"
              icon={<ClearOutlined />}
              onClick={() => handleResetTraffic(record.id)}
            />
          </Tooltip>
          
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
              onClick={() => handleDeleteUser(record.id)}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  return (
    <div className="users-container">
      <Card>
        <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
          <Col>
            <h2>用户管理</h2>
          </Col>
          <Col>
            <Space>
              <Select
                placeholder="按状态筛选"
                style={{ width: 120 }}
                allowClear
                value={statusFilter}
                onChange={setStatusFilter}
                options={[
                  { label: '活跃', value: 'active' },
                  { label: '禁用', value: 'disabled' },
                  { label: '已过期', value: 'expired' },
                  { label: '超配额', value: 'over_quota' },
                ]}
              />
              <Button
                icon={<ReloadOutlined />}
                onClick={fetchUsers}
                loading={loading}
              >
                刷新
              </Button>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => handleShowModal()}
              >
                创建用户
              </Button>
            </Space>
          </Col>
        </Row>

        <Table
          columns={columns}
          dataSource={users}
          rowKey="id"
          loading={loading}
          scroll={{ x: 1400 }}
          pagination={{
            current: pagination.current,
            pageSize: pagination.pageSize,
            total: total,
            showSizeChanger: true,
            pageSizeOptions: ['10', '20', '50'],
            showTotal: (total) => `共 ${total} 个用户`,
            onChange: (page, pageSize) => {
              setPagination({ current: page, pageSize });
            },
          }}
        />
      </Card>

      <Modal
        title={editingId ? '编辑用户' : '创建用户'}
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
            name="username"
            label="用户名"
            rules={[
              { required: true, message: '请输入用户名' },
              { min: 1, max: 100, message: '用户名长度 1-100 字符' },
            ]}
          >
            <Input placeholder="例如：user001" disabled={!!editingId} />
          </Form.Item>

          <Form.Item
            name="traffic_limit_gb"
            label="流量限制 (GB)"
            tooltip="0 表示无限制"
          >
            <InputNumber
              min={0}
              placeholder="0"
              style={{ width: '100%' }}
            />
          </Form.Item>

          <Form.Item
            name="speed_limit_kbps"
            label="速度限制 (Kbps)"
            tooltip="0 表示无限制"
          >
            <InputNumber
              min={0}
              placeholder="0"
              style={{ width: '100%' }}
            />
          </Form.Item>

          <Form.Item
            name="device_limit"
            label="设备限制"
            tooltip="0 表示无限制"
          >
            <InputNumber
              min={0}
              placeholder="0"
              style={{ width: '100%' }}
            />
          </Form.Item>

          <Form.Item
            name="expiry_date"
            label="过期时间"
            tooltip="不设置表示永不过期"
          >
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item
            name="preferred_regions"
            label="首选地区"
            tooltip="JSON 格式，例如: [\"CN\", \"HK\"]"
          >
            <Input placeholder='["CN", "HK"]' />
          </Form.Item>

          <Form.Item
            name="notes"
            label="备注"
          >
            <Input.TextArea placeholder="添加备注信息" />
          </Form.Item>
        </Form>
      </Modal>

      <Drawer
        title="用户详情"
        placement="right"
        onClose={() => setDetailDrawer(false)}
        open={detailDrawer}
        width={400}
      >
        {selectedUser && (
          <div>
            <div style={{ marginBottom: 24 }}>
              <Statistic
                title="用户名"
                value={selectedUser.username}
              />
            </div>
            
            <div style={{ marginBottom: 24 }}>
              <span className="user-uuid" onClick={() => handleCopyUUID(selectedUser.uuid)}>
                {selectedUser.uuid}
              </span>
              <Button
                type="text"
                size="small"
                icon={<CopyOutlined />}
                onClick={() => handleCopyUUID(selectedUser.uuid)}
                style={{ marginLeft: 8 }}
              />
            </div>

            <div style={{ marginBottom: 24 }}>
              <Statistic
                title="状态"
                value={selectedUser.status}
              />
            </div>

            <div style={{ marginBottom: 24 }}>
              <Statistic
                title="流量使用"
                value={`${selectedUser.traffic_used_gb} / ${selectedUser.traffic_limit_gb || '∞'} GB`}
              />
            </div>

            <div style={{ marginBottom: 24 }}>
              <Statistic
                title="速度限制"
                value={selectedUser.speed_limit_kbps === 0 ? '无限制' : `${selectedUser.speed_limit_kbps} Kbps`}
              />
            </div>

            <div style={{ marginBottom: 24 }}>
              <Statistic
                title="设备限制"
                value={selectedUser.device_limit === 0 ? '无限制' : selectedUser.device_limit}
              />
            </div>

            <div style={{ marginBottom: 24 }}>
              <Statistic
                title="在线设备"
                value={selectedUser.devices_online}
              />
            </div>

            {selectedUser.expiry_date && (
              <div style={{ marginBottom: 24 }}>
                <Statistic
                  title="过期时间"
                  value={new Date(selectedUser.expiry_date).toLocaleString('zh-CN')}
                />
              </div>
            )}

            {selectedUser.service_ids && selectedUser.service_ids.length > 0 && (
              <div>
                <h4>可用服务</h4>
                <Space wrap>
                  {selectedUser.service_ids.map((id) => (
                    <Tag key={id}>{id}</Tag>
                  ))}
                </Space>
              </div>
            )}
          </div>
        )}
      </Drawer>
    </div>
  );
}
