import { IconFontFill } from '@/components/icon-font';
import { RAGFlowAvatar } from '@/components/ragflow-avatar';
import ThemeToggle from '@/components/theme-toggle';
import { Button } from '@/components/ui/button';
import { Domain } from '@/constants/common';
import { useSecondPathName } from '@/hooks/route-hook';
import { useLogout } from '@/hooks/use-login-request';
import {
  useFetchSystemVersion,
  useFetchUserInfo,
} from '@/hooks/use-user-setting-request';
import { cn } from '@/lib/utils';
import { Routes } from '@/routes';
import { TFunction } from 'i18next';
import { User } from 'lucide-react';
import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useHandleMenuClick } from './hooks';

// const menuItems = (t: TFunction) => [
//   // { icon: Server, label: t('setting.dataSources'), key: Routes.DataSource },
//   { icon: User, label: t('setting.profile'), key: Routes.Profile },
//   {
//           key: '/services',
//           label: t('admin.serviceStatus'),
//           icon: User,
//         },
//   {
//     key: '/users',
//     label: t('admin.userManagement'),
//     icon: User,
//   },
//   // { icon: Box, label: t('setting.model'), key: Routes.Model },
//   // { icon: Banknote, label: 'MCP', key: Routes.Mcp },
//   // { icon: Users, label: t('setting.team'), key: Routes.Team },

//   // { icon: Unplug, label: t('setting.api'), key: Routes.Api },
//   // {
//   //   icon: MessageSquareQuote,
//   //   label: 'Prompt Templates',
//   //   key: Routes.Profile,
//   // },
//   // { icon: TextSearch, label: 'Retrieval Templates', key: Routes.Profile },
//   // { icon: Cog, label: t('setting.system'), key: Routes.System },
//   // { icon: Banknote, label: 'Plan', key: Routes.Plan },
// ];

const menuItems = (t: TFunction) => {
  const {
    data: { language = 'English', avatar, nickname, is_admin_user, role_level },
  } = useFetchUserInfo();
  const isAdmin = is_admin_user || role_level === 1;

  return [
    { icon: User, label: t('setting.profile'), key: Routes.Profile },
    // 如果是管理员，就展开这两个对象；否则展开空数组（相当于不渲染）
    ...(isAdmin
      ? [
          {
            key: '/services',
            label: t('admin.serviceStatus'),
            icon: User,
          },
          {
            key: '/users',
            label: t('admin.userManagement'),
            icon: User,
          },
        ]
      : []),
  ];
};

export function SideBar() {
  const pathName = useSecondPathName();
  const { data: userInfo } = useFetchUserInfo();
  const { handleMenuClick, active } = useHandleMenuClick();
  const { version, fetchSystemVersion } = useFetchSystemVersion();
  const { t } = useTranslation();
  useEffect(() => {
    if (location.host !== Domain) {
      fetchSystemVersion();
    }
  }, [fetchSystemVersion]);
  const { logout } = useLogout();

  return (
    <aside className="w-[303px] bg-bg-base flex flex-col">
      <div className="px-6 flex gap-2 items-center">
        <RAGFlowAvatar
          avatar={userInfo?.avatar}
          name={userInfo?.nickname}
          isPerson
        />
        <p className="text-sm text-text-primary">{userInfo?.email}</p>
      </div>
      <div className="flex-1 overflow-auto">
        {menuItems(t).map((item, idx) => {
          const hoverKey = pathName === item.key;
          return (
            <div key={idx}>
              <div key={idx} className="mx-6 my-5 ">
                <Button
                  variant={hoverKey ? 'secondary' : 'ghost'}
                  className={cn('w-full justify-between gap-2.5 p-3 relative', {
                    'bg-bg-card text-text-primary': active === item.key,
                    'bg-bg-base text-text-secondary': active !== item.key,
                  })}
                  onClick={handleMenuClick(item.key)}
                >
                  <section className="flex items-center gap-2.5">
                    {item.key === Routes.Mcp ? (
                      <IconFontFill name={'mcp'} className="size-4 w-4 h-4" />
                    ) : (
                      <item.icon className="w-6 h-6" />
                    )}
                    <span>{item.label}</span>
                  </section>
                  {/* {item.key === Routes.System && (
                    <div className="mr-2 px-2 bg-accent-primary-5 text-accent-primary rounded-md">
                      {version}
                    </div>
                  )} */}
                  {/* {active && (
                    <div className="absolute right-0 w-[5px] h-[66px] bg-primary rounded-l-xl shadow-[0_0_5.94px_#7561ff,0_0_11.88px_#7561ff,0_0_41.58px_#7561ff,0_0_83.16px_#7561ff,0_0_142.56px_#7561ff,0_0_249.48px_#7561ff]" />
                  )} */}
                </Button>
              </div>
            </div>
          );
        })}
      </div>

      <div className="p-6 mt-auto ">
        <div className="flex items-center gap-2 mb-6 justify-between">
          {/* <div className="mr-2 px-2 text-accent-primary rounded-md">
            {version}
          </div> */}
          <ThemeToggle />
        </div>
        <Button
          variant="ghost"
          className="w-full gap-3 bg-bg-base border border-border-button"
          onClick={() => {
            logout();
          }}
        >
          {t('setting.logout')}
        </Button>
      </div>
    </aside>
  );
}

// import { useNavigate } from 'react-router-dom';
// // 引入管理后台菜单需要的图标（请确保你的项目已安装 react-icons/lucide 或对应的图标库）
// // import { LucideServerCrash, LucideUserCog, LucideUserStar, LucideSquareUserRound, LucideMonitor } from 'react-icons/lu';

// // 假设你有这些路由常量，如果没有可以直接换成字符串路径，如 '/admin/services'
// const Routes2 = {
//   AdminServices: '/admin/services',
//   AdminUserManagement: '/admin/users',
//   AdminWhitelist: '/admin/whitelist',
//   AdminRoles: '/admin/roles',
//   AdminMonitoring: '/admin/monitoring',
// };

// const IS_ENTERPRISE = true; // 控制是否显示企业版专属菜单

// // 融合后的管理后台菜单项
// const menuItems = (t: TFunction) => [
//   { icon: User, label: t('setting.profile'), key: Routes.Profile },

//   {
//     path: Routes2.AdminServices,
//     name: t('admin.serviceStatus') || '服务状态',
//     icon: User,
//   },
//   {
//     path: Routes2.AdminUserManagement,
//     name: t('admin.userManagement') || '用户管理',
//     icon: User,
//   },
//   ...(IS_ENTERPRISE
//     ? [
//         {
//           path: Routes2.AdminWhitelist,
//           name: t('admin.registrationWhitelist') || '注册白名单',
//           icon: User,
//         },
//         {
//           path: Routes2.AdminRoles,
//           name: t('admin.roles') || '角色管理',
//           icon: User,
//         },
//         {
//           path: Routes2.AdminMonitoring,
//           name: t('admin.monitoring') || '监控',
//           icon: User,
//         },
//       ]
//     : []),
// ];

// export function SideBar() {
//   const { data: userInfo } = useFetchUserInfo();
//   const { version, fetchSystemVersion } = useFetchSystemVersion();
//   const { t } = useTranslation();
//   const navigate = useNavigate();
//   // 保留你原有的 active 状态和点击处理逻辑
//   const { active, handleMenuClick } = useHandleMenuClick();

//   useEffect(() => {
//     if (location.host !== Domain) {
//       fetchSystemVersion();
//     }
//   }, [fetchSystemVersion]);

//   const { logout } = useLogout();

//   return (
//     <aside className="w-[303px] bg-bg-base flex flex-col">
//       {/* 顶部用户信息保持不变 */}
//       <div className="px-6 flex gap-2 items-center">
//         <RAGFlowAvatar
//           avatar={userInfo?.avatar}
//           name={userInfo?.nickname}
//           isPerson
//         />
//         <p className="text-sm text-text-primary">{userInfo?.email}</p>
//       </div>

//       {/* 中间导航菜单：保留 Button 按钮的方式 */}
//       <div className="flex-1 overflow-auto py-5">
//         {menuItems(t).map((item, idx) => {
//           // 判断当前按钮是否处于激活状态
//           const isActive = active === item.path;

//           return (
//             <div key={idx} className="mx-6 my-2">
//               <Button
//                 // 根据是否激活，切换 secondary（激活）和 ghost（未激活）变体
//                 variant={isActive ? 'secondary' : 'ghost'}
//                 className={cn('w-full justify-start gap-3 p-3', {
//                   'bg-bg-card text-text-primary': isActive, // 激活时的背景与文字颜色
//                   'bg-bg-base text-text-secondary': !isActive, // 未激活时的颜色
//                 })}
//                 onClick={() => handleMenuClick(item.path)}
//               >
//                 {/* 渲染对应的图标 */}
//                 <item.icon className="size-[1em]" />
//                 <span>{item.name}</span>
//               </Button>
//             </div>
//           );
//         })}
//       </div>

//       {/* 底部版本号和退出登录保持不变 */}
//       <div className="p-6 mt-auto">
//         <div className="flex items-center justify-between mb-6">
//           <span className="leading-none text-xs text-accent-primary">
//             {version}
//           </span>
//           <ThemeToggle />
//         </div>
//         <Button
//           variant="ghost"
//           className="w-full gap-3 bg-bg-base border border-border-button"
//           onClick={() => {
//             logout();
//           }}
//         >
//           {t('setting.logout') || '退出登录'}
//         </Button>
//       </div>
//     </aside>
//   );
// }
