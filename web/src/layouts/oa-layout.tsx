import { Routes } from '@/routes';
import { ClipboardList, Database, Shield } from 'lucide-react';
import { NavLink, Outlet, useNavigate } from 'umi';

export default function OALayout() {
  const navigate = useNavigate();

  const menus = [
    {
      path: Routes.OA,
      label: '文件上传审批',
      icon: ClipboardList,
      end: true,
    },
    {
      path: Routes.OARole,
      label: '权限审批',
      icon: Shield,
      end: false,
    },
    {
      path: Routes.OAKnowledgeBase,
      label: '建库审批',
      icon: Database,
      end: false,
    },
  ];

  return (
    <div className="flex min-h-[calc(100vh-88px)] bg-transparent text-foreground">
      <aside className="w-60 shrink-0 border-r border-border bg-transparent p-4">
        {/* <button
          type="button"
          onClick={() => navigate(Routes.Root)}
          className="
            mb-6 flex w-full items-center gap-3 rounded-md
            px-3 py-2 text-sm text-muted-foreground
            transition-colors
            hover:text-foreground
          "
        >
          <ArrowLeft className="size-4" />
          <span>返回首页</span>
        </button> */}

        <div className="mb-6 px-3 text-lg font-semibold text-foreground">
          OA审批模拟
        </div>

        <nav className="space-y-2">
          {menus.map((item) => {
            const Icon = item.icon;

            return (
              <NavLink
                key={item.path}
                to={item.path}
                end={item.end}
                className={({ isActive }) =>
                  [
                    'flex items-center gap-3 rounded-md px-3 py-2 text-sm',
                    'border-l-2 transition-colors',
                    isActive
                      ? 'border-primary text-primary font-medium'
                      : 'border-transparent text-muted-foreground hover:border-border hover:text-foreground',
                  ].join(' ')
                }
              >
                <Icon className="size-4" />
                <span>{item.label}</span>
              </NavLink>
            );
          })}
        </nav>
      </aside>

      <main className="min-w-0 flex-1 bg-transparent p-6 text-foreground">
        <Outlet />
      </main>
    </div>
  );
}
