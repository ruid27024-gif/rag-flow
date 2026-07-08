import FileIcon from '@/components/file-icon';
import NewDocumentLink from '@/components/new-document-link';
import PdfSheet from '@/components/pdf-drawer';
import { useClickDrawer } from '@/components/pdf-drawer/hooks';
import DocumentPreviewer from '@/components/pdf-previewer';
import { cn } from '@/lib/utils';
import { getAuthorization } from '@/utils/authorization-util';
import { getExtension } from '@/utils/document-util';
import { Empty, Spin, message as antdMessage } from 'antd';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useParams } from 'umi';

// 按你的实际路径修改
import { ShareChatBox } from '@/pages/next-chats-default/chat/chat-box/share-chat-box';

type ReferenceDocumentItem = {
  id?: string;
  document_id?: string;
  doc_id?: string;
  document_name?: string;
  doc_name?: string;
  docnm_kwd?: string;
  url?: string | null;
  chunks?: any[];
  positions?: any[];
  content?: string;
  count?: number;
  [key: string]: any;
};

type ShareMessage = {
  id: string;
  role: 'user' | 'assistant' | string;
  content: string;
  reference?: any;
  prompt?: string;
  created_at?: string;
  create_time?: string;
  [key: string]: any;
};

type ShareSnapshot = {
  conversation_id: string;
  dialog_id: string;
  name?: string;
  messages: ShareMessage[];
};

type ShareData = {
  id: string;
  conversation_id: string;
  dialog_id: string;
  name?: string;
  snapshot: ShareSnapshot | string;
  user_id?: string;
};

export default function ShareChatPage() {
  const { shareId } = useParams<{ shareId: string }>();

  const [loading, setLoading] = useState(true);
  const [shareData, setShareData] = useState<ShareData | null>(null);

  /**
   * 右侧参考来源列表
   */
  const [referenceVisible, setReferenceVisible] = useState(false);
  const [referenceList, setReferenceList] = useState<ReferenceDocumentItem[]>(
    [],
  );

  /**
   * 右侧高亮预览
   */
  const [sourcePreviewVisible, setSourcePreviewVisible] = useState(false);
  const [sourcePreviewDocumentId, setSourcePreviewDocumentId] = useState('');
  const [sourcePreviewChunk, setSourcePreviewChunk] = useState<any>(null);

  /**
   * PDF 抽屉
   */
  const { visible, hideModal, documentId, selectedChunk, clickDocumentButton } =
    useClickDrawer();

  const openReferencePanel = useCallback((list: ReferenceDocumentItem[]) => {
    setReferenceList(list || []);
    setReferenceVisible(true);
    setSourcePreviewVisible(false);
  }, []);

  const closeReferencePanel = useCallback(() => {
    setReferenceVisible(false);
  }, []);

  const openSourcePreviewPanel = useCallback(
    (documentId: string, chunk: any) => {
      setSourcePreviewDocumentId(documentId);
      setSourcePreviewChunk(chunk);
      setSourcePreviewVisible(true);
      setReferenceVisible(false);
    },
    [],
  );

  const closeSourcePreviewPanel = useCallback(() => {
    setSourcePreviewVisible(false);
    setSourcePreviewDocumentId('');
    setSourcePreviewChunk(null);
  }, []);

  /**
   * 获取分享快照
   */
  useEffect(() => {
    const fetchShare = async () => {
      if (!shareId) return;

      try {
        setLoading(true);

        const response = await fetch(`/v1/conversation/share/${shareId}`, {
          method: 'GET',
          credentials: 'include',
          headers: {
            Authorization: getAuthorization() || '',
          },
        });

        const result = await response.json();

        if (result.code !== 0) {
          antdMessage.error(result.message || '获取分享失败');
          setShareData(null);
          return;
        }

        setShareData(result.data);
      } catch (error) {
        console.error(error);
        antdMessage.error('获取分享失败');
        setShareData(null);
      } finally {
        setLoading(false);
      }
    };

    fetchShare();
  }, [shareId]);

  /**
   * 兼容 snapshot 是 JSON 字符串或对象
   */
  const snapshot = useMemo(() => {
    if (!shareData?.snapshot) return null;

    if (typeof shareData.snapshot === 'string') {
      try {
        return JSON.parse(shareData.snapshot) as ShareSnapshot;
      } catch {
        return null;
      }
    }

    return shareData.snapshot;
  }, [shareData]);

  /**
   * 把分享快照转换成 SingleChatBox 需要的 conversation 结构
   *
   * 重点：
   * - SingleChatBox 使用 conversation.message 渲染消息
   * - MessageItem 里通常通过 conversation.reference 给 assistant 找溯源
   * - 你的 reference 只对应非开场白 assistant
   */
  const shareConversation = useMemo(() => {
    if (!snapshot) return {} as any;

    const messages = Array.isArray(snapshot.messages) ? snapshot.messages : [];

    /**
     * 还原 conversation.reference
     *
     * 规则：
     * 第 0 条 assistant 是开场白，不对应 reference
     * 后面的 assistant 才依次对应 reference
     *
     * 注意：
     * 这里不要过滤空 reference，否则可能导致 reference 下标错位。
     */
    const reference = messages
      .filter((item, index) => {
        if (item.role !== 'assistant') return false;

        // 第 0 条 assistant 是开场白，不消耗 reference
        if (index === 0) return false;

        return true;
      })
      .map((item) => item.reference || { chunks: [] });

    return {
      id: snapshot.conversation_id || shareData?.conversation_id || shareId,
      conversation_id:
        snapshot.conversation_id || shareData?.conversation_id || shareId,
      dialog_id: snapshot.dialog_id || shareData?.dialog_id,
      name: snapshot.name || shareData?.name || '分享的对话',
      user_id: shareData?.user_id,

      // SingleChatBox 用这个渲染消息
      message: messages,

      // SingleChatBox/MessageItem 用这个找溯源
      reference,
    } as any;
  }, [snapshot, shareData, shareId]);

  /**
   * SingleChatBox 需要这两个参数。
   * 分享页不需要真正停止生成，所以给空实现即可。
   */
  const controller = useMemo(() => new AbortController(), []);

  const stopOutputMessage = useCallback(() => {}, []);

  if (loading) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-[#f7f8fa]">
        <Spin />
      </div>
    );
  }

  if (!shareData || !snapshot) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-[#f7f8fa]">
        <Empty description="分享不存在或已失效" />
      </div>
    );
  }

  return (
    <div className="h-screen w-full overflow-hidden bg-[#f7f8fa]">
      <div className="flex h-full flex-col">
        {/* 顶部标题 */}
        <header className="flex h-14 shrink-0 items-center border-b border-gray-200 bg-white px-6">
          <div className="min-w-0">
            <div className="truncate text-base font-semibold text-gray-900">
              {snapshot.name || shareData.name || '分享的对话'}
            </div>
            <div className="text-xs text-gray-400">
              当前页面为分享快照，只读展示
            </div>
          </div>
        </header>

        <div className="flex min-h-0 flex-1 overflow-hidden">
          {/* 主聊天内容：直接复用 SingleChatBox */}
          <main
            id="share-chat-main-content"
            className={cn(
              'min-h-0 min-w-0 overflow-hidden',
              sourcePreviewVisible ? 'w-1/2 flex-none basis-1/2' : 'flex-1',
            )}
          >
            <ShareChatBox
              conversation={shareConversation}
              clickDocumentButton={clickDocumentButton}
              onOpenReferencePanel={openReferencePanel}
            />
          </main>

          {/* 右侧高亮预览 */}
          <SourcePreviewPanel
            className={cn('h-full min-h-0 min-w-0 flex-none basis-1/2 w-1/2', {
              hidden: !sourcePreviewVisible,
            })}
            documentId={sourcePreviewDocumentId}
            chunk={sourcePreviewChunk}
            visible={sourcePreviewVisible}
            onClose={closeSourcePreviewPanel}
          />

          {/* 右侧参考来源列表 */}
          <ReferenceSourcePanel
            className={cn('shrink-0', {
              hidden: !referenceVisible,
            })}
            list={referenceList}
            onClose={closeReferencePanel}
            onOpenSourcePreview={openSourcePreviewPanel}
          />
        </div>

        {/* PDF 抽屉 */}
        {visible && (
          <PdfSheet
            visible={visible}
            hideModal={hideModal}
            documentId={documentId}
            chunk={selectedChunk}
          />
        )}
      </div>
    </div>
  );
}

export function ReferenceSourcePanel({
  className,
  list,
  onClose,
  onOpenSourcePreview,
}: {
  className?: string;
  list: ReferenceDocumentItem[];
  onClose: () => void;
  onOpenSourcePreview?: (documentId: string, chunk: any) => void;
}) {
  const getDocumentId = (item: ReferenceDocumentItem) => {
    return item.document_id || item.doc_id || '';
  };

  const getDocumentName = (item: ReferenceDocumentItem) => {
    return item.document_name || item.doc_name || item.docnm_kwd || '';
  };

  const getDocumentUrl = (item: ReferenceDocumentItem) => {
    return item.url ?? null;
  };

  const handlePreview = (item: ReferenceDocumentItem, index: number) => {
    const documentId = getDocumentId(item);
    const documentName = getDocumentName(item);
    const documentUrl = getDocumentUrl(item);

    if (!documentId) {
      console.warn('documentId not found:', item);
      return;
    }

    const chunks = Array.isArray(item.chunks) ? item.chunks : [];

    const mergedPositions =
      item.positions && item.positions.length > 0
        ? item.positions
        : chunks.flatMap((chunk: any) => chunk.positions || []);

    const mergedContent =
      item.content ||
      chunks
        .map((chunk: any) => chunk.content)
        .filter(Boolean)
        .join('\n\n');

    const chunkItem = {
      ...item,

      document_id: documentId,
      doc_id: documentId,
      document_name: documentName,
      doc_name: documentName,
      docnm_kwd: item.docnm_kwd || documentName,
      url: documentUrl,

      positions: mergedPositions,
      content: mergedContent,

      chunks,
      source_index: index,
    };

    onOpenSourcePreview?.(documentId, chunkItem);
  };

  return (
    <aside
      className={cn(
        `
          flex h-full w-[360px] max-w-[40vw] flex-col overflow-hidden
          border-l border-gray-200 bg-white
          dark:border-gray-800 dark:bg-gray-950
        `,
        className,
      )}
    >
      <div
        className="
          flex shrink-0 items-center justify-between
          border-b border-gray-100 px-4 py-3
          dark:border-gray-800
        "
      >
        <div className="text-sm font-semibold text-gray-900 dark:text-gray-100">
          参考来源 ({list?.length || 0})
        </div>

        <button
          type="button"
          onClick={onClose}
          className="
            flex h-7 w-7 items-center justify-center rounded-md
            text-lg text-gray-400
            hover:bg-gray-100 hover:text-gray-700
            dark:hover:bg-gray-800 dark:hover:text-gray-200
          "
        >
          ×
        </button>
      </div>

      <div className="flex-1 overflow-y-auto overscroll-contain px-4 py-4">
        {!list || list.length === 0 ? (
          <div className="text-sm text-gray-400">暂无参考来源</div>
        ) : (
          <div className="space-y-4">
            {list.map((item, i) => {
              const docId = getDocumentId(item);
              const docName = getDocumentName(item);
              const documentUrl = getDocumentUrl(item);
              const count = item.count || item.chunks?.length || 0;

              return (
                <div key={item.id || docId || i} className="flex gap-3">
                  <span
                    className="
                      mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center
                      rounded-full bg-[#018B8D]
                      text-[11px] font-medium text-white
                    "
                  >
                    {i + 1}
                  </span>

                  <div className="min-w-0 flex-1">
                    <div className="flex min-w-0 items-start">
                      <div className="min-w-0 flex-1">
                        <NewDocumentLink
                          documentId={docId}
                          documentName={docName}
                          prefix="document"
                          link={documentUrl || undefined}
                          showDownloadButton={false}
                          className="
                            group/title
                            flex
                            min-w-0
                            items-start
                            gap-2
                            text-sm
                            font-semibold
                            leading-5
                            text-gray-900
                            hover:text-[#018B8D]
                            dark:text-gray-100
                            dark:hover:text-[#018B8D]
                          "
                        >
                          <span className="mt-0.5 shrink-0">
                            <FileIcon id={docId} name={docName} />
                          </span>

                          <span className="min-w-0 flex-1 line-clamp-2 break-all">
                            {docName}
                          </span>
                        </NewDocumentLink>

                        <div className="mt-3">
                          <div className="mt-2 ml-[2em] flex flex-wrap items-center gap-1.5 text-[11px] leading-none">
                            <button
                              type="button"
                              onClick={() => handlePreview(item, i + 1)}
                              className="
                                inline-flex
                                items-center
                                gap-1
                                rounded-md
                                border
                                border-[#018B8D]/25
                                bg-[#018B8D]/5
                                px-2
                                py-1
                                font-medium
                                text-[#018B8D]
                                transition-all
                                hover:border-[#018B8D]/50
                                hover:bg-[#018B8D]/10
                                hover:text-[#01777A]
                                active:scale-[0.98]
                                dark:border-[#20B2AA]/25
                                dark:bg-[#018B8D]/10
                                dark:text-[#20B2AA]
                                dark:hover:border-[#20B2AA]/50
                                dark:hover:bg-[#018B8D]/20
                                dark:hover:text-[#5eead4]
                              "
                            >
                              <span className="text-[11px]">✦</span>
                              <span>高亮预览</span>
                            </button>

                            <a
                              href={
                                documentUrl ||
                                `/document/${docId}?ext=${getExtension(
                                  docName,
                                )}&prefix=document`
                              }
                              target="_blank"
                              rel="noreferrer"
                              onClick={(e) => e.stopPropagation()}
                              className="
                                inline-flex
                                items-center
                                gap-1
                                rounded-md
                                border
                                border-[#018B8D]/25
                                bg-[#018B8D]/5
                                px-2
                                py-1
                                font-medium
                                text-[#018B8D]
                                transition-all
                                hover:border-[#018B8D]/50
                                hover:bg-[#018B8D]/10
                                hover:text-[#01777A]
                                active:scale-[0.98]
                                dark:border-[#20B2AA]/25
                                dark:bg-[#018B8D]/10
                                dark:text-[#20B2AA]
                                dark:hover:border-[#20B2AA]/50
                                dark:hover:bg-[#018B8D]/20
                                dark:hover:text-[#5eead4]
                              "
                            >
                              <span className="text-[11px]">↗</span>
                              <span>显示原文</span>
                            </a>

                            <a
                              href={`/v1/document/get/${docId}?ext=${getExtension(
                                docName,
                              )}`}
                              download={docName || 'download'}
                              onClick={(e) => e.stopPropagation()}
                              className="
                                inline-flex
                                items-center
                                gap-1
                                rounded-md
                                border
                                border-[#018B8D]/25
                                bg-[#018B8D]/5
                                px-2
                                py-1
                                font-medium
                                text-[#018B8D]
                                transition-all
                                hover:border-[#018B8D]/50
                                hover:bg-[#018B8D]/10
                                hover:text-[#01777A]
                                active:scale-[0.98]
                                dark:border-[#20B2AA]/25
                                dark:bg-[#018B8D]/10
                                dark:text-[#20B2AA]
                                dark:hover:border-[#20B2AA]/50
                                dark:hover:bg-[#018B8D]/20
                                dark:hover:text-[#5eead4]
                              "
                            >
                              <span className="text-[11px]">↓</span>
                              <span>下载文档</span>
                            </a>
                          </div>
                        </div>
                      </div>
                    </div>

                    {count > 0 && (
                      <div className="mt-1 pl-7 text-xs text-gray-400 dark:text-gray-500">
                        引用 {count} 处
                      </div>
                    )}

                    {item.content && (
                      <div className="mt-2 line-clamp-3 pl-7 text-xs leading-5 text-gray-500 dark:text-gray-400">
                        {String(item.content).replace(/\n/g, ' ')}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </aside>
  );
}

function SourcePreviewPanel({
  className,
  documentId,
  chunk,
  visible,
  onClose,
}: {
  className?: string;
  documentId: string;
  chunk: any;
  visible: boolean;
  onClose: () => void;
}) {
  const docName =
    chunk?.document_name || chunk?.doc_name || chunk?.docnm_kwd || '原文预览';

  const sourceIndex = chunk?.source_index || chunk?.reference_index;

  return (
    <aside
      className={cn(
        `
          flex h-full min-h-0 min-w-0 flex-col overflow-hidden
          border-l border-gray-200 bg-white
          dark:border-gray-800 dark:bg-gray-950
        `,
        className,
      )}
    >
      <div className="flex shrink-0 items-center justify-between px-3 pt-1 pb-0.5">
        <div className="flex min-w-0 flex-1 items-center gap-1 truncate text-xs text-gray-400">
          {sourceIndex ? (
            <span className="inline-flex h-4 min-w-4 shrink-0 items-center justify-center rounded-full bg-[#018B8D] px-1 text-[10px] font-medium text-white">
              {sourceIndex}
            </span>
          ) : null}

          <span className="truncate">{docName}</span>
        </div>

        <button
          type="button"
          onClick={onClose}
          className="
            ml-2 flex h-6 w-6 shrink-0 items-center justify-center rounded-md
            text-base text-gray-400
            hover:bg-gray-100 hover:text-gray-700
            dark:hover:bg-gray-800 dark:hover:text-gray-200
          "
        >
          ×
        </button>
      </div>

      <div className="min-h-0 flex-1 overflow-hidden">
        {documentId ? (
          <div className="h-full w-full min-w-0 overflow-hidden [&>div]:!h-full [&>div]:!w-full [&>div]:!min-w-0">
            <DocumentPreviewer
              documentId={documentId}
              chunk={chunk}
              visible={visible}
            />
          </div>
        ) : (
          <div className="p-4 text-sm text-gray-400">暂无可预览文档</div>
        )}
      </div>
    </aside>
  );
}
