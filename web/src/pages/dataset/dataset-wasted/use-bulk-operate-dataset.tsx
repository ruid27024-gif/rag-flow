import {
  UseRowSelectionType,
  useSelectedIds,
} from '@/hooks/logic-hooks/use-row-selection';
import {
  DocumentApiAction,
  useRemoveWastedDocument,
  useSetDocumentStatus,
} from '@/hooks/use-document-request';
import { IDocumentInfo } from '@/interfaces/database/document';
import { useQueryClient } from '@tanstack/react-query';
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
  const queryClient = useQueryClient();

  const { selectedIds: selectedRowKeys } = useSelectedIds(
    rowSelection,
    documents,
  );

  const { removeWastedDocument } = useRemoveWastedDocument();
  const { setDocumentStatus } = useSetDocumentStatus();

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

  const handleEnableClick = useCallback(async () => {
    const res = await setDocumentStatus({
      status: true,
      documentId: selectedRowKeys,
    });

    const code = typeof res === 'number' ? res : res?.code;

    if (code !== 0) return;

    setRowSelection({});

    const restoredIdSet = new Set(selectedRowKeys);

    queryClient.setQueriesData<{ docs: IDocumentInfo[]; total: number }>(
      {
        predicate: (query) =>
          query.queryKey.includes(DocumentApiAction.FetchWastedDocumentList),
      },
      (oldData) => {
        if (!oldData) return oldData;

        return {
          ...oldData,
          docs: oldData.docs.filter((doc) => !restoredIdSet.has(doc.id)),
          total: Math.max((oldData.total || 0) - selectedRowKeys.length, 0),
        };
      },
    );

    await queryClient.refetchQueries({
      predicate: (query) =>
        query.queryKey.includes(DocumentApiAction.FetchWastedDocumentList),
      type: 'active',
    });
  }, [selectedRowKeys, setDocumentStatus, setRowSelection, queryClient]);

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
