import { PageHeader } from '@/components/page-header';
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from '@/components/ui/breadcrumb';
import { useNavigatePage } from '@/hooks/logic-hooks/navigate-hooks';
import { useFetchKnowledgeBaseConfiguration } from '@/hooks/use-knowledge-request';
import { useTranslation } from 'react-i18next';
import { Outlet } from 'umi';
import { SideBar } from './sidebar';

export default function DatasetWrapper() {
  const { navigateToDatasetList } = useNavigatePage();
  const { t } = useTranslation();
  const { data } = useFetchKnowledgeBaseConfiguration();

  return (
    <section className="flex h-full flex-col w-full">
      <PageHeader>
        <Breadcrumb>
          <BreadcrumbList>
            <BreadcrumbItem>
              <BreadcrumbLink onClick={navigateToDatasetList}>
                <span
                  className="
                  text-lg font-bold
                  bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500
                  bg-clip-text text-transparent
                  group-hover:text-slate-900 dark:group-hover:text-white
                  transition-all duration-300
                  cursor-pointer
                "
                >
                  {t('knowledgeDetails.dataset')}
                </span>
              </BreadcrumbLink>
            </BreadcrumbItem>
            <BreadcrumbSeparator />
            <BreadcrumbItem>
              <BreadcrumbPage className="w-28 whitespace-nowrap text-ellipsis overflow-hidden">
                {data.name}
              </BreadcrumbPage>
            </BreadcrumbItem>
          </BreadcrumbList>
        </Breadcrumb>
      </PageHeader>
      <div className="flex flex-1 min-h-0">
        <SideBar></SideBar>
        <div className="flex-1 overflow-auto">
          <Outlet />
        </div>
      </div>
    </section>
  );
}
