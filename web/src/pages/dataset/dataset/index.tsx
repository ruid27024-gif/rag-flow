import { BulkOperateBar } from '@/components/bulk-operate-bar';
import { FileUploadDialog } from '@/components/file-upload-dialog';
import ListFilterBar from '@/components/list-filter-bar';
import { RenameDialog } from '@/components/rename-dialog';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { PermissionRole } from '@/constants/permission';
import { useRowSelection } from '@/hooks/logic-hooks/use-row-selection';
import { useFetchDocumentList } from '@/hooks/use-document-request';
import { useFetchKnowledgeBaseConfiguration } from '@/hooks/use-knowledge-request';
import { useFetchUserInfo } from '@/hooks/use-user-setting-request';
import { Upload } from 'lucide-react';
import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { DatasetTable } from './dataset-table';
import Generate from './generate-button/generate';
import { useBulkOperateDataset } from './use-bulk-operate-dataset';
import { useCreateEmptyDocument } from './use-create-empty-document';
import { useSelectDatasetFilters } from './use-select-filters';
import { useHandleUploadDocument } from './use-upload-document';

// export default function Dataset() {
//   const { t } = useTranslation();
//   const {
//     documentUploadVisible,
//     hideDocumentUploadModal,
//     showDocumentUploadModal,
//     onDocumentUploadOk,
//     documentUploadLoading,
//   } = useHandleUploadDocument();

//   const {
//     searchString,
//     documents,
//     pagination,
//     handleInputChange,
//     setPagination,
//     filterValue,
//     handleFilterSubmit,
//     loading,
//   } = useFetchDocumentList();

//   const refreshCount = useMemo(() => {
//     return documents.findIndex((doc) => doc.run === '1') + documents.length;
//   }, [documents]);

//   const { data: dataSetData } = useFetchKnowledgeBaseConfiguration({
//     refreshCount,
//   });
//   const { data: userInfo } = useFetchUserInfo();
//   const { filters, onOpenChange } = useSelectDatasetFilters();

//   const {
//     createLoading,
//     onCreateOk,
//     createVisible,
//     hideCreateModal,
//     showCreateModal,
//   } = useCreateEmptyDocument();

//   const { rowSelection, rowSelectionIsEmpty, setRowSelection, selectedCount } =
//     useRowSelection();

//   const { list } = useBulkOperateDataset({
//     documents,
//     rowSelection,
//     setRowSelection,
//   });
//   const readonly =
//     (dataSetData?.permission === PermissionRole.TeamVisible &&
//       dataSetData?.created_by !== userInfo?.id &&
//       !dataSetData?.is_admin) ||
//     (dataSetData?.permission === PermissionRole.Everyone &&
//       dataSetData?.created_by !== userInfo?.id &&
//       !dataSetData?.is_admin);
//   return (
//     <>
//       <div className="absolute top-4 right-5">
//         <Generate disabled={readonly || !(dataSetData.chunk_num > 0)} />
//       </div>
//       <section className="p-5 min-w-[880px]">
//         <ListFilterBar
//           title="Dataset"
//           onSearchChange={handleInputChange}
//           searchString={searchString}
//           value={filterValue}
//           onChange={handleFilterSubmit}
//           onOpenChange={onOpenChange}
//           filters={filters}
//           leftPanel={
//             <div className="items-start">
//               <div className="pb-1">{t('knowledgeDetails.subbarFiles')}</div>
//               <div className="text-text-secondary text-sm">
//                 {t('knowledgeDetails.datasetDescription')}
//               </div>
//             </div>
//           }
//         >
//           {readonly || (
//             <DropdownMenu>
//               <DropdownMenuTrigger asChild>
//                 <Button size={'sm'}>
//                   <Upload />
//                   {t('knowledgeDetails.addFile')}
//                 </Button>
//               </DropdownMenuTrigger>
//               <DropdownMenuContent className="w-56">
//                 <DropdownMenuItem onClick={showDocumentUploadModal}>
//                   {t('fileManager.uploadFile')}
//                 </DropdownMenuItem>
//                 <DropdownMenuSeparator />
//                 <DropdownMenuItem onClick={showCreateModal}>
//                   {t('knowledgeDetails.emptyFiles')}
//                 </DropdownMenuItem>
//               </DropdownMenuContent>
//             </DropdownMenu>
//           )}
//         </ListFilterBar>
//         {rowSelectionIsEmpty || readonly || (
//           <BulkOperateBar list={list} count={selectedCount}></BulkOperateBar>
//         )}
//         <DatasetTable
//           documents={documents}
//           pagination={pagination}
//           setPagination={setPagination}
//           rowSelection={rowSelection}
//           setRowSelection={setRowSelection}
//           loading={loading}
//           readonly={readonly}
//         ></DatasetTable>
//         {documentUploadVisible && (
//           <FileUploadDialog
//             hideModal={hideDocumentUploadModal}
//             onOk={onDocumentUploadOk}
//             loading={documentUploadLoading}
//             // showParseOnCreation
//           ></FileUploadDialog>
//         )}
//         {createVisible && (
//           <RenameDialog
//             hideModal={hideCreateModal}
//             onOk={onCreateOk}
//             loading={createLoading}
//             title={'File Name'}
//           ></RenameDialog>
//         )}
//       </section>
//     </>
//   );
// }

export default function Dataset() {
  const { t } = useTranslation();

  const {
    documentUploadVisible,
    hideDocumentUploadModal,
    showDocumentUploadModal,
    onDocumentUploadOk,
    documentUploadLoading,
  } = useHandleUploadDocument();

  const {
    searchString,
    documents,
    pagination,
    handleInputChange,
    setPagination,
    filterValue,
    handleFilterSubmit,
    loading,
    currentUserRole,
  } = useFetchDocumentList();

  const refreshCount = useMemo(() => {
    return documents.findIndex((doc) => doc.run === '1') + documents.length;
  }, [documents]);

  const { data: dataSetData } = useFetchKnowledgeBaseConfiguration({
    refreshCount,
  });

  const { data: userInfo } = useFetchUserInfo();
  const { filters, onOpenChange } = useSelectDatasetFilters();

  const {
    createLoading,
    onCreateOk,
    createVisible,
    hideCreateModal,
    showCreateModal,
  } = useCreateEmptyDocument();

  const { rowSelection, rowSelectionIsEmpty, setRowSelection, selectedCount } =
    useRowSelection();

  const readonly =
    (dataSetData?.permission === PermissionRole.TeamVisible &&
      dataSetData?.created_by !== userInfo?.id &&
      !dataSetData?.is_admin) ||
    (dataSetData?.permission === PermissionRole.Everyone &&
      dataSetData?.created_by !== userInfo?.id &&
      !dataSetData?.is_admin);

  const isAdmin = currentUserRole?.is_admin === true;
  const permissions = currentUserRole?.operation_permissions;

  const canUpload = !readonly && (isAdmin || permissions?.upload === true);
  const canDownload = !readonly && (isAdmin || permissions?.download === true);
  const canDelete = !readonly && (isAdmin || permissions?.delete === true);
  const canEdit = !readonly && (isAdmin || permissions?.edit === true);

  const { list } = useBulkOperateDataset({
    documents,
    rowSelection,
    setRowSelection,
    canUpload,
    canEdit,
    canDelete,
  });

  return (
    <>
      <div className="absolute top-4 right-5">
        <Generate disabled={readonly || !(dataSetData?.chunk_num > 0)} />
      </div>

      <section className="min-w-[880px] p-5">
        <ListFilterBar
          title="Dataset"
          onSearchChange={handleInputChange}
          searchString={searchString}
          value={filterValue}
          onChange={handleFilterSubmit}
          onOpenChange={onOpenChange}
          filters={filters}
          leftPanel={
            <div className="items-start">
              <div className="pb-1">{t('knowledgeDetails.subbarFiles')}</div>
              <div className="text-text-secondary text-sm">
                {t('knowledgeDetails.datasetDescription')}
              </div>
            </div>
          }
        >
          <DropdownMenu>
            <Tooltip>
              <TooltipTrigger asChild>
                <DropdownMenuTrigger asChild>
                  <span>
                    <Button
                      size="sm"
                      disabled={!canUpload}
                      title={canUpload ? '上传文件' : '当前用户没有上传权限'}
                    >
                      <Upload />
                      {t('knowledgeDetails.addFile')}
                    </Button>
                  </span>
                </DropdownMenuTrigger>
              </TooltipTrigger>
              {!canUpload ? (
                <TooltipContent>
                  <p>
                    {readonly ? '当前知识库不可编辑' : '当前用户没有上传权限'}
                  </p>
                </TooltipContent>
              ) : null}
            </Tooltip>

            <DropdownMenuContent className="w-56">
              <DropdownMenuItem
                disabled={!canUpload}
                onClick={showDocumentUploadModal}
              >
                {t('fileManager.uploadFile')}
              </DropdownMenuItem>

              <DropdownMenuSeparator />

              <DropdownMenuItem disabled={!canEdit} onClick={showCreateModal}>
                {t('knowledgeDetails.emptyFiles')}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </ListFilterBar>

        {!rowSelectionIsEmpty && (
          <BulkOperateBar list={list} count={selectedCount} />
        )}

        <DatasetTable
          documents={documents}
          pagination={pagination}
          setPagination={setPagination}
          rowSelection={rowSelection}
          setRowSelection={setRowSelection}
          loading={loading}
          readonly={readonly}
          currentUserRole={currentUserRole}
        />

        {documentUploadVisible && (
          <FileUploadDialog
            hideModal={hideDocumentUploadModal}
            onOk={onDocumentUploadOk}
            loading={documentUploadLoading}
          />
        )}

        {createVisible && (
          <RenameDialog
            hideModal={hideCreateModal}
            onOk={onCreateOk}
            loading={createLoading}
            title="File Name"
          />
        )}
      </section>
    </>
  );
}
