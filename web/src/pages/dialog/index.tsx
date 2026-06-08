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
  Empty,
  Layout,
  Row,
  Spin,
  Statistic,
  Table,
  Tag,
  Typography,
  message,
} from 'antd';
import axios from 'axios'; // 假设你使用 axios
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

// 1. 定义对话（Conversation）接口
interface ConversationInfo {
  id: string;
  name: string;
  message: any[]; // 对应后端的 JSONField，通常是一个包含消息对象的数组
}

// 2. 定义应用（Dialog）接口，内部嵌套 Conversation
interface DialogInfo {
  id: string;
  name: string;
  conversations: ConversationInfo[]; // 核心：直接对应后端返回的嵌套数组
}

const periodOptions = [
  { label: '全部', value: 'all' },
  { label: '天', value: 'day' },
  { label: '周', value: 'week' },
  { label: '月', value: 'month' },
  { label: '年', value: 'year' },
];

/**
 * 页面外壳 (纯净版)
 */
const DashboardShell = ({ children }) => {
  return (
    <div className="relative h-screen overflow-y-auto p-6">{children}</div>
  );
};

const GroupMemberStatsPage: React.FC = () => {
  // 定义导出函数
  const handleExportExcel = async (tenantId: string, dialogId: string) => {
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

      console.log('导出接口已返回:', response);
      console.log('导出接口状态码:', response.status);
      console.log('导出接口 headers:', response.headers);
      console.log('导出接口 content-type:', response.headers['content-type']);
      console.log('导出文件 blob:', response.data);
      console.log('导出文件大小 bytes:', response.data?.size);

      const contentType = response.headers['content-type'];

      if (
        !contentType?.includes(
          'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
      ) {
        const errorText = await response.data.text();

        console.log('导出接口返回非 Excel 内容:', errorText);

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

      console.time('export_excel_blob_download');

      const blob = new Blob([response.data], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      });

      console.log('构造后的下载 blob:', blob);
      console.log('构造后的下载 blob size:', blob.size);

      const link = document.createElement('a');
      const url = URL.createObjectURL(blob);

      console.log('生成的 blob url:', url);

      link.href = url;
      link.download = `dialog_logs_${dialogId}.xlsx`;
      link.style.visibility = 'hidden';

      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      setTimeout(() => {
        URL.revokeObjectURL(url);
        console.log('blob url 已释放:', url);
      }, 5000);

      console.timeEnd('export_excel_blob_download');
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

  const [switchSide, setSwitchSide] = useState<'left' | 'right'>('right');
  const navigate = useNavigate();
  const handleGoBoard = useCallback(() => {
    setSwitchSide('left');

    window.setTimeout(() => {
      navigate('/dashboard');
    }, 250);
  }, [navigate]);

  // 记录当前展开的 Conversation ID 数组
  const [expandedConvKeys, setExpandedConvKeys] = useState<string[]>([]);
  const [period, setPeriod] = useState<Period>('all');
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  // 【新增】存储当前选中用户的对话数据
  const [dialogs, setDialogs] = useState<DialogInfo[]>([]);
  const [dialogLoading, setDialogLoading] = useState(false);

  const [groups, setGroups] = useState<GroupStats[]>([]);
  const [selectedMember, setSelectedMember] = useState<SelectedMember | null>(
    null,
  );

  const fetchingRef = useRef(false);

  /**
   * 获取组成员统计数据
   */
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

      /**
       * 兼容两种返回：
       * 1. 直接返回数组
       * [
       *   { group_id, group_name, members: [] }
       * ]
       *
       * 2. get_json_result 格式
       * {
       *   code: 0,
       *   data: [
       *     { group_id, group_name, members: [] }
       *   ]
       * }
       */
      if (Array.isArray(json)) {
        list = json;
      } else if (Array.isArray(json?.data)) {
        list = json.data;
      } else {
        throw new Error('接口返回格式不正确');
      }

      setGroups(list);

      /**
       * 默认选中第一个有成员的组里的第一个人
       */
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

  /**
   * 【新增】根据用户 ID 获取对话列表
   */
  const fetchUserDialogs = useCallback(async (userId: string) => {
    if (!userId) return;

    try {
      setDialogLoading(true);
      const res = await fetch('/v1/api/user_dialogs_and_conversations', {
        // 替换为实际的后端接口地址
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

      // 兼容返回格式（直接数组或 { data: [] }）
      const list = Array.isArray(json) ? json : json?.data || [];
      //       console.log(list)
      setDialogs(list);
      console.log(dialogs);
    } catch (error) {
      console.error('获取用户对话失败:', error);
      message.error('获取对话记录失败');
      setDialogs([]);
    } finally {
      setDialogLoading(false);
    }
  }, []);

  /**
   * 页面进入默认请求 all
   */
  useEffect(() => {
    fetchGroupMemberStats('all');
  }, [fetchGroupMemberStats]);

  /**
   * 【新增】当选中的人员发生变化时，重新获取对话数据
   */
  useEffect(() => {
    if (selectedMember?.user_id) {
      console.log(selectedMember.user_id);
      fetchUserDialogs(selectedMember.user_id);
    } else {
      setDialogs([]); // 如果没有选中人，清空对话列表
    }
  }, [selectedMember, fetchUserDialogs]);

  /**
   * 切换统计周期
   */
  const handlePeriodChange = async (value: Period) => {
    setPeriod(value);
    await fetchGroupMemberStats(value);
  };

  /**
   * 点击左侧人员
   */
  const handleSelectMember = (group: GroupStats, member: Member) => {
    setSelectedMember({
      ...member,
      group_id: group.group_id,
      group_name: group.group_name,
    });
  };

  /**
   * 全部组 Token 总数
   */
  const allTokenTotal = useMemo(() => {
    return groups.reduce(
      (sum, group) => sum + Number(group.total_tokens || 0),
      0,
    );
  }, [groups]);

  /**
   * 当前用户应用数量
   */
  const appTotal = useMemo(() => {
    return Array.isArray(dialogs) ? dialogs.length : 0;
  }, [dialogs]);

  /**
   * 当前用户对话数量
   */
  const conversationTotal = useMemo(() => {
    if (!Array.isArray(dialogs)) return 0;

    return dialogs.reduce((sum, dialog) => {
      const conversations = Array.isArray(dialog.conversations)
        ? dialog.conversations
        : [];

      return sum + conversations.length;
    }, 0);
  }, [dialogs]);

  /**
   * 当前用户消息总数
   */
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

  /**
   * 全部组问答总数
   */
  const allDialogTotal = useMemo(() => {
    return groups.reduce(
      (sum, group) => sum + Number(group.total_dialogs || 0),
      0,
    );
  }, [groups]);

  /**
   * 当前选中人员所在组
   */
  const selectedGroup = useMemo(() => {
    if (!selectedMember) return null;

    return groups.find((group) => group.group_id === selectedMember.group_id);
  }, [groups, selectedMember]);

  return (
    <>
      <DashboardShell>
        <div className="mb-7 flex items-center justify-between">
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
            <TeamOutlined className="text-[#00BEB4]" />
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

        <Layout className="stats-page">
          <Sider width={300} className="stats-sider">
            <div className="sider-header">
              <div className="sider-title">
                <FileTextOutlined />
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
                {groups.map((group) => (
                  <div key={group.group_id} className="group-block">
                    <div className="group-title">
                      <TeamOutlined />
                      <span>{group.group_name || '未命名组'}</span>
                    </div>

                    {Array.isArray(group.members) &&
                    group.members.length > 0 ? (
                      group.members.map((member) => {
                        const active =
                          selectedMember?.user_id === member.user_id &&
                          selectedMember?.group_id === group.group_id;

                        return (
                          <div
                            key={`${group.group_id}_${member.user_id}`}
                            className={`member-item ${active ? 'member-item-active' : ''}`}
                            onClick={() => handleSelectMember(group, member)}
                          >
                            <div className="member-name">
                              {/* 图标大小恢复为 16px，颜色可以跟随文字或保持灰色 */}
                              <UserOutlined
                                style={{
                                  fontSize: '16px',
                                  marginRight: '8px',
                                  color: '#999',
                                }}
                              />
                              <span>{member.nickname || '未命名用户'}</span>
                            </div>
                          </div>
                        );
                      })
                    ) : (
                      <div className="no-member">暂无成员</div>
                    )}
                  </div>
                ))}
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
                          title="应用数量"
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

                  {/* 【新增】对话记录表格展示区域 */}
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
                            title: '应用名称 (Dialog)',
                            dataIndex: 'name',
                            key: 'name',
                            render: (text) => (
                              <Text strong style={{ color: '#1890ff' }}>
                                {text || '未命名应用'}
                              </Text>
                            ),
                          },

                          // ✅ 新增这一列：操作/导出
                          {
                            title: '操作',
                            key: 'action',
                            width: 150, // 根据按钮宽度调整
                            align: 'center',
                            render: (_, record) => (
                              <Button
                                type="primary"
                                size="small"
                                icon={<DownloadOutlined />} // 可选：添加一个下载图标
                                onClick={() =>
                                  handleExportExcel(
                                    selectedMember.user_id,
                                    record.id,
                                  )
                                }
                              >
                                导出日志
                              </Button>
                            ),
                          },
                          {
                            title: '对话数量',
                            dataIndex: 'conversations',
                            key: 'conv_count',
                            width: 120,
                            align: 'center',
                            render: (conversations) => (
                              <Tag color="blue">
                                {Array.isArray(conversations)
                                  ? conversations.length
                                  : 0}{' '}
                                个对话
                              </Tag>
                            ),
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
                                    // 防止点击内层区域时触发外层 Dialog 的收起
                                    event.stopPropagation();
                                  }}
                                >
                                  <Table
                                    dataSource={conversations}
                                    showHeader={false}
                                    rowKey={(convRecord) =>
                                      `${String(dialogRecord.id)}-${String(convRecord.id)}`
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
                                            render: (role) => {
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
                                            render: (content) => (
                                              <Text>{content || '-'}</Text>
                                            ),
                                          },
                                        ];

                                        return (
                                          <div
                                            onClick={(event) => {
                                              // 防止点击消息表格时，又触发 Conversation 行的展开/收起
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

                                        const currentKey = `${String(dialogRecord.id)}-${String(
                                          convRecord.id,
                                        )}`;

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
                                        dataIndex: 'id',
                                        key: 'name',
                                        render: (text) => (
                                          <span
                                            style={{
                                              fontWeight: 600,
                                              color: '#FF69B4', // 直接用纯正的 HotPink，不加任何渐变
                                            }}
                                          >
                                            {text || '新对话'}
                                          </span>
                                        ),
                                      },
                                      {
                                        dataIndex: 'message',
                                        key: 'message',
                                        width: 50,
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
