import { CardSineLineContainer } from '@/components/card-singleline-container';
import { EmptyCardType } from '@/components/empty/constant';
import { EmptyAppCard } from '@/components/empty/empty';
import { RenameDialog } from '@/components/rename-dialog';
import { HomeIcon } from '@/components/svg-icon';
import { CardSkeleton } from '@/components/ui/skeleton';
import { useNavigatePage } from '@/hooks/logic-hooks/navigate-hooks';
import { useFetchNextKnowledgeListByPage } from '@/hooks/use-knowledge-request';
import { useTranslation } from 'react-i18next';
import { DatasetCard } from '../datasets/dataset-card';
import { useRenameDataset } from '../datasets/use-rename-dataset';
import { SeeAllAppCard } from './application-card';

export function Datasets() {
  const { t } = useTranslation();
  const { kbs, loading } = useFetchNextKnowledgeListByPage();
  const {
    datasetRenameLoading,
    initialDatasetName,
    onDatasetRenameOk,
    datasetRenameVisible,
    hideDatasetRenameModal,
    showDatasetRenameModal,
  } = useRenameDataset();
  const { navigateToDatasetList } = useNavigatePage();

  return (
    <section>
      <h2 className="text-2xl font-semibold mb-6 flex gap-2.5 items-center">
        {/* <IconFont name="data" className="size-8"></IconFont> */}
        <HomeIcon name="datasets" width={'32'} />
        {t('header.dataset')}
      </h2>
      <div className="">
        {loading ? (
          <div className="flex-1">
            <CardSkeleton />
          </div>
        ) : (
          <>
            {kbs?.length > 0 && (
              <CardSineLineContainer>
                {kbs
                  ?.slice(0, 6)
                  .map((dataset) => (
                    <DatasetCard
                      key={dataset.id}
                      dataset={dataset}
                      showDatasetRenameModal={showDatasetRenameModal}
                    ></DatasetCard>
                  ))}
                {
                  <SeeAllAppCard
                    click={() => navigateToDatasetList({ isCreate: false })}
                  ></SeeAllAppCard>
                }
              </CardSineLineContainer>
            )}
            {kbs?.length <= 0 && (
              <EmptyAppCard
                type={EmptyCardType.Dataset}
                onClick={() => navigateToDatasetList({ isCreate: true })}
              />
            )}
          </>
          //           <>
          //   {kbs?.length > 0 && (
          //     <div className="grid grid-cols-[repeat(auto-fill,_minmax(200px,_300px))] gap-6">
          //       {kbs?.slice(0, 6).map((dataset) => (
          //         <DatasetCard
          //           key={dataset.id}
          //           dataset={dataset}
          //           showDatasetRenameModal={showDatasetRenameModal}
          //           cardClassName="
          //         border-green-400/40
          //         bg-green-500/10
          //         shadow-[0_0_18px_rgba(248,113,113,0.25)]
          //         hover:border-green-400/70
          //         hover:bg-green-500/15
          //         hover:shadow-[0_0_28px_rgba(248,113,113,0.45)]
          //       "
          //         />
          //       ))}

          //       <SeeAllAppCard
          //         click={() => navigateToDatasetList({ isCreate: false })}
          //       />
          //     </div>
          //   )}

          //   {kbs?.length <= 0 && (
          //     <EmptyAppCard
          //       type={EmptyCardType.Dataset}
          //       onClick={() => navigateToDatasetList({ isCreate: true })}
          //     />
          //   )}
          // </>
          // </div>
        )}
      </div>
      {datasetRenameVisible && (
        <RenameDialog
          hideModal={hideDatasetRenameModal}
          onOk={onDatasetRenameOk}
          initialName={initialDatasetName}
          loading={datasetRenameLoading}
        ></RenameDialog>
      )}
    </section>
  );
}
