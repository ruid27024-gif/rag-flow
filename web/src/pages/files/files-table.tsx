'use client';

import {
  ColumnDef,
  ColumnFiltersState,
  SortingState,
  VisibilityState,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  useReactTable,
} from '@tanstack/react-table';
import { ArrowUpDown } from 'lucide-react';
import * as React from 'react';

import { FileIcon } from '@/components/icon-font';
import { RenameDialog } from '@/components/rename-dialog';
import { TableEmpty, TableSkeleton } from '@/components/table-skeleton';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
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
import { UseRowSelectionType } from '@/hooks/logic-hooks/use-row-selection';
import { useFetchFileList } from '@/hooks/use-file-request';
import { IFile } from '@/interfaces/database/file-manager';
import { cn } from '@/lib/utils';
import { formatFileSize } from '@/utils/common-util';
// import { formatDate } from '@/utils/date';
import { pick } from 'lodash';
import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { ActionCell } from './action-cell';
import { useHandleConnectToKnowledge, useRenameCurrentFile } from './hooks';
import { KnowledgeCell } from './knowledge-cell';
import { LinkToDatasetDialog } from './link-to-dataset-dialog';
import { UseMoveDocumentShowType } from './use-move-file';
import { useNavigateToOtherFolder } from './use-navigate-to-folder';
import { isFolderType } from './util';

// type FilesTableProps = Pick<
//   ReturnType<typeof useFetchFileList>,
//   'files' | 'loading' | 'pagination' | 'setPagination' | 'total'
// > &
//   Pick<UseRowSelectionType, 'rowSelection' | 'setRowSelection'> &
//   UseMoveDocumentShowType;

// type FilesTableProps = Pick<
//   ReturnType<typeof useFetchFileList>,
//   'files' | 'loading' | 'pagination' | 'setPagination' | 'total'
// > &
//   Pick<UseRowSelectionType, 'rowSelection' | 'setRowSelection'> &
//   UseMoveDocumentShowType & // ✅ 在这里加上 onMoveClick 的类型定义
//   { onMoveClick?: (record: IFile) => void };
type FilesTableProps = Pick<
  ReturnType<typeof useFetchFileList>,
  'files' | 'loading' | 'pagination' | 'setPagination' | 'total'
> &
  Pick<UseRowSelectionType, 'rowSelection' | 'setRowSelection'> &
  UseMoveDocumentShowType & {
    // ✅ 单独扩展出拖拽和移动需要的额外回调函数
    onMoveClick?: (record: IFile) => void;
    onDragStart?: (e: React.DragEvent, file: any) => void;
    onDragOver?: (e: React.DragEvent) => void;
    onDrop?: (e: React.DragEvent, file: any) => void;
  };
export const formatDate = (date?: string | number | Date) => {
  if (!date) return '';

  const d = new Date(date);

  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');

  const hour = String(d.getHours()).padStart(2, '0');
  const minute = String(d.getMinutes()).padStart(2, '0');
  const second = String(d.getSeconds()).padStart(2, '0');

  return `${year}-${month}-${day} ${hour}:${minute}:${second}`;
};

export function FilesTable({
  onMoveClick,
  files,
  total,
  pagination,
  setPagination,
  loading,
  rowSelection,
  setRowSelection,
  showMoveFileModal,
  onDragStart, // 2. 解构接收 props
  onDragOver,
  onDrop,
}: FilesTableProps) {
  const [sorting, setSorting] = React.useState<SortingState>([]);
  const [columnFilters, setColumnFilters] = React.useState<ColumnFiltersState>(
    [],
  );
  const [columnVisibility, setColumnVisibility] =
    React.useState<VisibilityState>({});
  const { t } = useTranslation('translation', {
    keyPrefix: 'fileManager',
  });
  const navigateToOtherFolder = useNavigateToOtherFolder();
  const {
    connectToKnowledgeVisible,
    hideConnectToKnowledgeModal,
    showConnectToKnowledgeModal,
    initialConnectedIds,
    onConnectToKnowledgeOk,
    connectToKnowledgeLoading,
  } = useHandleConnectToKnowledge();
  const {
    fileRenameVisible,
    showFileRenameModal,
    hideFileRenameModal,
    onFileRenameOk,
    initialFileName,
    fileRenameLoading,
  } = useRenameCurrentFile();

  const columns: ColumnDef<IFile>[] = [
    {
      id: 'select',
      header: ({ table }) => {
        const hasSelectableRows = table
          .getRowModel()
          .rows.some((row) => row.getCanSelect());

        if (!hasSelectableRows) {
          return null;
        }

        return (
          <Checkbox
            checked={
              table.getIsAllPageRowsSelected() ||
              (table.getIsSomePageRowsSelected() && 'indeterminate')
            }
            onCheckedChange={(value) =>
              table.toggleAllPageRowsSelected(!!value)
            }
            aria-label="Select all"
          />
        );
      },
      cell: ({ row }) => {
        const record = row.original;
        const sourceType = record?.source_type;

        // const shouldHideCheckbox = sourceType
        //   ? isAdminownerType(sourceType)
        //   : false;

        // if (shouldHideCheckbox) {
        //   return null;
        // }
        const shouldHideCheckbox =
          sourceType === 'adminowner' || sourceType === 'knowledgebase';

        if (shouldHideCheckbox) {
          return null;
        }

        return (
          <Checkbox
            checked={row.getIsSelected()}
            onCheckedChange={(value) => row.toggleSelected(!!value)}
            aria-label="Select row"
            disabled={!row.getCanSelect()}
            onClick={(e) => e.stopPropagation()}
          />
        );
      },
      enableSorting: false,
      enableHiding: false,
    },
    {
      accessorKey: 'name',
      header: ({ column }) => {
        return (
          <Button
            variant="ghost"
            onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
          >
            {t('name')}
            <ArrowUpDown />
          </Button>
        );
      },
      meta: { cellClassName: 'max-w-[20vw]' },
      cell: ({ row }) => {
        const name: string = row.getValue('name');
        const type = row.original.type;
        const id = row.original.id;
        const isFolder = isFolderType(type);

        const handleNameClick = () => {
          if (isFolder) {
            navigateToOtherFolder(id);
          }
        };

        // return (
        //   <div
        //     className="flex gap-2 items-center "
        //     draggable // 让这一整块区域都能被拖拽
        //     onDragStart={(e) => {
        //       // 手动触发父组件传下来的拖拽开始事件
        //       onDragStart?.(e, row.original);
        //     }}
        //     // 阻止这个 div 的点击事件冒泡，防止和拖拽冲突
        //     onClick={(e) => e.stopPropagation()}
        //   >
        //     <Tooltip>
        //       <TooltipTrigger asChild>
        //         <div className="flex gap-2">
        //           <span className="size-4">
        //             <FileIcon name={name} type={type}></FileIcon>
        //           </span>
        //           <span
        //             className={cn('truncate', { ['cursor-pointer']: isFolder })}
        //             onClick={handleNameClick}
        //           >
        //             {name}
        //           </span>
        //         </div>
        //       </TooltipTrigger>
        //       <TooltipContent>
        //         {/* <p>{name}</p> */}
        //         <p>{isFolder ? `点击进入文件夹：${name}` : name}</p>
        //       </TooltipContent>
        //     </Tooltip>
        //   </div>
        // );

        return (
          <div
            className="flex items-center gap-2 min-w-0 max-w-[20vw]"
            draggable
            onDragStart={(e) => {
              onDragStart?.(e, row.original);
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <Tooltip>
              <TooltipTrigger asChild>
                <div className="flex items-center gap-2 min-w-0 max-w-full">
                  <span className="size-4 shrink-0">
                    <FileIcon name={name} type={type}></FileIcon>
                  </span>

                  <span
                    className={cn('min-w-0 flex-1 truncate', {
                      ['cursor-pointer']: isFolder,
                    })}
                    onClick={handleNameClick}
                    title={name}
                  >
                    {name}
                  </span>
                </div>
              </TooltipTrigger>

              <TooltipContent>
                <p>{isFolder ? `点击进入文件夹：${name}` : name}</p>
              </TooltipContent>
            </Tooltip>
          </div>
        );
      },
    },
    {
      accessorKey: 'create_time',
      header: ({ column }) => {
        return (
          <Button
            variant="ghost"
            onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
          >
            {t('uploadDate')}
            <ArrowUpDown />
          </Button>
        );
      },
      cell: ({ row }) => (
        <div className="lowercase">
          {formatDate(row.getValue('create_time'))}
        </div>
      ),
    },
    {
      accessorKey: 'size',
      header: ({ column }) => {
        return (
          <Button
            variant="ghost"
            onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
          >
            {t('size')}
            <ArrowUpDown />
          </Button>
        );
      },
      cell: ({ row }) => (
        <div className="capitalize">{formatFileSize(row.getValue('size'))}</div>
      ),
    },
    {
      accessorKey: 'kbs_info',
      header: t('knowledgeBase'),
      cell: ({ row }) => {
        const value: IFile['kbs_info'] = row.getValue('kbs_info');
        return <KnowledgeCell value={value}></KnowledgeCell>;
      },
    },
    {
      id: 'actions',
      header: t('action'),
      enableHiding: false,
      enablePinning: true,
      cell: ({ row }) => {
        return (
          <div onClick={(e) => e.stopPropagation()}>
            {' '}
            {/* ✅ 阻止点击操作按钮时触发整行点击 */}
            <ActionCell
              row={row}
              showConnectToKnowledgeModal={showConnectToKnowledgeModal}
              showFileRenameModal={showFileRenameModal}
              showMoveFileModal={showMoveFileModal}
              onMoveClick={onMoveClick} // 2. 把回调函数传给 ActionCell
            ></ActionCell>
          </div>
        );
      },
    },
  ];

  const currentPagination = useMemo(() => {
    return {
      pageIndex: (pagination.current || 1) - 1,
      pageSize: pagination.pageSize || 10,
    };
  }, [pagination]);

  const table = useReactTable({
    data: files || [],
    columns,
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    onColumnVisibilityChange: setColumnVisibility,
    onRowSelectionChange: setRowSelection,

    manualPagination: true,

    enableRowSelection: (row) => {
      const sourceType = row.original?.source_type;

      if (!sourceType) {
        return true;
      }

      return sourceType !== 'adminowner' && sourceType !== 'knowledgebase';
    },

    state: {
      sorting,
      columnFilters,
      columnVisibility,
      rowSelection,
      pagination: currentPagination,
    },
    rowCount: total ?? 0,
    debugTable: true,
  });

  return (
    <>
      <div className="w-full">
        <Table rootClassName="max-h-[calc(100vh-242px)] overflow-auto">
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => {
                  return (
                    <TableHead key={header.id}>
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
          <TableBody className="max-h-96 overflow-y-auto">
            {loading ? (
              <TableSkeleton columnsLength={columns.length}></TableSkeleton>
            ) : table.getRowModel().rows?.length ? (
              table.getRowModel().rows.map((row) => (
                <Tooltip key={row.id} delayDuration={200}>
                  <TooltipTrigger asChild>
                    <TableRow
                      data-state={row.getIsSelected() && 'selected'}
                      className="group"
                      draggable
                      onDragStart={(e) => onDragStart?.(e, row.original)}
                      onDragOver={
                        row.original.type === 'folder' ? onDragOver : undefined
                      }
                      onDrop={
                        row.original.type === 'folder'
                          ? (e) => onDrop?.(e, row.original)
                          : undefined
                      }
                      style={{
                        cursor:
                          row.original.type === 'folder' ? 'copy' : 'default',
                      }}
                      onClick={() => {
                        if (isFolderType(row.original.type)) {
                          navigateToOtherFolder(row.original.id);
                        }
                      }}
                    >
                      {row.getVisibleCells().map((cell) => (
                        <TableCell key={cell.id}>
                          {flexRender(
                            cell.column.columnDef.cell,
                            cell.getContext(),
                          )}
                        </TableCell>
                      ))}
                    </TableRow>
                  </TooltipTrigger>
                  {/* 整行悬浮时的统一提示 */}
                  {/* <TooltipContent side="top" align="end">
                  <p>点击查阅、长按移动</p>
                </TooltipContent> */}
                </Tooltip>
              ))
            ) : (
              <TableEmpty columnsLength={columns.length}></TableEmpty>
            )}
          </TableBody>
        </Table>
      </div>
      <div className="flex items-center justify-end py-4">
        <div className="space-x-2">
          <RAGFlowPagination
            {...pick(pagination, 'current', 'pageSize')}
            total={total}
            onChange={(page, pageSize) => {
              setPagination({ page, pageSize });
            }}
          ></RAGFlowPagination>
        </div>
      </div>
      {connectToKnowledgeVisible && (
        <LinkToDatasetDialog
          hideModal={hideConnectToKnowledgeModal}
          initialConnectedIds={initialConnectedIds}
          onConnectToKnowledgeOk={onConnectToKnowledgeOk}
          loading={connectToKnowledgeLoading}
        ></LinkToDatasetDialog>
      )}
      {fileRenameVisible && (
        <RenameDialog
          hideModal={hideFileRenameModal}
          onOk={onFileRenameOk}
          initialName={initialFileName}
          loading={fileRenameLoading}
        ></RenameDialog>
      )}
    </>
  );
}
