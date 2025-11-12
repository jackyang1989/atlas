// frontend/src/pages/Settings.jsx - 系统设置页面

import { useState, useEffect } from 'react';
import {
  Card,
  Tabs,
  Form,
  Input,
  InputNumber,
  Button,
  message,
  Space,
  Divider,
  Typography,
  Switch,
} from 'antd';
import {
  MailOutlined,
  BellOutlined,
  SafetyOutlined,
  ToolOutlined,
} from '@ant-design/icons';
import { alertsAPI, authAPI } from '../services/api';

const { Title, Paragraph } = Typography;

export default function Settings() {
  const [loading, setLoading] = useState(false);
  const [alertConfig, setAlertConfig] = useState(null);
  const [passwordForm] = Form.useForm();
  const [emailForm] = Form.useForm();

  useEffect(() => {
    fetchAlertConfig();
  }, []);

  const fetchAlertConfig = async () => {
    try {
      const response = await alertsAPI.getConfig();
      setAlertConfig(response.data);
    } catch (error) {
      console.error('获取告警配置失败:', error);
    }
  };

  const handleChangePassword = async (values) => {
    setLoading(true);
    try {
      await authAPI.changePassword(values.old_password, values.new_password);
      message.success('密码修改成功，请重新登录');
      passwordForm.resetFields();
      
      // 3 秒后跳转到登录页
      setTimeout(() => {
        localStorage.removeItem('access_token');
        window.location.href = '/login';
      }, 3000);
    } catch (error) {
      const errorMsg = error.response?.data?.detail || '修改失败';
      message.error(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const handleTestEmail = async (values) => {
    setLoading(true);
    try {
      await alertsAPI.test(values.test_email);
      message.success('测试邮件已发送，请检查您的邮箱');
      emailForm.resetFields();
    } catch (error) {
      const errorMsg = error.response?.data?.detail || '发送失败';
      message.error(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const tabItems = [
    {
      key: 'password',
      label: (
        <span>
          <SafetyOutlined />
          密码设置
        </span>
      ),
      children: (
        <Card>
          <Title level={4}>修改密码</Title>
          <Paragraph type="secondary">
            为了账户安全，建议定期修改密码
          </Paragraph>
          
          <Form
            form={passwordForm}
            layout="vertical"
            onFinish={handleChangePassword}
            style={{ maxWidth: 500 }}
          >
            <Form.Item
              name="old_password"
              label="当前密码"
              rules={[
                { required: true, message: '请输入当前密码' },
              ]}
            >
              <Input.Password placeholder="请输入当前密码" />
            </Form.Item>

            <Form.Item
              name="new_password"
              label="新密码"
              rules={[
                { required: true, message: '请输入新密码' },
                { min: 8, message: '密码至少 8 位' },
              ]}
            >
              <Input.Password placeholder="请输入新密码（至少 8 位）" />
            </Form.Item>

            <Form.Item
              name="confirm_password"
              label="确认密码"
              dependencies={['new_password']}
              rules={[
                { required: true, message: '请确认新密码' },
                ({ getFieldValue }) => ({
                  validator(_, value) {
                    if (!value || getFieldValue('new_password') === value) {
                      return Promise.resolve();
                    }
                    return Promise.reject(new Error('两次输入的密码不一致'));
                  },
                }),
              ]}
            >
              <Input.Password placeholder="请再次输入新密码" />
            </Form.Item>

            <Form.Item>
              <Button type="primary" htmlType="submit" loading={loading}>
                修改密码
              </Button>
            </Form.Item>
          </Form>
        </Card>
      ),
    },
    {
      key: 'alerts',
      label: (
        <span>
          <BellOutlined />
          告警设置
        </span>
      ),
      children: (
        <Card>
          <Title level={4}>告警通知配置</Title>
          
          {alertConfig && (
            <div style={{ marginBottom: 24 }}>
              <Paragraph>
                <strong>SMTP 服务器：</strong> {alertConfig.smtp_server}:{alertConfig.smtp_port}
              </Paragraph>
              <Paragraph>
                <strong>发件邮箱：</strong> {alertConfig.from_email}
              </Paragraph>
              <Paragraph>
                <strong>配置状态：</strong> 
                {alertConfig.configured ? (
                  <span style={{ color: '#52c41a' }}> ✓ 已配置</span>
                ) : (
                  <span style={{ color: '#ff4d4f' }}> ✗ 未配置</span>
                )}
              </Paragraph>
            </div>
          )}

          <Divider />

          <Title level={5}>测试邮件通知</Title>
          <Paragraph type="secondary">
            发送测试邮件验证告警配置是否正确
          </Paragraph>

          <Form
            form={emailForm}
            layout="vertical"
            onFinish={handleTestEmail}
            style={{ maxWidth: 500 }}
          >
            <Form.Item
              name="test_email"
              label="测试邮箱地址"
              rules={[
                { required: true, message: '请输入邮箱地址' },
                { type: 'email', message: '请输入有效的邮箱地址' },
              ]}
            >
              <Input
                prefix={<MailOutlined />}
                placeholder="请输入接收测试邮件的邮箱地址"
              />
            </Form.Item>

            <Form.Item>
              <Button type="primary" htmlType="submit" loading={loading}>
                发送测试邮件
              </Button>
            </Form.Item>
          </Form>

          <Divider />

          <Title level={5}>告警规则</Title>
          <Paragraph type="secondary">
            系统会在以下情况自动发送告警通知：
          </Paragraph>
          <ul>
            <li>服务停止或异常</li>
            <li>用户流量超过 80% 配额</li>
            <li>SSL 证书即将过期（30 天内）</li>
            <li>系统资源使用率超过 90%</li>
          </ul>
        </Card>
      ),
    },
    {
      key: 'system',
      label: (
        <span>
          <ToolOutlined />
          系统信息
        </span>
      ),
      children: (
        <Card>
          <Title level={4}>系统信息</Title>
          
          <div style={{ marginTop: 24 }}>
            <Paragraph>
              <strong>项目名称：</strong> ATLAS
            </Paragraph>
            <Paragraph>
              <strong>版本：</strong> 1.0.0
            </Paragraph>
            <Paragraph>
              <strong>描述：</strong> Advanced Traffic & Load Administration System
            </Paragraph>
            <Paragraph>
              <strong>技术栈：</strong> FastAPI + React + PostgreSQL
            </Paragraph>
          </div>

          <Divider />

          <Title level={5}>功能模块</Title>
          <ul>
            <li>✓ 服务管理（VLESS、Hysteria2、TUIC）</li>
            <li>✓ 用户管理与配额控制</li>
            <li>✓ 域名与证书管理</li>
            <li>✓ 组件管理与升级</li>
            <li>✓ 系统监控与统计</li>
            <li>✓ 数据备份与恢复</li>
            <li>✓ 邮件告警通知</li>
          </ul>
        </Card>
      ),
    },
  ];

  return (
    <div>
      <Card>
        <Title level={2}>系统设置</Title>
        <Tabs items={tabItems} />
      </Card>
    </div>
  );
}
