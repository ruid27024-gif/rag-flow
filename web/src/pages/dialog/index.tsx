import {
  AppstoreOutlined,
  CommentOutlined,
  DownloadOutlined,
  FileTextOutlined,
  MessageOutlined,
  TeamOutlined,
  ThunderboltOutlined,
  UserOutlined,
} from '@ant-design/icons';
import {
  Alert,
  Button,
  Card,
  Col,
  Collapse,
  Empty,
  Layout,
  Row,
  Select,
  Spin,
  Statistic,
  Table,
  Tag,
  Typography,
  message,
} from 'antd';
import axios from 'axios';
import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { useNavigate } from 'react-router-dom';
import './GroupMemberStatsPage.css';

const { Sider, Content } = Layout;
const { Title, Text } = Typography;

type Period = 'all' | 'day' | 'week' | 'month' | 'year';

interface Member {
  user_id: string;
  nickname: string;
  token_usage: number;
  dialog_count: number;
}

interface GroupStats {
  group_id: string;
  group_name: string;
  period: Period;
  start_time: string | null;
  end_time: string | null;
  start_time_ts: number | null;
  end_time_ts: number | null;
  total_tokens: number;
  total_dialogs: number;
  members: Member[];
}

interface SelectedMember extends Member {
  group_id: string;
  group_name: string;
}

interface ConversationInfo {
  id: string;
  name: string;
  message: any[];
  create_date?: string;
  conversation_create_date?: string;
}

interface DialogInfo {
  id: string;
  name: string;
  create_date?: string;
  dialog_create_date?: string;
  conversations: ConversationInfo[];
}

const periodOptions = [
  { label: '全部', value: 'all' },
  { label: '天', value: 'day' },
  { label: '周', value: 'week' },
  { label: '月', value: 'month' },
  { label: '年', value: 'year' },
];

const departmentOptions = [
  { label: '全部', value: '全部' },
  { label: '工艺研究一室', value: '100146' },
  { label: '工艺研究二室', value: '100147' },
  { label: '工艺研究三室', value: '100148' },
  { label: '新品事业部研发部', value: '100051' },
  { label: '数字化管理中心', value: '100380' },
];

const getDisplayTime = (value?: string | null) => {
  if (!value) return '-';
  return value;
};

const DashboardShell = ({ children }: { children: React.ReactNode }) => {
  return (
    <div className="relative flex h-screen min-h-0 flex-col overflow-hidden p-6">
      {children}
    </div>
  );
};

const GroupMemberStatsPage: React.FC = () => {
  const navigate = useNavigate();

  const [switchSide, setSwitchSide] = useState<'left' | 'right'>('right');
  const [period, setPeriod] = useState<Period>('all');
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [dialogs, setDialogs] = useState<DialogInfo[]>([]);
  const [dialogLoading, setDialogLoading] = useState(false);
  const [groups, setGroups] = useState<GroupStats[]>([]);
  const [selectedMember, setSelectedMember] = useState<SelectedMember | null>(
    null,
  );
  const [expandedConvKeys, setExpandedConvKeys] = useState<string[]>([]);
  const [activeGroupKeys, setActiveGroupKeys] = useState<string[]>([]);
  const [organizationCode, setOrganizationCode] = useState('全部');

  const fetchingRef = useRef(false);

  const handleGoBoard = useCallback(() => {
    setSwitchSide('left');

    window.setTimeout(() => {
      navigate('/dashboard');
    }, 250);
  }, [navigate]);

  const handleExportExcel = async (
    tenantId: string,
    dialogId: string,
    dialogName: string,
  ) => {
    try {
      console.time('export_excel_total');
      console.time('export_excel_request');

      message.loading({ content: '正在生成日志文件...', key: 'exporting' });

      const response = await axios.post(
        '/v1/api/user_dialogs_export_excel',
        {
          tenant_id: tenantId,
          dialog_id: dialogId,
        },
        {
          responseType: 'blob',
        },
      );

      console.timeEnd('export_excel_request');

      const contentType = response.headers['content-type'];

      if (
        !contentType?.includes(
          'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
      ) {
        const errorText = await response.data.text();

        let errorMessage = '导出失败，请重试';

        try {
          const errorJson = JSON.parse(errorText);
          errorMessage =
            errorJson.message ||
            errorJson.retmsg ||
            errorJson.error ||
            errorMessage;
        } catch {
          errorMessage = errorText || errorMessage;
        }

        throw new Error(errorMessage);
      }

      const now = new Date();
      const pad = (n: number) => String(n).padStart(2, '0');
      const dateStr = `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(
        now.getDate(),
      )}_${pad(now.getHours())}${pad(now.getMinutes())}${pad(
        now.getSeconds(),
      )}`;

      const safeDialogName =
        dialogName?.replace(/[\\/:*?"<>|]/g, '_') || 'unknown_dialog';

      const fileName = `${safeDialogName}_${dateStr}.xlsx`;

      const blob = new Blob([response.data], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      });

      const link = document.createElement('a');
      const url = URL.createObjectURL(blob);

      link.href = url;
      link.download = fileName;
      link.style.visibility = 'hidden';

      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      setTimeout(() => {
        URL.revokeObjectURL(url);
      }, 5000);

      console.timeEnd('export_excel_total');

      message.success({
        content: '导出请求已完成，文件已开始下载',
        key: 'exporting',
      });
    } catch (error) {
      console.timeEnd('export_excel_total');
      console.error('Export failed:', error);

      message.error({
        content: error instanceof Error ? error.message : '导出失败，请重试',
        key: 'exporting',
      });
    }
  };

  const handleExportDepartmentExcel = async () => {
    try {
      message.loading({ content: '正在生成日志文件...', key: 'exporting' });

      const response = await axios.post(
        '/v1/api/user_dialogs_export_excel_all',
        {
          organizationCode,
        },
        {
          responseType: 'blob',
        },
      );

      const contentType = response.headers['content-type'];

      if (
        !contentType?.includes(
          'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
      ) {
        const errorText = await response.data.text();

        let errorMessage = '导出失败，请重试';

        try {
          const errorJson = JSON.parse(errorText);
          errorMessage =
            errorJson.message ||
            errorJson.retmsg ||
            errorJson.error ||
            errorMessage;
        } catch {
          errorMessage = errorText || errorMessage;
        }

        throw new Error(errorMessage);
      }

      const now = new Date();
      const pad = (n: number) => String(n).padStart(2, '0');
      const dateStr = `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(
        now.getDate(),
      )}_${pad(now.getHours())}${pad(now.getMinutes())}${pad(
        now.getSeconds(),
      )}`;

      const selectedDepartment =
        departmentOptions.find((item) => item.value === organizationCode)
          ?.label ||
        organizationCode ||
        '全部';

      const safeDepartmentName = selectedDepartment.replace(
        /[\\/:*?"<>|]/g,
        '_',
      );

      const fileName = `${safeDepartmentName}_${dateStr}.xlsx`;

      const blob = new Blob([response.data], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      });

      const link = document.createElement('a');
      const url = URL.createObjectURL(blob);

      link.href = url;
      link.download = fileName;
      link.style.visibility = 'hidden';

      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      setTimeout(() => {
        URL.revokeObjectURL(url);
      }, 5000);

      message.success({
        content: '日志文件已开始下载',
        key: 'exporting',
      });
    } catch (error) {
      console.error('Export failed:', error);

      message.error({
        content: error instanceof Error ? error.message : '导出失败，请重试',
        key: 'exporting',
      });
    }
  };

  const fetchGroupMemberStats = useCallback(async (currentPeriod: Period) => {
    if (fetchingRef.current) {
      return;
    }

    fetchingRef.current = true;

    try {
      setLoading(true);
      setErrorMsg('');

      const res = await fetch('/v1/api/group_member_stats', {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          period: currentPeriod,
        }),
      });

      if (!res.ok) {
        throw new Error(`接口请求失败，状态码：${res.status}`);
      }

      const json = await res.json();

      let list: GroupStats[] = [];

      if (Array.isArray(json)) {
        list = json;
      } else if (Array.isArray(json?.data)) {
        list = json.data;
      } else {
        throw new Error('接口返回格式不正确');
      }

      setGroups(list);

      const firstGroupWithMember = list.find(
        (group) => Array.isArray(group.members) && group.members.length > 0,
      );

      if (firstGroupWithMember) {
        const firstMember = firstGroupWithMember.members[0];

        setSelectedMember({
          ...firstMember,
          group_id: firstGroupWithMember.group_id,
          group_name: firstGroupWithMember.group_name,
        });
      } else {
        setSelectedMember(null);
      }
    } catch (error) {
      console.error('获取组成员统计失败:', error);

      const msg = error instanceof Error ? error.message : '获取组成员统计失败';
      setErrorMsg(msg);
      message.error(msg);
    } finally {
      setLoading(false);
      fetchingRef.current = false;
    }
  }, []);

  const fetchUserDialogs = useCallback(async (userId: string) => {
    if (!userId) return;

    try {
      setDialogLoading(true);

      const res = await fetch('/v1/api/user_dialogs_and_conversations', {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          tenant_id: userId,
        }),
      });

      if (!res.ok) {
        throw new Error(`获取对话失败，状态码：${res.status}`);
      }

      const json = await res.json();
      const list = Array.isArray(json) ? json : json?.data || [];
      setDialogs(list);
    } catch (error) {
      console.error('获取用户对话失败:', error);
      message.error('获取对话记录失败');
      setDialogs([]);
    } finally {
      setDialogLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchGroupMemberStats('all');
  }, [fetchGroupMemberStats]);

  useEffect(() => {
    if (selectedMember?.user_id) {
      fetchUserDialogs(selectedMember.user_id);
    } else {
      setDialogs([]);
    }
  }, [selectedMember, fetchUserDialogs]);

  const handlePeriodChange = async (value: Period) => {
    setPeriod(value);
    await fetchGroupMemberStats(value);
  };

  const handleSelectMember = (group: GroupStats, member: Member) => {
    setSelectedMember({
      ...member,
      group_id: group.group_id,
      group_name: group.group_name,
    });
  };

  const appTotal = useMemo(() => {
    return Array.isArray(dialogs) ? dialogs.length : 0;
  }, [dialogs]);

  const conversationTotal = useMemo(() => {
    if (!Array.isArray(dialogs)) return 0;

    return dialogs.reduce((sum, dialog) => {
      const conversations = Array.isArray(dialog.conversations)
        ? dialog.conversations
        : [];

      return sum + conversations.length;
    }, 0);
  }, [dialogs]);

  const messageTotal = useMemo(() => {
    if (!Array.isArray(dialogs)) return 0;

    return dialogs.reduce((dialogSum, dialog) => {
      const conversations = Array.isArray(dialog.conversations)
        ? dialog.conversations
        : [];

      const currentDialogMessageTotal = conversations.reduce(
        (convSum, conv) => {
          const messages = Array.isArray(conv.message) ? conv.message : [];
          return convSum + messages.length;
        },
        0,
      );

      return dialogSum + currentDialogMessageTotal;
    }, 0);
  }, [dialogs]);

  return (
    <>
      <DashboardShell>
        <div className="mb-7 flex items-center justify-between gap-4">
          <h1
            className="
              m-0
              flex
              items-center
              gap-2.5
              text-[28px]
              font-bold
              text-slate-900
              dark:text-white
            "
          >
            <TeamOutlined className="text-green-700" />
            团队数据仪表盘
          </h1>

          <div
            className="
              relative
              flex
              h-9
              w-[160px]
              items-center
              rounded-full
              border
              border-slate-200
              bg-slate-100
              p-1
              transition-colors
              dark:border-white/[0.08]
              dark:bg-white/[0.06]
            "
          >
            <div
              className={`
                absolute
                left-1
                top-1
                h-7
                w-[76px]
                rounded-full
                bg-white
                shadow-sm
                transition-transform
                duration-300
                ease-out
                dark:bg-[#00BEB4]
                ${switchSide === 'left' ? 'translate-x-0' : 'translate-x-[76px]'}
              `}
            />

            <button
              type="button"
              className={`
                relative
                z-10
                flex
                h-7
                flex-1
                items-center
                justify-center
                rounded-full
                p-0
                text-sm
                leading-none
                transition-colors
                ${
                  switchSide === 'left'
                    ? 'text-slate-900 dark:text-white'
                    : 'text-slate-500 dark:text-slate-400'
                }
              `}
              onClick={handleGoBoard}
            >
              看板
            </button>

            <button
              type="button"
              className={`
                relative
                z-10
                flex
                h-7
                flex-1
                items-center
                justify-center
                rounded-full
                p-0
                text-sm
                leading-none
                transition-colors
                ${
                  switchSide === 'right'
                    ? 'text-slate-900 dark:text-white'
                    : 'text-slate-500 dark:text-slate-400'
                }
              `}
              onClick={(event) => {
                event.preventDefault();
              }}
            >
              日志
            </button>
          </div>
        </div>

        <div className="mb-4 flex flex-wrap items-center gap-3 rounded-md border border-slate-200/70 bg-transparent px-4 py-3 dark:border-white/[0.08]">
          <div className="flex items-center gap-2">
            <TeamOutlined className="text-green-700 dark:text-green-400" />
            <Text strong className="dark:text-slate-100">
              部门日志导出
            </Text>
          </div>

          <Select
            style={{ width: 240 }}
            value={organizationCode}
            options={departmentOptions}
            onChange={(value) => setOrganizationCode(value)}
          />

          <Button
            type="primary"
            icon={<DownloadOutlined />}
            onClick={handleExportDepartmentExcel}
          >
            导出
          </Button>
        </div>

        <Layout className="stats-page">
          <Sider width={300} className="stats-sider">
            <div className="sider-header">
              <div className="sider-title">
                <FileTextOutlined className="text-green-700" />
                <span>用户日志</span>
              </div>
            </div>

            {loading ? (
              <div className="loading-box">
                <Spin tip="加载中..." />
              </div>
            ) : groups.length === 0 ? (
              <div className="empty-box">
                <Empty description="暂无数据" />
              </div>
            ) : (
              <div className="group-list">
                <Collapse
                  ghost
                  activeKey={activeGroupKeys}
                  onChange={(keys) => {
                    setActiveGroupKeys(
                      Array.isArray(keys) ? keys.map(String) : [String(keys)],
                    );
                  }}
                  items={groups.map((group) => {
                    const members = Array.isArray(group.members)
                      ? group.members
                      : [];

                    return {
                      key: group.group_id,
                      label: (
                        <div className="group-collapse-row">
                          <TeamOutlined className="group-collapse-icon" />

                          <span className="group-collapse-name">
                            {group.group_name || '未命名组'}
                          </span>

                          <span className="group-member-count-text">
                            {members.length}人
                          </span>
                        </div>
                      ),
                      children: (
                        <div className="group-member-list">
                          {members.length > 0 ? (
                            members.map((member) => {
                              const active =
                                selectedMember?.user_id === member.user_id &&
                                selectedMember?.group_id === group.group_id;

                              return (
                                <div
                                  key={`${group.group_id}_${member.user_id}`}
                                  className={`member-item ${
                                    active ? 'member-item-active' : ''
                                  }`}
                                  onClick={() =>
                                    handleSelectMember(group, member)
                                  }
                                >
                                  <div className="member-name">
                                    <UserOutlined
                                      style={{
                                        fontSize: '16px',
                                        marginRight: '8px',
                                        color: active ? '#00BEB4' : '#999',
                                      }}
                                    />
                                    <span>
                                      {member.nickname || '未命名用户'}
                                    </span>
                                  </div>
                                </div>
                              );
                            })
                          ) : (
                            <div className="no-member">暂无成员</div>
                          )}
                        </div>
                      ),
                    };
                  })}
                />
              </div>
            )}
          </Sider>

          <Content className="stats-content">
            <Card className="content-card">
              {errorMsg ? (
                <Alert
                  type="error"
                  showIcon
                  message="请求失败"
                  description={errorMsg}
                  className="error-alert"
                />
              ) : null}

              {loading ? (
                <div className="content-loading">
                  <Spin tip="正在加载统计数据..." />
                </div>
              ) : !selectedMember ? (
                <div className="content-empty">
                  <Empty description="暂无人员数据" />
                </div>
              ) : (
                <>
                  <div className="content-header">
                    <div>
                      <Title level={3} className="user-title">
                        {selectedMember.nickname || '未命名用户'}
                      </Title>

                      <div className="user-meta">
                        <Text type="secondary">
                          所属组：{selectedMember.group_name}
                        </Text>
                      </div>
                    </div>

                    <Tag color="cyan" className="period-tag">
                      当前周期：
                      {periodOptions.find((item) => item.value === period)
                        ?.label || '全部'}
                    </Tag>
                  </div>

                  <Row gutter={[24, 24]}>
                    <Col xs={24} sm={12} lg={8} xl={8}>
                      <Card className="stat-card token-card">
                        <Statistic
                          title="Token 消耗"
                          value={selectedMember.token_usage || 0}
                          prefix={<ThunderboltOutlined />}
                        />
                      </Card>
                    </Col>

                    <Col xs={24} sm={12} lg={8} xl={8}>
                      <Card className="stat-card dialog-card">
                        <Statistic
                          title="问答总数"
                          value={selectedMember.dialog_count || 0}
                          prefix={<MessageOutlined />}
                        />
                      </Card>
                    </Col>

                    <Col xs={24} sm={12} lg={8} xl={8}>
                      <Card className="stat-card app-card">
                        <Statistic
                          title="主题数量"
                          value={appTotal}
                          prefix={<AppstoreOutlined />}
                        />
                      </Card>
                    </Col>

                    <Col xs={24} sm={12} lg={8} xl={8}>
                      <Card className="stat-card conversation-card">
                        <Statistic
                          title="对话数量"
                          value={conversationTotal}
                          prefix={<CommentOutlined />}
                        />
                      </Card>
                    </Col>

                    <Col xs={24} sm={12} lg={8} xl={8}>
                      <Card className="stat-card message-card">
                        <Statistic
                          title="消息总数"
                          value={messageTotal}
                          prefix={<MessageOutlined />}
                        />
                      </Card>
                    </Col>

                    <Col xs={24} sm={12} lg={8} xl={8}>
                      <Card className="stat-card token-card">
                        <Statistic
                          title="当前组消耗 Token"
                          value={selectedMember.token_usage || 0}
                          prefix={<ThunderboltOutlined />}
                        />
                      </Card>
                    </Col>
                  </Row>

                  <div style={{ marginTop: 24 }}>
                    <Title level={4}>对话记录</Title>

                    {dialogLoading ? (
                      <div className="content-loading">
                        <Spin tip="正在加载对话数据..." />
                      </div>
                    ) : dialogs.length === 0 ? (
                      <Empty description="该用户暂无对话记录" />
                    ) : (
                      <Table
                        dataSource={dialogs}
                        rowKey={(record) => String(record.id)}
                        pagination={false}
                        bordered
                        columns={[
                          {
                            title: '主题名称',
                            dataIndex: 'name',
                            key: 'name',
                            render: (text) => (
                              <Text strong style={{ color: '#1890ff' }}>
                                {text || '未命名主题'}
                              </Text>
                            ),
                          },
                          {
                            title: '主题创建时间',
                            dataIndex: 'dialog_create_date',
                            key: 'dialog_create_date',
                            width: 180,
                            align: 'center',
                            render: (_value, record) => (
                              <Text type="secondary">
                                {getDisplayTime(
                                  record.dialog_create_date ||
                                    record.create_date,
                                )}
                              </Text>
                            ),
                          },
                          {
                            title: '对话数量',
                            dataIndex: 'conversations',
                            key: 'conv_count',
                            width: 120,
                            align: 'center',
                            render: (conversations) => {
                              const count = Array.isArray(conversations)
                                ? conversations.length
                                : 0;

                              return (
                                <Tag color={count > 0 ? 'blue' : 'default'}>
                                  {count} 个对话
                                </Tag>
                              );
                            },
                          },
                          {
                            title: '操作',
                            key: 'action',
                            width: 150,
                            align: 'center',
                            render: (_, record) => {
                              const conversations = Array.isArray(
                                record.conversations,
                              )
                                ? record.conversations
                                : [];

                              const disabled = conversations.length === 0;

                              return (
                                <Button
                                  type="primary"
                                  size="small"
                                  icon={<DownloadOutlined />}
                                  disabled={disabled}
                                  onClick={() => {
                                    if (disabled) return;

                                    handleExportExcel(
                                      selectedMember.user_id,
                                      record.id,
                                      record.name,
                                    );
                                  }}
                                >
                                  导出日志
                                </Button>
                              );
                            },
                          },
                        ]}
                        expandable={{
                          expandedRowRender: (dialogRecord) => {
                            const conversations = Array.isArray(
                              dialogRecord.conversations,
                            )
                              ? dialogRecord.conversations
                              : [];

                            if (conversations.length === 0) {
                              return <Empty description="暂无对话" />;
                            }

                            return (
                              <div style={{ paddingLeft: '2em' }}>
                                <div
                                  onClick={(event) => {
                                    event.stopPropagation();
                                  }}
                                >
                                  <Table
                                    dataSource={conversations}
                                    showHeader={false}
                                    rowKey={(convRecord) =>
                                      `${String(dialogRecord.id)}-${String(
                                        convRecord.id,
                                      )}`
                                    }
                                    pagination={false}
                                    size="small"
                                    bordered={false}
                                    expandable={{
                                      expandedRowKeys: expandedConvKeys,
                                      showExpandColumn: false,
                                      expandedRowRender: (convRecord) => {
                                        const messages = Array.isArray(
                                          convRecord.message,
                                        )
                                          ? convRecord.message
                                          : [];

                                        if (messages.length === 0) {
                                          return (
                                            <Text type="secondary">
                                              暂无消息
                                            </Text>
                                          );
                                        }

                                        const messageColumns = [
                                          {
                                            title: '发送者',
                                            dataIndex: 'role',
                                            key: 'role',
                                            width: 120,
                                            render: (role: string) => {
                                              if (role === 'user') {
                                                return (
                                                  <Tag color="green">用户</Tag>
                                                );
                                              }

                                              if (role === 'assistant') {
                                                return (
                                                  <Tag color="blue">助手</Tag>
                                                );
                                              }

                                              if (role === 'system') {
                                                return (
                                                  <Tag color="orange">系统</Tag>
                                                );
                                              }

                                              return (
                                                <Tag>{role || '未知'}</Tag>
                                              );
                                            },
                                          },
                                          {
                                            title: '消息详情',
                                            dataIndex: 'content',
                                            key: 'content',
                                            render: (content: any) => (
                                              <Text>{content || '-'}</Text>
                                            ),
                                          },
                                        ];

                                        return (
                                          <div
                                            onClick={(event) => {
                                              event.stopPropagation();
                                            }}
                                          >
                                            <Table
                                              dataSource={messages}
                                              columns={messageColumns}
                                              rowKey={(msgRecord, index) =>
                                                String(
                                                  msgRecord.id ??
                                                    `${dialogRecord.id}-${convRecord.id}-${index}`,
                                                )
                                              }
                                              pagination={false}
                                              size="small"
                                              bordered={false}
                                              onRow={() => ({
                                                onClick: (event) => {
                                                  event.stopPropagation();
                                                },
                                              })}
                                            />
                                          </div>
                                        );
                                      },
                                    }}
                                    onRow={(convRecord) => ({
                                      onClick: (event) => {
                                        event.stopPropagation();

                                        const currentKey = `${String(
                                          dialogRecord.id,
                                        )}-${String(convRecord.id)}`;

                                        setExpandedConvKeys((prev) =>
                                          prev.includes(currentKey)
                                            ? prev.filter(
                                                (key) => key !== currentKey,
                                              )
                                            : [...prev, currentKey],
                                        );
                                      },
                                      style: {
                                        cursor: 'pointer',
                                      },
                                    })}
                                    columns={[
                                      {
                                        dataIndex: 'name',
                                        key: 'name',
                                        render: (text) => (
                                          <span
                                            style={{
                                              fontWeight: 600,
                                              color: '#FF69B4',
                                            }}
                                          >
                                            {text || '新对话'}
                                          </span>
                                        ),
                                      },
                                      {
                                        dataIndex: 'conversation_create_date',
                                        key: 'conversation_create_date',
                                        width: 180,
                                        align: 'center',
                                        render: (_value, record) => (
                                          <Text type="secondary">
                                            {getDisplayTime(
                                              record.conversation_create_date ||
                                                record.create_date,
                                            )}
                                          </Text>
                                        ),
                                      },
                                      {
                                        dataIndex: 'message',
                                        key: 'message',
                                        width: 90,
                                        align: 'center',
                                        render: (messages) => (
                                          <Tag color="pink">
                                            {Array.isArray(messages)
                                              ? messages.length
                                              : 0}{' '}
                                            条消息
                                          </Tag>
                                        ),
                                      },
                                    ]}
                                  />
                                </div>
                              </div>
                            );
                          },
                        }}
                      />
                    )}
                  </div>
                </>
              )}
            </Card>
          </Content>
        </Layout>
      </DashboardShell>
    </>
  );
};

export default GroupMemberStatsPage;
