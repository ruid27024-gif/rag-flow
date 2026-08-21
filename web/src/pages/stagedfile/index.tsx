import { getAuthorization } from '@/utils/authorization-util';
import { DownOutlined } from '@ant-design/icons';
import {
  Card,
  Select,
  Space,
  Table,
  Tag,
  Tooltip,
  Typography,
  message,
} from 'antd';

import type { ColumnsType } from 'antd/es/table';

import { RAGFlowPagination } from '@/components/ui/ragflow-pagination';
import React, { useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';

const { Text } = Typography;

const PEACOCK_GREEN = '#1FA67A';

type CollapsibleApproverListProps = {
  approvers?: ApproverItem[];
  defaultCount?: number;
};

type TagOption = {
  option_code: string;
  option_name: string;
};

type FileTagItem = {
  type_code: string;
  type_name: string;
  multi_select?: boolean;
  required?: boolean;
  option_names?: string[];
  options?: TagOption[];
};

type ApproverItem = {
  user_id: string;
  user_name?: string;
  email?: string | null;
  avatar?: string | null;
  mdm_code?: string | null;
  mdm_name?: string | null;
  department_id?: string | null;
  department_name?: string | null;
  role_id?: number | null;
  role_name?: string | null;
  approver_user_id?: string;
  approver_name?: string;
  id?: string;
  name?: string;

  /**
   * 兼容老字段。
   * 新逻辑不再使用 approval_order。
   */
  approval_order?: number | null;
};

type DepartmentInfo = {
  department_id?: string | null;
  department_name?: string | null;
  is_reference_kb?: boolean;
  is_global_reference_kb?: boolean;
  tenant_id?: string;
} | null;

type StagedFileItem = {
  id: string;
  batch_id?: string;
  kb_id: string;
  tenant_id?: string;

  user_id: string;
  user_name?: string;
  user_email?: string;
  user_avatar?: string;

  filename: string;
  path?: string;
  size?: number;

  status: string;
  doc_id?: string | null;

  created_at?: string;
  approved_at?: string | null;
  approved_by?: string | null;
  committed_at?: string | null;
  error_msg?: string | null;

  tags?: FileTagItem[];

  /**
   * 新字段：统一审批人。
   */
  approvers?: ApproverItem[] | null;

  /**
   * 如果后端字段叫 approval_users，也兼容。
   */
  approval_users?: ApproverItem[] | null;

  /**
   * 老字段兼容。
   */
  approval_level_1?: ApproverItem[] | null;
  approval_level_2?: ApproverItem[] | null;
};

type ApproverConfig = {
  department?: DepartmentInfo;

  /**
   * 新字段：统一审批人。
   */
  approvers?: ApproverItem[];

  /**
   * 老字段兼容。
   */
  level_1?: ApproverItem[];
  level_2?: ApproverItem[];
};

type ListResponseData = {
  is_admin: boolean;
  is_approver?: boolean;
  total: number;
  page: number;
  page_size: number;

  /**
   * 推荐新结构：
   * {
   *   department: {},
   *   approvers: []
   * }
   */
  department?: DepartmentInfo;

  /**
   * 兼容两种：
   * 1. approvers: []
   * 2. approvers: { department: {}, approvers: [] }
   */
  approvers?: ApproverItem[] | ApproverConfig | null;

  items: StagedFileItem[];
};

const statusOptions = [
  { label: '全部', value: '' },
  { label: '待审批', value: 'pending' },
  { label: '已提交 OA', value: 'oa_submitted' },
  { label: '一级审批中', value: 'pending_level_1' },
  { label: '二级审批中', value: 'pending_level_2' },
  { label: '审批通过', value: 'approved' },
  { label: '入库中', value: 'importing' },
  { label: '已入库', value: 'imported' },
  { label: '部分入库', value: 'partial_imported' },
  { label: '已拒绝', value: 'rejected' },
  { label: '入库失败', value: 'import_failed' },
];

const statusTextMap: Record<string, string> = {
  pending: '待审批',
  oa_submitted: '已提交 OA',
  pending_approval: '审批中',
  pending_level_1: '一级审批中',
  pending_level_2: '二级审批中',
  approved: '审批通过，准备入库',

  committing: '入库中',
  importing: '入库中',

  imported: '已入库',
  partial_imported: '部分入库',

  rejected: '已拒绝',

  failed: '失败',
  import_failed: '入库失败',

  callback_success: '回调成功',
  callback_failed: '回调失败',

  deleted: '已删除',
};

const statusColorMap: Record<string, React.CSSProperties> = {
  pending: {
    color: '#0f766e',
    backgroundColor: '#f0fdfa',
    borderColor: '#99f6e4',
  },
  oa_submitted: {
    color: '#0f766e',
    backgroundColor: '#f0fdfa',
    borderColor: '#99f6e4',
  },
  pending_approval: {
    color: '#0f766e',
    backgroundColor: '#f0fdfa',
    borderColor: '#99f6e4',
  },
  pending_level_1: {
    color: '#0f766e',
    backgroundColor: '#f0fdfa',
    borderColor: '#99f6e4',
  },
  pending_level_2: {
    color: '#0f766e',
    backgroundColor: '#f0fdfa',
    borderColor: '#99f6e4',
  },
  approved: {
    color: '#047857',
    backgroundColor: '#ecfdf5',
    borderColor: '#86efac',
  },
  committing: {
    color: '#0f766e',
    backgroundColor: '#f0fdfa',
    borderColor: '#99f6e4',
  },
  importing: {
    color: '#0f766e',
    backgroundColor: '#f0fdfa',
    borderColor: '#99f6e4',
  },
  imported: {
    color: '#ffffff',
    backgroundColor: '#16a36f',
    borderColor: '#16a36f',
  },
  partial_imported: {
    color: '#a16207',
    backgroundColor: '#fefce8',
    borderColor: '#fde68a',
  },
  rejected: {
    color: '#b91c1c',
    backgroundColor: '#fef2f2',
    borderColor: '#fecaca',
  },
  failed: {
    color: '#b91c1c',
    backgroundColor: '#fef2f2',
    borderColor: '#fecaca',
  },
  import_failed: {
    color: '#b91c1c',
    backgroundColor: '#fef2f2',
    borderColor: '#fecaca',
  },
  callback_failed: {
    color: '#b91c1c',
    backgroundColor: '#fef2f2',
    borderColor: '#fecaca',
  },
  callback_success: {
    color: '#047857',
    backgroundColor: '#ecfdf5',
    borderColor: '#86efac',
  },
  deleted: {
    color: '#6b7280',
    backgroundColor: '#f9fafb',
    borderColor: '#d1d5db',
  },
};

const formatFileSize = (size?: number) => {
  if (!size) return '0 B';

  if (size < 1024) {
    return `${size} B`;
  }

  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(2)} KB`;
  }

  if (size < 1024 * 1024 * 1024) {
    return `${(size / 1024 / 1024).toFixed(2)} MB`;
  }

  return `${(size / 1024 / 1024 / 1024).toFixed(2)} GB`;
};

const isApproverArray = (value: unknown): value is ApproverItem[] => {
  return Array.isArray(value);
};

const uniqueApprovers = (list: ApproverItem[]) => {
  const result: ApproverItem[] = [];
  const added = new Set<string>();

  list.forEach((item) => {
    if (!item) return;

    const key = String(item.user_id || '');

    if (!key) return;

    if (added.has(key)) return;

    result.push(item);
    added.add(key);
  });

  return result;
};

/**
 * 兼容后端不同返回结构，统一整理成：
 * {
 *   department,
 *   approvers
 * }
 */
const normalizeApproverConfig = (
  data?: ListResponseData | null,
): ApproverConfig | null => {
  if (!data) {
    return null;
  }

  const rawApprovers = data.approvers;

  /**
   * 新推荐结构：
   * {
   *   department: {},
   *   approvers: []
   * }
   */
  if (Array.isArray(rawApprovers)) {
    return {
      department: data.department || null,
      approvers: uniqueApprovers(rawApprovers),
    };
  }

  /**
   * 老结构或嵌套结构：
   * {
   *   approvers: {
   *     department: {},
   *     approvers: []
   *   }
   * }
   */
  if (rawApprovers && typeof rawApprovers === 'object') {
    const config = rawApprovers as ApproverConfig;

    const list = config.approvers || [
      ...(config.level_1 || []),
      ...(config.level_2 || []),
    ];

    return {
      department: config.department || data.department || null,
      approvers: uniqueApprovers(list),
      level_1: config.level_1,
      level_2: config.level_2,
    };
  }

  return {
    department: data.department || null,
    approvers: [],
  };
};

/**
 * 获取每一行文件的审批人。
 * 优先使用新字段，兼容老字段。
 */
const getRowApprovers = (record: StagedFileItem): ApproverItem[] => {
  const list = record.approvers ||
    record.approval_users || [
      ...(record.approval_level_1 || []),
      ...(record.approval_level_2 || []),
    ];

  return uniqueApprovers(list || []);
};

type CollapsibleTagListProps = {
  tags?: string[];
  defaultCount?: number;
};

const CollapsibleTagList: React.FC<CollapsibleTagListProps> = ({
  tags = [],
  defaultCount = 1,
}) => {
  const [expanded, setExpanded] = useState(false);

  if (!tags || tags.length === 0) {
    return <Text type="secondary">-</Text>;
  }

  const visibleTags = expanded ? tags : tags.slice(0, defaultCount);

  return (
    <div
      style={{
        position: 'relative',
        width: '100%',
        minWidth: 0,
        boxSizing: 'border-box',
        paddingRight: tags.length > defaultCount ? 18 : 0,
      }}
    >
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: 4,
          width: '100%',
          minWidth: 0,
          alignItems: 'flex-start',
        }}
      >
        {visibleTags.map((name, index) => (
          <Tag
            key={`${name}_${index}`}
            style={{
              marginRight: 0,
              marginBottom: 2,
              backgroundColor: PEACOCK_GREEN,
              borderColor: PEACOCK_GREEN,
              color: '#fff',
              fontSize: 12,
              whiteSpace: 'normal',
              wordBreak: 'break-all',
              maxWidth: '100%',
            }}
          >
            {name}
          </Tag>
        ))}
      </div>

      {tags.length > defaultCount ? (
        <span
          role="button"
          tabIndex={0}
          aria-label={expanded ? '收起标签' : '展开标签'}
          onClick={() => setExpanded((value) => !value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' || event.key === ' ') {
              event.preventDefault();
              setExpanded((value) => !value);
            }
          }}
          style={{
            position: 'absolute',
            right: 0,
            top: 0,
            cursor: 'pointer',
            color: '#9ca3af',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: 18,
            height: 20,
            borderRadius: 4,
            transition: 'background-color 180ms ease',
          }}
        >
          <DownOutlined
            style={{
              fontSize: 10,
              color: expanded ? PEACOCK_GREEN : '#9ca3af',
              transition: 'transform 180ms ease, color 180ms ease',
              transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)',
            }}
          />
        </span>
      ) : null}
    </div>
  );
};

const renderTagValue = (tags?: FileTagItem[] | null, typeCode?: string) => {
  if (!tags || !tags.length || !typeCode) {
    return <Text type="secondary">-</Text>;
  }

  const tagItem = tags.find((item) => item.type_code === typeCode);

  if (!tagItem) {
    return <Text type="secondary">-</Text>;
  }

  const optionNames =
    tagItem.option_names && tagItem.option_names.length > 0
      ? tagItem.option_names
      : tagItem.options?.map((item) => item.option_name || item.option_code) ||
        [];

  if (!optionNames.length) {
    return <Text type="secondary">-</Text>;
  }

  return <CollapsibleTagList tags={optionNames} defaultCount={1} />;
};

const getApproverName = (item: ApproverItem) => {
  return (
    item.user_name ||
    item.approver_name ||
    item.name ||
    item.user_id ||
    item.approver_user_id ||
    item.id ||
    '-'
  );
};

const CollapsibleApproverList: React.FC<CollapsibleApproverListProps> = ({
  approvers = [],
  defaultCount = 1,
}) => {
  const [expanded, setExpanded] = useState(false);

  if (!approvers || approvers.length === 0) {
    return <Text type="secondary">-</Text>;
  }

  const visibleApprovers = expanded
    ? approvers
    : approvers.slice(0, defaultCount);

  const hasMore = approvers.length > defaultCount;

  return (
    <div
      style={{
        position: 'relative',
        width: '100%',
        minWidth: 0,
        boxSizing: 'border-box',
        paddingRight: hasMore ? 18 : 0,
      }}
    >
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: 4,
          width: '100%',
          minWidth: 0,
          alignItems: 'flex-start',
        }}
      >
        {visibleApprovers.map((item, index) => {
          const name = getApproverName(item);
          const key =
            item.user_id ||
            item.approver_user_id ||
            item.id ||
            `${name}_${index}`;

          return (
            <Tag
              key={key}
              title={name}
              style={{
                marginRight: 0,
                marginBottom: 2,
                backgroundColor: '#f3f4f6',
                borderColor: '#d1d5db',
                color: '#4b5563',
                fontSize: 12,
                lineHeight: '20px',
                borderRadius: 4,
                padding: '0 8px',
                whiteSpace: 'normal',
                wordBreak: 'break-all',
                maxWidth: '100%',
              }}
            >
              {name}
            </Tag>
          );
        })}
      </div>

      {hasMore ? (
        <span
          role="button"
          tabIndex={0}
          onClick={() => setExpanded((value) => !value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' || event.key === ' ') {
              event.preventDefault();
              setExpanded((value) => !value);
            }
          }}
          style={{
            position: 'absolute',
            right: 0,
            top: 1,
            cursor: 'pointer',
            color: '#0f766e',
            fontSize: 12,
            lineHeight: '18px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: 16,
            height: 18,
          }}
        >
          <DownOutlined
            style={{
              fontSize: 10,
              color: expanded ? PEACOCK_GREEN : '#9ca3af',
              transition: 'transform 180ms ease, color 180ms ease',
              transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)',
            }}
          />
        </span>
      ) : null}
    </div>
  );
};

const renderApproverList = (approvers?: ApproverItem[] | null) => {
  return (
    <CollapsibleApproverList approvers={approvers || []} defaultCount={1} />
  );
};

const renderApproverConfig = (config?: ApproverConfig | null) => {
  if (!config) {
    return null;
  }

  const department = config.department;
  const approverList = config.approvers || [];

  return (
    <Card
      size="small"
      style={{ marginBottom: 12 }}
      bodyStyle={{ padding: 12 }}
      title={
        <Space size={8} wrap>
          <span>审批配置</span>

          {department?.department_name || department?.department_id ? (
            <Tag color="blue">
              {department.department_name || department.department_id}
            </Tag>
          ) : (
            <Tag>未匹配部门</Tag>
          )}

          {department?.is_global_reference_kb ? (
            <Tag color="red">全局参考库</Tag>
          ) : department?.is_reference_kb ? (
            <Tag color="purple">部门参考库</Tag>
          ) : (
            <Tag>普通知识库</Tag>
          )}
        </Space>
      }
    >
      <Space direction="vertical" size={6} style={{ width: '100%' }}>
        <div>
          <Text strong style={{ fontSize: 12 }}>
            审批人：
          </Text>{' '}
          {approverList.length > 0 ? (
            <Space wrap size={4}>
              {approverList.map((item, index) => {
                const displayName =
                  item.user_name || item.mdm_name || item.user_id || '未知人员';

                const tooltipText = [
                  item.email,
                  item.mdm_code ? `MDM：${item.mdm_code}` : '',
                  item.department_name,
                  item.role_name,
                ]
                  .filter(Boolean)
                  .join(' / ');

                return (
                  <Tooltip
                    key={`config-approver-${item.user_id}-${index}`}
                    title={tooltipText || item.user_id}
                  >
                    <Tag
                      style={{
                        marginRight: 0,
                        marginBottom: 2,
                        backgroundColor: PEACOCK_GREEN,
                        borderColor: PEACOCK_GREEN,
                        color: '#fff',
                      }}
                    >
                      {displayName}
                    </Tag>
                  </Tooltip>
                );
              })}
            </Space>
          ) : (
            <Text type="secondary" style={{ fontSize: 12 }}>
              暂无
            </Text>
          )}
        </div>
      </Space>
    </Card>
  );
};

type StagedFileListPageProps = {
  kbId?: string;
};

const StagedFileListPage: React.FC<StagedFileListPageProps> = ({
  kbId: propKbId,
}) => {
  const [statusSelectOpen, setStatusSelectOpen] = useState(false);
  const params = useParams<{ id: string }>();
  const kbId = propKbId || params.id || '';

  const [loading, setLoading] = useState(false);
  const [dataSource, setDataSource] = useState<StagedFileItem[]>([]);
  const [isAdmin, setIsAdmin] = useState(false);
  const [isApprover, setIsApprover] = useState(false);
  const [approverConfig, setApproverConfig] = useState<ApproverConfig | null>(
    null,
  );

  const [status, setStatus] = useState('');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [total, setTotal] = useState(0);

  const fetchStagedFiles = async (
    nextPage = page,
    nextPageSize = pageSize,
    nextStatus = status,
  ) => {
    if (!kbId) {
      message.error('缺少 kb_id');
      return;
    }

    try {
      setLoading(true);

      const res = await fetch('/v1/document/staged_file/list', {
        method: 'POST',
        headers: {
          Authorization: getAuthorization() || '',
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          kb_id: kbId,
          status: nextStatus || undefined,
          page: nextPage,
          page_size: nextPageSize,
        }),
      });

      const result = await res.json();

      if (result.code !== 0 && result.code !== 200) {
        message.error(result.message || '获取文件列表失败');
        return;
      }

      const data: ListResponseData = result.data || {};

      const normalizedApproverConfig = normalizeApproverConfig(data);

      setDataSource(data.items || []);
      setTotal(data.total || 0);
      setIsAdmin(!!data.is_admin);
      setIsApprover(!!data.is_approver);
      setApproverConfig(normalizedApproverConfig);
      setPage(data.page || nextPage);
      setPageSize(data.page_size || nextPageSize);
    } catch (error) {
      console.error(error);
      message.error('获取文件列表请求失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (kbId) {
      fetchStagedFiles(1, pageSize, status);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [kbId]);

  const tagColumns: ColumnsType<StagedFileItem> = useMemo(() => {
    const tagTypeMap = new Map<
      string,
      {
        type_code: string;
        type_name: string;
      }
    >();

    dataSource.forEach((file) => {
      file.tags?.forEach((tag) => {
        if (!tagTypeMap.has(tag.type_code)) {
          tagTypeMap.set(tag.type_code, {
            type_code: tag.type_code,
            type_name: tag.type_name || tag.type_code,
          });
        }
      });
    });

    return Array.from(tagTypeMap.values()).map((tagType) => ({
      title: tagType.type_name,
      dataIndex: 'tags',
      key: `tag_${tagType.type_code}`,
      width: 120,
      render: (tags: FileTagItem[] | null | undefined) =>
        renderTagValue(tags, tagType.type_code),
      onCell: () => ({
        style: {
          whiteSpace: 'normal',
          wordBreak: 'break-all',
          verticalAlign: 'top',
        },
      }),
    }));
  }, [dataSource]);

  const columns: ColumnsType<StagedFileItem> = [
    {
      title: '文件名',
      dataIndex: 'filename',
      key: 'filename',
      // width: 180,
      render: (text: string) => (
        <div style={{ whiteSpace: 'normal', wordBreak: 'break-all' }}>
          <Text style={{ fontSize: 12 }}>{text}</Text>
        </div>
      ),
      onCell: () => ({
        style: {
          whiteSpace: 'normal',
          wordBreak: 'break-all',
          verticalAlign: 'top',
        },
      }),
    },
    {
      title: '上传人',
      dataIndex: 'user_name',
      key: 'user_name',
      width: 110,
      render: (_value, record) => (
        <Text style={{ fontSize: 12 }}>
          {record.user_name || record.user_id || '-'}
        </Text>
      ),
      onCell: () => ({
        style: {
          verticalAlign: 'top',
        },
      }),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (value: string | undefined) => {
        const normalizedStatus = String(value || '').trim();

        return (
          <Tag
            style={{
              ...(statusColorMap[normalizedStatus] || {
                color: '#6b7280',
                backgroundColor: '#f9fafb',
                borderColor: '#d1d5db',
              }),
              marginInlineEnd: 0,
              borderRadius: 4,
              fontSize: 12,
              lineHeight: '20px',
              padding: '0 7px',
              fontWeight: 500,
            }}
          >
            {statusTextMap[normalizedStatus] || normalizedStatus || '-'}
          </Tag>
        );
      },
      onCell: () => ({
        style: {
          verticalAlign: 'top',
        },
      }),
    },

    ...tagColumns,

    {
      title: '审批人',
      dataIndex: 'approvers',
      key: 'approvers',
      width: 160,
      render: (_value, record) => renderApproverList(getRowApprovers(record)),
      onCell: () => ({
        style: {
          verticalAlign: 'top',
        },
      }),
    },
    {
      title: '大小',
      dataIndex: 'size',
      key: 'size',
      render: (value: number | undefined) => (
        <span className="text-xs text-gray-400">{formatFileSize(value)}</span>
      ),
      onCell: () => ({
        style: {
          verticalAlign: 'top',
        },
      }),
    },
    {
      title: '上传时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (value: string | undefined) => (
        <span className="text-xs text-gray-400">{value || '-'}</span>
      ),
      onCell: () => ({
        style: {
          verticalAlign: 'top',
        },
      }),
    },
    {
      title: '审批时间',
      dataIndex: 'approved_at',
      key: 'approved_at',
      render: (value: string | null | undefined) => (
        <span className="text-xs text-text-secondary">{value || '-'}</span>
      ),
      onCell: () => ({
        style: {
          verticalAlign: 'top',
        },
      }),
    },
    {
      title: '入库时间',
      dataIndex: 'committed_at',
      key: 'committed_at',
      render: (value: string | null | undefined) => (
        <span className="text-xs text-text-secondary">{value || '-'}</span>
      ),
      onCell: () => ({
        style: {
          verticalAlign: 'top',
        },
      }),
    },
  ];

  const handleStatusChange = (value: string) => {
    setStatus(value);
    setPage(1);
    fetchStagedFiles(1, pageSize, value);
  };

  const viewTag = isAdmin ? (
    <Tag color="gold">管理员视图</Tag>
  ) : isApprover ? (
    <Tag color="green">审批人视图</Tag>
  ) : (
    <Tag>个人视图</Tag>
  );

  // 在 return 中：
  return (
    <div
      style={{
        fontSize: 12,
        lineHeight: 1.3,
        display: 'flex',
        flexDirection: 'column',
        height: 'calc(100vh - 120px)',
        minHeight: 0,
        overflow: 'hidden',
      }}
    >
      {/* 标题 */}
      <div className="mb-4 flex shrink-0 items-center justify-between">
        <span className="text-2xl font-semibold">上传日志</span>
        <Space size={8}>
          <Select
            style={{ width: 120 }}
            size="small"
            value={status}
            options={statusOptions}
            onChange={handleStatusChange}
          />
        </Space>
      </div>

      {/* 表格滚动区域 */}
      <div style={{ flex: 1, minHeight: 0, overflow: 'hidden' }}>
        <Table
          size="small"
          bordered
          rowKey="id"
          loading={loading}
          columns={columns}
          dataSource={dataSource}
          tableLayout="auto"
          pagination={false}
          style={{ height: '100%' }}
          scroll={{ x: 'max-content', y: 600 }} // 这里改成具体数值
        />
      </div>

      {/* 分页 */}
      <div className="mt-2 flex shrink-0 items-center justify-end pb-3 pr-3">
        <RAGFlowPagination
          current={page}
          pageSize={pageSize}
          total={total}
          onChange={(nextPage, nextPageSize) => {
            setPage(nextPage);
            setPageSize(nextPageSize);
            fetchStagedFiles(nextPage, nextPageSize, status);
          }}
        />
      </div>
    </div>
  );
};

export default StagedFileListPage;
