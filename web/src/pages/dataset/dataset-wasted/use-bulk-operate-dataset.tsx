import {
  UseRowSelectionType,
  useSelectedIds,
} from '@/hooks/logic-hooks/use-row-selection';
import {
  useRemoveWastedDocument,
  useSetDocumentStatus,
} from '@/hooks/use-document-request';
import { IDocumentInfo } from '@/interfaces/database/document';
import { CircleCheck, Trash2 } from 'lucide-react';
import { useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { RunningStatus } from './constant';

export function useBulkOperateWastedDataset({
  rowSelection,
  setRowSelection,
  documents,
}: Pick<UseRowSelectionType, 'rowSelection' | 'setRowSelection'> & {
  documents: IDocumentInfo[];
}) {
  const { t } = useTranslation();

  const { selectedIds: selectedRowKeys } = useSelectedIds(
    rowSelection,
    documents,
  );

  const { removeWastedDocument } = useRemoveWastedDocument();

  const handleDelete = useCallback(() => {
    const deletedKeys = selectedRowKeys.filter(
      (x) =>
        !documents
          .filter((y) => y.run === RunningStatus.RUNNING)
          .some((y) => y.id === x),
    );

    if (deletedKeys.length === 0) {
      toast.error(t('theDocumentBeingParsedCannotBeDeleted'));
      return;
    }

    return removeWastedDocument(deletedKeys);
  }, [selectedRowKeys, removeWastedDocument, documents, t]);

  const { setDocumentStatus } = useSetDocumentStatus();

  const onChangeStatus = useCallback(
    (enabled: boolean) => {
      setDocumentStatus({ status: enabled, documentId: selectedRowKeys });
    },
    [selectedRowKeys, setDocumentStatus],
  );
  const handleEnableClick = useCallback(() => {
    onChangeStatus(true);
  }, [onChangeStatus]);

  const list = [
    {
      id: 'enabled',
      label: '恢复',
      icon: <CircleCheck />,
      onClick: handleEnableClick,
    },
    {
      id: 'delete',
      label: '彻底删除',
      icon: <Trash2 />,
      onClick: async () => {
        const code = await handleDelete();
        if (code === 0) {
          setRowSelection({});
        }
      },
    },
  ];

  return { list };
}
