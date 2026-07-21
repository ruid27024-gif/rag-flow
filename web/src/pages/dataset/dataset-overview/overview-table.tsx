import { EmptyType } from '@/components/empty/constant';
import Empty from '@/components/empty/empty';
import FileStatusBadge from '@/components/file-status-badge';
import { FileIcon, IconFontFill } from '@/components/icon-font';
import { RAGFlowAvatar } from '@/components/ragflow-avatar';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { RAGFlowPagination } from '@/components/ui/ragflow-pagination';
import { Separator } from '@/components/ui/separator';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { RunningStatusMap } from '@/constants/knowledge';
import { useTranslate } from '@/hooks/common-hooks';
import { useNavigatePage } from '@/hooks/logic-hooks/navigate-hooks';
import { cn } from '@/lib/utils';
import { PipelineResultSearchParams } from '@/pages/dataflow-result/constant';
import { NavigateToDataflowResultProps } from '@/pages/dataflow-result/interface';
import { useDataSourceInfo } from '@/pages/user-setting/data-source/contant';
import { IDataSourceInfoMap } from '@/pages/user-setting/data-source/interface';
import { getAuthorization } from '@/utils/authorization-util';
import { formatSecondsToHumanReadable } from '@/utils/date';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ColumnDef,
  ColumnFiltersState,
  Row,
  SortingState,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
} from '@tanstack/react-table';
import { TFunction } from 'i18next';
import {
  ArrowUpDown,
  BrushCleaning,
  ClipboardList,
  Eye,
  MonitorUp,
  Trash2,
} from 'lucide-react';
import { FC, useCallback, useMemo, useState } from 'react';
import { useParams } from 'umi';
import { RunningStatus } from '../dataset/constant';
import ProcessLogModal from '../process-log-modal';
import { LogTabs, ProcessingType, ProcessingTypeMap } from './dataset-common';
import { DocumentLog, FileLogsTableProps, IFileLogItem } from './interface';

const formatDate = (dateStr: string) => {
  if (!dateStr) return '-';
  const date = new Date(dateStr);

  const year = date.getUTCFullYear();
  const month = String(date.getUTCMonth() + 1).padStart(2, '0');
  const day = String(date.getUTCDate()).padStart(2, '0');
  const hours = String(date.getUTCHours()).padStart(2, '0');
  const minutes = String(date.getUTCMinutes()).padStart(2, '0');
  const seconds = String(date.getUTCSeconds()).padStart(2, '0');

  return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
};
export const useRemovePipelineLogs = () => {
  const queryClient = useQueryClient();

  const { isPending: loading, mutateAsync } = useMutation({
    mutationFn: async ({
      kbId,
      logIds,
    }: {
      kbId: string;
      logIds: string[];
    }) => {
      const response = await fetch(
        `/v1/kb/delete_pipeline_logs_bydoc?kb_id=${kbId}`,
        {
          method: 'POST',
          headers: {
            Authorization: getAuthorization() || '',
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ log_ids: logIds }),
        },
      );

      if (!response.ok) {
        throw new Error('删除失败');
      }

      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['fileLogList'],
      });
    },
  });

  return {
    loading,
    deletePipelineLogs: mutateAsync,
  };
};

// const deletePipelineLogs = async (kbId: string, logIds: string[]) => {
//   const response = await fetch(`/v1/kb/delete_pipeline_logs?kb_id=${kbId}`, {
//     method: 'POST',
//     headers: {
//               Authorization: getAuthorization() || '',
//             },
//     body: JSON.stringify({ log_ids: logIds }),
//   });
//   if (!response.ok) throw new Error('删除失败');
//   return response.json();
// };

export const getFileLogsTableColumns = (
  t: TFunction<'translation', string>,
  showLog: (row: Row<IFileLogItem & DocumentLog>, active: LogTabs) => void,
  kowledgeId: string,
  navigateToDataflowResult: (
    props: NavigateToDataflowResultProps,
  ) => () => void,
  dataSourceInfo: IDataSourceInfoMap,
  // 【新增】批量删除回调函数，接收选中的 ID 数组
  onBatchDelete?: (ids: string[]) => void,
  isDeleting?: boolean,
) => {
  // const { t } = useTranslate('knowledgeDetails');

  const columns: ColumnDef<IFileLogItem & DocumentLog>[] = [
    // {
    //   id: 'select',
    //   header: ({ table }) => (
    //     <input
    //       type="checkbox"
    //       checked={table.getIsAllRowsSelected()}
    //       onChange={table.getToggleAllRowsSelectedHandler()}
    //       className="rounded bg-gray-900 text-blue-500 focus:ring-blue-500"
    //     />
    //   ),
    //   cell: ({ row }) => (
    //     <input
    //       type="checkbox"
    //       checked={row.getIsSelected()}
    //       onChange={row.getToggleSelectedHandler()}
    //       className="rounded border-gray-600 bg-gray-900 text-blue-500 focus:ring-blue-500"
    //     />
    //   ),
    // },
    {
      id: 'select',
      header: ({ table }) => (
        <div className="flex items-center justify-center">
          <input
            type="checkbox"
            checked={table.getIsAllRowsSelected()}
            onChange={table.getToggleAllRowsSelectedHandler()}
            className="rounded bg-gray-900 text-blue-500 focus:ring-blue-500"
          />
        </div>
      ),
      cell: ({ row }) => (
        <div className="flex items-center justify-center">
          <input
            type="checkbox"
            checked={row.getIsSelected()}
            onChange={row.getToggleSelectedHandler()}
            className="rounded border-gray-600 bg-gray-900 text-blue-500 focus:ring-blue-500"
          />
        </div>
      ),
      enableSorting: false,
      enableHiding: false,
    },
    {
      accessorKey: 'id',
      header: 'ID',
      meta: {
        cellClassName: 'max-w-[20vw] text-left',
        headerClassName: 'text-left',
      },
      cell: ({ row }) => (
        <div className="text-text-primary text-left">{row.original.id}</div>
      ),
    },
    {
      accessorKey: 'fileName',
      header: t('fileName'),
      meta: {
        cellClassName: 'max-w-[20vw] text-left',
        headerClassName: 'text-left',
      },
      cell: ({ row }) => (
        <Tooltip>
          <TooltipTrigger asChild>
            <div className="flex items-center gap-2 cursor-pointer text-left">
              <FileIcon name={row.original.document_name}></FileIcon>
              <span className={cn('truncate')}>
                {row.original.document_name}
              </span>
            </div>
          </TooltipTrigger>
          <TooltipContent>
            <p>{row.original.document_name}</p>
          </TooltipContent>
        </Tooltip>
      ),
    },
    {
      accessorKey: 'source_from',
      header: t('source'),
      meta: {
        cellClassName: 'max-w-[20vw] text-left',
        headerClassName: 'text-left',
      },
      cell: ({ row }) => (
        <div className="text-text-primary flex justify-start">
          {row.original.source_from === 'local' ||
          row.original.source_from === '' ? (
            <div className="flex items-center gap-2">
              <div className="bg-accent-primary-5 w-6 h-6 rounded-full flex items-center justify-center">
                <MonitorUp className="text-accent-primary" size={16} />
              </div>
              <span className="text-sm">本地</span>
            </div>
          ) : (
            <div className="w-6 h-6 flex items-center justify-center">
              {
                dataSourceInfo[
                  row.original.source_from as keyof typeof dataSourceInfo
                ].icon
              }
            </div>
          )}
        </div>
      ),
    },
    {
      accessorKey: 'pipeline_title',
      header: t('dataPipeline'),
      meta: {
        cellClassName: 'max-w-[20vw] text-left',
        headerClassName: 'text-left',
      },
      cell: ({ row }) => {
        const title = row.original.pipeline_title;
        const pipelineTitle = title === 'naive' ? 'general' : title;
        return (
          <div className="flex items-center justify-start gap-2 text-text-primary">
            <RAGFlowAvatar
              avatar={row.original.avatar}
              name={pipelineTitle}
              className="size-4"
            />
            {pipelineTitle}
          </div>
        );
      },
    },
    {
      accessorKey: 'process_begin_at',
      header: ({ column }) => {
        return (
          <Button
            variant="transparent"
            className="border-none justify-start px-0"
            onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
          >
            {t('startDate')}
            <ArrowUpDown />
          </Button>
        );
      },
      meta: {
        cellClassName: 'max-w-[20vw] text-left',
        headerClassName: 'text-left',
      },
      cell: ({ row }) => (
        <div className="text-text-primary text-left">
          {formatDate(row.original.process_begin_at)}
        </div>
      ),
    },
    {
      accessorKey: 'task_type',
      header: t('task'),
      meta: {
        cellClassName: 'max-w-[20vw] text-left',
        headerClassName: 'text-left',
      },
      cell: ({ row }) => (
        <div className="text-text-primary text-left">
          {row.original.task_type}
        </div>
      ),
    },
    {
      accessorKey: 'latest_task_scene_text',
      header: t('task_detail'),
      meta: {
        cellClassName: 'max-w-[20vw] text-left',
        headerClassName: 'text-left',
      },
      cell: ({ row }) => {
        const scene = row.original.process_scene;
        const taskText = row.original.process_scene_text || '-';

        const sceneStyleMap = {
          author_extract: 'bg-blue-50 text-blue-700 border-blue-200',
          full_parse: 'bg-emerald-50 text-emerald-700 border-emerald-200',
          graph_parse: 'bg-purple-50 text-purple-700 border-purple-200',
          raptor: 'bg-orange-50 text-orange-700 border-orange-200',
          unknown: 'bg-slate-50 text-slate-600 border-slate-200',

          // 兼容旧字段
          author_only: 'bg-blue-50 text-blue-700 border-blue-200',
          parse_only: 'bg-emerald-50 text-emerald-700 border-emerald-200',
          author_with_parse:
            'bg-emerald-50 text-emerald-700 border-emerald-200',
        } as const;

        const tagClassName =
          sceneStyleMap[scene as keyof typeof sceneStyleMap] ||
          sceneStyleMap.unknown;

        return (
          <span
            className={[
              'inline-flex items-center w-fit rounded-md border px-2 py-0.5',
              'text-xs font-medium leading-5 truncate max-w-full',
              tagClassName,
            ].join(' ')}
            title={taskText}
          >
            {taskText}
          </span>
        );
      },
    },
    {
      accessorKey: 'operation_status',
      header: t('status'),
      meta: {
        headerClassName: 'text-center',
        cellClassName: 'text-center',
      },
      cell: ({ row }) => (
        <div className="flex justify-center">
          <FileStatusBadge
            status={row.original.operation_status as RunningStatus}
            name={
              RunningStatusMap[row.original.operation_status as RunningStatus]
            }
          />
        </div>
      ),
    },
    {
      id: 'operations',
      header: t('operations'),
      meta: {
        cellClassName: 'max-w-[20vw] text-center',
        headerClassName: 'text-center',
      },
      // cell: ({ row }) => (
      //   <div className="flex justify-center">
      //     <div className="flex min-w-[72px] justify-center space-x-2 opacity-0 group-hover:opacity-100 transition-opacity">
      //       <Button
      //         variant="ghost"
      //         size="sm"
      //         className="p-1"
      //         onClick={() => {
      //           showLog(row, LogTabs.FILE_LOGS);
      //         }}
      //       >
      //         <Eye />
      //       </Button>
      //       {row.original.pipeline_id && (
      //         <Button
      //           variant="ghost"
      //           size="sm"
      //           className="p-1"
      //           onClick={navigateToDataflowResult({
      //             id: row.original.id,
      //             [PipelineResultSearchParams.KnowledgeId]: kowledgeId,
      //             [PipelineResultSearchParams.DocumentId]:
      //               row.original.document_id,
      //             [PipelineResultSearchParams.IsReadOnly]: 'false',
      //             [PipelineResultSearchParams.Type]: 'dataflow',
      //           })}
      //         >
      //           <ClipboardList />
      //         </Button>
      //       )}
      //     </div>
      //   </div>
      // ),
      cell: ({ row }) => (
        <div className="flex justify-center">
          <div className="flex min-w-[96px] justify-center space-x-2 opacity-0 group-hover:opacity-100 transition-opacity">
            <Button
              variant="ghost"
              size="sm"
              className="p-1"
              onClick={() => {
                showLog(row, LogTabs.FILE_LOGS);
              }}
              title="任务记录"
            >
              <Eye />
            </Button>

            {row.original.pipeline_id && (
              <Button
                variant="ghost"
                size="sm"
                className="p-1"
                onClick={navigateToDataflowResult({
                  id: row.original.id,
                  [PipelineResultSearchParams.KnowledgeId]: kowledgeId,
                  [PipelineResultSearchParams.DocumentId]:
                    row.original.document_id,
                  [PipelineResultSearchParams.IsReadOnly]: 'false',
                  [PipelineResultSearchParams.Type]: 'dataflow',
                })}
              >
                <ClipboardList />
              </Button>
            )}

            {onBatchDelete && (
              <Button
                variant="ghost"
                size="sm"
                className="p-1 text-state-error hover:text-state-error"
                disabled={isDeleting}
                onClick={() => {
                  onBatchDelete([row.original.id]);
                }}
                title="删除"
              >
                <Trash2 />
              </Button>
            )}
          </div>
        </div>
      ),
    },
  ];

  return columns;
};

export const getDatasetLogsTableColumns = (
  t: TFunction<'translation', string>,
  showLog: (row: Row<IFileLogItem & DocumentLog>, active: LogTabs) => void,
) => {
  // const { t } = useTranslate('knowledgeDetails');
  const columns: ColumnDef<IFileLogItem & DocumentLog>[] = [
    // {
    // id: 'select',
    // header: ({ table }) => (
    //   <input
    //     type="checkbox"
    //     checked={table.getIsAllRowsSelected()}
    //     onChange={table.getToggleAllRowsSelectedHandler()}
    //     className="rounded bg-gray-900 text-blue-500 focus:ring-blue-500"
    //   />
    // ),
    // cell: ({ row }) => (
    //   <input
    //     type="checkbox"
    //     checked={row.getIsSelected()}
    //     onChange={row.getToggleSelectedHandler()}
    //     className="rounded border-gray-600 bg-gray-900 text-blue-500 focus:ring-blue-500"
    //   />
    // ),
    // },
    {
      accessorKey: 'id',
      header: t('taskId'),
      cell: ({ row }) => (
        <div className="text-text-primary">{row.original.id}</div>
      ),
    },
    {
      accessorKey: 'process_begin_at',
      header: ({ column }) => {
        return (
          <Button
            variant="transparent"
            className="border-none"
            onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
          >
            {t('startDate')}
            <ArrowUpDown />
          </Button>
        );
      },
      cell: ({ row }) => (
        <div className="text-text-primary">
          {formatDate(row.original.process_begin_at)}
        </div>
      ),
    },
    {
      accessorKey: 'task_type',
      header: t('processingType'),
      cell: ({ row }) => (
        <div className="flex items-center gap-2 text-text-primary">
          {ProcessingType.knowledgeGraph === row.original.task_type && (
            <IconFontFill
              name={`knowledgegraph`}
              className="text-text-secondary"
            ></IconFontFill>
          )}
          {ProcessingType.raptor === row.original.task_type && (
            <IconFontFill
              name={`dataflow-01`}
              className="text-text-secondary"
            ></IconFontFill>
          )}
          {ProcessingTypeMap[row.original.task_type as ProcessingType] ||
            row.original.task_type}
        </div>
      ),
    },
    {
      accessorKey: 'operation_status',
      header: t('status'),
      cell: ({ row }) => (
        // <FileStatusBadge
        //   status={row.original.status}
        //   name={row.original.statusName}
        // />
        <FileStatusBadge
          status={row.original.operation_status as RunningStatus}
          name={
            RunningStatusMap[row.original.operation_status as RunningStatus]
          }
        />
      ),
    },
    {
      id: 'operations',
      header: t('operations'),
      cell: ({ row }) => (
        <div className="flex justify-start space-x-2 opacity-0 group-hover:opacity-100 transition-opacity">
          <Button
            variant="ghost"
            size="sm"
            className="p-1"
            onClick={() => {
              showLog(row, LogTabs.DATASET_LOGS);
            }}
          >
            <Eye />
          </Button>
        </div>
      ),
    },
  ];

  return columns;
};

const FileLogsTable: FC<FileLogsTableProps> = ({
  data,
  pagination,
  setPagination,
  active = LogTabs.FILE_LOGS,
}) => {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);
  const [rowSelection, setRowSelection] = useState({});
  const kowledgeId = useParams().id;
  const { loading: isDeleting, deletePipelineLogs } = useRemovePipelineLogs();
  const handleBatchDelete = useCallback(
    async (ids: string[]) => {
      if (!ids.length || !kowledgeId) return;
      if (!confirm(`确定要删除这 ${ids.length} 条日志吗？`)) return;

      try {
        await deletePipelineLogs({
          kbId: kowledgeId,
          logIds: ids,
        });

        setRowSelection({});
      } catch (error) {
        console.error(error);
        alert('删除失败，请稍后重试');
      }
    },
    [kowledgeId, deletePipelineLogs],
  );

  const { t } = useTranslate('knowledgeDetails');
  const { t: tDatasetOverview } = useTranslate('datasetOverview');
  const [isModalVisible, setIsModalVisible] = useState(false);
  const { navigateToDataflowResult } = useNavigatePage();
  const [logInfo, setLogInfo] = useState<IFileLogItem>();

  const showLog = (row: Row<IFileLogItem & DocumentLog>) => {
    const logDetail = {
      taskId: row.original?.dsl?.task_id,
      fileName: row.original.document_name,
      source: row.original.source_from,
      task: row.original?.task_type,
      // 具体任务
      task_detail:
        row.original.process_scene_text ||
        row.original.latest_task_scene_text ||
        '-',
      status: row.original.status as RunningStatus,
      startDate: formatDate(row.original.process_begin_at),
      duration: formatSecondsToHumanReadable(
        row.original.process_duration || 0,
      ),
      details: row.original.progress_msg,
    } as unknown as IFileLogItem;
    console.log('logDetail', logDetail);
    setLogInfo(logDetail);
    setIsModalVisible(true);
  };
  const { dataSourceInfo } = useDataSourceInfo();
  const columns = useMemo(() => {
    return active === LogTabs.FILE_LOGS
      ? getFileLogsTableColumns(
          t,
          showLog,
          kowledgeId || '',
          navigateToDataflowResult,
          dataSourceInfo,
          handleBatchDelete,
          isDeleting,
        )
      : getDatasetLogsTableColumns(t, showLog);
  }, [
    active,
    t,
    showLog,
    kowledgeId,
    navigateToDataflowResult,
    dataSourceInfo,
    handleBatchDelete,
    isDeleting,
  ]);

  const currentPagination = useMemo(
    () => ({
      pageIndex: (pagination.current || 1) - 1,
      pageSize: pagination.pageSize || 10,
    }),
    [pagination],
  );

  const table = useReactTable<IFileLogItem & DocumentLog>({
    data: data || [],
    columns,
    manualPagination: true,
    getCoreRowModel: getCoreRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onRowSelectionChange: setRowSelection,
    state: {
      sorting,
      columnFilters,
      rowSelection,
      pagination: currentPagination,
    },
    pageCount: pagination.total
      ? Math.ceil(pagination.total / pagination.pageSize)
      : 0,
  });

  return (
    <div className="w-full h-[calc(100vh-360px)]">
      {table.getSelectedRowModel().rows.length > 0 && (
        <Card className="mb-4">
          <CardContent className="p-1 pl-5 flex items-center gap-6">
            <section className="text-text-sub-title-invert flex items-center gap-2">
              <span>
                已选: {table.getSelectedRowModel().rows.length} 个文件
              </span>
              <BrushCleaning className="size-3" />
            </section>

            <Separator orientation="vertical" className="h-3" />

            <ul className="flex gap-2">
              <li className="text-state-error">
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 gap-1 px-3 text-state-error hover:text-state-error"
                  disabled={isDeleting}
                  onClick={() => {
                    const ids = table
                      .getSelectedRowModel()
                      .rows.map((row) => row.original.id)
                      .filter(Boolean);

                    handleBatchDelete(ids);
                  }}
                >
                  <Trash2 size={15} />
                  删除
                </Button>
              </li>
            </ul>
          </CardContent>
        </Card>
      )}
      <Table rootClassName="max-h-[calc(100vh-380px)]">
        <TableHeader>
          {table.getHeaderGroups().map((headerGroup) => (
            <TableRow key={headerGroup.id}>
              {headerGroup.headers.map((header) => (
                // <TableHead key={header.id} className={cn('text-center', header.column.columnDef.meta?.headerClassName)}>
                //   {flexRender(
                //     header.column.columnDef.header,
                //     header.getContext(),
                //   )}
                // </TableHead>
                <TableHead
                  key={header.id}
                  className={cn(
                    'text-left',
                    header.column.columnDef.meta?.headerClassName,
                  )}
                >
                  {flexRender(
                    header.column.columnDef.header,
                    header.getContext(),
                  )}
                </TableHead>
              ))}
            </TableRow>
          ))}
        </TableHeader>
        <TableBody className="relative min-w-[1280px] overflow-auto">
          {table.getRowModel().rows?.length ? (
            table.getRowModel().rows.map((row) => (
              <TableRow
                key={row.id}
                data-state={row.getIsSelected() && 'selected'}
                className="group"
              >
                {row.getVisibleCells().map((cell) => (
                  <TableCell
                    key={cell.id}
                    className={cell.column.columnDef.meta?.cellClassName}
                  >
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </TableCell>
                ))}
              </TableRow>
            ))
          ) : (
            <TableRow>
              <TableCell colSpan={columns.length} className="h-24 text-center">
                <Empty
                  type={EmptyType.Data}
                  text={tDatasetOverview('noData')}
                />
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
      <div className="flex items-center justify-end absolute bottom-3 right-12">
        <div className="space-x-2">
          <RAGFlowPagination
            {...{ current: pagination.current, pageSize: pagination.pageSize }}
            total={pagination.total}
            onChange={(page, pageSize) => setPagination({ page, pageSize })}
          />
        </div>
      </div>
      {isModalVisible && (
        <ProcessLogModal
          title={active === LogTabs.FILE_LOGS ? t('fileLogs') : t('datasetLog')}
          visible={isModalVisible}
          onCancel={() => setIsModalVisible(false)}
          logInfo={logInfo}
        />
      )}
    </div>
  );
};

export default FileLogsTable;
