import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  type ColumnDef,
} from '@tanstack/react-table';
import { Modal, message } from 'antd';
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

import { RAGFlowPagination } from '@/components/ui/ragflow-pagination';
import { getAuthorization } from '@/utils/authorization-util';
// import { Hourglass } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Filter, Search } from 'lucide-react';

const authHeaders = {
  Authorization: getAuthorization() || '',
  'Content-Type': 'application/json',
};

type OperationLogItem = {
  id: string;
  user_id: string;
  user_name?: string | null;
  user_email?: string | null;
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
        console.log('operation log response:', res);
        console.log('operation logs:', res.data?.logs);
      } else {
        setLogs([]);
        setTotal(0);
        message.error(res.message || '获取操作日志失败');
      }
    } catch (e) {
      console.error(e);
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
        accessorKey: 'operation_time',
        header: '时间',
        cell: ({ row }) => row.original.operation_time || '-',
      },
      {
        accessorKey: 'user_name',
        header: '用户',
        cell: ({ row }) => (
          <div className="flex flex-col">
            <span>{row.original.user_name || row.original.user_id || '-'}</span>
            <span className="text-xs text-gray-500">
              {row.original.user_email || '-'}
            </span>
          </div>
        ),
      },
      {
        accessorKey: 'kb_name',
        header: '知识库',
        cell: ({ row }) => row.original.kb_name || row.original.kb_id || '-',
      },
      {
        accessorKey: 'target_name',
        header: '文件',
        cell: ({ row }) =>
          row.original.target_name || row.original.target_id || '-',
      },
      {
        accessorKey: 'action',
        header: '操作类型',
        cell: ({ row }) =>
          actionMap[row.original.action] || row.original.action || '-',
      },
      {
        accessorKey: 'status',
        header: '结果',
        cell: ({ row }) => {
          const success = row.original.status === 'success';
          return (
            <span className={success ? 'text-green-600' : 'text-red-600'}>
              {statusMap[row.original.status] || row.original.status || '-'}
            </span>
          );
        },
      },
      {
        accessorKey: 'message',
        header: '说明',
        cell: ({ row }) => row.original.message || '-',
      },
      {
        id: 'actions',
        header: '详情',
        cell: ({ row }) => (
          <button
            className="text-blue-600 hover:underline"
            onClick={() => {
              setSelectedLog(row.original);
              setDetailVisible(true);
            }}
          >
            查看
          </button>
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
    <section className="min-w-[880px] p-5">
      <div className="flex flex-wrap items-end justify-between gap-4 pb-4">
        <div className="items-start">
          <div className="pb-1 text-2xl font-semibold">{title}</div>
          <div className="text-text-secondary text-sm">
            查看用户、文件和知识库的操作记录
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button
                type="button"
                className="h-9 w-9 rounded border bg-transparent flex items-center justify-center text-sm outline-none hover:bg-white/10 focus:border-gray-400 focus:outline-none focus:ring-0"
              >
                <Filter className="h-4 w-4" />
              </button>
            </DropdownMenuTrigger>

            <DropdownMenuContent className="w-40">
              <DropdownMenuItem
                onClick={() => {
                  setAction('');
                  setPagination((prev) => ({
                    ...prev,
                    current: 1,
                  }));
                }}
              >
                全部操作
              </DropdownMenuItem>

              <DropdownMenuItem
                onClick={() => {
                  setAction('upload');
                  setPagination((prev) => ({
                    ...prev,
                    current: 1,
                  }));
                }}
              >
                上传
              </DropdownMenuItem>

              <DropdownMenuItem
                onClick={() => {
                  setAction('download');
                  setPagination((prev) => ({
                    ...prev,
                    current: 1,
                  }));
                }}
              >
                下载
              </DropdownMenuItem>

              <DropdownMenuItem
                onClick={() => {
                  setAction('rename');
                  setPagination((prev) => ({
                    ...prev,
                    current: 1,
                  }));
                }}
              >
                重命名
              </DropdownMenuItem>

              <DropdownMenuItem
                onClick={() => {
                  setAction('enable');
                  setPagination((prev) => ({
                    ...prev,
                    current: 1,
                  }));
                }}
              >
                修改状态为开启
              </DropdownMenuItem>

              <DropdownMenuItem
                onClick={() => {
                  setAction('disable');
                  setPagination((prev) => ({
                    ...prev,
                    current: 1,
                  }));
                }}
              >
                修改状态为关闭
              </DropdownMenuItem>

              <DropdownMenuItem
                onClick={() => {
                  setAction('update_tags');
                  setPagination((prev) => ({
                    ...prev,
                    current: 1,
                  }));
                }}
              >
                修改标签
              </DropdownMenuItem>

              <DropdownMenuItem
                onClick={() => {
                  setAction('update_meta');
                  setPagination((prev) => ({
                    ...prev,
                    current: 1,
                  }));
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
            onChange={(e) => setKeyword(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                setPagination((prev) => ({
                  ...prev,
                  current: 1,
                }));
                loadData();
              }
            }}
          />

          <Button
            size="sm"
            onClick={() => {
              setPagination((prev) => ({
                ...prev,
                current: 1,
              }));
              loadData();
            }}
          >
            <Search />
            查询
          </Button>
        </div>
      </div>

      <Table rootClassName="max-h-[calc(100vh-222px)]">
        <TableHeader>
          {table.getHeaderGroups().map((headerGroup) => (
            <TableRow key={headerGroup.id}>
              {headerGroup.headers.map((header) => (
                <TableHead key={header.id}>
                  {header.isPlaceholder
                    ? null
                    : flexRender(
                        header.column.columnDef.header,
                        header.getContext(),
                      )}
                </TableHead>
              ))}
            </TableRow>
          ))}
        </TableHeader>

        <TableBody className="relative">
          {!loading && table.getRowModel().rows?.length ? (
            table.getRowModel().rows.map((row) => (
              <TableRow key={row.id} className="group">
                {row.getVisibleCells().map((cell) => (
                  <TableCell key={cell.id}>
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </TableCell>
                ))}
              </TableRow>
            ))
          ) : (
            <TableRow>
              <TableCell
                colSpan={columns.length}
                className="h-24 text-center text-gray-500"
              >
                暂无操作日志
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>

      <div className="flex items-center justify-end py-4 absolute bottom-3 right-3">
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
        onCancel={() => setDetailVisible(false)}
        footer={null}
        width={800}
        title="操作日志详情"
      >
        <div className="space-y-4 text-sm">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <b>用户：</b>
              {selectedLog?.user_name || selectedLog?.user_id || '-'}
            </div>
            <div>
              <b>账号：</b>
              {selectedLog?.user_email || '-'}
            </div>
            <div>
              <b>知识库：</b>
              {selectedLog?.kb_name || selectedLog?.kb_id || '-'}
            </div>
            <div>
              <b>文件：</b>
              {selectedLog?.target_name || selectedLog?.target_id || '-'}
            </div>
            <div>
              <b>操作：</b>
              {selectedLog
                ? actionMap[selectedLog.action] || selectedLog.action
                : '-'}
            </div>
            <div>
              <b>结果：</b>
              {selectedLog
                ? statusMap[selectedLog.status] || selectedLog.status
                : '-'}
            </div>
            <div>
              <b>IP：</b>
              {selectedLog?.ip || '-'}
            </div>
            <div>
              <b>时间：</b>
              {selectedLog?.operation_time || '-'}
            </div>
          </div>

          <div>
            <div className="mb-2 font-medium">说明</div>
            <div className="rounded border border-gray-200 bg-gray-50 p-3 text-gray-800 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100">
              {selectedLog?.message || '-'}
            </div>
          </div>

          <div>
            <div className="mb-2 font-medium">操作前数据</div>
            <pre className="max-h-56 overflow-auto rounded border border-gray-200 bg-gray-50 p-3 text-xs text-gray-800 whitespace-pre-wrap dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100">
              {formatJsonText(selectedLog?.before_data)}
            </pre>
          </div>

          <div>
            <div className="mb-2 font-medium">操作后数据</div>
            <pre className="max-h-56 overflow-auto rounded border border-gray-200 bg-gray-50 p-3 text-xs text-gray-800 whitespace-pre-wrap dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100">
              {formatJsonText(selectedLog?.after_data)}
            </pre>
          </div>
        </div>
      </Modal>
    </section>
  );
}
