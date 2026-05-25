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
              <BreadcrumbLink
                onClick={navigateToDatasetList}
                className="cursor-pointer"
              >
                <span
                  className="
                  text-lg font-bold
                  bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500
                  bg-clip-text text-transparent
                  ml-2
                  transition-all duration-300 ease-in-out
                  hover:underline hover:decoration-2 hover:underline-offset-4
                  hover:scale-105 hover:opacity-80
                  "
                >
                  {t('knowledgeDetails.dataset')}
                </span>
              </BreadcrumbLink>
            </BreadcrumbItem>
            <BreadcrumbSeparator className="translate-y-[7px]" />
            <BreadcrumbItem>
              <BreadcrumbPage className="w-28 whitespace-nowrap text-ellipsis overflow-hidden translate-y-[3px] text-gray-400 dark:text-gray-500">
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
