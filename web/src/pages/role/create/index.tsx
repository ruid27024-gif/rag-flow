import { getAuthorization } from '@/utils/authorization-util';
import {
  Button,
  Card,
  Checkbox,
  Form,
  Input,
  InputNumber,
  Radio,
  Space,
  Switch,
  message,
} from 'antd';
import React, { useState } from 'react';

const FILE_PERMISSION_LEVEL = {
  PUBLIC: 1,
  INTERNAL: 2,
};

const operationOptions = [
  {
    label: '查看',
    value: 'view',
  },
  {
    label: '上传',
    value: 'upload',
  },
  {
    label: '下载',
    value: 'download',
  },
  {
    label: '删除',
    value: 'delete',
  },
  {
    label: '编辑',
    value: 'edit',
  },
];

interface AddRoleFormValues {
  role_name: string;
  file_permission_level: number;
  operation_permissions: string[];
  need_approval: boolean;
  approval_order: number;
  department_id?: string;
  is_admin: boolean;
  cover_child_dept: boolean;
  enabled: boolean;
}

const AddRolePage: React.FC = () => {
  const [form] = Form.useForm<AddRoleFormValues>();
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (values: AddRoleFormValues) => {
    try {
      setLoading(true);

      const payload = {
        role_name: values.role_name,
        file_permission_level: values.file_permission_level,
        operation_permissions: values.operation_permissions || [],
        need_approval: values.need_approval,
        approval_order: values.approval_order || 0,
        department_id: values.department_id || null,
        is_admin: values.is_admin,
        cover_child_dept: values.cover_child_dept,
        enabled: values.enabled,
      };

      console.log('提交数据:', payload);

      const res = await fetch('/v1/role/add', {
        method: 'POST',
        headers: {
          Authorization: getAuthorization() || '',
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify(payload),
      });

      const result = await res.json();

      if (result.code === 0 || result.code === 200 || result.data) {
        message.success('角色创建成功');
        form.resetFields();
      } else {
        message.error(result.message || '角色创建失败');
      }
    } catch (error) {
      console.error(error);
      message.error('请求失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card title="新增角色" style={{ maxWidth: 700 }}>
      <Form<AddRoleFormValues>
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
        initialValues={{
          file_permission_level: FILE_PERMISSION_LEVEL.PUBLIC,
          operation_permissions: ['view'],
          need_approval: true,
          approval_order: 0,
          is_admin: false,
          cover_child_dept: false,
          enabled: true,
        }}
      >
        <Form.Item
          label="角色名称"
          name="role_name"
          rules={[
            {
              required: true,
              message: '请输入角色名称',
            },
          ]}
        >
          <Input placeholder="请输入角色名称，例如：部门管理员" />
        </Form.Item>

        <Form.Item
          label="文件权限"
          name="file_permission_level"
          rules={[
            {
              required: true,
              message: '请选择文件权限',
            },
          ]}
        >
          <Radio.Group>
            <Radio value={FILE_PERMISSION_LEVEL.PUBLIC}>公开</Radio>
            <Radio value={FILE_PERMISSION_LEVEL.INTERNAL}>内部</Radio>
          </Radio.Group>
        </Form.Item>

        <Form.Item
          label="操作权限"
          name="operation_permissions"
          rules={[
            {
              required: true,
              message: '请选择至少一个操作权限',
            },
          ]}
        >
          <Checkbox.Group options={operationOptions} />
        </Form.Item>

        <Form.Item
          label="是否审批"
          name="need_approval"
          valuePropName="checked"
        >
          <Switch checkedChildren="是" unCheckedChildren="否" />
        </Form.Item>

        <Form.Item label="审批序号" name="approval_order">
          <InputNumber min={0} style={{ width: '100%' }} />
        </Form.Item>

        <Form.Item label="所属部门" name="department_id">
          <Input placeholder="请输入部门 ID，例如 dept_001" />
        </Form.Item>

        <Form.Item label="管理员权限" name="is_admin" valuePropName="checked">
          <Switch checkedChildren="是" unCheckedChildren="否" />
        </Form.Item>

        <Form.Item
          label="覆盖下级部门"
          name="cover_child_dept"
          valuePropName="checked"
        >
          <Switch checkedChildren="是" unCheckedChildren="否" />
        </Form.Item>

        <Form.Item label="是否启用" name="enabled" valuePropName="checked">
          <Switch checkedChildren="启用" unCheckedChildren="禁用" />
        </Form.Item>

        <Form.Item>
          <Space>
            <Button type="primary" htmlType="submit" loading={loading}>
              创建角色
            </Button>

            <Button
              onClick={() => {
                form.resetFields();
              }}
            >
              重置
            </Button>
          </Space>
        </Form.Item>
      </Form>
    </Card>
  );
};

export default AddRolePage;
