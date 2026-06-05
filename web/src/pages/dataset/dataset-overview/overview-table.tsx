import { EmptyType } from '@/components/empty/constant';
import Empty from '@/components/empty/empty';
import FileStatusBadge from '@/components/file-status-badge';
import { FileIcon, IconFontFill } from '@/components/icon-font';
import { RAGFlowAvatar } from '@/components/ragflow-avatar';
import { Button } from '@/components/ui/button';
import { RAGFlowPagination } from '@/components/ui/ragflow-pagination';
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
import { formatSecondsToHumanReadable } from '@/utils/date';
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
import { ArrowUpDown, ClipboardList, Eye, MonitorUp } from 'lucide-react';
import { FC, useMemo, useState } from 'react';
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

export const getFileLogsTableColumns = (
  t: TFunction<'translation', string>,
  showLog: (row: Row<IFileLogItem & DocumentLog>, active: LogTabs) => void,
  kowledgeId: string,
  navigateToDataflowResult: (
    props: NavigateToDataflowResultProps,
  ) => () => void,
  dataSourceInfo: IDataSourceInfoMap,
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
      accessorKey: 'id',
      // header: t('taskId'),
      header: 'ID',
      cell: ({ row }) => (
        <div className="text-text-primary text-center">{row.original.id}</div>
      ),
    },
    {
      accessorKey: 'fileName',
      header: t('fileName'),
      meta: { cellClassName: 'max-w-[20vw]' },
      cell: ({ row }) => (
        <Tooltip>
          <TooltipTrigger asChild>
            <div className="flex gap-2 cursor-pointer">
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
      meta: { cellClassName: 'max-w-[10vw]' },
      cell: ({ row }) => (
        <div className="text-text-primary">
          {row.original.source_from === 'local' ||
          row.original.source_from === '' ? (
            <div className="bg-accent-primary-5 w-6 h-6 rounded-full flex items-center justify-center">
              <MonitorUp className="text-accent-primary" size={16} />
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
      cell: ({ row }) => {
        const title = row.original.pipeline_title;
        const pipelineTitle = title === 'naive' ? 'general' : title;
        return (
          <div className="flex items-center gap-2 text-text-primary">
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
            className="border-none"
            onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
          >
            {t('startDate')}
            <ArrowUpDown />
          </Button>
        );
      },
      cell: ({ row }) => (
        <div className="text-text-primary text-center">
          {formatDate(row.original.process_begin_at)}
          {/* {row.original.process_begin_at} */}
        </div>
      ),
    },
    {
      accessorKey: 'task_type',
      header: t('task'),
      cell: ({ row }) => (
        <div className="text-text-primary text-center">
          {row.original.task_type}
        </div>
      ),
    },
    {
      accessorKey: 'operation_status',
      header: t('status'),
      cell: ({ row }) => (
        <FileStatusBadge
          status={row.original.operation_status as RunningStatus}
          name={
            RunningStatusMap[row.original.operation_status as RunningStatus]
          }
        />
      ),
    },
    {
      accessorKey: 'document_id_count',
      header: '文档解析次数',
      cell: ({ row }) => {
        const count = row.original.document_id_count || 0;

        const colorMap: Record<number, string> = {
          1: 'bg-gradient-to-r from-green-50 to-green-100 text-green-700 ring-green-200',
          2: 'bg-gradient-to-r from-emerald-50 to-emerald-100 text-emerald-700 ring-emerald-200',
          3: 'bg-gradient-to-r from-teal-50 to-teal-100 text-teal-700 ring-teal-200',
          4: 'bg-gradient-to-r from-cyan-50 to-cyan-100 text-cyan-700 ring-cyan-200',
          5: 'bg-gradient-to-r from-sky-50 to-sky-100 text-sky-700 ring-sky-200',
          6: 'bg-gradient-to-r from-blue-50 to-blue-100 text-blue-700 ring-blue-200',
          7: 'bg-gradient-to-r from-indigo-50 to-indigo-100 text-indigo-700 ring-indigo-200',
          8: 'bg-gradient-to-r from-violet-50 to-violet-100 text-violet-700 ring-violet-200',
          9: 'bg-gradient-to-r from-orange-50 to-orange-100 text-orange-700 ring-orange-200',
          10: 'bg-gradient-to-r from-red-50 to-red-100 text-red-700 ring-red-200',
        };

        const normalizedCount = Math.min(Math.max(count, 1), 10);

        const className =
          count <= 0
            ? 'bg-gray-50 text-gray-500 ring-gray-200'
            : colorMap[normalizedCount];

        return (
          <div className="flex items-center">
            <span
              className={`
            inline-flex items-center justify-center
            min-w-[54px] px-2.5 py-1
            text-xs font-semibold tracking-wide
            rounded-full ring-1 ring-inset
            transition-all duration-200
            ${className}
          `}
              title={`该文档共解析 ${count} 次`}
            >
              <svg
                className="mr-1 h-3 w-3 opacity-80"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={2}
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182M21.015 4.356v4.992"
                />
              </svg>
              {count} 次
            </span>
          </div>
        );
      },
    },
    {
      accessorKey: 'is_latest_parse',
      header: '是否最新',
      cell: ({ row }) => {
        const isLatest = row.original.is_latest_parse === 1;

        return (
          <span
            className={`
          inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset
          ${
            isLatest
              ? 'bg-green-50 text-green-700 ring-green-200'
              : 'bg-gray-50 text-gray-500 ring-gray-200'
          }
        `}
          >
            {isLatest ? '最新' : '历史'}
          </span>
        );
      },
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
              showLog(row, LogTabs.FILE_LOGS);
            }}
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
  const { t } = useTranslate('knowledgeDetails');
  const { t: tDatasetOverview } = useTranslate('datasetOverview');
  const [isModalVisible, setIsModalVisible] = useState(false);
  const { navigateToDataflowResult } = useNavigatePage();
  const [logInfo, setLogInfo] = useState<IFileLogItem>();
  const kowledgeId = useParams().id;
  const showLog = (row: Row<IFileLogItem & DocumentLog>) => {
    const logDetail = {
      taskId: row.original?.dsl?.task_id,
      fileName: row.original.document_name,
      source: row.original.source_from,
      task: row.original?.task_type,
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
        )
      : getDatasetLogsTableColumns(t, showLog);
  }, [active, t]);

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
      <Table rootClassName="max-h-[calc(100vh-380px)]">
        <TableHeader>
          {table.getHeaderGroups().map((headerGroup) => (
            <TableRow key={headerGroup.id}>
              {headerGroup.headers.map((header) => (
                <TableHead key={header.id} className="text-center">
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
