import { useEffect, useState } from 'react';
import {
  Table,
  Button,
  Modal,
  Form,
  Input,
  Select,
  Tree,
  message,
  Space,
  Card,
  Row,
  Col,
  Tabs,
  Tooltip,
  Switch,
  Tag,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  UserOutlined,
  LockOutlined,
  UnlockOutlined,
  ShieldOutlined,
} from '@ant-design/icons';
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';
const token = localStorage.getItem('access_token');

const rbacAPI = {
  // 权限相关
  getPermissions: () => axios.get(`${API_URL}/api/rbac/permissions`, {
    headers: { 'Authorization': `Bearer ${token}` }
  }),
  
  // 角色相关
  getRoles: (skip = 0, limit = 10) => axios.get(
    `${API_URL}/api/rbac/roles?skip=${skip}&limit=${limit}`,
    { headers: { 'Authorization': `Bearer ${token}` } }
  ),
  createRole: (data) => axios.post(`${API_URL}/api/rbac/roles`, data, {
    headers: { 'Authorization': `Bearer ${token}` }
  }),
  updateRole: (roleId, data) => axios.put(`${API_URL}/api/rbac/roles/${roleId}`, data, {
    headers: { 'Authorization': `Bearer ${token}` }
  }),
  deleteRole: (roleId) => axios.delete(`${API_URL}/api/rbac/roles/${roleId}`, {
    headers: { 'Authorization': `Bearer ${token}` }
  }),
  
  // 用户相关
  getUsers: (skip = 0, limit = 10) => axios.get(
    `${API_URL}/api/rbac/users?skip=${skip}&limit=${limit}`,
    { headers: { 'Authorization': `Bearer ${token}` } }
  ),
  createUser: (data) => axios.post(`${API_URL}/api/rbac/users`, data, {
    headers: { 'Authorization': `Bearer ${token}` }
  }),
  assignRole: (userId, roleId) => axios.put(
    `${API_URL}/api/rbac/users/${userId}/role`,
    { role_id: roleId },
    { headers: { 'Authorization': `Bearer ${token}` } }
  ),
  enableUser: (userId) => axios.post(`${API_URL}/api/rbac/users/${userId}/enable`, {}, {
    headers: { 'Authorization': `Bearer ${token}` }
  }),
  disableUser: (userId) => axios.post(`${API_URL}/api/rbac/users/${userId}/disable`, {}, {
    headers: { 'Authorization': `Bearer ${token}` }
  }),
};

export default function RBAC() {
  const [activeTab, setActiveTab] = useState('roles');
  const [roles, setRoles] = useState([]);
  const [users, setUsers] = useState([]);
  const [permissions, setPermissions] = useState([]);
  const [loading, setLoading] = useState(false);
  
  const [roleModalVisible, setRoleModalVisible] = useState(false);
  const [userModalVisible, setUserModalVisible] = useState(false);
  const [selectedPermissions, setSelectedPermissions] = useState([]);
  const [permissionTree, setPermissionTree] = useState([]);
  
  const [roleForm] = Form.useForm();
  const [userForm] = Form.useForm();

  // ==================== 获取数据 ====================
  
  useEffect(() => {
    if (activeTab === 'roles') {
      fetchRoles();
      fetchPermissions();
    } else if (activeTab === 'users') {
      fetchUsers();
    }
  }, [activeTab]);

  const fetchRoles = async () => {
    setLoading(true);
    try {
      const response = await rbacAPI.getRoles();
      setRoles(response.data.items);
    } catch (error) {
      message.error('获取角色列表失败');
    } finally {
      setLoading(false);
    }
  };

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const response = await rbacAPI.getUsers();
      setUsers(response.data.items);
    } catch (error) {
      message.error('获取用户列表失败');
    } finally {
      setLoading(false);
    }
  };

  const fetchPermissions = async () => {
    try {
      const response = await rbacAPI.getPermissions();
      setPermissions(response.data.items);
      
      // 构建权限树
      const grouped = {};
      response.data.items.forEach(perm => {
        if (!grouped[perm.resource]) {
          grouped[perm.resource] = [];
        }
        grouped[perm.resource].push(perm);
      });
      
      const tree = Object.keys(grouped).map(resource => ({
        title: resource,
        key: `resource_${resource}`,
        children: grouped[resource].map(perm => ({
          title: `${perm.action}:${perm.name}`,
          key: perm.id,
          perm: perm,
        })),
      }));
      
      setPermissionTree(tree);
    } catch (error) {
      message.error('获取权限列表失败');
    }
  };

  // ==================== 角色操作 ====================

  const handleCreateRole = async (values) => {
    try {
      await rbacAPI.createRole({
        name: values.name,
        description: values.description,
        permission_ids: selectedPermissions,
      });
      message.success('角色创建成功');
      setRoleModalVisible(false);
      roleForm.resetFields();
      setSelectedPermissions([]);
      fetchRoles();
    } catch (error) {
      message.error(error.response?.data?.detail || '创建失败');
    }
  };

  const handleDeleteRole = (roleId) => {
    Modal.confirm({
      title: '删除角色',
      content: '确定要删除此角色吗？',
      okType: 'danger',
      onOk: async () => {
        try {
          await rbacAPI.deleteRole(roleId);
          message.success('角色已删除');
          fetchRoles();
        } catch (error) {
          message.error(error.response?.data?.detail || '删除失败');
        }
      },
    });
  };

  // ==================== 用户操作 ====================

  const handleCreateUser = async (values) => {
    try {
      await rbacAPI.createUser({
        username: values.username,
        password: values.password,
        role_id: values.role_id,
      });
      message.success('用户创建成功');
      setUserModalVisible(false);
      userForm.resetFields();
      fetchUsers();
    } catch (error) {
      message.error(error.response?.data?.detail || '创建失败');
    }
  };

  const handleAssignRole = (userId, roleId) => {
    Modal.confirm({
      title: '分配角色',
      content: `确定要分配此角色吗？`,
      onOk: async () => {
        try {
          await rbacAPI.assignRole(userId, roleId);
          message.success('角色已分配');
          fetchUsers();
        } catch (error) {
          message.error('分配失败');
        }
      },
    });
  };

  const handleToggleUser = async (userId, isActive) => {
    try {
      if (isActive) {
        await rbacAPI.disableUser(userId);
        message.success('用户已禁用');
      } else {
        await rbacAPI.enableUser(userId);
        message.success('用户已启用');
      }
      fetchUsers();
    } catch (error) {
      message.error(error.response?.data?.detail || '操作失败');
    }
  };

  // ==================== 角色表格 ====================

  const roleColumns = [
    {
      title: '角色名称',
      dataIndex: 'name',
      key: 'name',
      width: 120,
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      width: 200,
    },
    {
      title: '权限数量',
      key: 'permission_count',
      width: 100,
      render: (_, record) => record.permissions.length,
    },
    {
      title: '内置',
      dataIndex: 'is_builtin',
      key: 'is_builtin',
      width: 80,
      render: (builtin) => (
        <Tag color={builtin ? 'blue' : 'green'}>
          {builtin ? '内置' : '自定义'}
        </Tag>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 120,
      render: (_, record) => (
        <Space>
          {!record.is_builtin && (
            <Tooltip title="删除">
              <Button
                size="small"
                danger
                icon={<DeleteOutlined />}
                onClick={() => handleDeleteRole(record.id)}
              />
            </Tooltip>
          )}
        </Space>
      ),
    },
  ];

  // ==================== 用户表格 ====================

  const userColumns = [
    {
      title: '用户名',
      dataIndex: 'username',
      key: 'username',
      width: 120,
    },
    {
      title: '角色',
      dataIndex: ['role', 'name'],
      key: 'role',
      width: 100,
      render: (role, record) => (
        <Select
          value={record.role?.id}
          style={{ width: 100 }}
          size="small"
          onChange={(value) => handleAssignRole(record.id, value)}
          options={roles.map(r => ({ label: r.name, value: r.id }))}
        />
      ),
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 80,
      render: (isActive, record) => (
        <Switch
          checked={isActive}
          onChange={() => handleToggleUser(record.id, isActive)}
          size="small"
        />
      ),
    },
    {
      title: '最后登录',
      dataIndex: 'last_login',
      key: 'last_login',
      width: 150,
      render: (date) => date ? new Date(date).toLocaleString('zh-CN') : '-',
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 150,
      render: (date) => new Date(date).toLocaleString('zh-CN'),
    },
  ];

  return (
    <div>
      <h2>权限管理 (RBAC)</h2>
      
      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={[
          {
            key: 'roles',
            label: (
              <span>
                <ShieldOutlined />
                角色管理
              </span>
            ),
            children: (
              <Card>
                <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
                  <Col>角色列表</Col>
                  <Col>
                    <Button
                      type="primary"
                      icon={<PlusOutlined />}
                      onClick={() => setRoleModalVisible(true)}
                    >
                      创建角色
                    </Button>
                  </Col>
                </Row>

                <Table
                  columns={roleColumns}
                  dataSource={roles}
                  rowKey="id"
                  loading={loading}
                  pagination={false}
                />

                <Modal
                  title="创建角色"
                  open={roleModalVisible}
                  onOk={() => roleForm.submit()}
                  onCancel={() => {
                    setRoleModalVisible(false);
                    roleForm.resetFields();
                  }}
                  width={800}
                >
                  <Form
                    form={roleForm}
                    layout="vertical"
                    onFinish={handleCreateRole}
                  >
                    <Form.Item
                      name="name"
                      label="角色名称"
                      rules={[{ required: true }]}
                    >
                      <Input placeholder="例如：data_operator" />
                    </Form.Item>

                    <Form.Item
                      name="description"
                      label="描述"
                    >
                      <Input.TextArea />
                    </Form.Item>

                    <Form.Item label="权限">
                      <Tree
                        checkable
                        defaultExpandAll
                        onCheck={(checkedKeys) => setSelectedPermissions(checkedKeys)}
                        treeData={permissionTree}
                      />
                    </Form.Item>
                  </Form>
                </Modal>
              </Card>
            ),
          },
          {
            key: 'users',
            label: (
              <span>
                <UserOutlined />
                用户管理
              </span>
            ),
            children: (
              <Card>
                <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
                  <Col>管理员用户</Col>
                  <Col>
                    <Button
                      type="primary"
                      icon={<PlusOutlined />}
                      onClick={() => setUserModalVisible(true)}
                    >
                      创建用户
                    </Button>
                  </Col>
                </Row>

                <Table
                  columns={userColumns}
                  dataSource={users}
                  rowKey="id"
                  loading={loading}
                  pagination={false}
                />

                <Modal
                  title="创建管理员用户"
                  open={userModalVisible}
                  onOk={() => userForm.submit()}
                  onCancel={() => {
                    setUserModalVisible(false);
                    userForm.resetFields();
                  }}
                  width={500}
                >
                  <Form
                    form={userForm}
                    layout="vertical"
                    onFinish={handleCreateUser}
                  >
                    <Form.Item
                      name="username"
                      label="用户名"
                      rules={[{ required: true }]}
                    >
                      <Input placeholder="例如：operator1" />
                    </Form.Item>

                    <Form.Item
                      name="password"
                      label="密码"
                      rules={[
                        { required: true },
                        { min: 8, message: '密码至少 8 位' }
                      ]}
                    >
                      <Input.Password />
                    </Form.Item>

                    <Form.Item
                      name="role_id"
                      label="角色"
                      rules={[{ required: true }]}
                    >
                      <Select
                        placeholder="选择角色"
                        options={roles.map(r => ({
                          label: r.name,
                          value: r.id,
                        }))}
                      />
                    </Form.Item>
                  </Form>
                </Modal>
              </Card>
            ),
          },
        ]}
      />
    </div>
  );
}
