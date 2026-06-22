import { FileIcon } from '@/components/icon-font';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Progress } from '@/components/ui/progress';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { RunningStatus } from '@/constants/knowledge';
import { useNavigatePage } from '@/hooks/logic-hooks/navigate-hooks';
import { useSetDocumentStatus } from '@/hooks/use-document-request';
import { IDocumentInfo } from '@/interfaces/database/document';
import { cn } from '@/lib/utils';
import { useDataSourceInfo } from '@/pages/user-setting/data-source/contant';
// import { formatDate } from '@/utils/date';
import { ColumnDef } from '@tanstack/table-core';
import { ArrowUpDown, Edit, MonitorUp } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { DatasetActionCell } from './dataset-action-cell';
import { UseChangeDocumentParserShowType } from './use-change-document-parser';
import { UseRenameDocumentShowType } from './use-rename-document';
import { UseSaveMetaShowType } from './use-save-meta';

type UseDatasetTableColumnsType = UseChangeDocumentParserShowType &
  UseRenameDocumentShowType &
  UseSaveMetaShowType & {
    showLog: (record: IDocumentInfo) => void;
    readonly?: boolean;
  };

export function useDatasetTableColumns({
  showChangeParserModal,
  showRenameModal,
  showSetMetaModal,
  showLog,
  readonly = false,
}: UseDatasetTableColumnsType) {
  const toText = (v: unknown) => {
    if (v === null || v === undefined) return '';
    if (typeof v === 'string') return v;
    if (typeof v === 'number' || typeof v === 'boolean') return String(v);
    try {
      return JSON.stringify(v);
    } catch {
      return String(v);
    }
  };
  const { t } = useTranslation('translation', {
    keyPrefix: 'knowledgeDetails',
  });
  const { dataSourceInfo } = useDataSourceInfo();
  const { navigateToChunkParsedResult } = useNavigatePage();
  const { setDocumentStatus } = useSetDocumentStatus();

  const formatDate = (dateStr: string) => {
    if (!dateStr) return '-';
    const date = new Date(dateStr);

    const year = date.getFullYear(); // 获取本地年份
    const month = String(date.getMonth() + 1).padStart(2, '0'); // 月份从0开始
    const day = String(date.getDate()).padStart(2, '0'); // 获取本地日期
    const hours = String(date.getHours()).padStart(2, '0'); // 获取本地小时
    const minutes = String(date.getMinutes()).padStart(2, '0');
    const seconds = String(date.getSeconds()).padStart(2, '0');

    return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
  };

  const columns: ColumnDef<IDocumentInfo>[] = [
    {
      id: 'select',
      header: ({ table }) => (
        <Checkbox
          checked={
            table.getIsAllPageRowsSelected() ||
            (table.getIsSomePageRowsSelected() && 'indeterminate')
          }
          onCheckedChange={(value) => table.toggleAllPageRowsSelected(!!value)}
          aria-label="Select all"
        />
      ),
      cell: ({ row }) => (
        <Checkbox
          checked={row.getIsSelected()}
          onCheckedChange={(value) => row.toggleSelected(!!value)}
          aria-label="Select row"
        />
      ),
      enableSorting: false,
      enableHiding: false,
    },
    {
      accessorKey: 'name',
      header: ({ column }) => {
        return (
          <Button
            variant="transparent"
            className="border-none"
            onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
          >
            {t('name')}
            <ArrowUpDown />
          </Button>
        );
      },
      meta: { cellClassName: 'max-w-[20vw]' },
      cell: ({ row }) => {
        const name = toText(row.getValue('name'));

        return (
          <Tooltip>
            <TooltipTrigger asChild>
              <div
                className="flex gap-2 cursor-pointer"
                onClick={navigateToChunkParsedResult(
                  row.original.id,
                  row.original.kb_id,
                )}
              >
                <FileIcon name={name}></FileIcon>
                <span className={cn('truncate')}>{name}</span>
              </div>
            </TooltipTrigger>
            <TooltipContent>
              <p>{name}</p>
            </TooltipContent>
          </Tooltip>
        );
      },
    },
    {
      accessorKey: 'create_time',
      header: ({ column }) => {
        return (
          <Button
            variant="transparent"
            className="border-none"
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
      id: 'metadata',
      header: '来源信息',
      cell: ({ row }) => {
        const author = toText(row.original.author);
        const schoolRaw = row.original.school;
        let school = '';
        if (typeof schoolRaw === 'string') {
          const trimmed = schoolRaw.trim();
          if (trimmed && trimmed[0] !== '{' && trimmed[0] !== '[') {
            school = schoolRaw;
          }
        }
        const publishTime = toText(row.original.publish_time);
        return (
          <div className="flex flex-col gap-1 text-xs text-text-secondary group relative min-h-[20px]">
            <div className="flex items-center gap-1">
              <span className="font-medium">作者:</span>
              <span className="truncate max-w-[120px]" title={author}>
                {author}
              </span>
            </div>
            <div className="flex items-center gap-1">
              <span className="font-medium">学校:</span>
              <span className="truncate max-w-[120px]" title={school}>
                {school}
              </span>
            </div>
            <div className="flex items-center gap-1">
              <span className="font-medium">发布日期:</span>
              <span className="truncate max-w-[120px]" title={publishTime}>
                {publishTime}
              </span>
            </div>
            {!readonly && (
              <div className="absolute right-0 top-0 hidden group-hover:block">
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-6 w-6"
                  title="手动输入"
                  onClick={() => showSetMetaModal(row.original)}
                >
                  <Edit className="h-4 w-4" />
                </Button>
              </div>
            )}
          </div>
        );
      },
    },
    {
      accessorKey: 'source_from',
      header: t('source'),
      cell: ({ row }) => (
        <div className="text-text-primary">
          {row.original.source_type === 'local' ||
          row.original.source_type === '' ? (
            <div className="bg-accent-primary-5 w-6 h-6 rounded-full flex items-center justify-center">
              <MonitorUp className="text-accent-primary" size={16} />
            </div>
          ) : (
            <div className="w-6 h-6 flex items-center justify-center">
              {dataSourceInfo[
                row.original.source_type as keyof typeof dataSourceInfo
              ]?.icon || null}
            </div>
          )}
        </div>
      ),
    },
    // {
    //   accessorKey: 'status',
    //   header: t('enabled'),
    //   cell: ({ row }) => {
    //     const id = row.original.id;
    //     return (
    //       <Switch
    //         checked={String(row.getValue('status') ?? '') === '1'}
    //         disabled={readonly}
    //         onCheckedChange={(e) => {
    //           setDocumentStatus({ status: e, documentId: id });
    //         }}
    //       />
    //     );
    //   },
    // },
    {
      accessorKey: 'chunk_num',
      header: t('chunkNumber'),
      cell: ({ row }) => (
        <div className="capitalize">{row.getValue('chunk_num')}</div>
      ),
    },
    {
      id: 'parsingStatus',
      header: t('parsingStatus'),
      cell: ({ row }) => {
        const record = row.original;
        const run = record.run;
        const chunkNum = record.chunk_num || 0; // 👈 获取解析出的 chunk 数量
        const processScene = record.process_scene;

        // ==========================================
        // 【核心逻辑】：根据 run 和 chunk_num 联合判断真实状态
        // ==========================================
        let statusText = '';
        let statusColor = '';

        if (processScene === 'author_only') {
          if (run === RunningStatus.DONE) {
            statusText = t(
              'statusAuthorSuccessNoParse',
              '提取成功<br />未解析',
            );
            statusColor = 'text-orange-500';
          } else if (run === RunningStatus.FAIL) {
            statusText = t('statusAuthorFailNoParse', '提取失败<br />未解析');
            statusColor = 'text-yellow-600';
          }
        } else if (processScene === 'author_with_parse') {
          if (run === RunningStatus.DONE) {
            statusText = t('statusAuthorSuccessParseSuccess', '解析成功');
            statusColor = 'text-green-600';
          } else if (run === RunningStatus.FAIL) {
            statusText = t('statusAuthorSuccessParseFail', '解析失败');
            statusColor = 'text-red-600';
          }
        } else if (processScene === 'parse_only') {
          if (run === RunningStatus.DONE) {
            statusText = t('statusParseSuccess', '解析成功');
            statusColor = 'text-green-600';
          } else if (run === RunningStatus.FAIL) {
            statusText = t('statusParseFail', '解析失败');
            statusColor = 'text-red-600';
          }
        }

        if (statusText) {
          const statusStyles = {
            'text-orange-500': {
              wrapper:
                'bg-orange-50 text-orange-700 border-orange-200 shadow-orange-100',
              dot: 'bg-orange-400',
            },
            'text-yellow-600': {
              wrapper:
                'bg-yellow-50 text-yellow-700 border-yellow-200 shadow-yellow-100',
              dot: 'bg-yellow-400',
            },
            'text-green-600': {
              wrapper:
                'bg-emerald-50 text-emerald-700 border-emerald-200 shadow-emerald-100',
              dot: 'bg-emerald-500',
            },
            'text-red-600': {
              wrapper: 'bg-red-50 text-red-700 border-red-200 shadow-red-100',
              dot: 'bg-red-500',
            },
          } as const;

          const currentStyle = statusStyles[
            statusColor as keyof typeof statusStyles
          ] ?? {
            wrapper:
              'bg-slate-50 text-slate-600 border-slate-200 shadow-slate-100',
            dot: 'bg-slate-400',
          };

          return (
            <div
              className={[
                'inline-flex items-center gap-1.5 rounded-xl border px-2.5 py-1',
                'text-xs font-medium leading-tight shadow-sm',
                'transition-colors duration-200',
                currentStyle.wrapper,
              ].join(' ')}
            >
              <span
                className={`h-1.5 w-1.5 shrink-0 rounded-full ${currentStyle.dot}`}
              />
              <span
                className="whitespace-nowrap text-center"
                dangerouslySetInnerHTML={{ __html: statusText }}
              />
            </div>
          );
        }

        const raw = typeof record.progress === 'number' ? record.progress : 0;
        const percent = Math.max(
          0,
          Math.min(100, Number((raw * 100).toFixed(2))),
        );
        const isRunning =
          run === RunningStatus.RUNNING || run === RunningStatus.SCHEDULE;
        const label = t(`runningStatus${run}`);

        if (!isRunning) {
          return <div className="text-xs text-text-secondary">{label}</div>;
        }

        return (
          <div
            className="flex items-center gap-2 cursor-pointer min-w-28"
            onClick={() => showLog(record)}
          >
            <Progress value={percent} className="h-1 flex-1" />
            <span className="text-xs text-text-secondary tabular-nums">
              {percent}%
            </span>
          </div>
        );
      },
    },
    {
      id: 'actions',
      header: t('action'),
      enableHiding: false,
      cell: ({ row }) => {
        const record = row.original;

        return (
          <DatasetActionCell
            record={record}
            showRenameModal={showRenameModal}
            readonly={readonly}
          ></DatasetActionCell>
        );
      },
    },
  ];

  return columns;
}
