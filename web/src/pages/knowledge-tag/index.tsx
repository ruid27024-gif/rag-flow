import { HomeIcon } from '@/components/svg-icon';
import { getAuthorization } from '@/utils/authorization-util';
import { DownOutlined, UpOutlined } from '@ant-design/icons';
import {
  Button,
  Form,
  Input,
  InputNumber,
  Modal,
  Popconfirm,
  Space,
  Switch,
  Table,
  Tag,
  Typography,
  message,
  theme,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'umi';

const { Title } = Typography;

type TagOption = {
  option_code: string;
  option_name: string;
  sort_order?: number;
  enabled?: boolean;
};

type TagType = {
  type_code: string;
  type_name: string;
  multi_select: boolean;
  required: boolean;
  sort_order?: number;
  enabled?: boolean;
  options: TagOption[];
};

const authHeaders = {
  Authorization: getAuthorization() || '',
  'Content-Type': 'application/json',
};

const KnowledgeTagPage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [tagConfig, setTagConfig] = useState<TagType[]>([]);

  const [typeModalOpen, setTypeModalOpen] = useState(false);
  const [typeModalMode, setTypeModalMode] = useState<'create' | 'edit'>(
    'create',
  );
  const [currentType, setCurrentType] = useState<TagType | null>(null);
  const [typeForm] = Form.useForm();

  const [optionModalOpen, setOptionModalOpen] = useState(false);
  const [optionModalMode, setOptionModalMode] = useState<'create' | 'edit'>(
    'create',
  );
  const [currentOptionTypeCode, setCurrentOptionTypeCode] =
    useState<string>('');
  const [currentOption, setCurrentOption] = useState<TagOption | null>(null);
  const [optionForm] = Form.useForm();

  /**
   * 获取标签配置
   */
  const fetchTagConfig = async () => {
    try {
      setLoading(true);

      const res = await fetch('/v1/knowledge_tag/tag/config_all', {
        method: 'GET',
        headers: authHeaders,
        credentials: 'include',
      });

      const result = await res.json();

      if (result.code === 0 || result.code === 200) {
        setTagConfig(result.data || []);
      } else {
        message.error(result.message || '获取标签配置失败');
      }
    } catch (e) {
      console.error(e);
      message.error('获取标签配置请求失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTagConfig();
  }, []);

  /**
   * 打开新增标签类型弹窗
   */
  const openCreateTypeModal = () => {
    setTypeModalMode('create');
    setCurrentType(null);
    typeForm.resetFields();

    typeForm.setFieldsValue({
      multi_select: false,
      required: false,
      enabled: true,
      sort_order: 0,
      options: [
        {
          option_code: '',
          option_name: '',
          sort_order: 1,
        },
      ],
    });

    setTypeModalOpen(true);
  };

  /**
   * 打开编辑标签类型弹窗
   */
  const openEditTypeModal = (record: TagType) => {
    setTypeModalMode('edit');
    setCurrentType(record);
    typeForm.resetFields();

    typeForm.setFieldsValue({
      type_code: record.type_code,
      type_name: record.type_name,
      multi_select: record.multi_select,
      required: record.required,
      enabled: record.enabled !== false,
      sort_order: record.sort_order || 0,
    });

    setTypeModalOpen(true);
  };

  /**
   * 新增或修改标签类型
   */
  const submitTypeForm = async () => {
    try {
      const values = await typeForm.validateFields();

      if (typeModalMode === 'create') {
        await createTypeWithOptions(values);
      } else {
        await updateTagType(values);
      }
    } catch (e) {
      console.error(e);
    }
  };

  /**
   * 新增标签类型 + 选项
   */
  const createTypeWithOptions = async (values: any) => {
    try {
      const res = await fetch(
        '/v1/knowledge_tag/tag/type/create_with_options',
        {
          method: 'POST',
          headers: authHeaders,
          credentials: 'include',
          body: JSON.stringify({
            type_code: values.type_code,
            type_name: values.type_name,
            multi_select: values.multi_select || false,
            required: values.required || false,
            sort_order: values.sort_order || 0,
            enabled: values.enabled !== false,
            options: values.options || [],
          }),
        },
      );

      const result = await res.json();

      if (result.code === 0 || result.code === 200) {
        message.success('新增标签类型成功');
        setTypeModalOpen(false);
        fetchTagConfig();
      } else {
        message.error(result.message || '新增标签类型失败');
      }
    } catch (e) {
      console.error(e);
      message.error('新增标签类型请求失败');
    }
  };

  /**
   * 修改标签类型
   */
  const updateTagType = async (values: any) => {
    try {
      const res = await fetch('/v1/knowledge_tag/tag/type/update', {
        method: 'POST',
        headers: authHeaders,
        credentials: 'include',
        body: JSON.stringify({
          type_code: currentType?.type_code,
          type_name: values.type_name,
          multi_select: values.multi_select || false,
          required: values.required || false,
          sort_order: values.sort_order || 0,
          enabled: values.enabled !== false,
        }),
      });

      const result = await res.json();

      if (result.code === 0 || result.code === 200) {
        message.success('修改标签类型成功');
        setTypeModalOpen(false);
        fetchTagConfig();
      } else {
        message.error(result.message || '修改标签类型失败');
      }
    } catch (e) {
      console.error(e);
      message.error('修改标签类型请求失败');
    }
  };

  /**
   * 禁用标签类型
   */
  const disableTagType = async (typeCode: string) => {
    try {
      const res = await fetch('/v1/knowledge_tag/tag/type/disable', {
        method: 'POST',
        headers: authHeaders,
        credentials: 'include',
        body: JSON.stringify({
          type_code: typeCode,
        }),
      });

      const result = await res.json();

      if (result.code === 0 || result.code === 200) {
        message.success('禁用标签类型成功');
        fetchTagConfig();
      } else {
        message.error(result.message || '禁用标签类型失败');
      }
    } catch (e) {
      console.error(e);
      message.error('禁用标签类型请求失败');
    }
  };
  //   启用标签类型
  const enableTagType = async (typeCode: string) => {
    try {
      const res = await fetch('/v1/knowledge_tag/tag/type/enable', {
        method: 'POST',
        headers: authHeaders,
        credentials: 'include',
        body: JSON.stringify({
          type_code: typeCode,
        }),
      });

      const result = await res.json();

      if (result.code === 0 || result.code === 200) {
        message.success('启用标签类型成功');
        fetchTagConfig();
      } else {
        message.error(result.message || '启用标签类型失败');
      }
    } catch (e) {
      console.error(e);
      message.error('启用标签类型请求失败');
    }
  };

  // 启用标签
  const enableTagOption = async (typeCode: string, optionCode: string) => {
    try {
      const res = await fetch('/v1/knowledge_tag/tag/option/enable', {
        method: 'POST',
        headers: authHeaders,
        credentials: 'include',
        body: JSON.stringify({
          type_code: typeCode,
          option_code: optionCode,
        }),
      });

      const result = await res.json();

      if (result.code === 0 || result.code === 200) {
        message.success('启用选项成功');
        fetchTagConfig();
      } else {
        message.error(result.message || '启用选项失败');
      }
    } catch (e) {
      console.error(e);
      message.error('启用选项请求失败');
    }
  };
  // 删除标签类型
  const deleteTagType = async (typeCode: string) => {
    try {
      const res = await fetch('/v1/knowledge_tag/tag/type/delete', {
        method: 'POST',
        headers: authHeaders,
        credentials: 'include',
        body: JSON.stringify({
          type_code: typeCode,
        }),
      });

      const result = await res.json();

      if (result.code === 0 || result.code === 200) {
        message.success('删除标签类型成功');
        fetchTagConfig();
      } else {
        message.error(result.message || '删除标签类型失败');
      }
    } catch (e) {
      console.error(e);
      message.error('删除标签类型请求失败');
    }
  };
  //  删除标签选项
  const deleteTagOption = async (typeCode: string, optionCode: string) => {
    try {
      const res = await fetch('/v1/knowledge_tag/tag/option/delete', {
        method: 'POST',
        headers: authHeaders,
        credentials: 'include',
        body: JSON.stringify({
          type_code: typeCode,
          option_code: optionCode,
        }),
      });

      const result = await res.json();

      if (result.code === 0 || result.code === 200) {
        message.success('删除选项成功');
        fetchTagConfig();
      } else {
        message.error(result.message || '删除选项失败');
      }
    } catch (e) {
      console.error(e);
      message.error('删除选项请求失败');
    }
  };
  /**
   * 打开新增选项弹窗
   */
  const openCreateOptionModal = (typeCode: string) => {
    setOptionModalMode('create');
    setCurrentOptionTypeCode(typeCode);
    setCurrentOption(null);
    optionForm.resetFields();

    optionForm.setFieldsValue({
      type_code: typeCode,
      option_code: '',
      option_name: '',
      sort_order: 0,
      enabled: true,
    });

    setOptionModalOpen(true);
  };

  /**
   * 打开编辑选项弹窗
   */
  const openEditOptionModal = (typeCode: string, option: TagOption) => {
    setOptionModalMode('edit');
    setCurrentOptionTypeCode(typeCode);
    setCurrentOption(option);
    optionForm.resetFields();

    optionForm.setFieldsValue({
      type_code: typeCode,
      option_code: option.option_code,
      option_name: option.option_name,
      sort_order: option.sort_order || 0,
      enabled: option.enabled !== false,
    });

    setOptionModalOpen(true);
  };

  /**
   * 新增或修改选项
   */
  const submitOptionForm = async () => {
    try {
      const values = await optionForm.validateFields();

      if (optionModalMode === 'create') {
        await createTagOption(values);
      } else {
        await updateTagOption(values);
      }
    } catch (e) {
      console.error(e);
    }
  };

  /**
   * 新增标签选项
   */
  const createTagOption = async (values: any) => {
    try {
      const res = await fetch('/v1/knowledge_tag/tag/option/create', {
        method: 'POST',
        headers: authHeaders,
        credentials: 'include',
        body: JSON.stringify({
          type_code: currentOptionTypeCode,
          option_code: values.option_code,
          option_name: values.option_name,
          sort_order: values.sort_order || 0,
          enabled: values.enabled !== false,
        }),
      });

      const result = await res.json();

      if (result.code === 0 || result.code === 200) {
        message.success('新增选项成功');
        setOptionModalOpen(false);
        fetchTagConfig();
      } else {
        message.error(result.message || '新增选项失败');
      }
    } catch (e) {
      console.error(e);
      message.error('新增选项请求失败');
    }
  };

  /**
   * 修改标签选项
   */
  const updateTagOption = async (values: any) => {
    try {
      const res = await fetch('/v1/knowledge_tag/tag/option/update', {
        method: 'POST',
        headers: authHeaders,
        credentials: 'include',
        body: JSON.stringify({
          type_code: currentOptionTypeCode,
          option_code: currentOption?.option_code,
          option_name: values.option_name,
          sort_order: values.sort_order || 0,
          enabled: values.enabled !== false,
        }),
      });

      const result = await res.json();

      if (result.code === 0 || result.code === 200) {
        message.success('修改选项成功');
        setOptionModalOpen(false);
        fetchTagConfig();
      } else {
        message.error(result.message || '修改选项失败');
      }
    } catch (e) {
      console.error(e);
      message.error('修改选项请求失败');
    }
  };

  /**
   * 禁用标签选项
   */
  const disableTagOption = async (typeCode: string, optionCode: string) => {
    try {
      const res = await fetch('/v1/knowledge_tag/tag/option/disable', {
        method: 'POST',
        headers: authHeaders,
        credentials: 'include',
        body: JSON.stringify({
          type_code: typeCode,
          option_code: optionCode,
        }),
      });

      const result = await res.json();

      if (result.code === 0 || result.code === 200) {
        message.success('禁用选项成功');
        fetchTagConfig();
      } else {
        message.error(result.message || '禁用选项失败');
      }
    } catch (e) {
      console.error(e);
      message.error('禁用选项请求失败');
    }
  };

  const columns: ColumnsType<TagType> = [
    {
      title: '类型名称',
      dataIndex: 'type_name',
      width: 160,
    },
    {
      title: '类型编码',
      dataIndex: 'type_code',
      width: 200,
    },
    {
      title: '是否多选',
      dataIndex: 'multi_select',
      width: 100,
      render: (value) => {
        return value ? <Tag color="blue">多选</Tag> : <Tag>单选</Tag>;
      },
    },
    {
      title: '是否必填',
      dataIndex: 'required',
      width: 100,
      render: (value) => {
        return value ? <Tag color="red">必填</Tag> : <Tag>非必填</Tag>;
      },
    },
    {
      title: '排序',
      dataIndex: 'sort_order',
      width: 80,
    },
    {
      title: '选项',
      dataIndex: 'options',
      render: (_, record) => {
        return (
          <Space wrap>
            {(record.options || []).map((option) => (
              <Tag
                key={option.option_code}
                style={{
                  cursor: 'pointer',
                  color:
                    option.enabled === false
                      ? token.colorTextTertiary
                      : '#00A870',
                  background:
                    option.enabled === false
                      ? token.colorFillQuaternary
                      : 'rgba(0, 168, 112, 0.14)',
                  borderColor:
                    option.enabled === false
                      ? token.colorBorder
                      : 'rgba(0, 168, 112, 0.55)',
                }}
                onClick={() => openEditOptionModal(record.type_code, option)}
              >
                {option.option_name}
              </Tag>
            ))}
          </Space>
        );
      },
    },
    {
      title: '操作',
      width: 260,
      render: (_, record) => {
        return (
          <Space>
            <Button
              type="link"
              style={{ color: '#00A870' }}
              onClick={() => openEditTypeModal(record)}
            >
              编辑类型
            </Button>

            <Button
              type="link"
              style={{ color: '#00A870' }}
              onClick={() => openCreateOptionModal(record.type_code)}
            >
              新增选项
            </Button>

            {record.enabled === false ? (
              <Popconfirm
                title="确认启用该标签类型？"
                onConfirm={() => enableTagType(record.type_code)}
              >
                <Button type="link" style={{ color: '#00A870' }}>
                  启用
                </Button>
              </Popconfirm>
            ) : (
              <Popconfirm
                title="确认禁用该标签类型？"
                description="禁用后新上传文件不会再展示该类型，历史数据不删除。"
                onConfirm={() => disableTagType(record.type_code)}
              >
                <Button type="link" danger>
                  禁用
                </Button>
              </Popconfirm>
            )}
            <Popconfirm
              title="确认删除该标签类型？"
              description="删除后该类型及其所有选项都会被删除，请确认是否为误建数据。"
              okText="确认删除"
              cancelText="取消"
              onConfirm={() => deleteTagType(record.type_code)}
            >
              <Button type="link" danger>
                删除
              </Button>
            </Popconfirm>
          </Space>
        );
      },
    },
  ];
  const { token } = theme.useToken();
  const cardStyle: React.CSSProperties = {
    background: token.colorBgContainer,
    borderRadius: 12,
    padding: 20,
    // border: `1px solid ${token.colorBorderSecondary}`,
  };

  const greenButtonStyle: React.CSSProperties = {
    background: '#00A870',
    borderColor: '#00A870',
  };
  const navigate = useNavigate();

  return (
    <div
      style={{
        padding: 32,
        height: '100vh',
        overflowY: 'auto',
        overflowX: 'hidden',
        background: 'transparent',
      }}
    >
      {/* 顶部层级 */}
      <div style={{ marginBottom: 20 }}>
        <div
          className="text-2xl font-semibold flex items-center gap-2.5"
          style={{
            lineHeight: '32px',
          }}
        >
          <span
            onClick={() => navigate('/admin-files')} // 这里按你的实际父级路由改
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 10,
              cursor: 'pointer',
              color: token.colorText,
            }}
          >
            <HomeIcon name="set" width="32" />
            <span>系统设置</span>
          </span>

          <span
            style={{
              color: token.colorTextTertiary,
              fontWeight: 400,
            }}
          >
            /
          </span>

          <span
            style={{
              color: token.colorTextSecondary,
              fontWeight: 500,
            }}
          >
            知识库标签管理
          </span>
        </div>
      </div>

      <div style={cardStyle}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: 16,
            gap: 16,
          }}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              fontSize: 16,
              fontWeight: 700,
              color: token.colorText,
              flexShrink: 0,
            }}
          >
            <span
              style={{
                width: 4,
                height: 16,
                borderRadius: 999,
                background: '#00A870',
                display: 'inline-block',
              }}
            />
            知识库标签列表
          </div>

          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 12,
              marginLeft: 'auto',
            }}
          >
            {/* <Button onClick={fetchTagConfig}>刷新</Button> */}

            <Button
              type="primary"
              onClick={openCreateTypeModal}
              style={greenButtonStyle}
            >
              新增标签类型
            </Button>
          </div>
        </div>

        <Table
          className="knowledge-tag-table"
          rowKey="type_code"
          loading={loading}
          columns={columns}
          dataSource={tagConfig}
          pagination={false}
          expandable={{
            expandIcon: ({ expanded, onExpand, record }) => {
              return (
                <Button
                  type="text"
                  size="small"
                  onClick={(e) => onExpand(record, e)}
                  style={{
                    color: '#00A870',
                    padding: 0,
                    width: 24,
                    height: 24,
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  {expanded ? <UpOutlined /> : <DownOutlined />}
                </Button>
              );
            },

            expandedRowRender: (record) => {
              const optionColumns: ColumnsType<TagOption> = [
                {
                  title: '选项名称',
                  dataIndex: 'option_name',
                  width: 180,
                },
                {
                  title: '选项编码',
                  dataIndex: 'option_code',
                  width: 220,
                },
                {
                  title: '排序',
                  dataIndex: 'sort_order',
                  width: 100,
                },
                {
                  title: '状态',
                  dataIndex: 'enabled',
                  width: 100,
                  render: (value) => {
                    return value === false ? (
                      <Tag color="default">已禁用</Tag>
                    ) : (
                      <Tag
                        style={{
                          color: '#00A870',
                          background: 'rgba(0, 168, 112, 0.14)',
                          borderColor: 'rgba(0, 168, 112, 0.55)',
                        }}
                      >
                        启用
                      </Tag>
                    );
                  },
                },
                {
                  title: '操作',
                  width: 180,
                  render: (_, option) => {
                    return (
                      <Space>
                        <Button
                          type="link"
                          style={{ color: '#00A870' }}
                          onClick={() =>
                            openEditOptionModal(record.type_code, option)
                          }
                        >
                          编辑
                        </Button>

                        {option.enabled === false ? (
                          <Popconfirm
                            title="确认启用该选项？"
                            onConfirm={() =>
                              enableTagOption(
                                record.type_code,
                                option.option_code,
                              )
                            }
                          >
                            <Button type="link" style={{ color: '#00A870' }}>
                              启用
                            </Button>
                          </Popconfirm>
                        ) : (
                          <Popconfirm
                            title="确认禁用该选项？"
                            description="禁用后新上传文件不能再选择该选项。"
                            onConfirm={() =>
                              disableTagOption(
                                record.type_code,
                                option.option_code,
                              )
                            }
                          >
                            <Button type="link" danger>
                              禁用
                            </Button>
                          </Popconfirm>
                        )}

                        <Popconfirm
                          title="确认删除该选项？"
                          description="删除后不可恢复，请确认是否为误建数据。"
                          okText="确认删除"
                          cancelText="取消"
                          onConfirm={() =>
                            deleteTagOption(
                              record.type_code,
                              option.option_code,
                            )
                          }
                        >
                          <Button type="link" danger>
                            删除
                          </Button>
                        </Popconfirm>
                      </Space>
                    );
                  },
                },
              ];

              return (
                <Table
                  rowKey="option_code"
                  columns={optionColumns}
                  dataSource={record.options || []}
                  pagination={false}
                  size="small"
                  tableLayout="fixed"
                />
              );
            },
          }}
        />
      </div>

      {/* 新增/编辑 标签类型 */}
      <Modal
        title={typeModalMode === 'create' ? '新增标签类型' : '编辑标签类型'}
        open={typeModalOpen}
        onCancel={() => setTypeModalOpen(false)}
        onOk={submitTypeForm}
        destroyOnClose
        width={760}
      >
        <Form form={typeForm} layout="vertical">
          <Form.Item
            label="类型编码"
            name="type_code"
            rules={[{ required: true, message: '请输入类型编码' }]}
          >
            <Input
              disabled={typeModalMode === 'edit'}
              placeholder="例如：knowledge_level"
            />
          </Form.Item>

          <Form.Item
            label="类型名称"
            name="type_name"
            rules={[{ required: true, message: '请输入类型名称' }]}
          >
            <Input placeholder="例如：知识等级" />
          </Form.Item>

          <Form.Item
            label="是否多选"
            name="multi_select"
            valuePropName="checked"
          >
            <Switch checkedChildren="多选" unCheckedChildren="单选" />
          </Form.Item>

          <Form.Item label="是否必填" name="required" valuePropName="checked">
            <Switch checkedChildren="必填" unCheckedChildren="非必填" />
          </Form.Item>

          <Form.Item label="是否启用" name="enabled" valuePropName="checked">
            <Switch checkedChildren="启用" unCheckedChildren="禁用" />
          </Form.Item>

          <Form.Item label="排序" name="sort_order">
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>

          {typeModalMode === 'create' && (
            <Form.List name="options">
              {(fields, { add, remove }) => (
                <>
                  <div style={{ marginBottom: 8, fontWeight: 500 }}>
                    选项列表
                  </div>

                  {fields.map((field) => (
                    <Space
                      key={field.key}
                      align="baseline"
                      style={{ display: 'flex', marginBottom: 8 }}
                    >
                      <Form.Item
                        {...field}
                        name={[field.name, 'option_code']}
                        rules={[{ required: true, message: '请输入选项编码' }]}
                      >
                        <Input placeholder="选项编码，例如 internal" />
                      </Form.Item>

                      <Form.Item
                        {...field}
                        name={[field.name, 'option_name']}
                        rules={[{ required: true, message: '请输入选项名称' }]}
                      >
                        <Input placeholder="选项名称，例如 内部" />
                      </Form.Item>

                      <Form.Item {...field} name={[field.name, 'sort_order']}>
                        <InputNumber min={0} placeholder="排序" />
                      </Form.Item>

                      <Button danger onClick={() => remove(field.name)}>
                        删除
                      </Button>
                    </Space>
                  ))}

                  <Button type="dashed" onClick={() => add()} block>
                    新增选项
                  </Button>
                </>
              )}
            </Form.List>
          )}
        </Form>
      </Modal>

      {/* 新增/编辑 标签选项 */}
      <Modal
        title={optionModalMode === 'create' ? '新增标签选项' : '编辑标签选项'}
        open={optionModalOpen}
        onCancel={() => setOptionModalOpen(false)}
        onOk={submitOptionForm}
        destroyOnClose
      >
        <Form form={optionForm} layout="vertical">
          <Form.Item label="类型编码" name="type_code">
            <Input disabled />
          </Form.Item>

          <Form.Item
            label="选项编码"
            name="option_code"
            rules={[{ required: true, message: '请输入选项编码' }]}
          >
            <Input
              disabled={optionModalMode === 'edit'}
              placeholder="例如：operator"
            />
          </Form.Item>

          <Form.Item
            label="选项名称"
            name="option_name"
            rules={[{ required: true, message: '请输入选项名称' }]}
          >
            <Input placeholder="例如：操作工" />
          </Form.Item>

          <Form.Item label="排序" name="sort_order">
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item label="是否启用" name="enabled" valuePropName="checked">
            <Switch checkedChildren="启用" unCheckedChildren="禁用" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default KnowledgeTagPage;
