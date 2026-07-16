import {
  ConfirmDeleteDialog,
  ConfirmDeleteDialogNode,
} from '@/components/confirm-delete-dialog';
import { FileIcon } from '@/components/icon-font';
import NewDocumentLink from '@/components/new-document-link';
import { Button } from '@/components/ui/button';
import { useDownloadFile } from '@/hooks/use-file-request';
import { IFile } from '@/interfaces/database/file-manager';
import { cn } from '@/lib/utils';
import {
  getExtension,
  isSupportedPreviewDocumentType,
} from '@/utils/document-util';
import { CellContext } from '@tanstack/react-table';
import { Tooltip } from 'antd';
import { t } from 'i18next';
import {
  ArrowDownToLine,
  Eye,
  FolderInput,
  FolderPen,
  Link2,
  Trash2,
} from 'lucide-react';
import { useCallback } from 'react';
import {
  UseHandleConnectToKnowledgeReturnType,
  UseRenameCurrentFileReturnType,
} from './hooks';
import { useHandleDeleteFile } from './use-delete-file';
// import { isFolderType } from './util';
import { isAdminownerType, isFolderType, isKnowledgeBaseType } from './util';

// type IProps = Pick<CellContext<IFile, unknown>, 'row'> &
//   Pick<UseHandleConnectToKnowledgeReturnType, 'showConnectToKnowledgeModal'> &
//   Pick<UseRenameCurrentFileReturnType, 'showFileRenameModal'> &
//   UseMoveDocumentShowType;

interface IProps {
  row: CellContext<IFile, unknown>['row'];
  showConnectToKnowledgeModal: UseHandleConnectToKnowledgeReturnType['showConnectToKnowledgeModal'];
  showFileRenameModal: UseRenameCurrentFileReturnType['showFileRenameModal'];
  showMoveFileModal: (ids: string[]) => void;

  // ✅ 加上这个回调函数，用来把当前行的 record 传回父组件
  onMoveClick?: (record: IFile) => void;
}

export function ActionCell({
  row,
  showConnectToKnowledgeModal,
  showFileRenameModal,
  showMoveFileModal,
  onMoveClick, // 2. 解构出 onMoveClick
}: IProps) {
  const record = row.original;
  const documentId = record.id;
  const name: string = row.getValue('name');
  const type = record.type;

  const { downloadFile } = useDownloadFile();
  const isFolder = isFolderType(record.type);
  const extension = getExtension(record.name);
  const isKnowledgeBase =
    (isKnowledgeBaseType(record.source_type) && isFolderType(record.type)) ||
    isAdminownerType(record.source_type);
  // const isKnowledgeBase = isAdminownerType(record.source_type);
  // const isKnowledgeBase = false; // 👈 强制设为 false，绕过原本的判断逻辑

  const handleShowConnectToKnowledgeModal = useCallback(() => {
    showConnectToKnowledgeModal(record);
  }, [record, showConnectToKnowledgeModal]);

  const onDownloadDocument = useCallback(() => {
    downloadFile({
      id: documentId,
      filename: record.name,
    });
  }, [documentId, downloadFile, record.name]);

  const handleShowFileRenameModal = useCallback(() => {
    showFileRenameModal(record);
  }, [record, showFileRenameModal]);

  const handleShowMoveFileModal = useCallback(() => {
    onMoveClick?.(record); // 3. 点击时，先把当前行的完整数据传出去
    showMoveFileModal([record.id]);
  }, [record, showMoveFileModal]);

  const { handleRemoveFile } = useHandleDeleteFile();

  const onRemoveFile = useCallback(() => {
    handleRemoveFile([documentId]);
  }, [handleRemoveFile, documentId]);

  return (
    <section className="flex gap-4 items-center text-text-sub-title-invert">
      {!isKnowledgeBase && (
        <Tooltip
          title="链接知识库"
          placement="top" // 强制显示在按钮上方（可选 top/bottom/left/right 等）
          color="#1677ff" // 自定义背景色（例如 Antd 的主题蓝）
          overlayInnerStyle={{ color: '#fff', fontSize: '13px' }} // 自定义内部文字样式
        >
          <Button
            variant="transparent"
            className="border-none hover:bg-bg-card text-text-primary"
            size={'sm'}
            onClick={handleShowConnectToKnowledgeModal}
          >
            <Link2 />
          </Button>
        </Tooltip>
      )}
      {!isKnowledgeBase && (
        <Tooltip
          title="文件转移"
          placement="top" // 强制显示在按钮上方（可选 top/bottom/left/right 等）
          color="#1677ff" // 自定义背景色（例如 Antd 的主题蓝）
          overlayInnerStyle={{ color: '#fff', fontSize: '13px' }} // 自定义内部文字样式
        >
          <Button
            variant="transparent"
            className="border-none hover:bg-bg-card text-text-primary"
            size={'sm'}
            onClick={handleShowMoveFileModal}
          >
            <FolderInput />
          </Button>
        </Tooltip>
      )}
      {!isKnowledgeBase && (
        <Tooltip
          title="重命名"
          placement="top" // 强制显示在按钮上方（可选 top/bottom/left/right 等）
          color="#1677ff" // 自定义背景色（例如 Antd 的主题蓝）
          overlayInnerStyle={{ color: '#fff', fontSize: '13px' }} // 自定义内部文字样式
        >
          <Button
            variant="transparent"
            className="border-none hover:bg-bg-card text-text-primary"
            size={'sm'}
            onClick={handleShowFileRenameModal}
          >
            <FolderPen />
          </Button>
        </Tooltip>
      )}
      {isFolder || (
        <Button
          variant="transparent"
          className="border-none hover:bg-bg-card text-text-primary"
          size={'sm'}
          onClick={onDownloadDocument}
        >
          <ArrowDownToLine />
        </Button>
      )}

      {isSupportedPreviewDocumentType(extension) && (
        <NewDocumentLink
          documentId={documentId}
          documentName={record.name}
          className="text-text-sub-title-invert"
        >
          <Button
            variant="transparent"
            className="border-none hover:bg-bg-card text-text-primary"
            size={'sm'}
          >
            <Eye />
          </Button>
        </NewDocumentLink>
      )}

      {/* <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="transparent"
        className="border-none" size={'sm'}>
            <EllipsisVertical />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem onClick={handleShowMoveFileModal}>
            {t('common.move')}
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={handleShowFileRenameModal}>
            {t('common.rename')}
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          {isFolder || (
            <DropdownMenuItem onClick={onDownloadDocument}>
              {t('common.download')}
            </DropdownMenuItem>
          )}
        </DropdownMenuContent>
      </DropdownMenu> */}
      {isKnowledgeBase || (
        <ConfirmDeleteDialog
          onOk={onRemoveFile}
          title={t('deleteModal.delFile')}
          content={{
            node: (
              <ConfirmDeleteDialogNode>
                <div className="flex items-center gap-2 text-text-secondary">
                  <span className="size-4">
                    <FileIcon name={name} type={type}></FileIcon>
                  </span>
                  <span
                    className={cn('truncate text-xs', {
                      ['cursor-pointer']: isFolder,
                    })}
                  >
                    {name}
                  </span>
                </div>
              </ConfirmDeleteDialogNode>
            ),
          }}
        >
          <Tooltip
            title="删除"
            placement="top" // 强制显示在按钮上方（可选 top/bottom/left/right 等）
            color="#1677ff" // 自定义背景色（例如 Antd 的主题蓝）
            overlayInnerStyle={{ color: '#fff', fontSize: '13px' }} // 自定义内部文字样式
          >
            <Button
              variant="transparent"
              className="border-none hover:bg-bg-card text-text-primary"
              size={'sm'}
            >
              <Trash2 />
            </Button>
          </Tooltip>
        </ConfirmDeleteDialog>
      )}
    </section>
  );
}
