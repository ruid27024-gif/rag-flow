import { Outlet } from 'umi';
import { SideBar } from './sidebar';

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
import { cn } from '@/lib/utils';
import { House } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import styles from './index.less';

const UserSetting = () => {
  const { t } = useTranslation();
  const { navigateToHome } = useNavigatePage();

  return (
    <section className="flex flex-col h-full">
      <PageHeader>
        <Breadcrumb>
          <BreadcrumbList>
            <BreadcrumbItem>
              <BreadcrumbLink onClick={navigateToHome}>
                <House className="size-6 ml-8 text-gray-600 hover:text-blue-600 transition-colors" />
              </BreadcrumbLink>
            </BreadcrumbItem>
            <BreadcrumbSeparator className="translate-y-[7px]" />
            <BreadcrumbItem>
              <BreadcrumbPage className="w-28 whitespace-nowrap text-ellipsis overflow-hidden translate-y-[3px] text-gray-400 dark:text-gray-500">
                {t('setting.profile')}
              </BreadcrumbPage>
            </BreadcrumbItem>
          </BreadcrumbList>
        </Breadcrumb>
      </PageHeader>
      {/* <div
        className={cn(
          styles.settingWrapper,
          'overflow-auto flex flex-1 pt-4 pr-4 pb-4',
        )}
      >
        <SideBar></SideBar>
        <div className={cn(styles.outletWrapper, 'flex flex-1 rounded-lg')}>
          <Outlet></Outlet>
        </div>
      </div> */}

      <div
        className={cn(
          styles.settingWrapper,
          'flex flex-row flex-1 pt-4 pr-4 pb-4 overflow-hidden',
        )}
      >
        {/* 2. 左侧：锁定宽度 */}
        {/* <div className="w-[337px] flex-shrink-0 h-full">
      <SideBar />
    </div> */}
        <SideBar></SideBar>

        {/* 3. 右侧：flex-1 自动占满剩余宽度，h-full 占满高度 */}
        <div
          className={cn(
            styles.outletWrapper,
            'flex-1 h-full ml-4 rounded-lg overflow-hidden',
          )}
        >
          {/* 这里的内容现在应该能撑满高度了 */}
          <Outlet />
        </div>
      </div>
    </section>
  );
};

export default UserSetting;
