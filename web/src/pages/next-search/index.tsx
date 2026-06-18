import { useFetchTokenListBeforeOtherStep } from '@/components/embed-dialog/use-show-embed-dialog';
import { PageHeader } from '@/components/page-header';
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from '@/components/ui/breadcrumb';
import { Button } from '@/components/ui/button';
import { SharedFrom } from '@/constants/chat';
import { useNavigatePage } from '@/hooks/logic-hooks/navigate-hooks';
import {
  useFetchTenantInfo,
  useFetchUserInfo,
} from '@/hooks/use-user-setting-request';
import { ChevronLeft, Settings } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  ISearchAppDetailProps,
  useFetchSearchDetail,
} from '../next-searches/hooks';
import EmbedAppModal from './embed-app-modal';
import { useCheckSettings } from './hooks';
import './index.less';
import SearchHome from './search-home';
import { SearchSetting } from './search-setting';
import SearchingPage from './searching';

// export default function SearchPage() {
//   const { navigateToSearchList } = useNavigatePage();
//   // 是否正在搜索
//   const [isSearching, setIsSearching] = useState(false);
//   // 获取搜索应用的详情
//   const { data: SearchData } = useFetchSearchDetail();
//   const { beta, handleOperate } = useFetchTokenListBeforeOtherStep();

//   // 是否在右侧渲染侧边栏
//   const [openSetting, setOpenSetting] = useState(false);

//   const [openEmbed, setOpenEmbed] = useState(false);
//   const [searchText, setSearchText] = useState('');
//   const { data: tenantInfo } = useFetchTenantInfo();
//   const { data: userInfo } = useFetchUserInfo();
//   const tenantId = tenantInfo.tenant_id;
//   const { t } = useTranslation();
//   const { openSetting: checkOpenSetting } = useCheckSettings(
//     SearchData as ISearchAppDetailProps,
//   );
//   useEffect(() => {
//     setOpenSetting(checkOpenSetting);
//   }, [checkOpenSetting]);

//   // 搜索情况自动关闭右侧设置栏目
//   useEffect(() => {
//     if (isSearching) {
//       setOpenSetting(false);
//     }
//   }, [isSearching]);

//   return (
//     <section>
//       <PageHeader>
//         <Breadcrumb>
//           <BreadcrumbList>
//             <BreadcrumbItem>
//               <BreadcrumbLink onClick={navigateToSearchList}>
//                 <span
//                   className="
//                   text-lg font-bold
//                   bg-gradient-to-r from-blue-600 to-cyan-500
//                   bg-clip-text text-transparent
//                   group-hover:text-slate-900 dark:group-hover:text-white
//                   transition-all duration-300
//                   cursor-pointer
//                 "
//                 >
//                   {t('header.search')}
//                 </span>
//               </BreadcrumbLink>
//             </BreadcrumbItem>
//             <BreadcrumbSeparator className="translate-y-[7px]" />
//             <BreadcrumbItem>
//               <BreadcrumbPage className="w-28 whitespace-nowrap text-ellipsis overflow-hidden translate-y-[3px] text-gray-400 dark:text-gray-500">
//                 {SearchData?.name}
//               </BreadcrumbPage>
//             </BreadcrumbItem>
//           </BreadcrumbList>
//         </Breadcrumb>
//       </PageHeader>
//       <div className="flex gap-3 w-full bg-bg-base">
//         <div className="flex-1">
//           {!isSearching && (
//             <div className="animate-fade-in-down">
//               <SearchHome
//                 setIsSearching={setIsSearching}
//                 isSearching={isSearching}
//                 searchText={searchText}
//                 setSearchText={setSearchText}
//                 userInfo={userInfo}
//                 canSearch={!checkOpenSetting}
//               />
//             </div>
//           )}
//           {isSearching && (
//             <div className="animate-fade-in-up">
//               <SearchingPage
//                 setIsSearching={setIsSearching}
//                 searchText={searchText}
//                 setSearchText={setSearchText}
//                 data={SearchData as ISearchAppDetailProps}
//               />
//             </div>
//           )}
//         </div>
//         {openSetting && (
//           <SearchSetting
//             className="mt-20 mr-2"
//             open={openSetting}
//             setOpen={setOpenSetting}
//             data={SearchData as ISearchAppDetailProps}
//           />
//         )}
//         {
//           <EmbedAppModal
//             open={openEmbed}
//             setOpen={setOpenEmbed}
//             url="/next-search/share"
//             token={SearchData?.id as string}
//             from={SharedFrom.Search}
//             tenantId={tenantId}
//             beta={beta}
//           />
//         }
//         {
//           // <EmbedDialog
//           //   visible={openEmbed}
//           //   hideModal={setOpenEmbed}
//           //   token={SearchData?.id as string}
//           //   from={SharedFrom.Search}
//           //   beta={beta}
//           //   isAgent={false}
//           // ></EmbedDialog>
//         }
//       </div>
//       <div className="absolute right-5 top-4 ">
//         {/* <Button
//           className="bg-text-primary  text-bg-base border-b-accent-primary border-b-2"
//           onClick={() => {
//             handleOperate().then((res) => {
//               console.log(res, 'res');
//               if (res) {
//                 setOpenEmbed(!openEmbed);
//               }
//             });
//           }}
//         >
//           <Send />
//           <div>{t('search.embedApp')}</div>
//         </Button> */}
//       </div>
//       {!isSearching && (
//         <div className="absolute left-5 bottom-12 ">
//           <Button
//             variant="transparent"
//             className="bg-bg-card"
//             onClick={() => setOpenSetting(!openSetting)}
//           >
//             <Settings className="text-text-secondary" />
//             <div className="text-text-secondary">
//               {t('search.searchSettings')}
//             </div>
//           </Button>
//         </div>
//       )}
//     </section>
//   );
// }

import { useCallback, useRef } from 'react';
import { useParams } from 'react-router-dom';

export default function SearchPage() {
  const { navigateToSearchList } = useNavigatePage();
  const { id: searchId } = useParams();

  const [isSearching, setIsSearching] = useState(false);
  const { data: SearchData } = useFetchSearchDetail();
  const { beta, handleOperate } = useFetchTokenListBeforeOtherStep();

  const [openSetting, setOpenSetting] = useState(false);
  const [openEmbed, setOpenEmbed] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [searchMessages, setSearchMessages] = useState<any[]>([]);
  const [historyCollapsed, setHistoryCollapsed] = useState(true);

  const lastSavedTextRef = useRef('');

  const { data: tenantInfo } = useFetchTenantInfo();
  const { data: userInfo } = useFetchUserInfo();
  const tenantId = tenantInfo.tenant_id;
  const { t } = useTranslation();

  const { openSetting: checkOpenSetting } = useCheckSettings(
    SearchData as ISearchAppDetailProps,
  );

  const deleteSearchMessage = useCallback(async (messageId: string) => {
    if (!messageId) return;

    try {
      const res = await fetch('/v1/search_keep/message/delete', {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          id: messageId,
        }),
      });

      const data = await res.json();

      if (data.code === 0) {
        setSearchMessages((messages) =>
          messages.filter((item) => item.id !== messageId),
        );
      }
    } catch (error) {
      console.error('delete search message failed:', error);
    }
  }, []);

  const fetchSearchMessages = useCallback(async () => {
    if (!searchId) return;

    try {
      const res = await fetch('/v1/search_keep/messages', {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          search_id: searchId,
        }),
      });

      const data = await res.json();

      if (data.code === 0) {
        setSearchMessages(data.data || []);
      }
    } catch (error) {
      console.error('fetch search messages failed:', error);
    }
  }, [searchId]);

  const saveSearchMessage = useCallback(async () => {
    const content = searchText.trim();

    if (!searchId || !content) return;
    if (lastSavedTextRef.current === content) return;

    lastSavedTextRef.current = content;

    try {
      const res = await fetch('/v1/search_keep/message', {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          search_id: searchId,
          content,
        }),
      });

      const data = await res.json();

      if (data.code === 0) {
        fetchSearchMessages();
      }
    } catch (error) {
      console.error('save search message failed:', error);
    }
  }, [searchId, searchText, fetchSearchMessages]);

  useEffect(() => {
    setOpenSetting(checkOpenSetting);
  }, [checkOpenSetting]);

  useEffect(() => {
    fetchSearchMessages();
  }, [fetchSearchMessages]);

  useEffect(() => {
    const handleSearchMessageSaved = (event: Event) => {
      const customEvent = event as CustomEvent<{ content: string }>;
      const content = customEvent.detail?.content;

      if (content) {
        setSearchMessages((messages) => [
          {
            id: `${Date.now()}`,
            content,
            create_time: Date.now(),
          },
          ...messages,
        ]);
      }

      fetchSearchMessages();
    };

    window.addEventListener(
      'search-message-saved',
      handleSearchMessageSaved as EventListener,
    );

    return () => {
      window.removeEventListener(
        'search-message-saved',
        handleSearchMessageSaved as EventListener,
      );
    };
  }, [fetchSearchMessages]);

  useEffect(() => {
    if (isSearching) {
      setOpenSetting(false);
      saveSearchMessage();
    }
  }, [isSearching, saveSearchMessage]);
  const latestSearchId = searchMessages[0]?.id;
  const [selectedSearchId, setSelectedSearchId] = useState<
    string | number | null
  >(null);
  useEffect(() => {
    if (searchMessages.length > 0) {
      setSelectedSearchId(searchMessages[0].id);
    }
  }, [searchMessages]);

  return (
    <section className="relative h-full">
      <PageHeader>
        <Breadcrumb>
          <BreadcrumbList>
            <BreadcrumbItem>
              <BreadcrumbLink onClick={navigateToSearchList}>
                <span
                  className="
                    ml-4
                    text-lg font-bold
                    bg-gradient-to-r from-blue-600 to-cyan-500
                    bg-clip-text text-transparent
                    group-hover:text-slate-900 dark:group-hover:text-white
                    transition-all duration-300
                    cursor-pointer
                  "
                >
                  {t('header.search')}
                </span>
              </BreadcrumbLink>
            </BreadcrumbItem>

            <BreadcrumbSeparator className="translate-y-[7px]" />

            <BreadcrumbItem>
              <BreadcrumbPage className="w-28 whitespace-nowrap text-ellipsis overflow-hidden translate-y-[3px] text-gray-400 dark:text-gray-500">
                {SearchData?.name}
              </BreadcrumbPage>
            </BreadcrumbItem>
          </BreadcrumbList>
        </Breadcrumb>
      </PageHeader>

      <div className="flex gap-3 w-full bg-bg-base">
        <aside
          className={`
    shrink-0 h-[calc(100vh-80px)] overflow-hidden
    transition-all duration-300 ease-in-out border-r border-slate-200/70 dark:border-slate-700/70
    ${historyCollapsed ? 'w-0 border-r-0' : 'w-[260px] px-3 py-4'}
  `}
        >
          {/* 展开状态下的内容 */}
          <div
            className={`h-full flex flex-col transition-opacity duration-200 ${
              historyCollapsed ? 'opacity-0 pointer-events-none' : 'opacity-100'
            }`}
          >
            {/* 头部 */}
            <div className="mb-4 flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm font-semibold text-text-primary">
                <div className="h-6 w-6 shrink-0">
                  <img
                    src="/idle-3.png"
                    alt="Logo"
                    className="h-full w-full object-cover"
                  />
                </div>

                <span>搜索记录</span>
              </div>

              <button
                type="button"
                onClick={() => setHistoryCollapsed(true)}
                className="rounded-md p-1 text-text-secondary hover:bg-slate-100 hover:text-text-primary dark:hover:bg-slate-800 transition-colors"
                title="折叠搜索记录"
              >
                <ChevronLeft size={16} />
              </button>
            </div>

            {/* 列表区域 */}
            <div className="flex-1 space-y-1 overflow-y-auto pr-1 scrollbar-thin">
              {searchMessages.length === 0 ? (
                <div className="flex h-full items-center justify-center text-xs text-text-secondary/60">
                  暂无搜索记录
                </div>
              ) : (
                searchMessages.map((item: any) => {
                  const isSelected = selectedSearchId === item.id;

                  return (
                    <div
                      key={item.id}
                      className={`
                group relative flex items-center
                rounded-lg px-3 py-2.5
                text-sm
                transition-all duration-200
                hover:bg-slate-100 hover:text-text-primary
                dark:hover:bg-slate-800
                ${
                  isSelected
                    ? 'bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-blue-300'
                    : 'text-text-secondary'
                }
              `}
                    >
                      {/* 搜索内容按钮 */}
                      <button
                        type="button"
                        title={item.content}
                        onClick={() => {
                          setSelectedSearchId(item.id);
                          setSearchText(item.content);
                          setIsSearching(false);
                        }}
                        className="min-w-0 flex-1 truncate text-left focus:outline-none"
                      >
                        {item.content}
                      </button>

                      {/* 删除按钮：Hover 列表项时平滑浮现 */}
                      <button
                        type="button"
                        title="删除"
                        onClick={(e) => {
                          e.stopPropagation();

                          if (window.confirm('确定要删除这条搜索记录吗？')) {
                            deleteSearchMessage(item.id);

                            if (selectedSearchId === item.id) {
                              setSelectedSearchId(null);
                            }
                          }
                        }}
                        className={`
                  absolute right-1 flex h-6 w-6 shrink-0 items-center justify-center
                  rounded-full text-xs
                  transition-all duration-200
                  hover:bg-red-50 hover:text-red-500
                  dark:hover:bg-red-900/30 dark:hover:text-red-400
                  ${
                    isSelected
                      ? 'opacity-100 text-text-secondary'
                      : 'opacity-0 text-text-secondary group-hover:opacity-100'
                  }
                `}
                      >
                        ×
                      </button>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </aside>

        {historyCollapsed && (
          <button
            type="button"
            onClick={() => setHistoryCollapsed(false)}
            className="
      absolute left-0 top-1/2 z-10 -translate-y-1/2
      h-20 w-10
      overflow-hidden
      transition-all duration-300 ease-in-out
      hover:w-20
      group
    "
            title="展开搜索记录"
          >
            <img
              src="/idle-4.png"
              alt="展开搜索记录"
              className="
        h-20 w-20 max-w-none object-contain drop-shadow-md
        -translate-x-10
        transition-transform duration-300 ease-in-out
        group-hover:translate-x-0
      "
            />
          </button>
        )}

        {/* {historyCollapsed && (
  <button
    type="button"
    onClick={() => setHistoryCollapsed(false)}
    className="
      absolute left-0 top-1/2 z-10 -translate-y-1/2 flex items-center 
      h-10 w-10 rounded-r-full bg-white/80 backdrop-blur-sm shadow-md 
      transition-all duration-300 ease-in-out
      hover:w-28 hover:bg-blue-50 dark:bg-slate-800/80 dark:hover:bg-blue-900/50
      group
    "
    title="展开搜索记录"
  >
    
    <div className="h-9 w-9 shrink-0 overflow-hidden">
      <img 
        src="/48@4x.png" 
        alt="历史记录" 
        className="h-full w-full object-contain" // 使用 object-contain 保持抠图原始比例
      />
    </div>

    
    <div className="flex items-center gap-1 whitespace-nowrap opacity-0 transition-opacity duration-300 group-hover:opacity-100">
      <span className="text-xs font-medium text-slate-600 dark:text-slate-200">
        搜索记录
      </span>
      <ChevronRight size={14} className="text-blue-600 dark:text-blue-400" />
    </div>
  </button>
)} */}

        <div className="min-w-0 flex-1">
          {!isSearching && (
            <div className="animate-fade-in-down">
              <SearchHome
                setIsSearching={setIsSearching}
                isSearching={isSearching}
                searchText={searchText}
                setSearchText={setSearchText}
                userInfo={userInfo}
                canSearch={!checkOpenSetting}
              />
            </div>
          )}

          {isSearching && (
            <div className="animate-fade-in-up">
              <SearchingPage
                setIsSearching={setIsSearching}
                searchText={searchText}
                setSearchText={setSearchText}
                data={SearchData as ISearchAppDetailProps}
              />
            </div>
          )}
        </div>

        {openSetting && (
          <SearchSetting
            className="mt-20 mr-2"
            open={openSetting}
            setOpen={setOpenSetting}
            data={SearchData as ISearchAppDetailProps}
          />
        )}

        <EmbedAppModal
          open={openEmbed}
          setOpen={setOpenEmbed}
          url="/next-search/share"
          token={SearchData?.id as string}
          from={SharedFrom.Search}
          tenantId={tenantId}
          beta={beta}
        />
      </div>

      <div className="absolute right-5 top-4">{/* 原 embed button */}</div>

      {!isSearching && (
        <div
          className={`
            absolute bottom-12 transition-all duration-300
            ${historyCollapsed ? 'left-5' : 'left-[280px]'}
          `}
        >
          <Button
            variant="transparent"
            className="bg-bg-card"
            onClick={() => setOpenSetting(!openSetting)}
          >
            <Settings className="text-text-secondary" />
            <div className="text-text-secondary">
              {t('search.searchSettings')}
            </div>
          </Button>
        </div>
      )}
    </section>
  );
}
