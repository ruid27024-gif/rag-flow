import {
  AsyncTreeSelect,
  TreeNodeType,
} from '@/components/ui/async-tree-select';
import { ButtonLoading } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  useFetchPureFileList,
  useFetchPureFileListRoot,
  useFetchPureFileListUP,
} from '@/hooks/use-file-request';
import { IModalProps } from '@/interfaces/common';
import { IFile } from '@/interfaces/database/file-manager';
import { Tabs } from 'antd';
import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

// export function MoveDialog({
//   hideModal,
//   onOk,
//   loading,
//   currentFile,
// }: IModalProps<any>) {
//   const { t } = useTranslation();

//   const { fetchList } = useFetchPureFileList();
//   const { fetchListUP } = useFetchPureFileListUP();

//   const [treeValue, setTreeValue] = useState<number | string>('');

//   // const [treeData, setTreeData] = useState([]);
//   // 分别维护两份树形数据：同级目录 和 外部目录
//   const [sameLevelTreeData, setSameLevelTreeData] = useState<any[]>([]);
//   const [upLevelTreeData, setUpLevelTreeData] = useState<any[]>([]);
//   const [externalTreeData, setExternalTreeData] = useState<any[]>([]);

//   const onLoadSameLevelData = useCallback(
//     async ({ id }: TreeNodeType) => {
//       console.log('选择的id:', currentFile.parent_id);
//       const ret = await fetchList(currentFile.parent_id as string );
//       if (ret.code === 0) {
//         console.log('返回的文件列表:', ret.data.files);
//         setSameLevelTreeData((tree) => {
//           return tree.concat(
//             ret.data.files
//               .filter((x: IFile) => x.type === 'folder'&& x.id !== currentFile.id)
//               .map((x: IFile) => ({
//                 id: x.id,
//                 parentId: x.parent_id,
//                 title: x.name,
//                 isLeaf:
//                   typeof x.has_child_folder === 'boolean'
//                     ? !x.has_child_folder
//                     : false,
//               })),
//           );
//         });
//       }
//     },
//     [fetchList],
//   );

//   const onLoadUpLevelData = useCallback(
//     async ({ id }: TreeNodeType) => {
//       console.log('选择的id:', currentFile.parent_id);
//       const ret = await fetchListUP(currentFile.parent_id as string);
//       if (ret.code === 0) {
//         console.log('返回的文件列表:', ret.data.files);
//         setUpLevelTreeData((tree) => {
//           return tree.concat(
//             ret.data.files
//               .filter((x: IFile) => x.type === 'folder')
//               .map((x: IFile) => ({
//                 id: x.id,
//                 parentId: x.parent_id,
//                 title: x.name,
//                 isLeaf:
//                   typeof x.has_child_folder === 'boolean'
//                     ? !x.has_child_folder
//                     : false,
//               })),
//           );
//         });
//       }
//     },
//     [fetchListUP],
//   );

//   const onLoadExternalData = useCallback(
//     async ({ id }: TreeNodeType) => {
//       const ret = await fetchList(id as string);
//       if (ret.code === 0) {
//         console.log('返回的文件列表:', ret.data.files);
//         setExternalTreeData((tree) => {
//           return tree.concat(
//             ret.data.files
//               .filter((x: IFile) => x.type === 'folder')
//               .map((x: IFile) => ({
//                 id: x.id,
//                 parentId: x.parent_id,
//                 title: x.name,
//                 isLeaf:
//                   typeof x.has_child_folder === 'boolean'
//                     ? !x.has_child_folder
//                     : false,
//               })),
//           );
//         });
//       }
//     },
//     [fetchList],
//   );

//   const handleSubmit = useCallback(() => {
//     onOk?.(treeValue);
//   }, [onOk, treeValue]);

//   // Tabs 的两个页签配置
//   const tabItems = [
//     {
//       key: 'same-level',
//       label: '同级目录',
//       children: (
//         <AsyncTreeSelect
//           treeData={sameLevelTreeData}
//           value={treeValue}
//           onChange={setTreeValue}
//           loadData={onLoadSameLevelData}
//         />
//       ),
//     },
//     {
//       key: 'up-level',
//       label: '上级目录',
//       children: (
//         <AsyncTreeSelect
//           treeData={upLevelTreeData}
//           value={treeValue}
//           onChange={setTreeValue}
//           loadData={onLoadUpLevelData}
//         />
//       ),
//     },
//     {
//       key: 'external',
//       label: '根目录',
//       children: (
//         <AsyncTreeSelect
//           treeData={externalTreeData}
//           value={treeValue}
//           onChange={setTreeValue}
//           loadData={onLoadExternalData}
//         />
//       ),
//     },
//   ];

//   //   return (
//   //     <Dialog open onOpenChange={hideModal}>
//   //       <DialogContent>
//   //         <DialogHeader>
//   //           <DialogTitle>{t('common.move')}</DialogTitle>
//   //         </DialogHeader>
//   //         <div>
//   //           <AsyncTreeSelect
//   //             treeData={treeData}
//   //             value={treeValue}
//   //             onChange={setTreeValue}
//   //             loadData={onLoadData}
//   //           ></AsyncTreeSelect>
//   //         </div>
//   //         <DialogFooter>
//   //           <ButtonLoading
//   //             type="submit"
//   //             onClick={handleSubmit}
//   //             disabled={isEmpty(treeValue)}
//   //             loading={loading}
//   //           >
//   //             {t('common.save')}
//   //           </ButtonLoading>
//   //         </DialogFooter>
//   //       </DialogContent>
//   //     </Dialog>
//   //   );
//   // }
//   return (
//     <Dialog open onOpenChange={hideModal}>
//       <DialogContent>
//         <DialogHeader>
//           <DialogTitle>{t('common.move')}</DialogTitle>
//         </DialogHeader>
//         <div>
//           {/* 使用 Tabs 切换两种转移方式 */}
//           <Tabs defaultActiveKey="same-level" items={tabItems} />
//         </div>
//         <DialogFooter>
//           <ButtonLoading
//             type="submit"
//             onClick={handleSubmit}
//             disabled={!treeValue} // 修正：使用 !treeValue 判断是否为空
//             loading={loading}
//           >
//             {t('common.save')}
//           </ButtonLoading>
//         </DialogFooter>
//       </DialogContent>
//     </Dialog>
//   );
// // }
// export function MoveDialog({
//   hideModal,
//   onOk,
//   loading,
//   currentFile,
// }: IModalProps<any>) {
//   const { t } = useTranslation();

//   const { fetchList } = useFetchPureFileList();
//   const { fetchListUP } = useFetchPureFileListUP();
//   const { fetchListRoot } = useFetchPureFileListRoot();

//   const [treeValue, setTreeValue] = useState<number | string>('');

//   const [sameLevelTreeData, setSameLevelTreeData] = useState<any[]>([]);
//   const [upLevelTreeData, setUpLevelTreeData] = useState<any[]>([]);
//   const [externalTreeData, setExternalTreeData] = useState<any[]>([]);

//   const toTreeNodes = useCallback(
//     (files: IFile[]) =>
//       files
//         .filter((x: IFile) => x.type === 'folder' && x.id !== currentFile.id)
//         .map((x: IFile) => ({
//           id: x.id,
//           parentId: x.parent_id,
//           title: x.name,
//           isLeaf:
//             typeof x.has_child_folder === 'boolean'
//               ? !x.has_child_folder
//               : false,
//         })),
//     [currentFile.id],
//   );

//   const appendUniqueNodes = useCallback((tree: any[], nodes: any[]) => {
//     const existingIds = new Set(tree.map((item) => item.id));
//     return tree.concat(nodes.filter((item) => !existingIds.has(item.id)));
//   }, []);

//   const onLoadSameLevelData = useCallback(
//     async ({ id }: TreeNodeType) => {
//       const parentId = (id || currentFile.parent_id) as string;
//       const ret = await fetchList(parentId);

//       if (ret.code === 0) {
//         const nodes = toTreeNodes(ret.data.files);
//         setSameLevelTreeData((tree) => appendUniqueNodes(tree, nodes));
//       }
//     },
//     [fetchList, currentFile.parent_id, toTreeNodes, appendUniqueNodes],
//   );

//   const onLoadUpLevelData = useCallback(
//     async ({ id }: TreeNodeType) => {
//       const parentId = (id || currentFile.parent_id) as string;
//       const ret = await fetchListUP(parentId);

//       if (ret.code === 0) {
//         const nodes = toTreeNodes(ret.data.files);
//         setUpLevelTreeData((tree) => appendUniqueNodes(tree, nodes));
//       }
//     },
//     [fetchListUP, currentFile.parent_id, toTreeNodes, appendUniqueNodes],
//   );

//   const onLoadRootData = useCallback(async () => {
//     const ret = await fetchListRoot();

//     if (ret.code === 0) {
//       const nodes = toTreeNodes(ret.data.files);
//       setExternalTreeData((tree) => appendUniqueNodes(tree, nodes));
//     }
//   }, [fetchListRoot, toTreeNodes, appendUniqueNodes]);

//   const onLoadExternalData = useCallback(
//     async ({ id }: TreeNodeType) => {
//       if (!id) {
//         await onLoadRootData();
//         return;
//       }

//       const ret = await fetchList(id as string);

//       if (ret.code === 0) {
//         const nodes = toTreeNodes(ret.data.files);
//         setExternalTreeData((tree) => appendUniqueNodes(tree, nodes));
//       }
//     },
//     [fetchList, toTreeNodes, appendUniqueNodes, onLoadRootData],
//   );

//   useEffect(() => {
//     if (!currentFile.parent_id) return;

//     onLoadSameLevelData({ id: currentFile.parent_id } as TreeNodeType);
//     onLoadUpLevelData({ id: currentFile.parent_id } as TreeNodeType);
//     onLoadRootData();
//   }, [
//     currentFile.parent_id,
//     onLoadSameLevelData,
//     onLoadUpLevelData,
//     onLoadRootData,
//   ]);

//   const handleSubmit = useCallback(() => {
//     onOk?.(treeValue);
//   }, [onOk, treeValue]);

//   const tabItems = [
//     {
//       key: 'same-level',
//       label: '同级目录',
//       children: (
//         <AsyncTreeSelect
//           treeData={sameLevelTreeData}
//           value={treeValue}
//           onChange={setTreeValue}
//           loadData={onLoadSameLevelData}
//         />
//       ),
//     },
//     {
//       key: 'up-level',
//       label: '上级目录',
//       children: (
//         <AsyncTreeSelect
//           treeData={upLevelTreeData}
//           value={treeValue}
//           onChange={setTreeValue}
//           loadData={onLoadUpLevelData}
//         />
//       ),
//     },
//     {
//       key: 'external',
//       label: '根目录',
//       children: (
//         <AsyncTreeSelect
//           treeData={externalTreeData}
//           value={treeValue}
//           onChange={setTreeValue}
//           loadData={onLoadExternalData}
//         />
//       ),
//     },
//   ];

//   return (
//     <Dialog open onOpenChange={hideModal}>
//       <DialogContent>
//         <DialogHeader>
//           <DialogTitle>{t('common.move')}</DialogTitle>
//         </DialogHeader>

//         <div>
//           <Tabs defaultActiveKey="same-level" items={tabItems} />
//         </div>

//         <DialogFooter>
//           <ButtonLoading
//             type="submit"
//             onClick={handleSubmit}
//             disabled={treeValue === ''}
//             loading={loading}
//           >
//             {t('common.save')}
//           </ButtonLoading>
//         </DialogFooter>
//       </DialogContent>
//     </Dialog>
//   );
// }

export function MoveDialog({
  hideModal,
  onOk,
  loading,
  currentFile,
}: IModalProps<any>) {
  const { t } = useTranslation();

  const { fetchList } = useFetchPureFileList();
  const { fetchListUP } = useFetchPureFileListUP();
  const { fetchListRoot } = useFetchPureFileListRoot();

  const [treeValue, setTreeValue] = useState<number | string>('');

  const [sameLevelTreeData, setSameLevelTreeData] = useState<any[]>([]);
  const [upLevelTreeData, setUpLevelTreeData] = useState<any[]>([]);
  const [externalTreeData, setExternalTreeData] = useState<any[]>([]);

  const toTreeNodes = useCallback(
    (files: IFile[]) =>
      files
        .filter((x: IFile) => x.type === 'folder' && x.id !== currentFile.id)
        .map((x: IFile) => {
          const isRootNode = x.id === x.parent_id;

          return {
            id: x.id,
            parentId: isRootNode ? undefined : x.parent_id,
            title: isRootNode && x.name === '/' ? '根目录' : x.name,
            isLeaf: false,
          };
        }),
    [currentFile.id],
  );

  const appendUniqueNodes = useCallback((tree: any[], nodes: any[]) => {
    const existingIds = new Set(tree.map((item) => item.id));

    return tree.concat(nodes.filter((item) => !existingIds.has(item.id)));
  }, []);

  const onLoadSameLevelData = useCallback(
    async ({ id }: TreeNodeType) => {
      const parentId = (id || currentFile.parent_id) as string;
      const ret = await fetchList(parentId);

      if (ret.code === 0) {
        const nodes = toTreeNodes(ret.data.files);
        setSameLevelTreeData((tree) => appendUniqueNodes(tree, nodes));
      }
    },
    [fetchList, currentFile.parent_id, toTreeNodes, appendUniqueNodes],
  );

  const onLoadUpLevelData = useCallback(
    async ({ id }: TreeNodeType) => {
      const parentId = (id || currentFile.parent_id) as string;
      const ret = await fetchListUP(parentId);

      if (ret.code === 0) {
        const nodes = toTreeNodes(ret.data.files);
        setUpLevelTreeData((tree) => appendUniqueNodes(tree, nodes));
      }
    },
    [fetchListUP, currentFile.parent_id, toTreeNodes, appendUniqueNodes],
  );

  const onLoadRootData = useCallback(async () => {
    const ret = await fetchListRoot();

    if (ret.code === 0) {
      const nodes = toTreeNodes(ret.data.files);
      setExternalTreeData((tree) => appendUniqueNodes(tree, nodes));
    }
  }, [fetchListRoot, toTreeNodes, appendUniqueNodes]);

  const onLoadExternalData = useCallback(
    async ({ id }: TreeNodeType) => {
      if (!id) {
        await onLoadRootData();
        return;
      }

      const ret = await fetchList(id as string);

      if (ret.code === 0) {
        const nodes = toTreeNodes(ret.data.files);
        setExternalTreeData((tree) => appendUniqueNodes(tree, nodes));
      }
    },
    [fetchList, toTreeNodes, appendUniqueNodes, onLoadRootData],
  );

  useEffect(() => {
    if (!currentFile.parent_id) return;

    // onLoadSameLevelData({ id: currentFile.parent_id } as TreeNodeType);
    // onLoadUpLevelData({ id: currentFile.parent_id } as TreeNodeType);
    onLoadRootData();
  }, [
    currentFile.parent_id,
    // onLoadSameLevelData,
    // onLoadUpLevelData,
    onLoadRootData,
  ]);

  const handleSubmit = useCallback(() => {
    onOk?.(treeValue);
  }, [onOk, treeValue]);

  const tabItems = [
    // {
    //   key: 'same-level',
    //   label: '同级目录',
    //   children: (
    //     <AsyncTreeSelect
    //       treeData={sameLevelTreeData}
    //       value={treeValue}
    //       onChange={setTreeValue}
    //       loadData={onLoadSameLevelData}
    //     />
    //   ),
    // },
    // {
    //   key: 'up-level',
    //   label: '上级目录',
    //   children: (
    //     <AsyncTreeSelect
    //       treeData={upLevelTreeData}
    //       value={treeValue}
    //       onChange={setTreeValue}
    //       loadData={onLoadUpLevelData}
    //     />
    //   ),
    // },
    {
      key: 'external',
      label: '路径',
      children: (
        <AsyncTreeSelect
          treeData={externalTreeData}
          value={treeValue}
          onChange={setTreeValue}
          loadData={onLoadExternalData}
        />
      ),
    },
  ];

  return (
    <Dialog open onOpenChange={hideModal}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t('common.move')}</DialogTitle>
        </DialogHeader>

        <div>
          <Tabs defaultActiveKey="same-level" items={tabItems} />
        </div>

        <DialogFooter>
          <ButtonLoading
            type="submit"
            onClick={handleSubmit}
            disabled={treeValue === ''}
            loading={loading}
          >
            {t('common.save')}
          </ButtonLoading>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
