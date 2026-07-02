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
import { Database } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Outlet } from 'umi';
import { SideBar } from './sidebar';

export default function DatasetWrapper() {
  const { navigateToDatasetList } = useNavigatePage();
  const { t } = useTranslation();
  const { data } = useFetchKnowledgeBaseConfiguration();

  return (
    <section className="flex h-full flex-col w-full">
      {/* <PageHeader>
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
                  ml-6
                  bg-gradient-to-r from-emerald-700 via-green-500 to-lime-400
                  bg-clip-text text-transparent
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
      </PageHeader> */}
      <PageHeader>
        <div className="mx-4 mt-3 mb-2 pl-4">
          <Breadcrumb>
            <BreadcrumbList className="flex items-center gap-1.5 text-sm">
              <BreadcrumbItem>
                <BreadcrumbLink
                  onClick={navigateToDatasetList}
                  className="
            group
            inline-flex items-center gap-1.5
            cursor-pointer
            text-emerald-600 dark:text-emerald-400
            transition-all duration-200
            hover:text-emerald-700 dark:hover:text-emerald-300
            hover:opacity-90
          "
                >
                  <span className="inline-flex h-4 w-8 shrink-0 items-center align-middle">
                    {/* 最近 */}
                    <Database className="h-4 w-4 text-emerald-500 dark:text-emerald-300 opacity-100 transition-transform duration-200 group-hover:scale-105" />

                    {/* 中间 */}
                    <Database className="-ml-1 h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400 opacity-70 transition-transform duration-200 group-hover:scale-105" />

                    {/* 最远 */}
                    <Database className="-ml-1 h-3 w-3 text-emerald-700 dark:text-emerald-500 opacity-45 transition-transform duration-200 group-hover:scale-105" />
                  </span>

                  <span
                    className="
              font-semibold
              group-hover:underline
              group-hover:decoration-emerald-500
              group-hover:underline-offset-4
            "
                  >
                    {t('knowledgeDetails.dataset')}
                  </span>
                </BreadcrumbLink>
              </BreadcrumbItem>

              <BreadcrumbSeparator className="text-gray-300 dark:text-gray-600" />

              <BreadcrumbItem>
                <BreadcrumbPage
                  title={data.name}
                  className="
              inline-flex items-center gap-1.5
              max-w-[260px]
              cursor-default
              select-none
              font-medium
              text-blue-600 dark:text-blue-400
            "
                >
                  <Database className="h-4 w-4 shrink-0 text-blue-500 dark:text-blue-400 opacity-85" />

                  <span className="truncate">{data.name}</span>
                </BreadcrumbPage>
              </BreadcrumbItem>
            </BreadcrumbList>
          </Breadcrumb>
        </div>
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
