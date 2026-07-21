import { EmptyType } from '@/components/empty/constant';
import Empty from '@/components/empty/empty';
import HighLightMarkdown from '@/components/highlight-markdown';
import { FileIcon } from '@/components/icon-font';
import { ImageWithPopover } from '@/components/image';
import { Input } from '@/components/originui/input';
import { SkeletonCard } from '@/components/skeleton-card';
import { Button } from '@/components/ui/button';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { IReference } from '@/interfaces/database/chat';
import { cn } from '@/lib/utils';
import DOMPurify from 'dompurify';
import { isEmpty } from 'lodash';
import { BrainCircuit, Search, X } from 'lucide-react';
import { Dispatch, SetStateAction, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useParams } from 'react-router-dom';
import { ISearchAppDetailProps } from '../next-searches/hooks';
import PdfDrawer from './document-preview-modal';
import { ISearchReturnProps } from './hooks';
import './index.less';
import MarkdownContent from './markdown-content';
import MindMapDrawer from './mindmap-drawer';
import RetrievalDocuments from './retrieval-documents';

type SimplePaginationProps = {
  current: number;
  pageSize: number;
  total: number;
  onChange: (page: number, pageSize: number) => void;
  showSizeChanger?: boolean;
};

const pageSizeOptions = [10, 20, 50, 100];

export function SimplePagination({
  current = 1,
  pageSize = 10,
  total = 0,
  onChange,
  showSizeChanger = true,
}: SimplePaginationProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  const isFirstPage = current <= 1;
  const isLastPage = current >= totalPages;

  const getDisplayedPages = () => {
    const maxDisplayedPages = 5;

    if (totalPages <= maxDisplayedPages) {
      return Array.from({ length: totalPages }, (_, index) => index + 1);
    }

    const pages: number[] = [];
    const left = Math.max(2, current - 2);
    const right = Math.min(totalPages - 1, current + 2);

    pages.push(1);

    if (left > 2) {
      pages.push(-1);
    }

    for (let page = left; page <= right; page += 1) {
      pages.push(page);
    }

    if (right < totalPages - 1) {
      pages.push(-2);
    }

    pages.push(totalPages);

    return pages;
  };

  const displayedPages = getDisplayedPages();

  const handlePageChange = (page: number) => {
    if (page < 1 || page > totalPages || page === current) {
      return;
    }

    onChange(page, pageSize);
  };

  const handlePageSizeChange = (
    event: React.ChangeEvent<HTMLSelectElement>,
  ) => {
    const nextPageSize = Number(event.target.value);

    onChange(1, nextPageSize);
  };

  if (total <= 0) {
    return null;
  }

  return (
    <div className="flex items-center justify-end gap-4 text-sm text-text-primary">
      <span>共 {total} 条</span>

      <div className="flex items-center gap-1">
        {!isFirstPage && (
          <button
            type="button"
            onClick={() => handlePageChange(current - 1)}
            className="
              h-8
              px-3
              rounded-md
              border
              border-border-default
              bg-bg-card
              text-text-primary
              hover:bg-bg-base
              transition-colors
            "
          >
            上一页
          </button>
        )}

        {displayedPages.map((page, index) => {
          if (page < 0) {
            return (
              <span
                key={`ellipsis-${index}`}
                className="flex h-8 min-w-8 items-center justify-center text-text-secondary"
              >
                ...
              </span>
            );
          }

          const active = page === current;

          return (
            <button
              key={page}
              type="button"
              onClick={() => handlePageChange(page)}
              className={cn(
                `
                  flex
                  h-8
                  min-w-8
                  items-center
                  justify-center
                  rounded-md
                  px-2
                  transition-colors
                `,
                active
                  ? 'bg-bg-card text-text-primary font-semibold'
                  : 'text-text-secondary hover:bg-bg-card hover:text-text-primary',
              )}
            >
              {page}
            </button>
          );
        })}

        {!isLastPage && (
          <button
            type="button"
            onClick={() => handlePageChange(current + 1)}
            className="
              h-8
              px-3
              rounded-md
              border
              border-border-default
              bg-bg-card
              text-text-primary
              hover:bg-bg-base
              transition-colors
            "
          >
            下一页
          </button>
        )}
      </div>

      {showSizeChanger && (
        <select
          value={pageSize}
          onChange={handlePageSizeChange}
          className="
            h-8
            rounded-md
            border
            border-border-default
            bg-bg-card
            px-2
            text-text-primary
            outline-none
          "
        >
          {pageSizeOptions.map((size) => (
            <option key={size} value={size}>
              {size} 条/页
            </option>
          ))}
        </select>
      )}
    </div>
  );
}

export default function SearchingView({
  setIsSearching,
  searchData,
  handleClickRelatedQuestion,
  handleTestChunk,
  setSelectedDocumentIds,
  answer,
  sendingLoading,
  relatedQuestions,
  isFirstRender,
  selectedDocumentIds,
  isSearchStrEmpty,
  searchStr,
  stopOutputMessage,
  visible,
  hideModal,
  documentId,
  selectedChunk,
  clickDocumentButton,
  mindMapVisible,
  hideMindMapModal,
  showMindMapModal,
  mindMapLoading,
  mindMap,
  chunks,
  total,
  handleSearch,
  pagination,
  onChange,
}: ISearchReturnProps & {
  setIsSearching?: Dispatch<SetStateAction<boolean>>;
  searchData: ISearchAppDetailProps;
}) {
  const { t } = useTranslation();

  // useEffect(() => {
  //   const changeLanguage = async () => {
  //     await i18n.changeLanguage('zh');
  //   };
  //   changeLanguage();
  // }, [i18n]);
  const [searchtext, setSearchtext] = useState<string>('');
  const [retrievalLoading, setRetrievalLoading] = useState(false);
  const [previewImageId, setPreviewImageId] = useState<string>();

  // 新增：每次新搜索时 +1，用来通知 RetrievalDocuments 重置
  const [searchResetKey, setSearchResetKey] = useState(0);
  const [hideRetrievalForNewQuestion, setHideRetrievalForNewQuestion] =
    useState(false);
  const [newQuestionLoadingStarted, setNewQuestionLoadingStarted] =
    useState(false);

  const { id: searchId } = useParams();

  const saveSearchMessage = async (content: string) => {
    const nextContent = content.trim();

    if (!searchId || !nextContent) return false;

    try {
      const res = await fetch('/v1/search_keep/message', {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          search_id: searchId,
          content: nextContent,
        }),
      });

      const data = await res.json();

      console.log('保存搜索记录结果:', data);

      if (data.code === 0) {
        window.dispatchEvent(
          new CustomEvent('search-message-saved', {
            detail: {
              content: nextContent,
            },
          }),
        );

        return true;
      }

      return false;
    } catch (error) {
      console.error('save search message failed:', error);
      return false;
    }
  };

  const handleSubmitSearch = async (content: string) => {
    const nextContent = content.trim();

    if (!nextContent) return;

    /**
     * 用户重新提问，立即隐藏文件标签
     */
    setHideRetrievalForNewQuestion(true);
    setNewQuestionLoadingStarted(false);

    /**
     * 新问题默认恢复全部文件
     */
    setSelectedDocumentIds([]);

    /**
     * 通知 RetrievalDocuments 重置内部文档列表
     */
    setSearchResetKey((prev) => prev + 1);

    await saveSearchMessage(nextContent);

    handleSearch(nextContent);
  };

  useEffect(() => {
    setSearchtext(searchStr);
  }, [searchStr, setSearchtext]);
  useEffect(() => {
    if (!hideRetrievalForNewQuestion) return;

    /**
     * 新问题的 loading 真正开始了
     */
    if (sendingLoading || retrievalLoading) {
      setNewQuestionLoadingStarted(true);
      return;
    }

    /**
     * loading 已经开始过，并且现在结束了，恢复显示标签
     */
    if (newQuestionLoadingStarted && !sendingLoading && !retrievalLoading) {
      setHideRetrievalForNewQuestion(false);
      setNewQuestionLoadingStarted(false);
    }
  }, [
    hideRetrievalForNewQuestion,
    newQuestionLoadingStarted,
    sendingLoading,
    retrievalLoading,
  ]);

  console.log(retrievalLoading);
  const shouldShowRetrievalDocuments =
    !isSearchStrEmpty &&
    !sendingLoading &&
    !retrievalLoading &&
    (chunks?.length ?? 0) > 0;
  return (
    <section
      className={cn(
        'relative w-full flex transition-all justify-start items-center',
      )}
    >
      {/* search header */}
      <div
        className={cn(
          'relative z-10 px-8 pt-8 flex  text-transparent justify-start items-start w-full',
        )}
      >
        <h1
          className={cn(
            'text-4xl font-bold bg-gradient-to-l from-[#40EBE3] to-[#4A51FF] bg-clip-text cursor-pointer',
          )}
          onClick={() => {
            setIsSearching?.(false);
          }}
        >
          恒丰纸业
        </h1>
        <div
          className={cn(
            ' rounded-lg text-primary text-xl sticky flex flex-col justify-center w-2/3 max-w-[780px] transform scale-100 ml-16 ',
          )}
        >
          <div className={cn('flex flex-col justify-start items-start w-full')}>
            <div className="relative w-full text-primary">
              <Input
                placeholder={t('search.searchGreeting')}
                className={cn(
                  'w-full rounded-full py-6 pl-4 !pr-[8rem] text-primary text-lg bg-bg-base',
                )}
                value={searchtext}
                onChange={(e) => {
                  setSearchtext(e.target.value);
                }}
                disabled={sendingLoading}
                // onKeyUp={(e) => {
                //   if (e.key === 'Enter') {
                //     handleSearch(searchtext);
                //   }
                onKeyUp={async (e) => {
                  if (e.key === 'Enter') {
                    await handleSubmitSearch(searchtext);
                  }
                }}
              />
              <div className="absolute right-2 top-1/2 -translate-y-1/2 transform flex items-center gap-1">
                <X
                  className="text-text-secondary cursor-pointer opacity-80"
                  size={14}
                  onClick={() => {
                    setSearchtext('');
                    handleClickRelatedQuestion('');
                  }}
                />
                <span className="text-text-secondary opacity-20 ml-4">|</span>
                {/* <button
                  type="button"
                  className="rounded-full bg-text-primary p-1 text-bg-base shadow w-12 h-8 ml-4"
                  onClick={() => {
                    if (sendingLoading) {
                      stopOutputMessage();
                    } else {
                      handleSearch(searchtext);
                    }
                  }}
                >
                  {sendingLoading ? (
                    // <Square size={22} className="m-auto" />
                    <div className="w-2 h-2 bg-bg-base m-auto"></div>
                  ) : (
                    <Search size={22} className="m-auto" />
                  )}
                </button> */}

                <button
                  type="button"
                  className="rounded-full bg-text-primary p-1 text-bg-base shadow w-12 h-8 ml-4"
                  onClick={async () => {
                    if (sendingLoading) {
                      stopOutputMessage();
                      return;
                    }

                    await handleSubmitSearch(searchtext);
                  }}
                >
                  {sendingLoading ? (
                    <div className="w-2 h-2 bg-bg-base m-auto"></div>
                  ) : (
                    <Search size={22} className="m-auto" />
                  )}
                </button>
              </div>
            </div>
          </div>
          {/* search body */}
          <div
            className="w-full mt-5 overflow-auto scrollbar-none "
            style={{ height: 'calc(100vh - 250px)' }}
          >
            {searchData.search_config.summary && !isSearchStrEmpty && (
              <>
                <div className="flex justify-start items-start text-text-primary text-2xl">
                  {t('search.AISummary')}
                </div>
                {isEmpty(answer) && sendingLoading ? (
                  <SkeletonCard className=" mt-2" />
                ) : (
                  answer.answer && (
                    <div className="border rounded-lg p-4 mt-3 max-h-100 overflow-auto scrollbar-none">
                      <MarkdownContent
                        loading={sendingLoading}
                        content={answer.answer}
                        reference={answer.reference ?? ({} as IReference)}
                        clickDocumentButton={clickDocumentButton}
                      ></MarkdownContent>
                    </div>
                  )
                )}
                {answer.answer && !sendingLoading && (
                  <div className="w-full border-b border-border-default/80 my-6"></div>
                )}
              </>
            )}

            {/* retrieval documents */}
            {!isSearchStrEmpty && (
              <div
                className={cn('mt-3 w-80', {
                  hidden: hideRetrievalForNewQuestion || sendingLoading,
                })}
              >
                <RetrievalDocuments
                  selectedDocumentIds={selectedDocumentIds}
                  setSelectedDocumentIds={setSelectedDocumentIds}
                  onTesting={handleTestChunk}
                  setLoading={(loading: boolean) => {
                    setRetrievalLoading(loading);
                  }}
                  resetKey={searchResetKey}
                />
              </div>
            )}

            {/* loading */}
            {(sendingLoading || retrievalLoading) && chunks?.length === 0 && (
              <div className="mt-8 flex min-h-[240px] w-full flex-col items-center justify-center gap-5">
                <div className="relative flex h-20 w-20 items-center justify-center">
                  {/* 外层柔和光晕 */}
                  <div className="absolute inset-0 rounded-full bg-blue-500/20 blur-2xl animate-pulse" />

                  {/* 外层渐变流光环 */}
                  <div className="absolute inset-0 rounded-full bg-[conic-gradient(from_0deg,transparent_0deg,rgba(96,165,250,0.15)_80deg,#60a5fa_150deg,#22d3ee_220deg,transparent_300deg)] animate-spin shadow-[0_0_30px_rgba(59,130,246,0.45)]" />

                  {/* 挖空中间，形成环 */}
                  <div className="absolute inset-[6px] rounded-full bg-bg-base" />

                  {/* 内层反向流光环 */}
                  <div className="absolute inset-3 rounded-full bg-[conic-gradient(from_180deg,transparent_0deg,rgba(34,211,238,0.15)_90deg,#38bdf8_160deg,#818cf8_230deg,transparent_310deg)] animate-[spin_1.8s_linear_infinite_reverse]" />

                  {/* 再次挖空 */}
                  <div className="absolute inset-[18px] rounded-full bg-bg-base" />

                  {/* 中心呼吸点 */}
                  <div className="relative h-3 w-3 rounded-full bg-blue-400 shadow-[0_0_18px_rgba(96,165,250,0.95)] animate-pulse" />
                </div>

                <div className="flex flex-col items-center gap-1">
                  <span className="animate-pulse text-sm font-medium tracking-wide text-text-secondary">
                    正在检索相关内容，请稍候...
                  </span>
                  <span className="text-xs text-text-secondary/50">
                    正在加载知识库切片
                  </span>
                </div>
              </div>
            )}
            <div className="mt-3 ">
              {chunks?.length > 0 && (
                <>
                  {chunks.map((chunk, index) => {
                    const serialNumber = index + 1;
                    return (
                      // <div key={index}>
                      //   <div className="w-full flex flex-col">
                      //     <div className="w-full highlightContent">

                      //       {/* <ImageWithPopover
                      //         id={chunk.image_id || chunk.img_id}
                      //       ></ImageWithPopover> */}
                      //       <ImageWithPopover
                      //         id={chunk.image_id || chunk.img_id}
                      //         previewImageId={previewImageId}
                      //         setPreviewImageId={setPreviewImageId}
                      //       />
                      //       <Popover>
                      //         <PopoverTrigger asChild>
                      //           <div
                      //             dangerouslySetInnerHTML={{
                      //               __html: DOMPurify.sanitize(
                      //                 `${
                      //                   chunk.highlight ??
                      //                   chunk.content_with_weight ??
                      //                   ''
                      //                 }...`,
                      //               ),
                      //             }}
                      //             className="text-sm text-text-primary mb-1"
                      //           ></div>
                      //         </PopoverTrigger>
                      //         <PopoverContent className="text-text-primary !w-full max-w-lg ">
                      //           <div className="max-h-96 overflow-auto scrollbar-thin">
                      //             <HighLightMarkdown>
                      //               {chunk.content_with_weight}
                      //             </HighLightMarkdown>
                      //           </div>
                      //         </PopoverContent>
                      //       </Popover>
                      //     </div>
                      //     <div className="flex gap-2 items-center text-xs text-text-secondary border p-1 rounded-lg w-fit mt-3">
                      //       {/* 原有的可点击文档按钮 */}
                      //       {/* 1. 新增序号显示区域 */}
                      //       <div className="bg-blue-50 text-blue-600 text-xs font-bold px-2 py-0.5 rounded-full border border-blue-100">
                      //         文档切片 {index + 1}
                      //       </div>
                      //       <div
                      //         className="flex gap-2 items-center cursor-pointer"
                      //         onClick={() =>
                      //           clickDocumentButton(chunk.doc_id, chunk as any)
                      //         }
                      //       >
                      //         <FileIcon name={chunk.docnm_kwd}></FileIcon>
                      //         {chunk.docnm_kwd}
                      //       </div>

                      //       {/* 新增的橙色 kb_name 展示区域 */}
                      //       <div className="text-pink-300 font-medium pointer-events-none">
                      //         {chunk.kb_name || '未知知识库'}
                      //       </div>
                      //     </div>
                      //   </div>
                      //   {index < chunks.length - 1 && (
                      //     <div className="w-full border-b border-border-default/80 mt-6"></div>
                      //   )}
                      // </div>

                      <div key={index}>
                        <div className="w-full flex items-start gap-3">
                          {/* 左侧序号 */}
                          <div
                            className="
                              mt-1
                              shrink-0
                              inline-flex
                              items-center
                              justify-center
                              rounded-full
                              bg-blue-50
                              px-2.5
                              py-1
                              text-xs
                              font-bold
                              text-blue-600
                              border
                              border-blue-100
                              dark:bg-blue-500/10
                              dark:text-blue-400
                              dark:border-blue-500/20
                            "
                          >
                            切片{index + 1}
                          </div>

                          {/* 右侧内容：图片 + 文字 + 文件信息 */}
                          <div className="flex-1 min-w-0">
                            <div className="w-full highlightContent">
                              {/* 图片 */}
                              <ImageWithPopover
                                id={chunk.image_id || chunk.img_id}
                                previewImageId={previewImageId}
                                setPreviewImageId={setPreviewImageId}
                              />

                              {/* 文字内容 */}
                              <Popover>
                                <PopoverTrigger asChild>
                                  <div
                                    dangerouslySetInnerHTML={{
                                      __html: DOMPurify.sanitize(
                                        `${
                                          chunk.highlight ??
                                          chunk.content_with_weight ??
                                          ''
                                        }...`,
                                      ),
                                    }}
                                    className="text-sm text-text-primary mb-1"
                                  ></div>
                                </PopoverTrigger>

                                <PopoverContent className="text-text-primary !w-full max-w-lg ">
                                  <div className="max-h-96 overflow-auto scrollbar-thin">
                                    <HighLightMarkdown>
                                      {chunk.content_with_weight}
                                    </HighLightMarkdown>
                                  </div>
                                </PopoverContent>
                              </Popover>
                            </div>

                            {/* 文档信息 */}
                            <div className="flex gap-2 items-center text-xs text-text-secondary border p-1 rounded-lg w-fit mt-3">
                              <div
                                className="flex gap-2 items-center cursor-pointer"
                                onClick={() =>
                                  clickDocumentButton(
                                    chunk.doc_id,
                                    chunk as any,
                                  )
                                }
                              >
                                <FileIcon name={chunk.docnm_kwd}></FileIcon>
                                {chunk.docnm_kwd}
                              </div>

                              <div className="text-pink-300 font-medium pointer-events-none">
                                {chunk.kb_name || '未知知识库'}
                              </div>
                            </div>
                          </div>
                        </div>

                        {index < chunks.length - 1 && (
                          <div className="w-full border-b border-border-default/80 mt-6"></div>
                        )}
                      </div>
                    );
                  })}
                </>
              )}
              {relatedQuestions?.length > 0 &&
                searchData.search_config.related_search && (
                  <>
                    <div className="w-full border-b border-border-default/80 mt-6"></div>

                    <div className="mt-6 w-full overflow-hidden opacity-100 max-h-96">
                      <p className="text-text-primary mb-2 text-xl">
                        {t('search.relatedSearch')}
                      </p>
                      <div className="mt-2 flex flex-wrap justify-start gap-2">
                        {relatedQuestions?.map((x, idx) => (
                          <Button
                            key={idx}
                            variant="transparent"
                            className="bg-bg-card text-text-secondary"
                            onClick={(event) => {
                              setSelectedDocumentIds([]);
                              setSearchResetKey((prev) => prev + 1);

                              handleClickRelatedQuestion(
                                x,
                                searchData.search_config.summary,
                              )(event);
                            }}
                          >
                            {x}
                          </Button>
                        ))}
                      </div>
                    </div>
                  </>
                )}
            </div>
            {!isSearchStrEmpty &&
              !retrievalLoading &&
              !answer.answer &&
              !sendingLoading &&
              total <= 0 &&
              chunks?.length <= 0 &&
              relatedQuestions?.length <= 0 && (
                <div className="h-2/5 flex items-center justify-center">
                  <Empty type={EmptyType.SearchData} iconWidth={80} />
                </div>
              )}
          </div>

          {/* {total > 0 && (
            <div className="mt-8 px-8 pb-8 text-base">
              <RAGFlowPagination
                current={pagination.current}
                pageSize={pagination.pageSize}
                total={total}
                onChange={onChange}
              ></RAGFlowPagination>
            </div>
          )} */}

          {total > 0 && (
            <div className="mt-8 px-8 pb-8 text-base">
              <SimplePagination
                current={pagination.current}
                pageSize={pagination.pageSize}
                total={total}
                onChange={onChange}
              />
            </div>
          )}
        </div>
        {mindMapVisible && (
          <div className="flex-1 h-[88dvh] z-30 ml-32 mt-5">
            <MindMapDrawer
              visible={mindMapVisible}
              hideModal={hideMindMapModal}
              data={mindMap}
              loading={mindMapLoading}
            ></MindMapDrawer>
          </div>
        )}
      </div>
      {!mindMapVisible &&
        !isFirstRender &&
        !isSearchStrEmpty &&
        !isEmpty(searchData.search_config.kb_ids) &&
        searchData.search_config.query_mindmap && (
          <Popover>
            <PopoverTrigger asChild>
              <div
                className="rounded-lg h-16 w-16 p-0 absolute top-28 right-3 z-30 border cursor-pointer flex justify-center items-center bg-bg-card"
                onClick={showMindMapModal}
              >
                {/* <SvgIcon name="paper-clip" width={24} height={30}></SvgIcon> */}
                <BrainCircuit size={36} />
              </div>
            </PopoverTrigger>
            <PopoverContent className="w-fit">{t('chunk.mind')}</PopoverContent>
          </Popover>
        )}
      {visible && (
        <PdfDrawer
          visible={visible}
          hideModal={hideModal}
          documentId={documentId}
          chunk={selectedChunk}
        ></PdfDrawer>
      )}
    </section>
  );
}
