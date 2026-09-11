// import { Input } from '@/components/originui/input';
// import message from '@/components/ui/message';
// import { IUserInfo } from '@/interfaces/database/user-setting';
// import { cn } from '@/lib/utils';
// import { Search } from 'lucide-react';
// import { Dispatch, SetStateAction } from 'react';
// import { useTranslation } from 'react-i18next';
// import './index.less';

// export default function SearchPage({
//   isSearching,
//   setIsSearching,
//   searchText,
//   setSearchText,
//   userInfo,
//   canSearch,
// }: {
//   isSearching: boolean;
//   setIsSearching: Dispatch<SetStateAction<boolean>>;
//   searchText: string;
//   setSearchText: Dispatch<SetStateAction<string>>;
//   userInfo?: IUserInfo;
//   canSearch?: boolean;
// }) {
//   // const { data: userInfo } = useFetchUserInfo();
//   const { t } = useTranslation();
//   return (

//     <section className="relative w-full flex transition-all justify-center items-center mt-[15vh] overflow-visible">
//       {/* 背景特效层：大面积柔和光场 */}
//       {/* 干净网格背景层 */}
//       <div className="pointer-events-none absolute inset-x-0 -top-16 -bottom-[260px] z-0 overflow-hidden">
//         {/* 基础背景 */}
//         <div className="absolute inset-0 bg-bg-base" />

//         {/* 主网格 */}
//         <div
//           className="
//       absolute inset-0 opacity-[0.18]
//       bg-[linear-gradient(to_right,rgba(100,116,139,0.22)_1px,transparent_1px),linear-gradient(to_bottom,rgba(100,116,139,0.22)_1px,transparent_1px)]
//       bg-[size:40px_40px]
//     "
//         />

//         {/* 大网格，增加层次但很淡 */}
//         <div
//           className="
//       absolute inset-0 opacity-[0.08]
//       bg-[linear-gradient(to_right,rgba(37,99,235,0.28)_1px,transparent_1px),linear-gradient(to_bottom,rgba(37,99,235,0.28)_1px,transparent_1px)]
//       bg-[size:160px_160px]
//     "
//         />

//         {/* 中心区域淡淡提亮 */}
//         <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(64,235,227,0.08)_0%,rgba(64,235,227,0.035)_34%,transparent_68%)]" />

//         {/* 顶部和底部渐隐，避免断层 */}
//         <div className="absolute inset-x-0 top-0 h-36 bg-gradient-to-b from-bg-base via-bg-base/70 to-transparent" />
//         <div className="absolute inset-x-0 bottom-0 h-48 bg-gradient-to-t from-bg-base via-bg-base/70 to-transparent" />
//       </div>

//       <div className="relative z-10 px-8 pt-8 flex flex-col justify-center items-center w-[780px]">
//         <h1
//           className={cn(
//             'text-4xl font-bold bg-gradient-to-l from-[#40EBE3] to-[#4A51FF] bg-clip-text text-transparent',
//           )}
//         >
//           恒丰纸业
//         </h1>

//         {!isSearching && (
//           <>
//             <p className="mt-8 mb-4 text-primary text-xl transition-opacity">
//               知识库检索
//             </p>

//             <p className="mb-10 min-h-[28px] text-primary text-xl transition-opacity">
//               {userInfo && (
//                 <>
//                   {t('search.welcomeBack')}, {userInfo.nickname}
//                 </>
//               )}
//             </p>
//           </>
//         )}

//         <div className="relative w-full max-w-[680px]">
//           <div
//             className="
//             relative h-14 w-full
//             rounded-full
//             border border-border/25
//             bg-bg-base
//             shadow-[0_8px_24px_rgba(0,0,0,0.05)]
//             transition-all duration-300
//             hover:border-[#40EBE3]/25
//             focus-within:border-[#4A51FF]/30
//             focus-within:shadow-[0_10px_28px_rgba(64,235,227,0.08)]
//           "
//           >
//             <Input
//               placeholder={t('search.searchGreeting')}
//               className="
//             h-14 w-full
//             rounded-full border-none bg-transparent
//             pl-6 pr-20
//             py-0 leading-[56px]
//             text-text-primary text-lg
//             shadow-none
//             placeholder:text-text-secondary/40
//             focus-visible:ring-0 focus-visible:ring-offset-0
//           "
//               value={searchText}
//               onKeyUp={(e) => {
//                 if (e.key === 'Enter') {
//                   if (canSearch === false) {
//                     message.warning(t('search.chooseDataset'));
//                     return;
//                   }
//                   setIsSearching(!isSearching);
//                 }
//               }}
//               onChange={(e) => {
//                 if (canSearch === false) {
//                   message.warning(t('search.chooseDataset'));
//                   return;
//                 }
//                 setSearchText(e.target.value || '');
//               }}
//             />

//             <button
//               type="button"
//               className="
//             absolute right-1.5 top-1/2
//             flex h-11 w-11 -translate-y-1/2 items-center justify-center
//             rounded-full

//             bg-gradient-to-r from-[#4A51FF] to-[#40EBE3]
//             text-white
//             shadow-[0_8px_24px_rgba(74,81,255,0.25)]
//             transition-all duration-300
//             hover:scale-105 hover:shadow-[0_10px_30px_rgba(64,235,227,0.35)]
//             active:scale-95
//           "
//               onClick={() => {
//                 if (canSearch === false) {
//                   message.warning(t('search.chooseDataset'));
//                   return;
//                 }
//                 setIsSearching(!isSearching);
//               }}
//             >
//               <Search size={22} />
//             </button>
//           </div>
//         </div>
//       </div>
//     </section>
//   );
// }
import HengfengLogo from '@/HengfengLogo'; // 根据实际路径调整
import message from '@/components/ui/message';
import { IUserInfo } from '@/interfaces/database/user-setting';
import { cn } from '@/lib/utils';
import { Search } from 'lucide-react';
import { Dispatch, SetStateAction } from 'react';
import { useTranslation } from 'react-i18next';
import './index.less';

import { Heading1, Layers3, Orbit } from 'lucide-react';

type SearchMode = 'mode1' | 'mode2' | 'mode3';

export default function SearchHome({
  isSearching,
  setIsSearching,
  searchText,
  setSearchText,
  userInfo,
  canSearch,
  currentMode,
  savingMode,
  onModeChange,
}: {
  isSearching: boolean;
  setIsSearching: Dispatch<SetStateAction<boolean>>;
  searchText: string;
  setSearchText: Dispatch<SetStateAction<string>>;
  userInfo?: IUserInfo;
  canSearch?: boolean;
  currentMode: SearchMode;
  savingMode: boolean;
  onModeChange: (mode: SearchMode) => void;
}) {
  const { t } = useTranslation();

  const modeOptions = [
    {
      value: 'mode1' as const,
      label: '标题检索',
      shortLabel: '标题检索',
      icon: Heading1,
    },
    {
      value: 'mode2' as const,
      label: '内容检索',
      shortLabel: '内容检索',
      icon: Orbit,
    },
    {
      value: 'mode3' as const,
      label: '标题 + 内容检索',
      shortLabel: '混合检索',
      icon: Layers3,
    },
  ];

  const currentModeItem =
    modeOptions.find((item) => item.value === currentMode) || modeOptions[2];

  const handleSearch = () => {
    if (canSearch === false) {
      message.warning(t('search.chooseDataset'));
      return;
    }
    setIsSearching((prev) => !prev);
  };

  return (
    <section className="relative mt-[15vh] flex w-full items-center justify-center overflow-visible transition-all">
      {/* 背景 */}
      <div className="pointer-events-none absolute inset-x-0 -top-16 -bottom-[260px] z-0 overflow-hidden">
        <div className="absolute inset-0 bg-bg-base" />

        <div
          className="
            absolute inset-0 opacity-[0.18]
            bg-[linear-gradient(to_right,rgba(100,116,139,0.22)_1px,transparent_1px),linear-gradient(to_bottom,rgba(100,116,139,0.22)_1px,transparent_1px)]
            bg-[size:40px_40px]
          "
        />

        <div
          className="
            absolute inset-0 opacity-[0.08]
            bg-[linear-gradient(to_right,rgba(37,99,235,0.28)_1px,transparent_1px),linear-gradient(to_bottom,rgba(37,99,235,0.28)_1px,transparent_1px)]
            bg-[size:160px_160px]
          "
        />

        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(64,235,227,0.08)_0%,rgba(64,235,227,0.035)_34%,transparent_68%)]" />

        <div className="absolute inset-x-0 top-0 h-36 bg-gradient-to-b from-bg-base via-bg-base/70 to-transparent" />
        <div className="absolute inset-x-0 bottom-0 h-48 bg-gradient-to-t from-bg-base via-bg-base/70 to-transparent" />
      </div>

      <div className="relative z-10 flex w-[780px] flex-col items-center justify-center px-8 pt-20">
        {/* 标题 */}
        {/* <h1 className="bg-gradient-to-l from-[#40EBE3] to-[#4A51FF] bg-clip-text text-4xl font-bold text-transparent"> */}
        <h1 className="flex items-center gap-1 text-4xl font-bold">
          <HengfengLogo size={48} />
          <span className="text-[#007A32]">恒丰纸业</span>
        </h1>

        {/* 模式切换器 */}
        {/* 模式切换器 */}
        <div className="mt-6 inline-flex items-center rounded-full border border-slate-200 bg-white p-1 shadow-sm dark:border-slate-700 dark:bg-slate-900">
          {modeOptions.map((item) => {
            const active = currentMode === item.value;
            const Icon = item.icon;

            return (
              <button
                key={item.value}
                type="button"
                disabled={savingMode}
                onClick={() => onModeChange(item.value)}
                className={cn(
                  'flex items-center gap-1.5 rounded-full px-4 py-2 text-sm transition-all duration-300',
                  active
                    ? `
                bg-emerald-50 text-[#006227] shadow-sm
                dark:bg-[#00C853]/15 dark:text-emerald-300
              `
                    : `
                text-slate-600 hover:bg-emerald-50 hover:text-[#006227]
                dark:text-slate-300 dark:hover:bg-emerald-950/40
                dark:hover:text-emerald-300
              `,
                  savingMode && 'cursor-not-allowed opacity-70',
                )}
              >
                <Icon size={14} />
                <span>{item.shortLabel}</span>
              </button>
            );
          })}
        </div>

        {/* 搜索框 */}
        <div className="relative mt-8 w-full max-w-[720px]">
          <div
            className="
      relative w-full rounded-xl border
      border-slate-200 bg-white
      px-5 py-4 shadow-lg
      transition-all duration-300

      hover:border-slate-300
      focus-within:border-slate-400
      focus-within:shadow-[0_10px_28px_rgba(15,23,42,0.08)]

      dark:border-slate-700
      dark:bg-zinc-900
      dark:shadow-none
      dark:hover:border-slate-600
      dark:focus-within:border-slate-500
    "
          >
            {/* 多行输入框 */}
            <textarea
              placeholder={t('search.searchGreeting')}
              value={searchText}
              rows={3}
              className="
        w-full resize-none
        border-none bg-transparent
        px-0 py-0
        text-base text-slate-900
        shadow-none outline-none
        placeholder:text-gray-400
        focus:ring-0
        dark:text-white
        dark:placeholder:text-slate-500
      "
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSearch();
                }
              }}
              onChange={(e) => {
                if (canSearch === false) {
                  message.warning(t('search.chooseDataset'));
                  return;
                }

                setSearchText(e.target.value || '');
              }}
            />

            {/* 底部一行：左侧标签 + 右侧按钮 */}
            <div className="mt-2 flex items-center justify-between gap-3">
              <div
                className="
          inline-flex h-9 items-center gap-1.5
          rounded-full border
          border-emerald-200 bg-emerald-50
          px-3 text-xs font-medium text-[#006227]
          shadow-sm
          dark:border-[#00C853]/30
          dark:bg-[#00C853]/10
          dark:text-emerald-300
        "
              >
                <currentModeItem.icon size={13} />
                <span>{currentModeItem.label}</span>
              </div>

              <button
                type="button"
                className="
          flex h-9 w-9 items-center justify-center
          rounded-full
          bg-gradient-to-r from-[#006227] to-[#00C853]
          text-white
          shadow-[0_8px_24px_rgba(0,98,39,0.25)]
          transition-all duration-300
          hover:scale-105
          hover:shadow-[0_10px_30px_rgba(0,200,83,0.35)]
          active:scale-95
        "
                onClick={handleSearch}
                aria-label="搜索"
              >
                <Search size={18} />
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
