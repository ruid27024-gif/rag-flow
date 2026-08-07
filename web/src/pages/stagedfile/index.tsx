import { getAuthorization } from '@/utils/authorization-util';
import { DownOutlined, ReloadOutlined, UpOutlined } from '@ant-design/icons';
import {
  Button,
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
import React, { useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';

const { Text } = Typography;

const PEACOCK_GREEN = '#1FA67A';

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
  approval_order?: number | null;
};

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

  approval_level_1?: ApproverItem[] | null;
  approval_level_2?: ApproverItem[] | null;
};

type ApproverConfig = {
  department?: {
    department_id?: string;
    department_name?: string;
    is_reference_kb?: boolean;
    is_global_reference_kb?: boolean;
    tenant_id?: string;
  } | null;

  level_1?: ApproverItem[];
  level_2?: ApproverItem[];
};

type ListResponseData = {
  is_admin: boolean;
  total: number;
  page: number;
  page_size: number;
  approvers?: ApproverConfig | null;
  items: StagedFileItem[];
};

const statusOptions = [
  { label: '全部', value: '' },
  { label: '待审批', value: 'pending' },
  { label: '已通过', value: 'approved' },
  { label: '入库中', value: 'committing' },
  { label: '已入库', value: 'committed' },
  { label: '已拒绝', value: 'rejected' },
  { label: '失败', value: 'failed' },
];

const statusTextMap: Record<string, string> = {
  pending: '待审批',
  approved: '已通过',
  committing: '入库中',
  committed: '已入库',
  rejected: '已拒绝',
  failed: '失败',
  deleted: '已删除',
};

const statusColorMap: Record<string, string> = {
  pending: 'orange',
  approved: 'blue',
  committing: 'processing',
  committed: 'green',
  rejected: 'red',
  failed: 'red',
  deleted: 'default',
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
          onClick={() => setExpanded(!expanded)}
          style={{
            position: 'absolute',
            right: 0,
            top: 0,
            cursor: 'pointer',
            color: '#999',
            fontSize: 12,
            lineHeight: '18px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: 16,
            height: 18,
          }}
        >
          {expanded ? <UpOutlined /> : <DownOutlined />}
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

const renderApproverList = (approvers?: ApproverItem[] | null) => {
  if (!approvers || approvers.length === 0) {
    return <Text type="secondary">暂无</Text>;
  }

  return (
    <Space direction="vertical" size={2}>
      {approvers.map((item, index) => {
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
            key={`${item.user_id}_${item.role_id || 'none'}_${index}`}
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
  );
};

const renderApproverConfig = (approvers?: ApproverConfig | null) => {
  if (!approvers) {
    return null;
  }

  const department = approvers.department;
  const level1 = approvers.level_1 || [];
  const level2 = approvers.level_2 || [];

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
            一级审批人：
          </Text>{' '}
          {level1.length > 0 ? (
            <Space wrap size={4}>
              {level1.map((item, index) => (
                <Tooltip
                  key={`config-level1-${item.user_id}-${index}`}
                  title={item.email || item.user_id}
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
                    {item.user_name || item.mdm_name || item.user_id}
                  </Tag>
                </Tooltip>
              ))}
            </Space>
          ) : (
            <Text type="secondary" style={{ fontSize: 12 }}>
              暂无
            </Text>
          )}
        </div>

        <div>
          <Text strong style={{ fontSize: 12 }}>
            二级审批人：
          </Text>{' '}
          {level2.length > 0 ? (
            <Space wrap size={4}>
              {level2.map((item, index) => (
                <Tooltip
                  key={`config-level2-${item.user_id}-${index}`}
                  title={item.email || item.user_id}
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
                    {item.user_name || item.mdm_name || item.user_id}
                  </Tag>
                </Tooltip>
              ))}
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
  const params = useParams<{ id: string }>();
  const kbId = propKbId || params.id || '';

  const [loading, setLoading] = useState(false);
  const [dataSource, setDataSource] = useState<StagedFileItem[]>([]);
  const [isAdmin, setIsAdmin] = useState(false);
  const [approvers, setApprovers] = useState<ApproverConfig | null>(null);

  const [status, setStatus] = useState('');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
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

      setDataSource(data.items || []);
      setTotal(data.total || 0);
      setIsAdmin(!!data.is_admin);
      setApprovers(data.approvers || null);
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
      width: 180,
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
      width: 180,
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
      width: 90,
      render: (value: string) => (
        <Tag
          color={statusColorMap[value] || 'default'}
          style={{ marginRight: 0 }}
        >
          {statusTextMap[value] || value || '-'}
        </Tag>
      ),
      onCell: () => ({
        style: {
          verticalAlign: 'top',
        },
      }),
    },

    ...tagColumns,

    {
      title: '一级审批人',
      dataIndex: 'approval_level_1',
      key: 'approval_level_1',
      width: 140,
      render: (value: ApproverItem[] | null | undefined) =>
        renderApproverList(value),
      onCell: () => ({
        style: {
          verticalAlign: 'top',
        },
      }),
    },
    {
      title: '二级审批人',
      dataIndex: 'approval_level_2',
      key: 'approval_level_2',
      width: 140,
      render: (value: ApproverItem[] | null | undefined) =>
        renderApproverList(value),
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
      width: 80,
      render: (value: number | undefined) => formatFileSize(value),
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
      width: 120,
      render: (value: string | undefined) => value || '-',
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
      width: 120,
      render: (value: string | null | undefined) => value || '-',
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
      width: 120,
      render: (value: string | null | undefined) => value || '-',
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

  return (
    <div style={{ fontSize: 12, lineHeight: 1.3 }}>
      {renderApproverConfig(approvers)}

      <Card
        size="small"
        bodyStyle={{ padding: 12 }}
        title={
          <Space size={8}>
            <span>暂存文件列表</span>
            {isAdmin ? <Tag color="gold">管理员视图</Tag> : <Tag>个人视图</Tag>}
          </Space>
        }
        extra={
          <Space size={8}>
            <Select
              style={{ width: 120 }}
              size="small"
              value={status}
              options={statusOptions}
              onChange={handleStatusChange}
            />
            <Button
              size="small"
              icon={<ReloadOutlined />}
              onClick={() => fetchStagedFiles(page, pageSize, status)}
            >
              刷新
            </Button>
          </Space>
        }
      >
        <Table
          size="small"
          bordered
          rowKey="id"
          loading={loading}
          columns={columns}
          dataSource={dataSource}
          tableLayout="fixed"
          scroll={{ x: 'max-content' }}
          pagination={{
            current: page,
            pageSize,
            total,
            showSizeChanger: true,
            showTotal: (count) => `共 ${count} 条`,
            pageSizeOptions: [10, 20, 50, 100],
            onChange: (nextPage, nextPageSize) => {
              setPage(nextPage);
              setPageSize(nextPageSize);
              fetchStagedFiles(nextPage, nextPageSize, status);
            },
          }}
        />
      </Card>
    </div>
  );
};

export default StagedFileListPage;
