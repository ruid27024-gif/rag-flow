import { getAuthorization } from '@/utils/authorization-util';
import {
  DownOutlined,
  SearchOutlined,
  UpOutlined,
  UserOutlined,
} from '@ant-design/icons';
import {
  Alert,
  Button,
  Card,
  ConfigProvider,
  Empty,
  Input,
  Space,
  Spin,
  Table,
  Tag,
  Tooltip,
  Tree,
  Typography,
  message,
  theme,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import type { DataNode } from 'antd/es/tree';
import React, { useCallback, useEffect, useMemo, useState } from 'react';

const { Title } = Typography;

interface PersonTreeNode extends DataNode {
  id?: string;
  key: string;
  value?: string;
  title?: React.ReactNode;
  type?: 'company' | 'dept' | 'person' | 'group';

  phone?: string;
  user_id?: number;
  bindable?: boolean;

  mdmName?: string;
  mdmCode?: string;
  email?: string;
  erpid?: string;
  organize?: string;
  organizationCode?: string;
  part?: string;

  children?: PersonTreeNode[];
}

interface PersonInfo {
  id?: number;
  mdmName?: string;
  mdmCode?: string;
  phone?: string;
  email?: string;
  erpid?: string;
  organize?: string;
  organizationCode?: string;
  part?: string;
  gender?: string;
  onDutyOrNot?: string;
  personnelCategory?: string;
}

interface UserInfo {
  id?: number;
  email?: string;
  nickname?: string;
  username?: string;
  status?: number | string;
}

interface RoleInfo {
  id: number;
  name?: string;
  role_name?: string;

  department_id?: string;
  department_ids?: string[];
  department_name?: string;
  department_names?: string[];
  departments?: {
    id: string;
    name: string;
    mdmCode?: string;
    departmentName?: string;
    mdmName?: string;
    longName?: string;
    companyCode?: string;
    corporateName?: string;
  }[];

  file_permission_level?: number;
  operation_permission_mask?: number;
  need_approval?: boolean;
  approval_order?: number;
  is_admin?: boolean;
  cover_child_dept?: boolean;
  enabled?: boolean;

  [key: string]: any;
}

interface PersonDetail {
  phone?: string;
  bindable?: boolean;
  person?: PersonInfo | null;
  user?: UserInfo | null;
  roles?: RoleInfo[];
}

const RolePersonDetailPage: React.FC = () => {
  const [personTreeData, setPersonTreeData] = useState<PersonTreeNode[]>([]);
  const [personTreeLoading, setPersonTreeLoading] = useState(false);

  const [keyword, setKeyword] = useState('');

  const [personDetailLoading, setPersonDetailLoading] = useState(false);
  const [personDetail, setPersonDetail] = useState<PersonDetail | null>(null);
  const [currentPhone, setCurrentPhone] = useState<string>('');

  const [roleList, setRoleList] = useState<RoleInfo[]>([]);
  const [roleLoading, setRoleLoading] = useState(false);

  const [selectedRoleId, setSelectedRoleId] = useState<number | null>(null);
  const [bindLoading, setBindLoading] = useState(false);

  const [expandedDeptRoleIds, setExpandedDeptRoleIds] = useState<number[]>([]);
  const [roleKeyword, setRoleKeyword] = useState('');

  const toggleDeptExpanded = (roleId: number) => {
    setExpandedDeptRoleIds((prev) => {
      if (prev.includes(roleId)) {
        return prev.filter((id) => id !== roleId);
      }

      return [...prev, roleId];
    });
  };

  const authHeaders = useMemo(() => {
    return {
      Authorization: getAuthorization() || '',
      'Content-Type': 'application/json',
    };
  }, []);

  /**
   * 获取左侧人员树
   */
  const fetchPersonTree = useCallback(
    async (searchKeyword = '') => {
      try {
        setPersonTreeLoading(true);

        const res = await fetch('/v1/deptperson/person-tree', {
          method: 'POST',
          headers: authHeaders,
          credentials: 'include',
          body: JSON.stringify({
            keyword: searchKeyword,
          }),
        });

        const result = await res.json();

        if (result.code === 0 || result.code === 200) {
          setPersonTreeData(result.data || []);
        } else {
          message.error(result.message || '获取人员树失败');
        }
      } catch (e) {
        console.error(e);
        message.error('获取人员树请求失败');
      } finally {
        setPersonTreeLoading(false);
      }
    },
    [authHeaders],
  );

  /**
   * 获取角色列表
   */
  const fetchRoleList = useCallback(async () => {
    try {
      setRoleLoading(true);

      const res = await fetch('/v1/role/personrole_list', {
        method: 'GET',
        headers: authHeaders,
        credentials: 'include',
      });

      const result = await res.json();

      if (result.code === 0 || result.code === 200) {
        setRoleList(result.data || []);
      } else {
        message.error(result.message || '获取角色列表失败');
      }
    } catch (e) {
      console.error(e);
      message.error('获取角色列表请求失败');
    } finally {
      setRoleLoading(false);
    }
  }, [authHeaders]);

  /**
   * 获取人员详情
   */
  const fetchPersonDetail = useCallback(
    async (phone: string) => {
      if (!phone) {
        message.warning('人员电话为空');
        return;
      }

      try {
        setPersonDetailLoading(true);
        setCurrentPhone(phone);

        const res = await fetch('/v1/role/person-detail', {
          method: 'POST',
          headers: authHeaders,
          credentials: 'include',
          body: JSON.stringify({
            phone,
          }),
        });

        const result = await res.json();

        if (result.code === 0 || result.code === 200) {
          const detail = result.data || null;

          setPersonDetail(detail);

          const currentRole = detail?.roles?.[0];

          setSelectedRoleId(
            currentRole?.id !== undefined ? Number(currentRole.id) : null,
          );
        } else {
          message.error(result.message || '获取人员详情失败');
          setPersonDetail(null);
          setSelectedRoleId(null);
        }
      } catch (e) {
        console.error(e);
        message.error('获取人员详情请求失败');
      } finally {
        setPersonDetailLoading(false);
      }
    },
    [authHeaders],
  );

  useEffect(() => {
    fetchPersonTree();
    fetchRoleList();
  }, [fetchPersonTree, fetchRoleList]);

  /**
   * 点击搜索
   */
  const handleSearch = () => {
    fetchPersonTree(keyword.trim());
  };

  /**
   * 重置搜索
   */
  const handleReset = () => {
    setKeyword('');
    fetchPersonTree('');
  };

  /**
   * 点击树节点
   */
  const handleSelectTreeNode = (_selectedKeys: React.Key[], info: any) => {
    const node = info.node as PersonTreeNode;

    if (node.type !== 'person') {
      return;
    }

    const phone = node.phone || node.value || '';

    if (!phone) {
      message.warning('当前人员没有电话');
      return;
    }

    fetchPersonDetail(phone);
  };

  /**
   * 绑定角色
   */
  const handleBindRole = async () => {
    if (!currentPhone) {
      message.warning('请先点击选择一个人员');
      return;
    }

    if (!personDetail) {
      message.warning('请先获取人员信息');
      return;
    }

    if (!personDetail.bindable) {
      message.warning('当前人员未匹配到系统用户，不能绑定角色');
      return;
    }

    if (selectedRoleId === null) {
      message.warning('请选择一个角色');
      return;
    }

    try {
      setBindLoading(true);

      const res = await fetch('/v1/role/bind-persons', {
        method: 'POST',
        headers: authHeaders,
        credentials: 'include',
        body: JSON.stringify({
          role_id: selectedRoleId,
          phones: [currentPhone],
        }),
      });

      const result = await res.json();

      if (result.code === 0 || result.code === 200) {
        message.success(result.message || '角色绑定成功');
        await fetchPersonDetail(currentPhone);
      } else {
        message.error(result.message || '角色绑定失败');
      }
    } catch (e) {
      console.error(e);
      message.error('角色绑定请求失败');
    } finally {
      setBindLoading(false);
    }
  };

  /**
   * 自定义树节点标题
   */
  const titleRender = (node: any) => {
    const treeNode = node as PersonTreeNode;
    const title = treeNode.title || '';

    if (treeNode.type === 'person') {
      const phone = treeNode.phone || treeNode.value || '';
      const isCurrent = phone && phone === currentPhone;

      return (
        <span
          style={{
            cursor: 'pointer',
            color: isCurrent ? '#1677ff' : undefined,
            fontWeight: isCurrent ? 600 : undefined,
          }}
          onClick={(e) => {
            e.stopPropagation();

            if (!phone) {
              message.warning('当前人员没有电话信息');
              return;
            }

            fetchPersonDetail(phone);
          }}
        >
          <UserOutlined style={{ marginRight: 4 }} />
          {title}

          {treeNode.bindable === false && (
            <Tag color="default" style={{ marginLeft: 6 }}>
              未匹配用户
            </Tag>
          )}
        </span>
      );
    }

    if (treeNode.type === 'company') {
      return <span style={{ fontWeight: 600 }}>{title}</span>;
    }

    return <span>{title}</span>;
  };

  const { token } = theme.useToken();
  const successTagStyle: React.CSSProperties = {
    border: 'none',
    borderRadius: 999,
    background: 'rgba(0, 168, 112, 0.14)',
    color: '#00A870',
    fontWeight: 500,
    padding: '0 10px',
  };

  const defaultTagStyle: React.CSSProperties = {
    border: '1px solid rgba(140, 140, 140, 0.4)',
    borderRadius: 999,
    background: 'rgba(245, 245, 245, 0.14)',
    color: token.colorTextSecondary,
    fontWeight: 500,
    padding: '0 10px',
  };

  const greenButtonStyle: React.CSSProperties = {
    backgroundColor: '#00A870',
    borderColor: '#00A870',
    color: '#fff',
    borderRadius: 6,
  };

  const greenBoxTagStyle: React.CSSProperties = {
    border: 'none',
    borderRadius: 999,
    background: 'rgba(0, 168, 112, 0.12)',
    color: '#00A870',
    fontWeight: 500,
    padding: '0 10px',
  };

  const internalTagStyle: React.CSSProperties = {
    border: '1px solid rgba(0, 168, 160, 0.28)',
    borderRadius: 999,
    background: 'rgba(0, 168, 160, 0.14)',
    color: '#00A8A0',
    fontWeight: 500,
    padding: '0 10px',
  };

  const deptTagStyle: React.CSSProperties = {
    display: 'inline-flex',
    alignItems: 'center',
    color: token.colorText,
    fontWeight: 400,
    padding: 0,
    maxWidth: 160,
    overflow: 'hidden',
    whiteSpace: 'nowrap',
    background: 'transparent',
    border: 'none',
    marginInlineEnd: 0,
  };

  const orderBadgeStyle: React.CSSProperties = {
    border: '1px solid rgba(0, 122, 85, 0.28)',
    borderRadius: 4,
    background: 'rgba(0, 122, 85, 0.12)',
    color: '#00A870',
    fontWeight: 500,
    padding: '0 8px',
    height: 22,
    lineHeight: '20px',
  };

  const FILE_PERMISSION_TEXT: Record<number, string> = {
    1: '公开',
    2: '内部',
  };

  /**
   * 角色表格列
   */
  const roleColumns: ColumnsType<RoleInfo> = [
    {
      title: '角色名称',
      dataIndex: 'role_name',
      key: 'role_name',
      width: 140,
      ellipsis: true,
      align: 'center',
      render: (_, record) => {
        const name = record.role_name || record.name || '-';

        return (
          <Tooltip title={name}>
            <span
              style={{
                color: token.colorText,
                fontWeight: 600,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
                display: 'inline-block',
                maxWidth: '100%',
              }}
            >
              {name}
            </span>
          </Tooltip>
        );
      },
    },
    {
      title: '文件权限',
      dataIndex: 'file_permission_level',
      key: 'file_permission_level',
      width: 100,
      align: 'center',
      render: (value: number) => {
        if (value === undefined || value === null) {
          return <span style={{ color: token.colorTextTertiary }}>-</span>;
        }

        const text = FILE_PERMISSION_TEXT[value] || String(value);
        const isPublic = value === 1;

        return (
          <Tag style={isPublic ? greenBoxTagStyle : internalTagStyle}>
            {text}
          </Tag>
        );
      },
    },
    {
      title: '是否需要审批',
      dataIndex: 'need_approval',
      key: 'need_approval',
      width: 120,
      align: 'center',
      render: (value: boolean) => {
        return value ? (
          <Tag style={successTagStyle}>需要</Tag>
        ) : (
          <Tag style={defaultTagStyle}>不需要</Tag>
        );
      },
    },
    {
      title: '审批序号',
      dataIndex: 'approval_order',
      key: 'approval_order',
      width: 110,
      align: 'center',
      render: (value: number) => {
        return value ? (
          <Tag style={orderBadgeStyle}>第 {value} 级</Tag>
        ) : (
          <span style={{ color: token.colorTextTertiary }}>-</span>
        );
      },
    },
    {
      title: '所属部门',
      dataIndex: 'department_names',
      key: 'department_names',
      width: 210,
      render: (_, record) => {
        let names: string[] = [];

        if (Array.isArray(record.department_names)) {
          names = record.department_names.filter(Boolean);
        }

        if (!names.length && typeof record.department_name === 'string') {
          names = record.department_name
            .split('、')
            .map((item) => item.trim())
            .filter(Boolean);
        }

        if (!names.length && Array.isArray(record.departments)) {
          names = record.departments
            .map((dept) => {
              return (
                dept.name ||
                dept.departmentName ||
                dept.mdmName ||
                dept.longName ||
                dept.corporateName ||
                ''
              );
            })
            .filter(Boolean);
        }

        if (!names.length) {
          return <span style={{ color: token.colorTextTertiary }}>-</span>;
        }

        const expanded = expandedDeptRoleIds.includes(record.id);
        const defaultShowCount = 2;

        const visibleDeptNames = expanded
          ? names
          : names.slice(0, defaultShowCount);

        const canToggle = names.length > defaultShowCount;

        return (
          <div
            style={{
              position: 'relative',
              maxHeight: expanded ? 120 : 56,
              overflowY: expanded ? 'auto' : 'hidden',
              overflowX: 'hidden',
              paddingRight: canToggle ? 24 : 0,
            }}
          >
            <Tooltip title={names.join('、')}>
              <Space size={[4, 6]} wrap>
                {visibleDeptNames.map((name, index) => (
                  <Tag key={`${name}-${index}`} style={deptTagStyle}>
                    <span
                      style={{
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {name}
                    </span>
                  </Tag>
                ))}
              </Space>
            </Tooltip>

            {canToggle && (
              <span
                onClick={(e) => {
                  e.stopPropagation();
                  toggleDeptExpanded(record.id);
                }}
                style={{
                  position: 'absolute',
                  right: 0,
                  top: '50%',
                  transform: 'translateY(-50%)',
                  width: 22,
                  height: 22,
                  color: token.colorTextSecondary,
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  cursor: 'pointer',
                  zIndex: 2,
                }}
              >
                {expanded ? (
                  <UpOutlined style={{ fontSize: 11 }} />
                ) : (
                  <DownOutlined style={{ fontSize: 11 }} />
                )}
              </span>
            )}
          </div>
        );
      },
    },
    {
      title: '管理员',
      dataIndex: 'is_admin',
      key: 'is_admin',
      width: 90,
      align: 'center',
      render: (value: boolean) => {
        return value ? (
          <Tag style={successTagStyle}>是</Tag>
        ) : (
          <Tag style={defaultTagStyle}>否</Tag>
        );
      },
    },
    {
      title: '覆盖子部门',
      dataIndex: 'cover_child_dept',
      key: 'cover_child_dept',
      width: 110,
      align: 'center',
      render: (value: boolean) => {
        return value ? (
          <Tag style={successTagStyle}>是</Tag>
        ) : (
          <Tag style={defaultTagStyle}>否</Tag>
        );
      },
    },
    {
      title: '启用状态',
      dataIndex: 'enabled',
      key: 'enabled',
      width: 100,
      align: 'center',
      render: (value: boolean) => {
        return value ? (
          <Tag style={successTagStyle}>启用</Tag>
        ) : (
          <Tag style={defaultTagStyle}>停用</Tag>
        );
      },
    },
  ];

  const filteredRoleList = useMemo(() => {
    const kw = roleKeyword.trim().toLowerCase();

    if (!kw) {
      return roleList;
    }

    return roleList.filter((role) => {
      const roleName = String(role.role_name || role.name || '').toLowerCase();
      return roleName.includes(kw);
    });
  }, [roleList, roleKeyword]);

  const renderBindableTag = () => {
    if (!personDetail) {
      return null;
    }

    if (personDetail.bindable) {
      return <Tag color="green">可绑定角色</Tag>;
    }

    return <Tag color="red">未匹配系统用户，不可绑定</Tag>;
  };

  const descriptionLabelStyle: React.CSSProperties = {
    width: 130,
    minWidth: 130,
    whiteSpace: 'nowrap',
  };

  const descriptionContentStyle: React.CSSProperties = {
    width: 'calc((100% - 260px) / 2)',
    minWidth: 180,
    wordBreak: 'break-all',
  };

  const infoGridStyle: React.CSSProperties = {
    display: 'grid',
    gridTemplateColumns: '120px minmax(0, 1fr) 120px minmax(0, 1fr)',
    borderTop: `1px solid ${token.colorSplit}`,
    borderLeft: `1px solid ${token.colorSplit}`,
    marginBottom: 24,
  };

  const infoLabelStyle: React.CSSProperties = {
    padding: '8px 12px',
    background: token.colorFillAlter,
    borderRight: `1px solid ${token.colorSplit}`,
    borderBottom: `1px solid ${token.colorSplit}`,
    color: token.colorTextSecondary,
    whiteSpace: 'nowrap',
  };

  const infoValueStyle: React.CSSProperties = {
    padding: '8px 12px',
    borderRight: `1px solid ${token.colorSplit}`,
    borderBottom: `1px solid ${token.colorSplit}`,
    color: token.colorText,
    wordBreak: 'break-all',
    minWidth: 0,
  };

  const peacockTagStyle: React.CSSProperties = {
    border: 'none',
    borderRadius: 999,
    background: 'rgba(0, 168, 112, 0.12)',
    color: '#00A870',
    fontWeight: 500,
    padding: '0 10px',
  };

  const peacockButtonStyle: React.CSSProperties = {
    backgroundColor: '#00A870',
    borderColor: '#00A870',
    color: '#fff',
    borderRadius: 6,
  };

  const renderInfoItem = (label: React.ReactNode, value: React.ReactNode) => (
    <>
      <div style={infoLabelStyle}>{label}</div>
      <div style={infoValueStyle}>{value || '-'}</div>
    </>
  );

  return (
    <div
      style={{
        padding: 0,
        height: '100%',
        boxSizing: 'border-box',
        background: token.colorBgLayout,
      }}
    >
      <div
        style={{
          display: 'flex',
          gap: 0,
          height: 'calc(100vh - 120px)',
          minHeight: 600,
          background: token.colorBgLayout,
        }}
      >
        <Card
          title="组织人员"
          style={{
            width: 390,
            minWidth: 390,
            height: '100%',
            display: 'flex',
            flexDirection: 'column',
          }}
          bodyStyle={{
            flex: 1,
            overflow: 'hidden',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          <Space.Compact
            style={{
              width: '100%',
              marginBottom: 12,
            }}
          >
            <Input
              allowClear
              placeholder="搜索人员 / 部门 / 电话"
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              onPressEnter={handleSearch}
            />
            <Button
              type="primary"
              icon={<SearchOutlined />}
              onClick={handleSearch}
              style={greenButtonStyle}
            >
              搜索
            </Button>
          </Space.Compact>

          <div
            style={{
              flex: 1,
              overflow: 'auto',
              border: `1px solid ${token.colorBorderSecondary}`,
              borderRadius: 6,
              padding: 8,
              background: token.colorBgContainer,
            }}
          >
            <Spin spinning={personTreeLoading}>
              {personTreeData.length > 0 ? (
                <ConfigProvider
                  theme={{
                    components: {
                      Tree: {
                        nodeSelectedBg: 'rgba(0, 168, 112, 0.12)',
                        nodeHoverBg: 'rgba(0, 168, 112, 0.08)',
                      },
                    },
                  }}
                >
                  <Tree
                    showLine
                    blockNode
                    treeData={personTreeData as any}
                    titleRender={titleRender}
                    onSelect={handleSelectTreeNode}
                    defaultExpandAll={!!keyword}
                    selectedKeys={[]}
                  />
                </ConfigProvider>
              ) : (
                <Empty description="暂无组织人员数据" />
              )}
            </Spin>
          </div>
        </Card>

        <div
          style={{
            flex: 1,
            minWidth: 0,
            height: '100%',
            overflow: 'auto',
            display: 'flex',
            flexDirection: 'column',
            gap: 0,
          }}
        >
          <Card
            title="绑定角色"
            extra={
              <Space>
                {personDetail?.roles?.length ? (
                  <span>
                    当前角色：
                    <Tag style={peacockTagStyle}>
                      {personDetail.roles[0].role_name ||
                        personDetail.roles[0].name ||
                        '-'}
                    </Tag>
                  </span>
                ) : (
                  <Tag style={peacockTagStyle}>当前未绑定角色</Tag>
                )}

                <Button
                  type="primary"
                  loading={bindLoading}
                  disabled={
                    !currentPhone ||
                    !personDetail?.bindable ||
                    selectedRoleId === null
                  }
                  onClick={handleBindRole}
                  style={
                    !currentPhone ||
                    !personDetail?.bindable ||
                    selectedRoleId === null
                      ? undefined
                      : peacockButtonStyle
                  }
                >
                  绑定角色
                </Button>
              </Space>
            }
          >
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: 12,
                gap: 12,
              }}
            >
              <Input
                allowClear
                placeholder="请输入角色名称搜索"
                value={roleKeyword}
                onChange={(e) => setRoleKeyword(e.target.value)}
                prefix={<SearchOutlined />}
                style={{
                  width: 280,
                }}
              />

              <span
                style={{
                  color: token.colorTextSecondary,
                  fontSize: 13,
                }}
              >
                共 {filteredRoleList.length} 个角色
              </span>
            </div>

            <ConfigProvider
              theme={{
                token: {
                  colorPrimary: '#00A870',
                },
              }}
            >
              <Table<RoleInfo>
                rowKey="id"
                size="small"
                bordered
                loading={roleLoading}
                columns={roleColumns}
                dataSource={filteredRoleList}
                pagination={{
                  pageSize: 10,
                }}
                rowSelection={{
                  type: 'radio',
                  selectedRowKeys:
                    selectedRoleId !== null ? [selectedRoleId] : [],
                  onChange: (selectedRowKeys) => {
                    const roleId = selectedRowKeys[0];

                    setSelectedRoleId(
                      roleId !== undefined ? Number(roleId) : null,
                    );
                  },
                  getCheckboxProps: () => ({
                    disabled: !personDetail?.bindable,
                  }),
                }}
                locale={{
                  emptyText: roleKeyword ? '未搜索到匹配角色' : '暂无角色数据',
                }}
                scroll={{ x: 1100 }}
              />
            </ConfigProvider>
          </Card>
          <Card
            title={
              <Space>
                <span>人员详情</span>
                {/* {renderBindableTag()} */}
              </Space>
            }
            // extra={
            //   currentPhone ? (
            //     <Button
            //       size="small"
            //       icon={<ReloadOutlined />}
            //       onClick={() => fetchPersonDetail(currentPhone)}
            //     >
            //       刷新详情
            //     </Button>
            //   ) : null
            // }
          >
            <Spin spinning={personDetailLoading}>
              {!personDetail ? (
                <Empty
                  description="请从左侧选择一个人员"
                  style={{
                    marginTop: 120,
                    marginBottom: 120,
                  }}
                />
              ) : (
                <>
                  {!personDetail.user && (
                    <Alert
                      type="warning"
                      showIcon
                      style={{ marginBottom: 16 }}
                      message="该人员未匹配到系统用户"
                      description="当前绑定规则是：SyncPerson.phone == User.email。未匹配到 User 时，该人员不能绑定角色，也不会有角色信息。"
                    />
                  )}

                  <Title level={5}>基础信息</Title>

                  <div style={infoGridStyle}>
                    {renderInfoItem(
                      '姓名',
                      personDetail.person?.mdmName || '-',
                    )}
                    {renderInfoItem(
                      '电话',
                      personDetail.phone || personDetail.person?.phone || '-',
                    )}

                    {renderInfoItem(
                      '人员MDM编码',
                      personDetail.person?.mdmCode || '-',
                    )}
                    {renderInfoItem('邮箱', personDetail.person?.email || '-')}

                    {renderInfoItem(
                      'ERP ID',
                      personDetail.person?.erpid || '-',
                    )}
                    {renderInfoItem(
                      '部门编码',
                      personDetail.person?.organizationCode || '-',
                    )}

                    {renderInfoItem(
                      '组织',
                      personDetail.person?.organize || '-',
                    )}
                    {renderInfoItem('性别', personDetail.person?.gender || '-')}

                    {renderInfoItem(
                      '在职状态',
                      personDetail.person?.onDutyOrNot || '-',
                    )}
                    {renderInfoItem(
                      '人员类别',
                      personDetail.person?.personnelCategory || '-',
                    )}
                  </div>

                  <Title level={5}>系统用户</Title>

                  <div style={infoGridStyle}>
                    {renderInfoItem('User ID', personDetail.user?.id || '-')}
                    {renderInfoItem(
                      '账号 / Email',
                      personDetail.user?.email || '-',
                    )}

                    {renderInfoItem('昵称', personDetail.user?.nickname || '-')}
                    {renderInfoItem(
                      '状态',
                      personDetail.user?.status === 1 ||
                        personDetail.user?.status === '1' ? (
                        <Tag color="green">激活</Tag>
                      ) : personDetail.user?.status === 0 ||
                        personDetail.user?.status === '0' ? (
                        <Tag color="red">未激活</Tag>
                      ) : (
                        '-'
                      ),
                    )}
                  </div>

                  <Title level={5}>已绑定角色</Title>

                  <Table<RoleInfo>
                    rowKey="id"
                    size="small"
                    bordered
                    columns={roleColumns}
                    dataSource={personDetail.roles || []}
                    pagination={false}
                    locale={{
                      emptyText: '暂无绑定角色',
                    }}
                    scroll={{ x: 1100 }}
                  />
                </>
              )}
            </Spin>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default RolePersonDetailPage;
