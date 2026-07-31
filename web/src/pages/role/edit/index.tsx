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
import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'umi';

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

interface RoleFormValues {
  role_name: string;
  file_permission_level: number;
  operation_permissions: string[];
  need_approval: boolean;
  approval_order: number;
  department_id?: string | null;
  is_admin: boolean;
  cover_child_dept: boolean;
  enabled: boolean;
}

const OPERATION_PERMISSION_MAP: Record<string, number> = {
  view: 1,
  upload: 2,
  download: 4,
  delete: 8,
  edit: 16,
};

const parseOperationMask = (mask: number): string[] => {
  const result: string[] = [];

  Object.entries(OPERATION_PERMISSION_MAP).forEach(([key, bit]) => {
    if (mask & bit) {
      result.push(key);
    }
  });

  return result;
};

const RoleEditPage: React.FC = () => {
  const navigate = useNavigate();
  const params = useParams();

  const id = params.id;

  const [form] = Form.useForm<RoleFormValues>();
  const [loading, setLoading] = useState(false);
  const [submitLoading, setSubmitLoading] = useState(false);

  const fetchRoleDetail = async () => {
    if (!id) {
      message.error('角色ID不存在');
      return;
    }

    try {
      setLoading(true);

      const res = await fetch(`/v1/role/get/${id}`, {
        method: 'GET',
        headers: {
          Authorization: getAuthorization() || '',
          'Content-Type': 'application/json',
        },
        credentials: 'include',
      });

      const result = await res.json();

      if (result.code === 0 || result.code === 200) {
        const data = result.data;

        if (!data) {
          message.error('角色不存在');
          return;
        }

        /**
         * 后端如果返回 operation_permissions，优先用它。
         * 如果后端只返回 operation_permission_mask，这里也能自动解析。
         */
        const operationPermissions =
          data.operation_permissions ||
          parseOperationMask(data.operation_permission_mask || 0);

        form.setFieldsValue({
          role_name: data.role_name,
          file_permission_level: data.file_permission_level,
          operation_permissions: operationPermissions,
          need_approval: data.need_approval,
          approval_order: data.approval_order,
          department_id: data.department_id,
          is_admin: data.is_admin,
          cover_child_dept: data.cover_child_dept,
          enabled: data.enabled,
        });
      } else {
        message.error(result.message || '获取角色信息失败');
      }
    } catch (error) {
      console.error(error);
      message.error('请求失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRoleDetail();
  }, [id]);

  const handleSubmit = async (values: RoleFormValues) => {
    if (!id) {
      message.error('角色ID不存在');
      return;
    }

    try {
      setSubmitLoading(true);

      const payload = {
        id: Number(id),
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

      const res = await fetch('/v1/role/update', {
        method: 'POST',
        headers: {
          Authorization: getAuthorization() || '',
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify(payload),
      });

      const result = await res.json();

      if (result.code === 0 || result.code === 200 || result.data === true) {
        message.success('保存成功');
        navigate('/role');
      } else {
        message.error(result.message || '保存失败');
      }
    } catch (error) {
      console.error(error);
      message.error('请求失败');
    } finally {
      setSubmitLoading(false);
    }
  };

  return (
    <div style={{ padding: 24 }}>
      <Card title="编辑角色" loading={loading} style={{ maxWidth: 760 }}>
        <Form<RoleFormValues>
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
            <Input placeholder="请输入角色名称" />
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
            <Input placeholder="请输入部门ID" allowClear />
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
              <Button type="primary" htmlType="submit" loading={submitLoading}>
                保存
              </Button>

              <Button onClick={() => navigate('/role')}>返回</Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
};

export default RoleEditPage;
