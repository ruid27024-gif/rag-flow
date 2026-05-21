import { useSetModalState } from '@/hooks/common-hooks';
import { UseRowSelectionType } from '@/hooks/logic-hooks/use-row-selection';
import { useMoveFile } from '@/hooks/use-file-request';
import { useCallback, useRef, useState } from 'react';

export const useHandleMoveFile = ({
  clearRowSelection,
}: Pick<UseRowSelectionType, 'clearRowSelection'>) => {
  const {
    visible: moveFileVisible,
    hideModal: hideMoveFileModal,
    showModal: showMoveFileModal,
  } = useSetModalState();
  const { moveFile, loading } = useMoveFile();
  const [sourceFileIds, setSourceFileIds] = useState<string[]>([]);
  const isBulkRef = useRef(false);

  const onMoveFileOk = useCallback(
    async (targetFolderId: string) => {
      const ret = await moveFile({
        src_file_ids: sourceFileIds,
        dest_file_id: targetFolderId,
      });
      console.log('准备发送移动请求:', {
        src_file_ids: sourceFileIds,
        dest_file_id: targetFolderId,
      });

      if (ret === 0) {
        if (isBulkRef.current) {
          clearRowSelection();
        }
        hideMoveFileModal();
      }
      return ret;
    },
    [moveFile, sourceFileIds, hideMoveFileModal, clearRowSelection],
  );

  // 修改后 ✅
  const onMoveFileOk2 = useCallback(
    async (targetFolderId: string, draggedFileId?: string) => {
      // 增加可选参数
      // 优先使用拖拽传来的 ID，如果没有则使用批量选中的 IDs
      const idsToMove = draggedFileId ? [draggedFileId] : sourceFileIds;

      if (idsToMove.length === 0) {
        console.warn('没有文件需要移动');
        return -1;
      }

      const ret = await moveFile({
        src_file_ids: idsToMove, // 使用计算后的 ids
        dest_file_id: targetFolderId,
      });

      console.log('准备发送移动请求:', {
        src_file_ids: idsToMove,
        dest_file_id: targetFolderId,
      });

      if (ret === 0) {
        if (isBulkRef.current && !draggedFileId) {
          // 只有非拖拽模式才清空选中
          clearRowSelection();
        }
        hideMoveFileModal();
      }
      return ret;
    },
    [moveFile, sourceFileIds, hideMoveFileModal, clearRowSelection], // 依赖项不变
  );

  const handleShowMoveFileModal = useCallback(
    (ids: string[], isBulk = false) => {
      isBulkRef.current = isBulk;
      setSourceFileIds(ids);
      showMoveFileModal();
    },
    [showMoveFileModal],
  );

  return {
    initialValue: '',
    moveFileLoading: loading,
    onMoveFileOk,
    onMoveFileOk2,
    moveFileVisible,
    hideMoveFileModal,
    showMoveFileModal: handleShowMoveFileModal,
    sourceFileIds,
  };
};

export type UseMoveDocumentReturnType = ReturnType<typeof useHandleMoveFile>;

export type UseMoveDocumentShowType = Pick<
  ReturnType<typeof useHandleMoveFile>,
  'showMoveFileModal'
>;
