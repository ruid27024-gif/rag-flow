import { BulkOperateBar } from '@/components/bulk-operate-bar';
import { FileUploadDialog } from '@/components/file-upload-dialog';
import ListFilterBar from '@/components/list-filter-bar';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useRowSelection } from '@/hooks/logic-hooks/use-row-selection';
import { useFetchFileList } from '@/hooks/use-file-request';
import { Upload } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { CreateFolderDialog } from './create-folder-dialog';
import { FileBreadcrumb } from './file-breadcrumb';
import { FilesTable } from './files-table';
import { MoveDialog } from './move-dialog';
import { useBulkOperateFile } from './use-bulk-operate-file';
import { useHandleCreateFolder } from './use-create-folder';
import { useHandleMoveFile } from './use-move-file';
import { useSelectBreadcrumbItems } from './use-navigate-to-folder';
import { useHandleUploadFile } from './use-upload-file';

export default function Files() {
  const [currentMoveFile, setCurrentMoveFile] = useState<any | null>(null); // 1. 新增状态保存当

  const { t } = useTranslation();
  const {
    fileUploadVisible,
    hideFileUploadModal,
    showFileUploadModal,
    fileUploadLoading,
    onFileUploadOk,
  } = useHandleUploadFile();

  const {
    folderCreateModalVisible,
    showFolderCreateModal,
    hideFolderCreateModal,
    folderCreateLoading,
    onFolderCreateOk,
  } = useHandleCreateFolder();

  const {
    pagination,
    files,
    total,
    loading,
    setPagination,
    searchString,
    handleInputChange,
  } = useFetchFileList();

  const {
    rowSelection,
    setRowSelection,
    rowSelectionIsEmpty,
    clearRowSelection,
    selectedCount,
  } = useRowSelection();

  const {
    showMoveFileModal,
    moveFileVisible,
    onMoveFileOk,
    hideMoveFileModal,
    moveFileLoading,
  } = useHandleMoveFile({ clearRowSelection });

  const { list } = useBulkOperateFile({
    files,
    rowSelection,
    showMoveFileModal,
    setRowSelection,
  });

  const breadcrumbItems = useSelectBreadcrumbItems();

  const leftPanel = (
    <div>
      {breadcrumbItems.length > 0 ? (
        <FileBreadcrumb></FileBreadcrumb>
      ) : (
        t('fileManager.files')
      )}
    </div>
  );

  return (
    <section className="p-8">
      <ListFilterBar
        leftPanel={leftPanel}
        searchString={searchString}
        onSearchChange={handleInputChange}
        showFilter={false}
        icon={'file'}
      >
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button>
              <Upload />
              {t('knowledgeDetails.addFile')}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="w-56">
            <DropdownMenuItem onClick={showFileUploadModal}>
              {t('fileManager.uploadFile')}
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={showFolderCreateModal}>
              {t('fileManager.newFolder')}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </ListFilterBar>

      {/* 批量操作栏目 只有勾选了，才能显示 */}
      {!rowSelectionIsEmpty && (
        <BulkOperateBar list={list} count={selectedCount}></BulkOperateBar>
      )}
      <FilesTable
        files={files}
        total={total}
        pagination={pagination}
        setPagination={setPagination}
        loading={loading}
        rowSelection={rowSelection}
        setRowSelection={setRowSelection}
        showMoveFileModal={showMoveFileModal}
        // ✅ 2. 把保存文件的函数传给 FilesTable
        onMoveClick={setCurrentMoveFile} // 2. 把设置状态的函数传下去
      ></FilesTable>
      {fileUploadVisible && (
        <FileUploadDialog
          hideModal={hideFileUploadModal}
          onOk={onFileUploadOk}
          loading={fileUploadLoading}
        ></FileUploadDialog>
      )}
      {folderCreateModalVisible && (
        <CreateFolderDialog
          loading={folderCreateLoading}
          visible={folderCreateModalVisible}
          hideModal={hideFolderCreateModal}
          onOk={onFolderCreateOk}
        ></CreateFolderDialog>
      )}
      {moveFileVisible && (
        <MoveDialog
          hideModal={hideMoveFileModal}
          onOk={onMoveFileOk}
          loading={moveFileLoading}
          // 3. 把 ID 传给 MoveDialog
          // ✅ 3. 把当前文件传给弹窗
          currentFile={currentMoveFile} // 3. 把拿到的当前文件传给弹窗
        ></MoveDialog>
      )}
    </section>
  );
}
