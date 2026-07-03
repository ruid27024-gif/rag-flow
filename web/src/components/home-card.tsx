import { RAGFlowAvatar } from '@/components/ragflow-avatar';
import { Card, CardContent } from '@/components/ui/card';
// import { formatDate } from '@/utils/date';
import { ReactNode } from 'react';

interface IProps {
  data: {
    name: string;
    description?: string;
    avatar?: string;
    update_time?: string | number;
    color?: number;
  };
  onClick?: () => void;
  moreDropdown: React.ReactNode;
  sharedBadge?: ReactNode;
  icon?: React.ReactNode;
}
export function HomeCard({
  data,
  onClick,
  moreDropdown,
  sharedBadge,
  icon,
}: IProps) {
  console.log('HomeCard data:', data);
  console.log('HomeCard color:', data?.name, data?.color);
  const formatDate = (dateStr) => {
    const date = new Date(dateStr);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');

    // 新增：获取时、分、秒并补零
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    const seconds = String(date.getSeconds()).padStart(2, '0');

    // 拼接成你想要的格式，这里以 YYYY/MM/DD HH:mm:ss 为例
    return `${year}/${month}/${day} ${hours}:${minutes}:${seconds}`;
  };
  return (
    <Card
      onClick={() => {
        // navigateToSearch(data?.id);
        onClick?.();
      }}
    >
      <CardContent className="p-4 flex gap-2 items-start group h-full w-full hover:shadow-md">
        <div className="flex justify-between mb-4">
          <RAGFlowAvatar
            className="w-[32px] h-[32px]"
            avatar={data.avatar}
            name={data.name}
            color={data.color}
          />
        </div>
        <div className="flex flex-col justify-between gap-1 flex-1 h-full w-[calc(100%-50px)]">
          <section className="flex justify-between">
            <section className="flex flex-1 min-w-0 gap-1 items-center">
              <div className="text-base font-bold leading-snug truncate">
                {data.name}
              </div>
              {icon}
            </section>
            {moreDropdown}
          </section>

          <section className="flex flex-col gap-1 mt-1">
            <div className="whitespace-nowrap overflow-hidden text-ellipsis">
              {data.description}
            </div>
            <div className="flex justify-between items-center">
              <p className="text-sm opacity-80 whitespace-nowrap">
                {formatDate(data.update_time)}
              </p>
              {sharedBadge}
            </div>
          </section>
        </div>
      </CardContent>
    </Card>
  );
}

// interface IProps {
//   data: {
//     name: string;
//     description?: string;
//     avatar?: string;
//     update_time?: string | number;
//     color?: string;
//   };
//   onClick?: () => void;
//   moreDropdown: React.ReactNode;
//   sharedBadge?: ReactNode;
//   icon?: React.ReactNode;
//   cardClassName?: string;
// }

// interface IProps {
//   data: {
//     name: string;
//     description?: string;
//     avatar?: string;
//     update_time?: string | number;
//     color?: string;
//   };
//   onClick?: () => void;
//   moreDropdown: React.ReactNode;
//   sharedBadge?: ReactNode;
//   icon?: React.ReactNode;
//   cardClassName?: string;
// }

// export function HomeCard({
//   data,
//   onClick,
//   moreDropdown,
//   sharedBadge,
//   icon,
//   cardClassName,
// }: IProps) {
//   const formatDate = (dateStr?: string | number) => {
//     if (!dateStr) return '';

//     const date = new Date(dateStr);
//     const year = date.getFullYear();
//     const month = String(date.getMonth() + 1).padStart(2, '0');
//     const day = String(date.getDate()).padStart(2, '0');
//     const hours = String(date.getHours()).padStart(2, '0');
//     const minutes = String(date.getMinutes()).padStart(2, '0');
//     const seconds = String(date.getSeconds()).padStart(2, '0');

//     return `${year}/${month}/${day} ${hours}:${minutes}:${seconds}`;
//   };

//   return (
//     <Card
//       className={`
//         group relative h-full cursor-pointer overflow-hidden rounded-none
//         border bg-white/35 backdrop-blur-xl dark:bg-black/20
//         transition-all duration-300
//         shadow-[0_0_18px_currentColor,inset_0_0_28px_rgba(255,255,255,0.12)]
//         hover:-translate-y-1
//         hover:shadow-[0_0_32px_currentColor,inset_0_0_38px_rgba(255,255,255,0.18)]
//         ${cardClassName ?? 'text-purple-400 border-purple-400/50'}
//       `}
//       onClick={() => {
//         onClick?.();
//       }}
//     >
//       {/* 透明玻璃底 */}
//       <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-white/45 via-white/15 to-white/5 dark:from-white/18 dark:via-white/5 dark:to-black/35" />

//       {/* 中心彩色光晕 */}
//       <div className="pointer-events-none absolute inset-[-30%] bg-[radial-gradient(circle_at_35%_25%,currentColor,transparent_36%)] opacity-20 blur-2xl transition-opacity duration-300 group-hover:opacity-35" />

//       {/* 立体内边框 */}
//       <div className="pointer-events-none absolute inset-[3px] border border-current/35 shadow-[inset_0_0_14px_currentColor]" />
//       <div className="pointer-events-none absolute inset-[7px] border border-current/15 shadow-[inset_0_0_10px_currentColor]" />

//       {/* 顶部 / 底部发光线 */}
//       <div className="pointer-events-none absolute left-0 top-0 h-[2px] w-full bg-current opacity-75 shadow-[0_0_14px_currentColor]" />
//       <div className="pointer-events-none absolute bottom-0 left-0 h-[2px] w-full bg-current opacity-40 shadow-[0_0_14px_currentColor]" />

//       {/* 左右电流边 */}
//       <div className="pointer-events-none absolute left-0 top-3 h-12 w-[2px] bg-current opacity-75 shadow-[0_0_16px_currentColor]" />
//       <div className="pointer-events-none absolute bottom-3 right-0 h-12 w-[2px] bg-current opacity-75 shadow-[0_0_16px_currentColor]" />

//       {/* 折线电流裂纹 */}
//       <svg
//         className="pointer-events-none absolute inset-0 h-full w-full opacity-35"
//         viewBox="0 0 300 140"
//         preserveAspectRatio="none"
//       >
//         <path
//           d="M10 28 L58 28 L70 18 L92 42 L128 42 L140 30 L166 58 L210 58 L222 48 L290 48"
//           fill="none"
//           stroke="currentColor"
//           strokeWidth="1.2"
//           strokeLinecap="square"
//           strokeLinejoin="miter"
//           className="drop-shadow-[0_0_6px_currentColor]"
//         />
//         <path
//           d="M24 108 L72 108 L86 94 L112 120 L146 120 L158 104 L190 104 L204 88 L278 88"
//           fill="none"
//           stroke="currentColor"
//           strokeWidth="0.9"
//           strokeLinecap="square"
//           strokeLinejoin="miter"
//           opacity="0.65"
//           className="drop-shadow-[0_0_5px_currentColor]"
//         />
//         <path
//           d="M192 18 L204 34 L218 22 L230 46 L248 46"
//           fill="none"
//           stroke="currentColor"
//           strokeWidth="0.8"
//           strokeLinecap="square"
//           strokeLinejoin="miter"
//           opacity="0.55"
//           className="drop-shadow-[0_0_5px_currentColor]"
//         />
//       </svg>

//       {/* 科技网格纹 */}
//       <div className="pointer-events-none absolute inset-0 opacity-[0.08] bg-[linear-gradient(to_right,currentColor_1px,transparent_1px),linear-gradient(to_bottom,currentColor_1px,transparent_1px)] bg-[size:22px_22px]" />

//       {/* 闪电光点 */}
//       <div className="pointer-events-none absolute left-5 top-4 h-1.5 w-1.5 bg-white shadow-[0_0_12px_4px_currentColor]" />
//       <div className="pointer-events-none absolute right-8 bottom-5 h-1 w-1 bg-white shadow-[0_0_10px_3px_currentColor]" />
//       <div className="pointer-events-none absolute right-12 top-7 h-1 w-1 bg-white/80 shadow-[0_0_10px_3px_currentColor]" />

//       <CardContent className="relative z-10 flex h-full w-full items-start gap-3 p-4">
//         <RAGFlowAvatar
//           className="
//             h-9 w-9 shrink-0 rounded-none
//             ring-1 ring-current/60
//             shadow-[0_0_16px_currentColor]
//           "
//           avatar={data.avatar}
//           name={data.name}
//           color={data.color}
//         />

//         <div className="flex h-full min-w-0 flex-1 flex-col justify-between gap-3">
//           <section className="flex min-w-0 justify-between gap-2">
//             <section className="flex min-w-0 flex-1 items-center gap-1.5">
//               <div className="truncate text-base font-bold leading-snug text-slate-950 drop-shadow-[0_1px_1px_rgba(255,255,255,0.5)] dark:text-white dark:drop-shadow-[0_0_8px_currentColor]">
//                 {data.name}
//               </div>

//               <div className="text-slate-700 dark:text-white/85">
//                 {icon}
//               </div>
//             </section>

//             <div
//               className="shrink-0 text-slate-700 dark:text-white/80"
//               onClick={(event) => {
//                 event.stopPropagation();
//               }}
//             >
//               {moreDropdown}
//             </div>
//           </section>

//           <section className="flex min-w-0 flex-col gap-1">
//             <div className="truncate text-sm text-slate-700 dark:text-white/75">
//               {data.description}
//             </div>

//             <div className="flex items-center justify-between gap-2">
//               <p className="truncate whitespace-nowrap text-xs text-slate-500 dark:text-white/50">
//                 {formatDate(data.update_time)}
//               </p>

//               <div className="shrink-0 text-slate-700 dark:text-white/80">
//                 {sharedBadge}
//               </div>
//             </div>
//           </section>
//         </div>
//       </CardContent>
//     </Card>
//   );
// }
