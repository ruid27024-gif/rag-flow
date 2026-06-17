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
import { ChevronLeft, ChevronRight, History, Settings } from 'lucide-react';
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
  const [historyCollapsed, setHistoryCollapsed] = useState(false);

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
    shrink-0
    h-[calc(100vh-80px)]
    overflow-y-auto
    transition-all duration-300
    ${
      historyCollapsed
        ? 'w-[24px] px-0 border-r-0'
        : 'w-[260px] px-3 py-4 border-r border-slate-200/70 dark:border-slate-700/70'
    }
  `}
        >
          {historyCollapsed ? (
            <button
              type="button"
              onClick={() => setHistoryCollapsed(false)}
              className="mt-4 flex h-8 w-4 items-center justify-center text-text-secondary/30 hover:text-text-primary transition-colors"
              title="展开搜索记录"
            >
              <ChevronRight size={16} /> {/* 向右的箭头图标 */}
            </button>
          ) : (
            <>
              <div className="mb-3 flex items-center justify-between">
                <div className="flex items-center gap-1 text-sm font-semibold text-text-primary">
                  <History size={16} /> {/* 历史记录图标 */}
                  <span>搜索记录</span>
                </div>

                <button
                  type="button"
                  onClick={() => setHistoryCollapsed(true)}
                  className="rounded-md p-1 text-text-secondary hover:text-text-primary transition-colors"
                  title="折叠搜索记录"
                >
                  <ChevronLeft size={16} /> {/* 向左的箭头图标 */}
                </button>
              </div>

              <div className="space-y-2">
                {searchMessages.length === 0 && (
                  <div className="px-2 py-3 text-xs text-text-secondary">
                    暂无搜索记录
                  </div>
                )}

                {/* {searchMessages.map((item: any) => (
                  <button
                    key={item.id}
                    type="button"
                    title={item.content}
                    onClick={() => {
                      setSearchText(item.content);
                      setIsSearching(false);
                    }}
                    className="
                      w-full rounded-md
                      px-3 py-2
                      text-left text-sm
                      text-text-secondary
                      hover:text-text-primary
                      transition-colors
                      truncate
                    "
                  >
                    {item.content}
                  </button>
                ))} */}
                {searchMessages.map((item: any) => (
                  <div
                    key={item.id}
                    className="
      group
      flex items-center gap-2
      px-3 py-2
      text-sm text-text-secondary
      shadow-sm
      transition-all duration-200
      hover:shadow-md
      hover:text-text-primary
    "
                  >
                    <button
                      type="button"
                      title={item.content}
                      onClick={() => {
                        setSearchText(item.content);
                        setIsSearching(false);
                      }}
                      className="
        min-w-0 flex-1
        truncate text-left
        underline decoration-transparent
        transition-all
        hover:decoration-current
        focus:outline-none
      "
                    >
                      {item.content}
                    </button>

                    <button
                      type="button"
                      title="删除"
                      onClick={(e) => {
                        e.stopPropagation();

                        const confirmed =
                          window.confirm('确定要删除这条搜索记录吗？');

                        if (!confirmed) return;

                        deleteSearchMessage(item.id);
                      }}
                      className="
        shrink-0
        px-1.5
        text-text-secondary
        opacity-0
        transition-all
        group-hover:opacity-100
        hover:text-red-500
      "
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
            </>
          )}
        </aside>

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
