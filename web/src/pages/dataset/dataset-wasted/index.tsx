import { BulkOperateBar } from '@/components/bulk-operate-bar';
import { FileUploadDialog } from '@/components/file-upload-dialog';
import ListFilterBar from '@/components/list-filter-bar';
import { RenameDialog } from '@/components/rename-dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu';
import { PermissionRole } from '@/constants/permission';
import { useRowSelection } from '@/hooks/logic-hooks/use-row-selection';
import { useFetchWastedDocumentList } from '@/hooks/use-document-request';
import { useFetchKnowledgeBaseConfiguration } from '@/hooks/use-knowledge-request';
import { useFetchUserInfo } from '@/hooks/use-user-setting-request';
import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { DatasetTable } from './dataset-table';
import Generate from './generate-button/generate';
import { useBulkOperateWastedDataset } from './use-bulk-operate-dataset';
import { useCreateEmptyDocument } from './use-create-empty-document';
import { useSelectWastedDatasetFilters } from './use-select-filters';
import { useHandleUploadDocument } from './use-upload-document';

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
  } = useFetchWastedDocumentList();

  const refreshCount = useMemo(() => {
    return documents.findIndex((doc) => doc.run === '1') + documents.length;
  }, [documents]);

  const { data: dataSetData } = useFetchKnowledgeBaseConfiguration({
    refreshCount,
  });
  const { data: userInfo } = useFetchUserInfo();
  // const { filters, onOpenChange } = useSelectDatasetFilters();
  const { filters, onOpenChange } = useSelectWastedDatasetFilters();

  const {
    createLoading,
    onCreateOk,
    createVisible,
    hideCreateModal,
    showCreateModal,
  } = useCreateEmptyDocument();

  const { rowSelection, rowSelectionIsEmpty, setRowSelection, selectedCount } =
    useRowSelection();

  const { list } = useBulkOperateWastedDataset({
    documents,
    rowSelection,
    setRowSelection,
  });
  const readonly =
    (dataSetData?.permission === PermissionRole.TeamVisible &&
      dataSetData?.created_by !== userInfo?.id &&
      !dataSetData?.is_admin) ||
    (dataSetData?.permission === PermissionRole.Everyone &&
      dataSetData?.created_by !== userInfo?.id &&
      !dataSetData?.is_admin);
  return (
    <>
      <div className="absolute top-4 right-5">
        <Generate disabled={readonly || !(dataSetData.chunk_num > 0)} />
      </div>
      <section className="p-5 min-w-[880px]">
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
              <div className="pb-1">回收站</div>
              <div className="text-text-secondary text-sm">
                默认30天后自动删除。
              </div>
            </div>
          }
        >
          {readonly || (
            <DropdownMenu>
              {/* <DropdownMenuTrigger asChild>
                <Button size={'sm'}>
                  <Upload />
                  {t('knowledgeDetails.addFile')}
                </Button>
              </DropdownMenuTrigger> */}
              <DropdownMenuContent className="w-56">
                <DropdownMenuItem onClick={showDocumentUploadModal}>
                  {t('fileManager.uploadFile')}
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={showCreateModal}>
                  {t('knowledgeDetails.emptyFiles')}
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          )}
        </ListFilterBar>
        {rowSelectionIsEmpty || readonly || (
          <BulkOperateBar list={list} count={selectedCount}></BulkOperateBar>
        )}
        <DatasetTable
          documents={documents}
          pagination={pagination}
          setPagination={setPagination}
          rowSelection={rowSelection}
          setRowSelection={setRowSelection}
          loading={loading}
          readonly={readonly}
        ></DatasetTable>
        {documentUploadVisible && (
          <FileUploadDialog
            hideModal={hideDocumentUploadModal}
            onOk={onDocumentUploadOk}
            loading={documentUploadLoading}
            showParseOnCreation
          ></FileUploadDialog>
        )}
        {createVisible && (
          <RenameDialog
            hideModal={hideCreateModal}
            onOk={onCreateOk}
            loading={createLoading}
            title={'File Name'}
          ></RenameDialog>
        )}
      </section>
    </>
  );
}
