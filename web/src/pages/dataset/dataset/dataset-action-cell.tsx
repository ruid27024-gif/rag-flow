import { ConfirmDeleteDialog } from '@/components/confirm-delete-dialog';
import { Button } from '@/components/ui/button';
import {
  HoverCard,
  HoverCardContent,
  HoverCardTrigger,
} from '@/components/ui/hover-card';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { DocumentType } from '@/constants/knowledge';
import {
  useRemoveDocument,
  useRunDocument,
} from '@/hooks/use-document-request';
import { IDocumentInfo } from '@/interfaces/database/document';
import { getAuthorization } from '@/utils/authorization-util';
import { formatFileSize } from '@/utils/common-util';
// import { formatDate } from '@/utils/date';
import { downloadDocument } from '@/utils/file-util';
import { Download, Eye, PenLine, Play, Trash2 } from 'lucide-react';
import { useCallback, useState } from 'react';
import { toast } from 'sonner';
import { UseRenameDocumentShowType } from './use-rename-document';
import { isParserRunning } from './utils';

const Fields = ['name', 'size', 'type', 'create_time', 'update_time'];
const FieldNameMap: Record<string, string> = {
  name: '名称',
  size: '大小',
  type: '类型',
  create_time: '创建时间',
  update_time: '更新时间',
};

const formatDate = (dateStr: string | number | Date) => {
  if (!dateStr) return '-';

  const date = new Date(dateStr);

  if (Number.isNaN(date.getTime())) {
    return String(dateStr);
  }

  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');

  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');
  const seconds = String(date.getSeconds()).padStart(2, '0');

  return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
};

const FunctionMap = {
  size: formatFileSize,
  create_time: formatDate,
  update_time: formatDate,
};

export function DatasetActionCell({
  record,
  showRenameModal,
  readonly = false,
}: { record: IDocumentInfo; readonly?: boolean } & UseRenameDocumentShowType) {
  const { id, run, type } = record;
  const [logOpen, setLogOpen] = useState(false);
  const [logs, setLogs] = useState<any[]>([]);
  const [logLoading, setLogLoading] = useState(false);
  const isRunning = isParserRunning(run);
  const isVirtualDocument = type === DocumentType.Virtual;

  const { removeDocument } = useRemoveDocument();
  const { runDocumentByIds } = useRunDocument();
  const handleParse = useCallback(() => {
    runDocumentByIds({
      documentIds: [id],
      run: 1,
      shouldDelete: false,
    });
  }, [id, runDocumentByIds]);

  const handleGetDocumentLogs = useCallback(async () => {
    try {
      setLogOpen(true);
      setLogLoading(true);
      setLogs([]);

      const response = await fetch(
        `/v1/kb/pipeline_log_list?document_id=${id}`,
        {
          method: 'GET',
          headers: {
            Authorization: getAuthorization() || '',
            'Content-Type': 'application/json',
          },
        },
      );

      const result = await response.json();

      if (result.code !== 0) {
        toast.error(result.message || '获取日志失败');
        return;
      }

      setLogs(Array.isArray(result.data) ? result.data : []);
    } catch {
      toast.error('获取日志失败');
    } finally {
      setLogLoading(false);
    }
  }, [id]);

  const onDownloadDocument = useCallback(() => {
    downloadDocument({
      id,
      filename: record.name,
    });
  }, [id, record.name]);

  const handleRemove = useCallback(() => {
    removeDocument(id);
  }, [id, removeDocument]);

  const handleRename = useCallback(() => {
    showRenameModal(record);
  }, [record, showRenameModal]);

  // return (
  //   <section className="flex gap-4 items-center text-text-sub-title-invert opacity-0 group-hover:opacity-100 transition-opacity">
  //     <Button
  //       variant="transparent"
  //       className="border-none hover:bg-bg-card text-text-primary"
  //       size={'sm'}
  //       disabled={isRunning || readonly}
  //       onClick={handleRename}
  //     >
  //       <PenLine />
  //     </Button>
  //     <HoverCard>
  //       <HoverCardTrigger>
  //         <Button
  //           variant="transparent"
  //           className="border-none hover:bg-bg-card text-text-primary"
  //           disabled={isRunning}
  //           size={'sm'}
  //         >
  //           <Eye />
  //         </Button>
  //       </HoverCardTrigger>
  //       <HoverCardContent className="w-[40vw] max-h-[40vh] overflow-auto">
  //         <ul className="space-y-2">
  //           {Object.entries(record)
  //             .filter(([key]) => Fields.some((x) => x === key))

  //             .map(([key, value], idx) => {
  //               return (
  //                 <li key={idx} className="flex gap-2">
  //                   {key}:
  //                   <div>
  //                     {key in FunctionMap
  //                       ? FunctionMap[key as keyof typeof FunctionMap](value)
  //                       : value}
  //                   </div>
  //                 </li>
  //               );
  //             })}
  //         </ul>
  //       </HoverCardContent>
  //     </HoverCard>

  //     {isVirtualDocument || (
  //       <Button
  //         variant="transparent"
  //         className="border-none hover:bg-bg-card text-text-primary"
  //         onClick={handleParse}
  //         disabled={isRunning || readonly}
  //         size={'sm'}
  //       >
  //         <Play />
  //       </Button>
  //     )}

  //     {isVirtualDocument || (
  //       <Button
  //         variant="transparent"
  //         className="border-none hover:bg-bg-card text-text-primary"
  //         onClick={onDownloadDocument}
  //         disabled={isRunning || readonly}
  //         size={'sm'}
  //       >
  //         <Download />
  //       </Button>
  //     )}
  //     <ConfirmDeleteDialog onOk={handleRemove} hidden={readonly}>
  //       <Button
  //         variant="transparent"
  //         className="border-none hover:bg-bg-card text-text-primary"
  //         size={'sm'}
  //         disabled={isRunning || readonly}
  //       >
  //         <Trash2 />
  //       </Button>
  //     </ConfirmDeleteDialog>
  //   </section>
  // );
  return (
    <>
      <section className="flex gap-4 items-center text-text-sub-title-invert opacity-0 group-hover:opacity-100 transition-opacity">
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="transparent"
              className="border-none hover:bg-bg-card text-text-primary"
              size={'sm'}
              disabled={isRunning || readonly}
              onClick={handleRename}
            >
              <PenLine />
            </Button>
          </TooltipTrigger>
          <TooltipContent>
            <p>重命名</p>
          </TooltipContent>
        </Tooltip>

        <HoverCard>
          <Tooltip>
            <TooltipTrigger asChild>
              <HoverCardTrigger asChild>
                <Button
                  variant="transparent"
                  className="border-none hover:bg-bg-card text-text-primary"
                  disabled={isRunning}
                  size={'sm'}
                >
                  <Eye />
                </Button>
              </HoverCardTrigger>
            </TooltipTrigger>
            <TooltipContent>
              <p>查看详情</p>
            </TooltipContent>
          </Tooltip>

          <HoverCardContent className="w-[40vw] max-h-[40vh] overflow-auto">
            <ul className="space-y-2">
              {Object.entries(record)
                .filter(([key]) => Fields.some((x) => x === key))
                .map(([key, value], idx) => {
                  return (
                    <li key={idx} className="flex gap-2">
                      {/* {key}: */}
                      {FieldNameMap[key] || key}:
                      <div>
                        {key in FunctionMap
                          ? FunctionMap[key as keyof typeof FunctionMap](value)
                          : value}
                      </div>
                    </li>
                  );
                })}
            </ul>
          </HoverCardContent>
        </HoverCard>

        {isVirtualDocument || (
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="transparent"
                className="border-none hover:bg-bg-card text-text-primary"
                onClick={handleParse}
                disabled={isRunning || readonly}
                size={'sm'}
              >
                <Play />
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              <p>解析</p>
            </TooltipContent>
          </Tooltip>
        )}
        {/* 
    {isVirtualDocument || (
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant="transparent"
            className="border-none hover:bg-bg-card text-text-primary"
            onClick={handleGetDocumentLogs}
            disabled={readonly}
            size={'sm'}
          >
            <Logs />
          </Button>
        </TooltipTrigger>
        <TooltipContent>
          <p>日志</p>
        </TooltipContent>
      </Tooltip>
    )} */}

        {isVirtualDocument || (
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="transparent"
                className="border-none hover:bg-bg-card text-text-primary"
                onClick={onDownloadDocument}
                disabled={isRunning || readonly}
                size={'sm'}
              >
                <Download />
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              <p>下载</p>
            </TooltipContent>
          </Tooltip>
        )}

        <Tooltip>
          <TooltipTrigger asChild>
            <span>
              <ConfirmDeleteDialog onOk={handleRemove} hidden={readonly}>
                <Button
                  variant="transparent"
                  className="border-none hover:bg-bg-card text-text-primary"
                  size="sm"
                  disabled={isRunning || readonly}
                >
                  <Trash2 />
                </Button>
              </ConfirmDeleteDialog>
            </span>
          </TooltipTrigger>

          <TooltipContent>
            <p>删除</p>
          </TooltipContent>
        </Tooltip>
      </section>
      {/* <Dialog open={logOpen} onOpenChange={setLogOpen}>
      <DialogContent>
        {logLoading ? (
          <div>加载中...</div>
        ) : logs.length === 0 ? (
          <div>暂无日志</div>
        ) : (
          <pre>{JSON.stringify(logs, null, 2)}</pre>
        )}
      </DialogContent>
    </Dialog> */}
    </>
  );
}
