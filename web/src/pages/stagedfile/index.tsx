import { getAuthorization } from '@/utils/authorization-util';
import { DownOutlined } from '@ant-design/icons';
import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  type ColumnDef,
} from '@tanstack/react-table';
// import { Select, message } from 'antd';
import { Avatar, Select, message } from 'antd';
import React, { useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';

import { RAGFlowPagination } from '@/components/ui/ragflow-pagination';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

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

  approval_order?: number | null;
};

type StagedFileItem = {
  id: string;
  batch_id?: string;
  kb_id: string;
  tenant_id?: string;
  version?: string | null;

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

  approvers?: ApproverItem[] | null;
  approval_users?: ApproverItem[] | null;

  approval_level_1?: ApproverItem[] | null;
  approval_level_2?: ApproverItem[] | null;
};

type ListResponseData = {
  is_admin?: boolean;
  is_approver?: boolean;
  total?: number;
  page?: number;
  page_size?: number;
  items?: StagedFileItem[];
};

type ListResponse = {
  code: number;
  message?: string;
  data?: ListResponseData;
};

type StagedFileListPageProps = {
  kbId?: string;
};

type ProgressStep = {
  key: number;
  label: string;
};

type StatusProgressInfo = {
  currentStep: number;
  statusText: string;
  progressText: string;
};

type CollapsibleTextListProps = {
  items?: string[];
  defaultCount?: number;
  variant?: 'cyan' | 'gray';
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

  approved: '审批通过',

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

const PROGRESS_STEPS: ProgressStep[] = [
  {
    key: 1,
    label: '上传',
  },
  {
    key: 2,
    label: '审批',
  },
  {
    key: 3,
    label: '入库',
  },
];

const ACTIVE_DOT_CLASS = 'bg-cyan-500';
const ACTIVE_TEXT_CLASS = 'text-cyan-700 dark:text-cyan-300';
const INACTIVE_DOT_CLASS = 'bg-gray-200 dark:bg-gray-700';

const formatFileSize = (size?: number) => {
  if (!size) {
    return '0 B';
  }

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

const uniqueApprovers = (list: ApproverItem[]) => {
  const result: ApproverItem[] = [];
  const added = new Set<string>();

  list.forEach((item) => {
    if (!item) {
      return;
    }

    const key = String(
      item.user_id ||
        item.approver_user_id ||
        item.id ||
        item.user_name ||
        item.name ||
        '',
    );

    if (!key || added.has(key)) {
      return;
    }

    added.add(key);
    result.push(item);
  });

  return result;
};

const getRowApprovers = (record: StagedFileItem): ApproverItem[] => {
  const list = record.approvers ||
    record.approval_users || [
      ...(record.approval_level_1 || []),
      ...(record.approval_level_2 || []),
    ];

  return uniqueApprovers(list || []);
};

const getApproverName = (item: ApproverItem) => {
  return (
    item.user_name ||
    item.approver_name ||
    item.name ||
    item.mdm_name ||
    item.user_id ||
    item.approver_user_id ||
    item.id ||
    '-'
  );
};

/**
 * 将后端状态映射到：
 * 1：上传阶段
 * 2：审批阶段
 * 3：入库阶段
 */
const getStatusProgress = (status?: string): StatusProgressInfo => {
  const normalizedStatus = String(status || '').trim();

  const statusText =
    statusTextMap[normalizedStatus] || normalizedStatus || '未知状态';

  if (normalizedStatus === 'pending') {
    return {
      currentStep: 2,
      statusText,
      progressText: '等待提交审批',
    };
  }

  if (
    [
      'oa_submitted',
      'pending_approval',
      'pending_level_1',
      'pending_level_2',
    ].includes(normalizedStatus)
  ) {
    return {
      currentStep: 2,
      statusText,
      progressText: '正在审批',
    };
  }

  if (normalizedStatus === 'approved') {
    return {
      currentStep: 2,
      statusText,
      progressText: '等待入库',
    };
  }

  if (['committing', 'importing'].includes(normalizedStatus)) {
    return {
      currentStep: 3,
      statusText,
      progressText: '正在入库',
    };
  }

  if (
    ['imported', 'partial_imported', 'callback_success'].includes(
      normalizedStatus,
    )
  ) {
    return {
      currentStep: 3,
      statusText,
      progressText: '流程已完成',
    };
  }

  if (normalizedStatus === 'rejected') {
    return {
      currentStep: 2,
      statusText,
      progressText: '审批流程终止',
    };
  }

  if (['import_failed', 'callback_failed'].includes(normalizedStatus)) {
    return {
      currentStep: 3,
      statusText,
      progressText: '入库流程终止',
    };
  }

  if (normalizedStatus === 'failed') {
    return {
      currentStep: 1,
      statusText,
      progressText: '上传流程终止',
    };
  }

  if (normalizedStatus === 'deleted') {
    return {
      currentStep: 1,
      statusText,
      progressText: '记录已删除',
    };
  }

  return {
    currentStep: 1,
    statusText,
    progressText: '上传记录',
  };
};

const getColumnClassName = (columnId: string) => {
  if (columnId === 'filename') {
    return 'w-[260px] min-w-[260px] max-w-[260px]';
  }

  if (columnId === 'user_name') {
    return 'w-[140px] min-w-[140px] max-w-[140px]';
  }

  if (columnId === 'status') {
    return 'w-[210px] min-w-[210px] max-w-[210px]';
  }

  if (columnId === 'approvers') {
    return 'w-[170px] min-w-[170px] max-w-[170px]';
  }

  if (columnId === 'size') {
    return 'w-[100px] min-w-[100px] max-w-[100px] whitespace-nowrap';
  }

  if (
    columnId === 'created_at' ||
    columnId === 'approved_at' ||
    columnId === 'committed_at'
  ) {
    return 'w-[170px] min-w-[170px] max-w-[170px] whitespace-nowrap';
  }

  if (columnId.startsWith('tag_')) {
    return 'w-[150px] min-w-[150px] max-w-[150px]';
  }

  return 'w-[140px] min-w-[140px] max-w-[140px]';
};

const StatusProgressCell = ({
  status,
  errorMsg,
}: {
  status?: string;
  errorMsg?: string | null;
}) => {
  const progress = getStatusProgress(status);

  return (
    <div className="flex min-w-[185px] items-start gap-2.5">
      {/* 左侧纵向进度条 */}
      <div className="flex shrink-0 flex-col items-center pt-0.5">
        {PROGRESS_STEPS.map((step, index) => {
          const isReached = step.key <= progress.currentStep;
          const isCurrent = step.key === progress.currentStep;
          const isLast = index === PROGRESS_STEPS.length - 1;

          return (
            <React.Fragment key={step.key}>
              <span
                title={step.label}
                className={`relative flex h-2.5 w-2.5 items-center justify-center rounded-full ${
                  isReached ? ACTIVE_DOT_CLASS : INACTIVE_DOT_CLASS
                } ${
                  isCurrent ? 'ring-2 ring-cyan-100 dark:ring-cyan-900' : ''
                }`}
              >
                {isCurrent ? (
                  <span className="h-1 w-1 rounded-full bg-white dark:bg-cyan-950" />
                ) : null}
              </span>

              {!isLast ? (
                <span
                  className={`h-3.5 w-px ${
                    step.key < progress.currentStep
                      ? ACTIVE_DOT_CLASS
                      : INACTIVE_DOT_CLASS
                  }`}
                />
              ) : null}
            </React.Fragment>
          );
        })}
      </div>

      {/* 右侧状态信息 */}
      <div className="min-w-0 text-xs leading-4">
        <div className="flex min-w-0 items-center gap-1.5">
          <span className="shrink-0 text-gray-400">当前</span>

          <span
            className={`min-w-0 truncate font-medium ${ACTIVE_TEXT_CLASS}`}
            title={progress.statusText}
          >
            {progress.statusText}
          </span>
        </div>

        <div className="mt-0.5 flex min-w-0 items-center gap-1.5">
          <span className="shrink-0 text-gray-400">进度</span>

          <span
            className="min-w-0 max-w-[135px] truncate text-gray-500 dark:text-gray-400"
            title={errorMsg || progress.progressText}
          >
            {errorMsg || progress.progressText}
          </span>
        </div>
      </div>
    </div>
  );
};

const CollapsibleTextList: React.FC<CollapsibleTextListProps> = ({
  items = [],
  defaultCount = 1,
  variant = 'gray',
}) => {
  const [expanded, setExpanded] = useState(false);

  if (!items.length) {
    return <span className="text-xs text-gray-400">-</span>;
  }

  const visibleItems = expanded ? items : items.slice(0, defaultCount);
  const hasMore = items.length > defaultCount;

  const itemClassName =
    variant === 'cyan'
      ? [
          'inline-flex max-w-full items-center rounded border',
          'border-cyan-200 bg-cyan-50 text-cyan-700',
          'px-2 py-0.5 text-xs font-medium',
          'dark:border-cyan-800 dark:bg-cyan-950 dark:text-cyan-300',
        ].join(' ')
      : [
          'inline-flex max-w-full items-center rounded border',
          'border-gray-200 bg-gray-50 text-gray-600',
          'px-2 py-0.5 text-xs',
          'dark:border-gray-700 dark:bg-gray-900/60 dark:text-gray-300',
        ].join(' ');

  return (
    <div
      className="relative w-full min-w-0"
      style={{
        paddingRight: hasMore ? 20 : 0,
      }}
    >
      <div
        className={
          variant === 'cyan'
            ? 'flex w-full min-w-0 flex-col items-start gap-1'
            : 'flex w-full min-w-0 flex-wrap items-start gap-1'
        }
      >
        {visibleItems.map((item, index) => (
          <span
            key={`${item}_${index}`}
            title={item}
            className={itemClassName}
            style={{
              maxWidth: '100%',
              whiteSpace: 'normal',
              wordBreak: 'break-all',
            }}
          >
            {item}
          </span>
        ))}
      </div>

      {hasMore ? (
        <button
          type="button"
          aria-label={expanded ? '收起' : '展开'}
          title={
            expanded ? '收起' : `展开剩余 ${items.length - defaultCount} 项`
          }
          className="absolute right-0 top-0 flex h-5 w-[18px] cursor-pointer items-center justify-center rounded text-gray-400 transition-colors hover:bg-gray-100 hover:text-cyan-600 dark:hover:bg-gray-800"
          onClick={(event) => {
            event.stopPropagation();
            setExpanded((value) => !value);
          }}
        >
          <DownOutlined
            style={{
              fontSize: 10,
              color: expanded ? '#0891b2' : undefined,
              transition: 'transform 180ms ease, color 180ms ease',
              transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)',
            }}
          />
        </button>
      ) : null}
    </div>
  );
};

const renderTagValue = (tags?: FileTagItem[] | null, typeCode?: string) => {
  if (!tags?.length || !typeCode) {
    return <span className="text-xs text-gray-400">-</span>;
  }

  const tagItem = tags.find((item) => item.type_code === typeCode);

  if (!tagItem) {
    return <span className="text-xs text-gray-400">-</span>;
  }

  const optionNames = tagItem.option_names?.length
    ? tagItem.option_names
    : tagItem.options?.map(
        (option) => option.option_name || option.option_code,
      ) || [];

  if (!optionNames.length) {
    return <span className="text-xs text-gray-400">-</span>;
  }

  return (
    <CollapsibleTextList items={optionNames} defaultCount={1} variant="cyan" />
  );
};

type ApproverListProps = {
  approvers?: ApproverItem[];
  defaultCount?: number;
};

const ApproverList: React.FC<ApproverListProps> = ({
  approvers = [],
  defaultCount = 1,
}) => {
  const [expanded, setExpanded] = useState(false);

  if (!approvers.length) {
    return <span className="text-xs text-gray-400">-</span>;
  }

  const visibleApprovers = expanded
    ? approvers
    : approvers.slice(0, defaultCount);

  const hasMore = approvers.length > defaultCount;

  return (
    <div
      className="relative w-full min-w-0"
      style={{
        paddingRight: hasMore ? 20 : 0,
      }}
    >
      <div className="flex min-w-0 flex-col items-start gap-1.5">
        {visibleApprovers.map((approver, index) => {
          const name = getApproverName(approver);

          const key =
            approver.user_id ||
            approver.approver_user_id ||
            approver.id ||
            `${name}_${index}`;

          return (
            <div
              key={key}
              title={name}
              className="flex max-w-full items-center gap-2"
            >
              <Avatar
                size={24}
                src={approver.avatar || undefined}
                className="shrink-0 bg-blue-100 text-xs font-medium text-blue-700 dark:bg-blue-950 dark:text-blue-300"
              >
                {name === '-' ? '?' : name.slice(0, 1).toUpperCase()}
              </Avatar>

              <span className="min-w-0 max-w-[105px] truncate text-xs text-gray-700 dark:text-gray-300">
                {name}
              </span>
            </div>
          );
        })}
      </div>

      {hasMore ? (
        <button
          type="button"
          aria-label={expanded ? '收起审批人' : '展开审批人'}
          title={
            expanded
              ? '收起审批人'
              : `展开剩余 ${approvers.length - defaultCount} 位审批人`
          }
          className="absolute right-0 top-0 flex h-6 w-[18px] items-center justify-center rounded text-gray-400 transition-colors hover:bg-gray-100 hover:text-cyan-600 dark:hover:bg-gray-800"
          onClick={(event) => {
            event.stopPropagation();
            setExpanded((value) => !value);
          }}
        >
          <DownOutlined
            style={{
              fontSize: 10,
              color: expanded ? '#0891b2' : undefined,
              transition: 'transform 180ms ease, color 180ms ease',
              transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)',
            }}
          />
        </button>
      ) : null}
    </div>
  );
};

const renderApproverList = (approvers?: ApproverItem[] | null) => {
  return <ApproverList approvers={approvers || []} defaultCount={1} />;
};

const StagedFileListPage: React.FC<StagedFileListPageProps> = ({
  kbId: propKbId,
}) => {
  const params = useParams<{ id: string }>();
  const kbId = propKbId || params.id || '';

  const [loading, setLoading] = useState(false);
  const [dataSource, setDataSource] = useState<StagedFileItem[]>([]);

  const [isAdmin, setIsAdmin] = useState(false);
  const [isApprover, setIsApprover] = useState(false);

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

      const response = await fetch('/v1/document/staged_file/list', {
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

      const result = (await response.json()) as ListResponse;

      if (result.code !== 0 && result.code !== 200) {
        setDataSource([]);
        setTotal(0);
        message.error(result.message || '获取文件列表失败');
        return;
      }

      const data = result.data;

      setDataSource(data?.items || []);
      setTotal(data?.total || 0);
      setIsAdmin(Boolean(data?.is_admin));
      setIsApprover(Boolean(data?.is_approver));
      setPage(data?.page || nextPage);
      setPageSize(data?.page_size || nextPageSize);
    } catch (error) {
      console.error(error);
      setDataSource([]);
      setTotal(0);
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

  const tagColumns = useMemo<ColumnDef<StagedFileItem>[]>(() => {
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
      id: `tag_${tagType.type_code}`,
      header: tagType.type_name,
      cell: ({ row }) => renderTagValue(row.original.tags, tagType.type_code),
    }));
  }, [dataSource]);

  const columns = useMemo<ColumnDef<StagedFileItem>[]>(
    () => [
      {
        accessorKey: 'filename',
        header: '文件名',
        cell: ({ row }) => {
          const filename = row.original.filename || '-';

          return (
            <div
              className="w-full max-w-[235px] truncate text-sm text-gray-700 dark:text-gray-200"
              title={filename}
            >
              {filename}
            </div>
          );
        },
      },
      {
        accessorKey: 'version',
        header: '版本',
        cell: ({ row }) => {
          const version = row.original.version?.trim();

          if (!version) {
            return <span className="text-xs text-gray-400">-</span>;
          }

          return (
            <span className="inline-flex items-center whitespace-nowrap rounded border border-cyan-200 bg-cyan-50 px-2 py-0.5 text-xs font-medium text-cyan-700 dark:border-cyan-800 dark:bg-cyan-950 dark:text-cyan-300">
              {version}
            </span>
          );
        },
      },
      {
        accessorKey: 'user_name',
        header: '上传人',
        cell: ({ row }) => {
          const userName =
            row.original.user_name || row.original.user_id || '-';

          return (
            <div className="min-w-0">
              <div
                className="max-w-[115px] truncate text-sm font-medium text-gray-700 dark:text-gray-200"
                title={userName}
              >
                {userName}
              </div>

              {row.original.user_email ? (
                <div
                  className="mt-0.5 max-w-[115px] truncate text-xs text-gray-500"
                  title={row.original.user_email}
                >
                  {row.original.user_email}
                </div>
              ) : null}
            </div>
          );
        },
      },
      {
        accessorKey: 'status',
        header: '状态',
        cell: ({ row }) => (
          <StatusProgressCell
            status={row.original.status}
            errorMsg={row.original.error_msg}
          />
        ),
      },

      ...tagColumns,

      {
        id: 'approvers',
        header: '审批人',
        cell: ({ row }) => (
          <div className="max-w-[145px]">
            {renderApproverList(getRowApprovers(row.original))}
          </div>
        ),
      },
      {
        accessorKey: 'size',
        header: '大小',
        cell: ({ row }) => (
          <span className="whitespace-nowrap text-xs text-gray-500">
            {formatFileSize(row.original.size)}
          </span>
        ),
      },
      {
        accessorKey: 'created_at',
        header: '上传时间',
        cell: ({ row }) => (
          <span className="whitespace-nowrap text-xs text-gray-500">
            {row.original.created_at || '-'}
          </span>
        ),
      },
      {
        accessorKey: 'approved_at',
        header: '审批时间',
        cell: ({ row }) => (
          <span className="whitespace-nowrap text-xs text-gray-500">
            {row.original.approved_at || '-'}
          </span>
        ),
      },
      {
        accessorKey: 'committed_at',
        header: '入库时间',
        cell: ({ row }) => (
          <span className="whitespace-nowrap text-xs text-gray-500">
            {row.original.committed_at || '-'}
          </span>
        ),
      },
    ],
    [tagColumns],
  );

  const table = useReactTable({
    data: dataSource,
    columns,
    getCoreRowModel: getCoreRowModel(),
    manualPagination: true,
    state: {
      pagination: {
        pageIndex: page - 1,
        pageSize,
      },
    },
  });

  const handleStatusChange = (value: string) => {
    setStatus(value);
    setPage(1);
    fetchStagedFiles(1, pageSize, value);
  };

  const viewText = isAdmin
    ? '管理员视图'
    : isApprover
      ? '审批人视图'
      : '个人视图';

  return (
    <section className="min-w-[880px] p-5">
      {/* 页面标题和筛选 */}
      <div className="flex flex-wrap items-end justify-between gap-4 pb-4">
        <div>
          <div className="pb-1 text-2xl font-semibold">上传日志</div>

          <div className="text-sm text-text-secondary">
            查看文件上传、审批和入库记录
            <span className="ml-2 text-xs text-gray-400">{viewText}</span>
          </div>
        </div>

        <Select
          style={{
            width: 140,
          }}
          size="small"
          value={status}
          options={statusOptions}
          onChange={handleStatusChange}
        />
      </div>

      <div className="flex min-h-[calc(100vh-220px)] flex-col">
        {/* 无外边框表格 */}
        <div className="min-h-0 flex-1 overflow-hidden">
          <Table rootClassName="max-h-[calc(100vh-260px)]">
            <TableHeader>
              {table.getHeaderGroups().map((headerGroup) => (
                <TableRow key={headerGroup.id}>
                  {headerGroup.headers.map((header) => {
                    const columnId = header.column.id;

                    return (
                      <TableHead
                        key={header.id}
                        className={getColumnClassName(columnId)}
                      >
                        {header.isPlaceholder
                          ? null
                          : flexRender(
                              header.column.columnDef.header,
                              header.getContext(),
                            )}
                      </TableHead>
                    );
                  })}
                </TableRow>
              ))}
            </TableHeader>

            <TableBody className="relative">
              {!loading && table.getRowModel().rows.length > 0 ? (
                table.getRowModel().rows.map((row) => (
                  <TableRow
                    key={row.original.id}
                    className="group transition-colors hover:bg-gray-50/70 dark:hover:bg-gray-900/40"
                  >
                    {row.getVisibleCells().map((cell) => {
                      const columnId = cell.column.id;

                      return (
                        <TableCell
                          key={cell.id}
                          className={`${getColumnClassName(
                            columnId,
                          )} align-top`}
                        >
                          {flexRender(
                            cell.column.columnDef.cell,
                            cell.getContext(),
                          )}
                        </TableCell>
                      );
                    })}
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell
                    colSpan={columns.length}
                    className="h-24 text-center text-gray-500"
                  >
                    {loading ? '正在加载...' : '暂无上传日志'}
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>

        {/* 分页 */}
        <div className="mt-3 flex shrink-0 items-center justify-end pb-3 pr-3">
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
    </section>
  );
};

export default StagedFileListPage;
