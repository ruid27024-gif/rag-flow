import {
  UseRowSelectionType,
  useSelectedIds,
} from '@/hooks/logic-hooks/use-row-selection';
import {
  useRemoveDocument,
  useRunDocument,
  useSetDocumentStatus,
} from '@/hooks/use-document-request';
import { IDocumentInfo } from '@/interfaces/database/document';
import { Ban, CircleCheck, CircleX, Play, Trash2 } from 'lucide-react';
import { useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { DocumentType, RunningStatus } from './constant';

// export function useBulkOperateDataset({
//   rowSelection,
//   setRowSelection,
//   documents,
// }: Pick<UseRowSelectionType, 'rowSelection' | 'setRowSelection'> & {
//   documents: IDocumentInfo[];
// }) {
//   const { t } = useTranslation();
//   const { selectedIds: selectedRowKeys } = useSelectedIds(
//     rowSelection,
//     documents,
//   );

//   const { runDocumentByIds } = useRunDocument();
//   const { setDocumentStatus } = useSetDocumentStatus();
//   const { removeDocument } = useRemoveDocument();

//   const runDocument = useCallback(
//     (run: number) => {
//       const nonVirtualKeys = selectedRowKeys.filter(
//         (x) =>
//           !documents.some((y) => x === y.id && y.type === DocumentType.Virtual),
//       );

//       if (nonVirtualKeys.length === 0) {
//         toast.error(t('Please select a non-empty file list'));
//         return;
//       }
//       runDocumentByIds({
//         documentIds: nonVirtualKeys,
//         run,
//         shouldDelete: false,
//       });
//     },
//     [documents, runDocumentByIds, selectedRowKeys, t],
//   );

//   const handleRunClick = useCallback(() => {
//     runDocument(1);
//   }, [runDocument]);

//   const handleCancelClick = useCallback(() => {
//     runDocument(2);
//   }, [runDocument]);

//   const onChangeStatus = useCallback(
//     (enabled: boolean) => {
//       setDocumentStatus({ status: enabled, documentId: selectedRowKeys });
//     },
//     [selectedRowKeys, setDocumentStatus],
//   );

//   const handleEnableClick = useCallback(() => {
//     onChangeStatus(true);
//   }, [onChangeStatus]);

//   const handleDisableClick = useCallback(() => {
//     onChangeStatus(false);
//   }, [onChangeStatus]);

//   const handleDelete = useCallback(() => {
//     const deletedKeys = selectedRowKeys.filter(
//       (x) =>
//         !documents
//           .filter((y) => y.run === RunningStatus.RUNNING)
//           .some((y) => y.id === x),
//     );
//     if (deletedKeys.length === 0) {
//       toast.error(t('theDocumentBeingParsedCannotBeDeleted'));
//       return;
//     }

//     return removeDocument(deletedKeys);
//   }, [selectedRowKeys, removeDocument, documents, t]);

//   const list = [
//     {
//       id: 'enabled',
//       label: t('knowledgeDetails.enabled'),
//       icon: <CircleCheck />,
//       onClick: handleEnableClick,
//     },
//     {
//       id: 'disabled',
//       label: t('knowledgeDetails.disabled'),
//       icon: <Ban />,
//       onClick: handleDisableClick,
//     },
//     {
//       id: 'run',
//       label: t('knowledgeDetails.run'),
//       icon: <Play />,
//       onClick: handleRunClick,
//     },
//     {
//       id: 'cancel',
//       label: t('knowledgeDetails.cancel'),
//       icon: <CircleX />,
//       onClick: handleCancelClick,
//     },
//     {
//       id: 'delete',
//       label: t('common.delete'),
//       icon: <Trash2 />,
//       onClick: async () => {
//         const code = await handleDelete();
//         if (code === 0) {
//           setRowSelection({});
//         }
//       },
//     },
//   ];

//   return { list };
// }

type UseBulkOperateDatasetProps = Pick<
  UseRowSelectionType,
  'rowSelection' | 'setRowSelection'
> & {
  documents: IDocumentInfo[];
  canUpload: boolean;
  canEdit: boolean;
  canDelete: boolean;
};

export function useBulkOperateDataset({
  rowSelection,
  setRowSelection,
  documents,
  canUpload,
  canEdit,
  canDelete,
}: UseBulkOperateDatasetProps) {
  const { t } = useTranslation();

  const { selectedIds: selectedRowKeys } = useSelectedIds(
    rowSelection,
    documents,
  );

  const { runDocumentByIds } = useRunDocument();
  const { setDocumentStatus } = useSetDocumentStatus();
  const { removeDocument } = useRemoveDocument();

  const runDocument = useCallback(
    (run: number) => {
      if (!canUpload) {
        toast.error('当前用户没有上传权限');
        return;
      }

      const nonVirtualKeys = selectedRowKeys.filter(
        (documentId) =>
          !documents.some(
            (document) =>
              document.id === documentId &&
              document.type === DocumentType.Virtual,
          ),
      );

      if (nonVirtualKeys.length === 0) {
        toast.error(t('Please select a non-empty file list'));
        return;
      }

      runDocumentByIds({
        documentIds: nonVirtualKeys,
        run,
        shouldDelete: false,
      });
    },
    [canUpload, documents, runDocumentByIds, selectedRowKeys, t],
  );

  const handleRunClick = useCallback(() => {
    runDocument(1);
  }, [runDocument]);

  const handleCancelClick = useCallback(() => {
    runDocument(2);
  }, [runDocument]);

  const onChangeStatus = useCallback(
    (enabled: boolean) => {
      if (!canEdit) {
        toast.error('当前用户没有编辑权限');
        return;
      }

      setDocumentStatus({
        status: enabled,
        documentId: selectedRowKeys,
      });
    },
    [canEdit, selectedRowKeys, setDocumentStatus],
  );

  const handleEnableClick = useCallback(() => {
    onChangeStatus(true);
  }, [onChangeStatus]);

  const handleDisableClick = useCallback(() => {
    onChangeStatus(false);
  }, [onChangeStatus]);

  const handleDelete = useCallback(() => {
    if (!canDelete) {
      toast.error('当前用户没有删除权限');
      return;
    }

    const deletedKeys = selectedRowKeys.filter(
      (documentId) =>
        !documents.some(
          (document) =>
            document.id === documentId &&
            document.run === RunningStatus.RUNNING,
        ),
    );

    if (deletedKeys.length === 0) {
      toast.error(t('theDocumentBeingParsedCannotBeDeleted'));
      return;
    }

    return removeDocument(deletedKeys);
  }, [canDelete, documents, removeDocument, selectedRowKeys, t]);

  const list = [
    {
      id: 'enabled',
      label: t('knowledgeDetails.enabled'),
      icon: <CircleCheck />,
      onClick: handleEnableClick,
      disabled: !canEdit,
      disabledTitle: '当前用户没有编辑权限',
    },
    {
      id: 'disabled',
      label: t('knowledgeDetails.disabled'),
      icon: <Ban />,
      onClick: handleDisableClick,
      disabled: !canEdit,
      disabledTitle: '当前用户没有编辑权限',
    },
    {
      id: 'run',
      label: t('knowledgeDetails.run'),
      icon: <Play />,
      onClick: handleRunClick,
      disabled: !canUpload,
      disabledTitle: '当前用户没有上传权限',
    },
    {
      id: 'cancel',
      label: t('knowledgeDetails.cancel'),
      icon: <CircleX />,
      onClick: handleCancelClick,
      disabled: !canUpload,
      disabledTitle: '当前用户没有上传权限',
    },
    {
      id: 'delete',
      label: t('common.delete'),
      icon: <Trash2 />,
      onClick: async () => {
        const code = await handleDelete();

        if (code === 0) {
          setRowSelection({});
        }
      },
      disabled: !canDelete,
      disabledTitle: '当前用户没有删除权限',
    },
  ];

  return { list };
}
