import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  type ColumnDef,
} from '@tanstack/react-table';
import { Avatar, Modal, message } from 'antd';
import { useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { RAGFlowPagination } from '@/components/ui/ragflow-pagination';
import { getAuthorization } from '@/utils/authorization-util';

import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';

import { CircleAlert, Filter, Search } from 'lucide-react';

const authHeaders = {
  Authorization: getAuthorization() || '',
  'Content-Type': 'application/json',
};

type OperationLogItem = {
  id: string;
  user_id: string;
  user_name?: string | null;
  user_email?: string | null;

  /**
   * 如果后端返回头像字段不是 user_avatar，
   * 比如叫 avatar，可以把这里和代码里的 user_avatar 改成 avatar。
   */
  user_avatar?: string | null;

  kb_id?: string | null;
  kb_name?: string | null;
  target_id?: string | null;
  target_name?: string | null;
  action: string;
  status: string;
  message?: string | null;
  before_data?: string | null;
  after_data?: string | null;
  ip?: string | null;
  create_time: string;
  operation_time: string;
};

type OperationLogResponse = {
  code: number;
  message?: string;
  data?: {
    logs: OperationLogItem[];
    total: number;
    page: number;
    page_size: number;
  };
};

const actionMap: Record<string, string> = {
  upload: '上传',
  download: '下载',
  rename: '重命名',
  update_tags: '修改标签',
  update_meta: '修改元数据',
  change_status: '修改状态',
  enable: '修改状态为开启',
  disable: '修改状态为关闭',
};

const statusMap: Record<string, string> = {
  success: '成功',
  failed: '失败',
};

const actionStyleMap: Record<string, string> = {
  upload:
    'border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-800 dark:bg-blue-950 dark:text-blue-300',
  download:
    'border-cyan-200 bg-cyan-50 text-cyan-700 dark:border-cyan-800 dark:bg-cyan-950 dark:text-cyan-300',
  rename:
    'border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-300',
  update_tags:
    'border-violet-200 bg-violet-50 text-violet-700 dark:border-violet-800 dark:bg-violet-950 dark:text-violet-300',
  update_meta:
    'border-indigo-200 bg-indigo-50 text-indigo-700 dark:border-indigo-800 dark:bg-indigo-950 dark:text-indigo-300',
  change_status:
    'border-orange-200 bg-orange-50 text-orange-700 dark:border-orange-800 dark:bg-orange-950 dark:text-orange-300',
  enable:
    'border-green-200 bg-green-50 text-green-700 dark:border-green-800 dark:bg-green-950 dark:text-green-300',
  disable:
    'border-red-200 bg-red-50 text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-300',
};

const defaultActionStyle =
  'border-gray-200 bg-gray-50 text-gray-700 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-300';

function getActionLabel(action?: string | null) {
  if (!action) return '-';
  return actionMap[action] || action;
}

function getActionStyle(action?: string | null) {
  if (!action) return defaultActionStyle;
  return actionStyleMap[action] || defaultActionStyle;
}

function getAvatarText(log?: OperationLogItem | null) {
  if (!log) return '?';

  const displayName =
    log.user_name?.trim() ||
    log.user_email?.trim() ||
    log.user_id?.trim() ||
    '?';

  return displayName.slice(0, 1).toUpperCase();
}

async function fetchOperationLogs(params: {
  kb_id?: string;
  page?: number;
  page_size?: number;
  action?: string;
  keyword?: string;
}) {
  const payload: Record<string, unknown> = {
    page: params.page ?? 1,
    page_size: params.page_size ?? 20,
  };

  if (params.kb_id) payload.kb_id = params.kb_id;
  if (params.action) payload.action = params.action;
  if (params.keyword) payload.keyword = params.keyword;

  const res = await fetch('/v1/document/operation_logs', {
    method: 'POST',
    headers: authHeaders,
    credentials: 'include',
    body: JSON.stringify(payload),
  });

  return (await res.json()) as OperationLogResponse;
}

function formatJsonText(value?: string | null) {
  if (!value) return '-';

  try {
    const parsed = JSON.parse(value);
    return JSON.stringify(parsed, null, 2);
  } catch {
    return value;
  }
}

export default function OperationLogIndex() {
  const { id } = useParams();
  const kbId = id || '';

  const [loading, setLoading] = useState(false);
  const [logs, setLogs] = useState<OperationLogItem[]>([]);
  const [total, setTotal] = useState(0);

  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 10,
  });

  const [action, setAction] = useState('');
  const [keyword, setKeyword] = useState('');

  const [detailVisible, setDetailVisible] = useState(false);
  const [selectedLog, setSelectedLog] = useState<OperationLogItem | null>(null);

  const title = kbId ? '操作日志' : '全部操作日志';

  const loadData = async () => {
    try {
      setLoading(true);

      const res = await fetchOperationLogs({
        kb_id: kbId || undefined,
        page: pagination.current,
        page_size: pagination.pageSize,
        action: action || undefined,
        keyword: keyword || undefined,
      });

      if (res.code === 0 || res.code === 200) {
        setLogs(res.data?.logs || []);
        setTotal(res.data?.total || 0);
      } else {
        setLogs([]);
        setTotal(0);
        message.error(res.message || '获取操作日志失败');
      }
    } catch (error) {
      console.error(error);
      message.error('请求失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();

    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [kbId, pagination.current, pagination.pageSize, action]);

  const columns = useMemo<ColumnDef<OperationLogItem>[]>(
    () => [
      {
        accessorKey: 'target_name',
        header: '文件',
        cell: ({ row }) => (
          <div
            className="max-w-[180px] truncate"
            title={row.original.target_name || row.original.target_id || ''}
          >
            {row.original.target_name || row.original.target_id || '-'}
          </div>
        ),
      },

      {
        accessorKey: 'user_name',
        header: '用户',
        cell: ({ row }) => {
          const log = row.original;

          return (
            <div className="flex min-w-[180px] items-center gap-2.5">
              <Avatar
                size={32}
                src={log.user_avatar || undefined}
                className="shrink-0 bg-blue-100 text-sm font-medium text-blue-700"
              >
                {getAvatarText(log)}
              </Avatar>

              <div className="min-w-0">
                <div
                  className="max-w-[150px] truncate text-sm font-medium text-text-primary"
                  title={log.user_name || log.user_id || ''}
                >
                  {log.user_name || log.user_id || '-'}
                </div>

                <div
                  className="max-w-[150px] truncate text-xs text-gray-500"
                  title={log.user_email || ''}
                >
                  {log.user_email || '-'}
                </div>
              </div>
            </div>
          );
        },
      },
      // {
      //   accessorKey: 'kb_name',
      //   header: '知识库',
      //   cell: ({ row }) => (
      //     <div
      //       className="max-w-[160px] truncate"
      //       title={row.original.kb_name || row.original.kb_id || ''}
      //     >
      //       {row.original.kb_name || row.original.kb_id || '-'}
      //     </div>
      //   ),
      // },

      {
        accessorKey: 'action',
        header: '操作类型',
        cell: ({ row }) => {
          const currentAction = row.original.action;

          return (
            <span
              className={`inline-flex h-6 items-center whitespace-nowrap rounded border px-2 text-xs font-medium ${getActionStyle(
                currentAction,
              )}`}
            >
              {getActionLabel(currentAction)}
            </span>
          );
        },
      },
      {
        accessorKey: 'status',
        header: '结果',
        cell: ({ row }) => {
          const success = row.original.status === 'success';

          return (
            <span
              className={`inline-flex h-6 items-center whitespace-nowrap rounded px-2 text-xs font-medium ${
                success
                  ? 'bg-green-50 text-green-700 dark:bg-green-950 dark:text-green-300'
                  : 'bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-300'
              }`}
            >
              {statusMap[row.original.status] || row.original.status || '-'}
            </span>
          );
        },
      },
      {
        accessorKey: 'message',
        header: '说明',
        cell: ({ row }) => {
          const messageText = row.original.message?.trim() || '';
          const isSuccess = row.original.status === 'success';

          if (!messageText) {
            return <span className="block w-[210px] pr-8">-</span>;
          }

          return (
            <div className="flex w-[210px] max-w-[210px] items-center gap-3 pr-8">
              <span className="min-w-0 flex-1 truncate" title={messageText}>
                {messageText}
              </span>

              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    type="button"
                    aria-label="查看完整说明"
                    className={`flex size-5 shrink-0 items-center justify-center rounded-full transition-colors focus:outline-none ${
                      isSuccess
                        ? 'text-green-500 hover:bg-green-50 hover:text-green-600'
                        : 'text-red-500 hover:bg-red-50 hover:text-red-600'
                    }`}
                    onClick={(event) => {
                      event.stopPropagation();
                    }}
                  >
                    <CircleAlert className="size-4" />
                  </button>
                </TooltipTrigger>

                <TooltipContent
                  side="top"
                  align="end"
                  sideOffset={8}
                  className={`z-[100] w-[320px] max-w-[calc(100vw-32px)] rounded-md border p-3 text-xs text-white shadow-xl ${
                    isSuccess
                      ? 'border-green-700 bg-green-950'
                      : 'border-red-700 bg-red-950'
                  }`}
                >
                  <div
                    className={`mb-1.5 font-medium ${
                      isSuccess ? 'text-green-300' : 'text-red-300'
                    }`}
                  >
                    说明详情
                  </div>

                  <div className="whitespace-pre-wrap break-words leading-5 text-white">
                    {messageText}
                  </div>
                </TooltipContent>
              </Tooltip>
            </div>
          );
        },
      },
      {
        accessorKey: 'operation_time',
        header: '时间',
        cell: ({ row }) => (
          <span className="block whitespace-nowrap pl-8">
            {row.original.operation_time || '-'}
          </span>
        ),
      },

      {
        id: 'actions',
        header: '详情',
        cell: ({ row }) => (
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="h-7 whitespace-nowrap px-3 text-xs"
            onClick={(event) => {
              event.stopPropagation();
              setSelectedLog(row.original);
              setDetailVisible(true);
            }}
          >
            查看
          </Button>
        ),
      },
    ],
    [],
  );

  const table = useReactTable({
    data: logs,
    columns,
    getCoreRowModel: getCoreRowModel(),
    manualPagination: true,
    state: {
      pagination: {
        pageIndex: pagination.current - 1,
        pageSize: pagination.pageSize,
      },
    },
  });

  return (
    <TooltipProvider delayDuration={200}>
      <section className="min-w-[880px] p-5">
        <div className="flex flex-wrap items-end justify-between gap-4 pb-4">
          <div className="items-start">
            <div className="pb-1 text-2xl font-semibold">{title}</div>
            <div className="text-sm text-text-secondary">
              查看用户、文件和知识库的操作记录
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button
                  type="button"
                  className="flex h-9 w-9 items-center justify-center rounded border bg-transparent text-sm outline-none hover:bg-white/10 focus:border-gray-400 focus:outline-none focus:ring-0"
                >
                  <Filter className="h-4 w-4" />
                </button>
              </DropdownMenuTrigger>

              <DropdownMenuContent className="w-40">
                <DropdownMenuItem
                  onClick={() => {
                    setAction('');
                    setPagination((prev) => ({ ...prev, current: 1 }));
                  }}
                >
                  全部操作
                </DropdownMenuItem>

                <DropdownMenuItem
                  onClick={() => {
                    setAction('upload');
                    setPagination((prev) => ({ ...prev, current: 1 }));
                  }}
                >
                  上传
                </DropdownMenuItem>

                <DropdownMenuItem
                  onClick={() => {
                    setAction('download');
                    setPagination((prev) => ({ ...prev, current: 1 }));
                  }}
                >
                  下载
                </DropdownMenuItem>

                <DropdownMenuItem
                  onClick={() => {
                    setAction('rename');
                    setPagination((prev) => ({ ...prev, current: 1 }));
                  }}
                >
                  重命名
                </DropdownMenuItem>

                <DropdownMenuItem
                  onClick={() => {
                    setAction('enable');
                    setPagination((prev) => ({ ...prev, current: 1 }));
                  }}
                >
                  修改状态为开启
                </DropdownMenuItem>

                <DropdownMenuItem
                  onClick={() => {
                    setAction('disable');
                    setPagination((prev) => ({ ...prev, current: 1 }));
                  }}
                >
                  修改状态为关闭
                </DropdownMenuItem>

                <DropdownMenuItem
                  onClick={() => {
                    setAction('update_tags');
                    setPagination((prev) => ({ ...prev, current: 1 }));
                  }}
                >
                  修改标签
                </DropdownMenuItem>

                <DropdownMenuItem
                  onClick={() => {
                    setAction('update_meta');
                    setPagination((prev) => ({ ...prev, current: 1 }));
                  }}
                >
                  修改元数据
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>

            <input
              className="h-9 w-56 rounded border bg-transparent px-3 text-sm outline-none placeholder:text-gray-400 focus:border-gray-400 focus:outline-none focus:ring-0"
              placeholder="搜索用户 / 文件 / 知识库"
              value={keyword}
              onChange={(event) => {
                setKeyword(event.target.value);
              }}
              onKeyDown={(event) => {
                if (event.key === 'Enter') {
                  if (pagination.current !== 1) {
                    setPagination((prev) => ({
                      ...prev,
                      current: 1,
                    }));
                  } else {
                    loadData();
                  }
                }
              }}
            />

            <Button
              size="sm"
              onClick={() => {
                if (pagination.current !== 1) {
                  setPagination((prev) => ({
                    ...prev,
                    current: 1,
                  }));
                } else {
                  loadData();
                }
              }}
            >
              <Search className="h-4 w-4" />
              查询
            </Button>
          </div>
        </div>

        <Table rootClassName="max-h-[calc(100vh-222px)]">
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => {
                  const columnId = header.column.id;

                  let headerClassName = '';

                  if (columnId === 'operation_time') {
                    headerClassName = 'whitespace-nowrap';
                  }

                  if (columnId === 'message') {
                    headerClassName = 'w-[160px] max-w-[160px]';
                  }

                  if (columnId === 'actions') {
                    headerClassName = 'whitespace-nowrap';
                  }

                  return (
                    <TableHead
                      key={header.id}
                      className={
                        header.column.id === 'message'
                          ? 'w-[230px] max-w-[230px] pr-8'
                          : header.column.id === 'operation_time'
                            ? 'whitespace-nowrap pl-8'
                            : undefined
                      }
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
            {!loading && table.getRowModel().rows?.length ? (
              table.getRowModel().rows.map((row) => (
                <TableRow key={row.id} className="group">
                  {row.getVisibleCells().map((cell) => {
                    const columnId = cell.column.id;

                    let cellClassName = '';

                    if (columnId === 'operation_time') {
                      cellClassName = 'whitespace-nowrap';
                    }

                    if (columnId === 'message') {
                      cellClassName = 'w-[160px] max-w-[160px]';
                    }

                    if (columnId === 'actions') {
                      cellClassName = 'whitespace-nowrap';
                    }

                    return (
                      <TableCell
                        key={cell.id}
                        className={
                          cell.column.id === 'message'
                            ? 'w-[230px] max-w-[230px] pr-8'
                            : cell.column.id === 'operation_time'
                              ? 'whitespace-nowrap pl-8'
                              : undefined
                        }
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
                  {loading ? '正在加载...' : '暂无操作日志'}
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>

        <div className="absolute bottom-3 right-3 flex items-center justify-end py-4">
          <div className="space-x-2">
            <RAGFlowPagination
              current={pagination.current}
              pageSize={pagination.pageSize}
              total={total}
              onChange={(page, pageSize) => {
                setPagination({
                  current: page,
                  pageSize,
                });
              }}
            />
          </div>
        </div>

        <Modal
          open={detailVisible}
          onCancel={() => {
            setDetailVisible(false);
          }}
          afterClose={() => {
            setSelectedLog(null);
          }}
          footer={null}
          width={800}
          title="操作日志详情"
        >
          <div className="space-y-4 text-sm">
            <div className="flex items-center gap-3 rounded border border-gray-200 bg-gray-50 p-3 dark:border-gray-700 dark:bg-gray-900">
              <Avatar
                size={42}
                src={selectedLog?.user_avatar || undefined}
                className="shrink-0 bg-blue-100 text-base font-medium text-blue-700"
              >
                {getAvatarText(selectedLog)}
              </Avatar>

              <div className="min-w-0">
                <div className="truncate font-medium">
                  {selectedLog?.user_name || selectedLog?.user_id || '-'}
                </div>
                <div className="truncate text-xs text-gray-500">
                  {selectedLog?.user_email || '-'}
                </div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <b>知识库：</b>
                {selectedLog?.kb_name || selectedLog?.kb_id || '-'}
              </div>

              <div>
                <b>文件：</b>
                {selectedLog?.target_name || selectedLog?.target_id || '-'}
              </div>

              <div className="flex items-center gap-2">
                <b>操作：</b>
                {selectedLog ? (
                  <span
                    className={`inline-flex h-6 items-center whitespace-nowrap rounded border px-2 text-xs font-medium ${getActionStyle(
                      selectedLog.action,
                    )}`}
                  >
                    {getActionLabel(selectedLog.action)}
                  </span>
                ) : (
                  '-'
                )}
              </div>

              <div>
                <b>结果：</b>
                {selectedLog ? (
                  <span
                    className={`ml-1 inline-flex h-6 items-center whitespace-nowrap rounded px-2 text-xs font-medium ${
                      selectedLog.status === 'success'
                        ? 'bg-green-50 text-green-700 dark:bg-green-950 dark:text-green-300'
                        : 'bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-300'
                    }`}
                  >
                    {statusMap[selectedLog.status] || selectedLog.status || '-'}
                  </span>
                ) : (
                  '-'
                )}
              </div>

              <div>
                <b>IP：</b>
                {selectedLog?.ip || '-'}
              </div>

              <div>
                <b>时间：</b>
                <span className="whitespace-nowrap">
                  {selectedLog?.operation_time || '-'}
                </span>
              </div>
            </div>

            <div>
              <div className="mb-2 font-medium">说明</div>

              <div
                className={`rounded border p-3 ${
                  selectedLog?.status === 'success'
                    ? 'border-green-200 bg-green-50 text-green-900 dark:border-green-800 dark:bg-green-950 dark:text-green-100'
                    : selectedLog?.status === 'failed'
                      ? 'border-red-200 bg-red-50 text-red-900 dark:border-red-800 dark:bg-red-950 dark:text-red-100'
                      : 'border-gray-200 bg-gray-50 text-gray-800 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100'
                }`}
              >
                {selectedLog?.message || '-'}
              </div>
            </div>

            <div>
              <div className="mb-2 font-medium">操作前数据</div>

              <pre className="max-h-56 overflow-auto whitespace-pre-wrap rounded border border-gray-200 bg-gray-50 p-3 text-xs text-gray-800 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100">
                {formatJsonText(selectedLog?.before_data)}
              </pre>
            </div>

            <div>
              <div className="mb-2 font-medium">操作后数据</div>

              <pre className="max-h-56 overflow-auto whitespace-pre-wrap rounded border border-gray-200 bg-gray-50 p-3 text-xs text-gray-800 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100">
                {formatJsonText(selectedLog?.after_data)}
              </pre>
            </div>
          </div>
        </Modal>
      </section>
    </TooltipProvider>
  );
}
