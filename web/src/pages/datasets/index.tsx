import { EmptyCardType } from '@/components/empty/constant';
import { EmptyAppCard } from '@/components/empty/empty';
import ListFilterBar from '@/components/list-filter-bar';
import { RenameDialog } from '@/components/rename-dialog';
import { Button } from '@/components/ui/button';
import { RAGFlowPagination } from '@/components/ui/ragflow-pagination';
import { useFetchNextKnowledgeListByPage } from '@/hooks/use-knowledge-request';
import { useQueryClient } from '@tanstack/react-query';
import { pick } from 'lodash';
import { Plus } from 'lucide-react';
import { useCallback, useEffect, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { useSearchParams } from 'umi';
import { DatasetCard } from './dataset-card';
import { DatasetCreatingDialog } from './dataset-creating-dialog';
import { useSaveKnowledge } from './hooks';
import { useRenameDataset } from './use-rename-dataset';
import { useSelectOwners } from './use-select-owners';

export default function Datasets() {
  const { t } = useTranslation();
  const {
    visible,
    hideModal,
    showModal,
    onCreateOk,
    loading: creatingLoading,
  } = useSaveKnowledge();

  // 获取数据
  const {
    kbs,
    total,
    pagination,
    setPagination,
    handleInputChange,
    searchString,
    filterValue,
    handleFilterSubmit,
  } = useFetchNextKnowledgeListByPage();

  // 获取筛选的人名
  const owners = useSelectOwners();

  // 封装了重命名知识库的所有逻辑。
  const {
    datasetRenameLoading,
    initialDatasetName,
    onDatasetRenameOk,
    datasetRenameVisible,
    hideDatasetRenameModal,
    showDatasetRenameModal,
  } = useRenameDataset();

  // 定义了一个处理分页变化的函数。
  const handlePageChange = useCallback(
    (page: number, pageSize?: number) => {
      setPagination({ page, pageSize });
    },
    [setPagination],
  );

  // 这通常用于实现“通过链接直接打开创建弹窗”的功能。
  const [searchUrl, setSearchUrl] = useSearchParams();
  const isCreate = searchUrl.get('isCreate') === 'true';
  // 获取 react-query 的客户端实例，用于手动触发数据刷新。
  // 所有 useQuery 请求回来的数据都存在这里。
  //

  // 在组件内部添加分组逻辑
  const groupedDatasets = useMemo(() => {
    if (!kbs?.length) return {};

    const groups: Record<string, typeof kbs> = {};

    kbs.forEach((dataset) => {
      const groupName = dataset.group_name || '管理员私有库';

      if (!groups[groupName]) {
        groups[groupName] = [];
      }
      groups[groupName].push(dataset);
    });

    return groups;
  }, [kbs]);

  const queryClient = useQueryClient(); //单例模式

  useEffect(() => {
    if (isCreate) {
      // 将tenantInfo标记为过期
      queryClient.invalidateQueries({ queryKey: ['tenantInfo'] });
      showModal(); // 显示新建框
      searchUrl.delete('isCreate');
      setSearchUrl(searchUrl); // 从 URL 中移除 isCreate 参数，避免刷新页面后再次触发。
    }
  }, [isCreate, showModal, searchUrl, setSearchUrl]);
  // 获取当前用户信息
  // const userInfo = JSON.parse(localStorage.getItem('user_info') || '{}');

  return (
    <>
      <section className="py-4 flex-1 flex flex-col min-h-0">
        {(!kbs?.length || kbs?.length <= 0) && !searchString && (
          <div className="flex w-full items-center justify-center h-[calc(100vh-164px)]">
            <EmptyAppCard
              showIcon
              size="large"
              className="w-[480px] p-14 "
              isSearch={!!searchString}
              type={EmptyCardType.Dataset}
              onClick={() => showModal()}
            />
          </div>
        )}
        {(!!kbs?.length || searchString) && (
          <>
            <div className="px-8 pt-5">
              <ListFilterBar
                title={t('header.dataset')}
                searchString={searchString}
                onSearchChange={handleInputChange}
                value={filterValue}
                filters={owners}
                onChange={handleFilterSubmit}
                // className="px-8"
                icon={'datasets'}
              >
                <Button onClick={showModal}>
                  <Plus className=" size-2.5" />
                  {t('knowledgeList.createKnowledgeBase')}
                </Button>
              </ListFilterBar>
            </div>
            {(!kbs?.length || kbs?.length <= 0) && searchString && (
              <div className="flex w-full items-center justify-center h-[calc(100vh-164px)]">
                <EmptyAppCard
                  showIcon
                  size="large"
                  className="w-[480px] p-14"
                  isSearch={!!searchString}
                  type={EmptyCardType.Dataset}
                  onClick={() => showModal()}
                />
              </div>
            )}
            {/* <div className="flex-1">
              <CardContainer className="max-h-[calc(100dvh-280px)] overflow-auto px-8">
                {kbs.map((dataset) => {
                  return (
                    <DatasetCard
                      dataset={dataset}
                      key={dataset.id}
                      showDatasetRenameModal={showDatasetRenameModal}
                    ></DatasetCard>
                  );
                })}
              </CardContainer>
            </div> */}

            {/* 滚动容器包含所有内容 */}
            <div className="flex-1 min-h-0 overflow-y-auto">
              <div className="flex flex-col gap-4 w-full px-8 pt-1">
                {Object.entries(groupedDatasets).map(
                  ([groupName, datasets]) => (
                    <div key={groupName} className="flex flex-col gap-4">
                      {/* 组名 */}
                      <h2
                        className="
                            pl-3
                            text-transparent
                            [-webkit-text-fill-color:transparent]
                            bg-clip-text
                            bg-gradient-to-r
                            from-[#065F46]
                            to-[#34D399]
                            font-serif
                          "
                        style={{
                          fontFamily: `Georgia, "Times New Roman", serif`,
                        }}
                      >
                        {groupName}{' '}
                        <span
                          className="
                          ml-2 relative inline-flex h-6 w-6 items-center justify-center overflow-hidden rounded-full
                          bg-gradient-to-br from-emerald-200 via-teal-300 to-green-300
                          text-[11px] font-bold text-emerald-800
                          ring-1 ring-white/60
                          cursor-default select-none
                          shadow-[0_2px_8px_rgba(52,211,153,0.25),inset_0_1px_1px_rgba(255,255,255,0.6)]
                          transition-all duration-300 ease-out
                          hover:scale-110 hover:shadow-[0_0_16px_rgba(52,211,153,0.5),0_0_24px_rgba(16,185,129,0.3),inset_0_1px_2px_rgba(255,255,255,0.8)]
                        "
                        >
                          <span className="relative z-10 text-blue [-webkit-text-fill-color:#2563eb]">
                            {datasets.length}
                          </span>

                          <span className="absolute left-1 top-1 h-2 w-2 rounded-full bg-white/80 blur-[1px]" />
                          <span className="absolute bottom-0 right-0 h-3 w-3 rounded-full bg-emerald-500/20 blur-sm" />
                        </span>
                      </h2>

                      {/* 卡片区域 */}
                      <div className="grid grid-cols-[repeat(auto-fill,_minmax(200px,_300px))] gap-6">
                        {datasets.map((dataset) => (
                          <DatasetCard
                            dataset={dataset}
                            key={dataset.id}
                            showDatasetRenameModal={showDatasetRenameModal}
                          />
                        ))}
                      </div>
                    </div>
                  ),
                )}
              </div>

              {/* 分页在滚动容器内部 */}
              <div className="mt-8 px-8 pb-8">
                {' '}
                {/* 添加 pb-8 底部内边距 */}
                <RAGFlowPagination
                  {...pick(pagination, 'current', 'pageSize')}
                  total={total}
                  onChange={handlePageChange}
                />
              </div>
            </div>
          </>
        )}
        {visible && (
          <DatasetCreatingDialog
            hideModal={hideModal}
            onOk={onCreateOk}
            loading={creatingLoading}
          ></DatasetCreatingDialog>
        )}
        {datasetRenameVisible && (
          <RenameDialog
            hideModal={hideDatasetRenameModal}
            onOk={onDatasetRenameOk}
            initialName={initialDatasetName}
            loading={datasetRenameLoading}
          ></RenameDialog>
        )}
      </section>
    </>
  );
}
