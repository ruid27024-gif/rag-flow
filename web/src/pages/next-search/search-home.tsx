import { Input } from '@/components/originui/input';
import message from '@/components/ui/message';
import { IUserInfo } from '@/interfaces/database/user-setting';
import { Search } from 'lucide-react';
import { Dispatch, SetStateAction } from 'react';
import { useTranslation } from 'react-i18next';
import './index.less';

export default function SearchPage({
  isSearching,
  setIsSearching,
  searchText,
  setSearchText,
  userInfo,
  canSearch,
}: {
  isSearching: boolean;
  setIsSearching: Dispatch<SetStateAction<boolean>>;
  searchText: string;
  setSearchText: Dispatch<SetStateAction<string>>;
  userInfo?: IUserInfo;
  canSearch?: boolean;
}) {
  // const { data: userInfo } = useFetchUserInfo();
  const { t } = useTranslation();
  return (
    // <section className="relative w-full flex transition-all justify-center items-center mt-[15vh]">
    //   <div className="relative z-10 px-8 pt-8 flex  text-transparent flex-col justify-center items-center w-[780px]">
    //     <h1
    //       className={cn(
    //         'text-4xl font-bold bg-gradient-to-l from-[#40EBE3] to-[#4A51FF] bg-clip-text',
    //       )}
    //     >
    //       恒丰纸业
    //     </h1>

    //     <div className="rounded-lg  text-primary text-xl sticky flex justify-center w-full transform scale-100 mt-8 p-6 h-[240px] border">
    //       {!isSearching && <Spotlight className="z-0" />}
    //       <div className="flex flex-col justify-center items-center  w-2/3">
    //         {!isSearching && (
    //           <>
    //             <p className="mb-4 transition-opacity">知识库检索</p>
    //             <p className="mb-10 transition-opacity">
    //               {userInfo && (
    //                 <>
    //                   {t('search.welcomeBack')}, {userInfo.nickname}
    //                 </>
    //               )}
    //             </p>
    //           </>
    //         )}

    //         <div className="relative w-full ">
    //           <Input
    //             placeholder={t('search.searchGreeting')}
    //             className="w-full rounded-full py-7 px-4 pr-10 text-text-primary text-lg bg-bg-base delay-700"
    //             value={searchText}
    //             onKeyUp={(e) => {
    //               if (e.key === 'Enter') {
    //                 if (canSearch === false) {
    //                   message.warning(t('search.chooseDataset'));
    //                   return;
    //                 }
    //                 setIsSearching(!isSearching);
    //               }
    //             }}
    //             onChange={(e) => {
    //               if (canSearch === false) {
    //                 message.warning(t('search.chooseDataset'));
    //                 return;
    //               }
    //               setSearchText(e.target.value || '');
    //             }}
    //           />
    //           <button
    //             type="button"
    //             className="absolute right-2 top-1/2 -translate-y-1/2 transform rounded-full bg-text-primary p-2 text-bg-base shadow w-12"
    //             onClick={() => {
    //               if (canSearch === false) {
    //                 message.warning(t('search.chooseDataset'));
    //                 return;
    //               }
    //               setIsSearching(!isSearching);
    //             }}
    //           >
    //             <Search size={22} className="m-auto" />
    //           </button>
    //         </div>
    //       </div>
    //     </div>
    //   </div>
    // </section>

    <section className="relative w-full flex transition-all justify-center items-center mt-[15vh] overflow-visible">
      {/* 背景特效层：大面积柔和光场 */}
      {/* 干净网格背景层 */}
      <div className="pointer-events-none absolute inset-x-0 -top-16 -bottom-[260px] z-0 overflow-hidden">
        {/* 基础背景 */}
        <div className="absolute inset-0 bg-bg-base" />

        {/* 主网格 */}
        <div
          className="
      absolute inset-0 opacity-[0.18]
      bg-[linear-gradient(to_right,rgba(100,116,139,0.22)_1px,transparent_1px),linear-gradient(to_bottom,rgba(100,116,139,0.22)_1px,transparent_1px)]
      bg-[size:40px_40px]
    "
        />

        {/* 大网格，增加层次但很淡 */}
        <div
          className="
      absolute inset-0 opacity-[0.08]
      bg-[linear-gradient(to_right,rgba(37,99,235,0.28)_1px,transparent_1px),linear-gradient(to_bottom,rgba(37,99,235,0.28)_1px,transparent_1px)]
      bg-[size:160px_160px]
    "
        />

        {/* 中心区域淡淡提亮 */}
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(64,235,227,0.08)_0%,rgba(64,235,227,0.035)_34%,transparent_68%)]" />

        {/* 顶部和底部渐隐，避免断层 */}
        <div className="absolute inset-x-0 top-0 h-36 bg-gradient-to-b from-bg-base via-bg-base/70 to-transparent" />
        <div className="absolute inset-x-0 bottom-0 h-48 bg-gradient-to-t from-bg-base via-bg-base/70 to-transparent" />
      </div>

      <div className="relative z-10 px-8 pt-8 flex flex-col justify-center items-center w-[780px]">
        <img
          src="/hengyue.png"
          alt="恒悦"
          className="h-16 w-auto object-contain"
        />

        {!isSearching && (
          <>
            <p className="mt-8 mb-4 text-primary text-xl transition-opacity">
              知识库检索
            </p>

            <p className="mb-10 min-h-[28px] text-primary text-xl transition-opacity">
              {userInfo && (
                <>
                  {t('search.welcomeBack')}, {userInfo.nickname}
                </>
              )}
            </p>
          </>
        )}

        <div className="relative w-full max-w-[680px]">
          <div
            className="
            relative h-14 w-full
            rounded-full
            border border-border/25
            bg-bg-base
            shadow-[0_8px_24px_rgba(0,0,0,0.05)]
            transition-all duration-300
            hover:border-[#40EBE3]/25
            focus-within:border-[#4A51FF]/30
            focus-within:shadow-[0_10px_28px_rgba(64,235,227,0.08)]
          "
          >
            <Input
              placeholder={t('search.searchGreeting')}
              className="
            h-14 w-full
            rounded-full border-none bg-transparent
            pl-6 pr-20
            py-0 leading-[56px]
            text-text-primary text-lg
            shadow-none
            placeholder:text-text-secondary/40
            focus-visible:ring-0 focus-visible:ring-offset-0
          "
              value={searchText}
              onKeyUp={(e) => {
                if (e.key === 'Enter') {
                  if (canSearch === false) {
                    message.warning(t('search.chooseDataset'));
                    return;
                  }
                  setIsSearching(!isSearching);
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

            <button
              type="button"
              className="
            absolute right-1.5 top-1/2
            flex h-11 w-11 -translate-y-1/2 items-center justify-center
            rounded-full
            
            bg-gradient-to-r from-[#4A51FF] to-[#40EBE3]
            text-white
            shadow-[0_8px_24px_rgba(74,81,255,0.25)]
            transition-all duration-300
            hover:scale-105 hover:shadow-[0_10px_30px_rgba(64,235,227,0.35)]
            active:scale-95
          "
              onClick={() => {
                if (canSearch === false) {
                  message.warning(t('search.chooseDataset'));
                  return;
                }
                setIsSearching(!isSearching);
              }}
            >
              <Search size={22} />
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}
