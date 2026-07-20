import EmbedDialog from '@/components/embed-dialog';
import { useShowEmbedModal } from '@/components/embed-dialog/use-show-embed-dialog';
import FileIcon from '@/components/file-icon';
import { KnowledgeBaseFormField } from '@/components/knowledge-base-item';
import NewDocumentLink from '@/components/new-document-link';
import PdfSheet from '@/components/pdf-drawer';
import { useClickDrawer } from '@/components/pdf-drawer/hooks';
import DocumentPreviewer from '@/components/pdf-previewer';
import { Button } from '@/components/ui/button';
import { Form } from '@/components/ui/form';
import { DatasetMetadata, SharedFrom } from '@/constants/chat';
import { useSetModalState } from '@/hooks/common-hooks';
import { useNavigatePage } from '@/hooks/logic-hooks/navigate-hooks';
import {
  useFetchConversationList,
  useFetchConversationManually,
  useFetchDialog,
  useGetChatSearchParams,
  useSetDialog,
} from '@/hooks/use-chat-request';
import { useFetchUserInfo } from '@/hooks/use-user-setting-request';
import { IClientConversation } from '@/interfaces/database/chat';
import { cn } from '@/lib/utils';
import { getExtension } from '@/utils/document-util';
import {
  removeUselessFieldsFromValues,
  setLLMSettingEnabledValues,
} from '@/utils/form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useMount } from 'ahooks';
import { message } from 'antd';
import { isEmpty, omit } from 'lodash';
import { LogOut } from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { useParams } from 'umi';
import { z } from 'zod';
import { useHandleClickConversationCard } from '../hooks/use-click-card';
import { ChatSettings } from './app-settings/chat-settings';
import { SavingButton } from './app-settings/saving-button';
import { useChatSettingSchema } from './app-settings/use-chat-setting-schema';
import { MultipleChatBox } from './chat-box/multiple-chat-box';
import { SingleChatBox } from './chat-box/single-chat-box';
import { Sessions } from './sessions';
import { useAddChatBox } from './use-add-box';
import { useSwitchDebugMode } from './use-switch-debug-mode';

type AgentFileItem = {
  name: string;
  size: number;
  mtime?: number;
  download_url: string;
};

function AgentFilesPanel({
  className,
  tenantId,
  conversationId,
  visible,
  onClose,
}: {
  className?: string;
  tenantId?: string;
  conversationId?: string;
  visible?: boolean;
  onClose?: () => void;
}) {
  const [loadingFiles, setLoadingFiles] = useState(false);
  const [files, setFiles] = useState<AgentFileItem[]>([]);
  const [error, setError] = useState('');

  const loadFiles = useCallback(async () => {
    if (!tenantId || !conversationId) {
      setError('缺少 tenantId 或 conversationId');
      setFiles([]);
      return;
    }

    setLoadingFiles(true);
    setError('');

    try {
      const url = `/v1/file/agent/list/${encodeURIComponent(
        tenantId,
      )}/${encodeURIComponent(conversationId)}`;

      const res = await fetch(url, {
        method: 'GET',
        credentials: 'include',
      });

      const result = await res.json();

      if (!res.ok) {
        throw new Error(result?.message || '获取文件列表失败');
      }

      setFiles(result?.data?.files || []);
    } catch (err: any) {
      console.error('加载会话文件失败:', err);
      setError(err?.message || '加载会话文件失败');
      setFiles([]);
    } finally {
      setLoadingFiles(false);
    }
  }, [tenantId, conversationId]);

  useEffect(() => {
    if (visible) {
      loadFiles();
    }
  }, [visible, loadFiles]);

  return (
    <aside
      className={cn(
        `
    flex
    h-full
    w-[360px]
    flex-col
    border-l
    border-gray-200
    bg-transparent
    dark:border-gray-800
    dark:bg-transparent
    `,
        className,
      )}
    >
      <div
        className="
          flex
          h-12
          shrink-0
          items-center
          justify-between
          border-b
          border-gray-200
          px-4
          dark:border-gray-800
        "
      >
        <div className="font-medium text-gray-900 dark:text-gray-100">
          本会话生成文件
        </div>

        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={loadFiles}
            className="
              rounded-md
              px-2
              py-1
              text-xs
              text-gray-500
              hover:bg-gray-100
              dark:text-gray-400
              dark:hover:bg-gray-800
            "
          >
            刷新
          </button>

          <button
            type="button"
            onClick={onClose}
            className="
              rounded-md
              px-2
              py-1
              text-xs
              text-gray-500
              hover:bg-gray-100
              dark:text-gray-400
              dark:hover:bg-gray-800
            "
          >
            关闭
          </button>
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-3">
        {loadingFiles && (
          <div className="py-6 text-center text-sm text-gray-500">
            加载中...
          </div>
        )}

        {!loadingFiles && error && (
          <div className="rounded-md bg-red-50 p-3 text-sm text-red-600 dark:bg-red-950/30 dark:text-red-400">
            {error}
          </div>
        )}

        {!loadingFiles && !error && files.length === 0 && (
          <div className="py-6 text-center text-sm text-gray-500">
            暂无生成文件
          </div>
        )}

        {!loadingFiles && !error && files.length > 0 && (
          <div className="flex flex-col gap-2">
            {files.map((file) => (
              <div
                key={file.name}
                className="
                  rounded-lg
                  border
                  border-gray-200
                  p-3
                  hover:bg-gray-50
                  dark:border-gray-800
                  dark:hover:bg-gray-900
                "
              >
                <div className="min-w-0">
                  <div
                    className="
                      truncate
                      text-sm
                      font-medium
                      text-gray-900
                      dark:text-gray-100
                    "
                    title={file.name}
                  >
                    {file.name}
                  </div>

                  <div className="mt-1 text-xs text-gray-500">
                    {formatBytes(file.size)}
                    {file.mtime ? ` · ${formatTime(file.mtime)}` : ''}
                  </div>
                </div>

                <div className="mt-3 flex justify-end">
                  <a
                    href={file.download_url}
                    target="_blank"
                    rel="noreferrer"
                    className="
                      rounded-md
                      bg-blue-600
                      px-2.5
                      py-1.5
                      text-xs
                      text-white
                      hover:bg-blue-700
                    "
                  >
                    下载
                  </a>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </aside>
  );
}

function formatTime(mtime: number) {
  try {
    return new Date(mtime * 1000).toLocaleString();
  } catch {
    return '';
  }
}

function formatBytes(bytes: number) {
  if (!Number.isFinite(bytes)) return '-';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export default function Chat() {
  const [referenceVisible, setReferenceVisible] = useState(false);
  const [referenceList, setReferenceList] = useState<ReferenceDocumentItem[]>(
    [],
  );
  // 溯源高亮预览右侧栏
  const [sourcePreviewVisible, setSourcePreviewVisible] = useState(false);
  const [sourcePreviewDocumentId, setSourcePreviewDocumentId] = useState('');
  const [sourcePreviewChunk, setSourcePreviewChunk] = useState<any>(null);

  // 打开来源列表
  const openReferencePanel = useCallback((list: ReferenceDocumentItem[]) => {
    setReferenceList(list);
    setReferenceVisible(true);

    // 打开来源列表时，关闭高亮预览栏
    setSourcePreviewVisible(false);
  }, []);

  // 关闭来源列表
  const closeReferencePanel = useCallback(() => {
    setReferenceVisible(false);
  }, []);

  // 打开溯源高亮预览右侧栏
  const openSourcePreviewPanel = useCallback(
    (documentId: string, chunk: any) => {
      setSourcePreviewDocumentId(documentId);
      setSourcePreviewChunk(chunk);
      setSourcePreviewVisible(true);

      // 重点：打开高亮预览后关闭来源列表
      // 这样主内容和预览可以各占一半
      setReferenceVisible(false);
    },
    [],
  );

  // 关闭溯源高亮预览右侧栏
  const closeSourcePreviewPanel = useCallback(() => {
    setSourcePreviewVisible(false);
    setSourcePreviewDocumentId('');
    setSourcePreviewChunk(null);
  }, []);

  const { visible, hideModal, documentId, selectedChunk, clickDocumentButton } =
    useClickDrawer();

  const { id } = useParams();
  const { navigateToChatList } = useNavigatePage();
  const { data } = useFetchDialog();
  const { t } = useTranslation();
  const [currentConversation, setCurrentConversation] =
    useState<IClientConversation>({} as IClientConversation);

  const [agentFilesVisible, setAgentFilesVisible] = useState(false);

  const openAgentFilesPanel = useCallback(() => {
    setAgentFilesVisible(true);

    if (referenceVisible) {
      closeReferencePanel();
    }

    if (sourcePreviewVisible) {
      closeSourcePreviewPanel();
    }

    if (settingVisible) {
      switchSettingVisible();
    }
  }, [
    referenceVisible,
    sourcePreviewVisible,
    closeReferencePanel,
    closeSourcePreviewPanel,
  ]);

  const closeAgentFilesPanel = useCallback(() => {
    setAgentFilesVisible(false);
  }, []);

  const { fetchConversationManually } = useFetchConversationManually();

  // 获取过往的对话
  const { handleConversationCardClick, controller, stopOutputMessage } =
    useHandleClickConversationCard();
  // 控制弹窗显示/隐藏
  const { visible: settingVisible, switchVisible: switchSettingVisible } =
    useSetModalState(false);

  // 控制是否开启调试模式
  const { isDebugMode, switchDebugMode } = useSwitchDebugMode();

  // 左侧的栏个数
  const { removeChatBox, addChatBox, chatBoxIds, hasSingleChatBox } =
    useAddChatBox(isDebugMode);

  // 嵌入代码模态框显示
  const { showEmbedModal, hideEmbedModal, embedVisible, beta } =
    useShowEmbedModal();

  // 从 URL 搜索参数中解析出 conversationId 和 isNew（是否新会话）
  const { conversationId, isNew } = useGetChatSearchParams();

  // 获取对话列表数据
  const { data: dialogList } = useFetchConversationList();

  const currentConversationName = useMemo(() => {
    return dialogList.find((x) => x.id === conversationId)?.name;
  }, [conversationId, dialogList]);

  // Form logic moved from ChatSettings
  // 获取聊天呢设置的校验规则
  const formSchema = useChatSettingSchema();
  // 获取保存对话框配置的函数
  const { setDialog, loading } = useSetDialog();

  // 定义一个数组状态 用来存储子组件session中传回的数组
  const [kbIds, setKbIds] = useState<string[]>([]);

  // 根据 Schema 推断出表单数据的 TypeScript 类型
  type FormSchemaType = z.infer<typeof formSchema>;

  // 初始化表单
  const form = useForm<FormSchemaType>({
    resolver: zodResolver(formSchema),
    shouldUnregister: false,
    defaultValues: {
      name: '',
      icon: '',
      description: '',
      kb_ids: [],
      prompt_config: {
        quote: true,
        keyword: false,
        tts: false,
        use_kg: false,
        refine_multiturn: true,
        system: '',
        parameters: [],
        reasoning: false,
        agent_mod: false,
        cross_languages: [],
        toc_enhance: false,
      },
      top_n: 8,
      similarity_threshold: 0.2,
      vector_similarity_weight: 0.2,
      top_k: 1024,
      meta_data_filter: {
        method: DatasetMetadata.Disabled,
        manual: [],
      },
    },
  });

  // // 表单values的提交逻辑
  // async function onSubmit(values: FormSchemaType) {
  //   // 移除llm_setting
  //   const nextValues: Record<string, any> = removeUselessFieldsFromValues(
  //     values,
  //     'llm_setting.',
  //   );

  //   // 调用 Hook 中的 setDialog 保存数据
  //   setDialog({
  //     ...omit(data, 'operator_permission'), // 保留原数据但剔除权限字段
  //     ...nextValues, // 合并新修改的值
  //     dialog_id: id, // 确保带上 ID
  //   });
  // }
  // 在 Chat 组件中
  async function onSubmit(
    values: FormSchemaType,
    options?: { silent?: boolean; successMessage?: string },
  ) {
    const nextValues = removeUselessFieldsFromValues(values, 'llm_setting.');

    // 调用 setDialog 时传入 options
    await setDialog(
      {
        ...omit(data, 'operator_permission'),
        ...nextValues,
        dialog_id: id,
      },
      options, // 透传
    );
  }

  const reasoning = !!form.watch('prompt_config.reasoning');
  const agentMod = !!form.watch('prompt_config.agent_mod');

  const setReasoningMode = useCallback(
    async (nextReasoning: boolean, nextAgentMod: boolean) => {
      const currentReasoning = !!form.getValues('prompt_config.reasoning');
      const currentAgentMod = !!form.getValues('prompt_config.agent_mod');

      // 如果已经是当前模式，不重复提交
      if (
        currentReasoning === nextReasoning &&
        currentAgentMod === nextAgentMod
      ) {
        return;
      }

      form.setValue('prompt_config.reasoning', nextReasoning, {
        shouldDirty: true,
        shouldTouch: true,
        shouldValidate: true,
      });

      form.setValue('prompt_config.agent_mod', nextAgentMod, {
        shouldDirty: true,
        shouldTouch: true,
        shouldValidate: true,
      });

      const values = form.getValues();

      await onSubmit(
        {
          ...values,
          prompt_config: {
            ...values.prompt_config,
            reasoning: nextReasoning,
            agent_mod: nextAgentMod,
          },
        },
        { silent: true },
      );
      message.success('切换成功');
    },
    [form, onSubmit],
  );

  const onEnableDeepReasoning = useCallback(() => {
    return setReasoningMode(true, false);
  }, [setReasoningMode]);

  const onEnableMultiKbReasoning = useCallback(() => {
    return setReasoningMode(false, false);
  }, [setReasoningMode]);

  const onEnableAgent = useCallback(() => {
    return setReasoningMode(false, true);
  }, [setReasoningMode]);

  function onInvalid(errors: any) {
    console.log('Form validation failed:', errors);
  }

  // 表单回显
  useEffect(() => {
    const llmSettingEnabledValues = setLLMSettingEnabledValues(
      data.llm_setting,
    );

    const nextData = {
      ...data,
      ...llmSettingEnabledValues,
    };
    // 将合并后的数据填入表单
    form.reset(nextData as FormSchemaType);
  }, [data, form]);

  // 封装了获取对话详情的逻辑
  const fetchConversation: typeof handleConversationCardClick = useCallback(
    async (conversationId, isNew) => {
      // 只有当有 ID 且不是新会话时才去拉取
      if (conversationId && !isNew) {
        const conversation = await fetchConversationManually(conversationId);
        if (!isEmpty(conversation)) {
          setCurrentConversation(conversation); // 更新本地状态
        }
      }
    },
    [fetchConversationManually],
  );

  // 传递给子组件用于切换会话的
  const handleSessionClick: typeof handleConversationCardClick = useCallback(
    (conversationId, isNew) => {
      handleConversationCardClick(conversationId, isNew); // 1. 执行通用逻辑（如跳转）
      // 2. 执行特定逻辑（如刷新数据）
      fetchConversation(conversationId, isNew);
    },
    [fetchConversation, handleConversationCardClick],
  );

  useMount(() => {
    // 第一次加载立即获取对话数据
    fetchConversation(conversationId, isNew === 'true');
  });

  const refreshCurrentConversation = useCallback(async () => {
    if (!conversationId) return null;

    const conversation = await fetchConversationManually(conversationId);

    if (!isEmpty(conversation)) {
      setCurrentConversation(conversation);
      return conversation;
    }

    return null;
  }, [conversationId, fetchConversationManually]);

  if (isDebugMode) {
    return (
      <section className="pt-14 h-[100vh] pb-24">
        <div className="flex items-center justify-between px-10 pb-5">
          <span className="text-2xl">
            {t('chat.multipleModels')} ({chatBoxIds.length}/3)
          </span>
          <Button variant={'ghost'} onClick={switchDebugMode}>
            {t('chat.exit')} <LogOut />
          </Button>
        </div>
        <MultipleChatBox
          chatBoxIds={chatBoxIds}
          controller={controller}
          removeChatBox={removeChatBox}
          addChatBox={addChatBox}
          stopOutputMessage={stopOutputMessage}
          conversation={currentConversation}
        ></MultipleChatBox>
      </section>
    );
  }

  const { data: userInfo } = useFetchUserInfo();

  const currentTenantId =
    (currentConversation as any)?.tenant_id ||
    (currentConversation as any)?.tenantId ||
    (currentConversation as any)?.user_id ||
    (currentConversation as any)?.userId ||
    (data as any)?.tenant_id ||
    (data as any)?.tenantId ||
    (data as any)?.user_id ||
    (data as any)?.userId ||
    (userInfo as any)?.tenant_id ||
    (userInfo as any)?.tenantId ||
    (userInfo as any)?.id ||
    (userInfo as any)?.user_id ||
    (userInfo as any)?.userId;

  const currentConversationId =
    (currentConversation as any)?.id ||
    (currentConversation as any)?.conversation_id ||
    conversationId;

  // 保存后端 -> 强制刷新 -> 重新拉取全量数据”
  // 先获取currentConversation, setting和kb_ids是通过表单保存后端 -> 强制刷新 -> 重新拉取全量数据再次调用fetchConversation更新currentConversation
  // 然后是通过currentConversation 传入对话模型的
  return (
    <Form {...form}>
      <form
        onSubmit={form.handleSubmit(onSubmit, onInvalid)}
        className="h-full flex flex-col pr-5"
      >
        {/* <div className="flex flex-1 min-h-0 pb-1">

          <Sessions
            hasSingleChatBox={hasSingleChatBox}
            handleConversationCardClick={handleSessionClick}
            switchSettingVisible={switchSettingVisible}
          ></Sessions> */}

        {/* <div className="flex flex-1 min-h-0 pb-1 overflow-hidden"> */}
        <div
          className="
    flex flex-1 min-h-0 pb-1 overflow-hidden
    bg-[#F3FAF7]
    dark:bg-transparent
  "
        >
          {/* 左侧会话列表：自己内部滚动 */}
          <Sessions
            hasSingleChatBox={hasSingleChatBox}
            handleConversationCardClick={handleSessionClick}
            switchSettingVisible={switchSettingVisible}
          />

          {/* 右侧整体区域 */}
          {/* <div className="flex flex-col flex-1 min-w-0 h-full min-h-0 overflow-hidden">
           
            <div className="shrink-0 flex items-center px-5 py-0 mt-2 bg-transparent">
              <div className="flex items-center gap-2 flex-1 min-w-0">
                <div
                  className={cn('flex items-center gap-1', {
                    hidden: settingVisible,
                  })}
                >
                  <div className="w-auto">
                    <KnowledgeBaseFormField hideLabel />
                  </div>

                  <SavingButton
                    loading={loading}
                    className="bg-white text-black hover:bg-gray-100 border"
                  />
                </div>
              </div>
            </div>

            
            <div className="flex flex-1 min-h-0 overflow-hidden">
            
              <div className="flex-1 min-w-0 min-h-0 overflow-hidden">
                <SingleChatBox
                  controller={controller}
                  stopOutputMessage={stopOutputMessage}
                  conversation={currentConversation}
                />
              </div>

              
              <ChatSettings
                className={cn('shrink-0', {
                  hidden: !settingVisible,
                })}
                switchSettingVisible={switchSettingVisible}
                onSubmit={form.handleSubmit(onSubmit, onInvalid)}
                loading={loading}
              />
            </div>
          </div>
        </div> */}

          <div className="flex flex-col flex-1 min-w-0 h-full min-h-0 overflow-hidden">
            {/* <div
  className="
    flex flex-col flex-1 min-w-0 h-full min-h-0 overflow-hidden
    bg-[#E3F5F1]
    dark:bg-[#071A16]
  "
> */}
            <div className="shrink-0 flex items-center px-5 py-0 mt-2 bg-transparent">
              <div className="flex items-center gap-2 flex-1 min-w-0">
                <div
                  className={cn('flex items-center gap-1', {
                    hidden:
                      settingVisible ||
                      referenceVisible ||
                      sourcePreviewVisible,
                  })}
                >
                  <div className="w-auto">
                    <KnowledgeBaseFormField hideLabel />
                  </div>

                  <SavingButton
                    loading={loading}
                    className="bg-white text-black hover:bg-gray-100 border"
                  />
                </div>

                {agentMod && currentTenantId && currentConversationId && (
                  <button
                    type="button"
                    onClick={openAgentFilesPanel}
                    className="
      h-9
      rounded-md
      border
      border-gray-200
      bg-white
      px-3
      text-sm
      text-gray-700
      hover:bg-gray-100
      dark:border-gray-700
      dark:bg-gray-900
      dark:text-gray-200
      dark:hover:bg-gray-800
    "
                  >
                    会话文件
                  </button>
                )}
              </div>
            </div>

            <div className="flex flex-1 min-h-0 overflow-hidden">
              <div
                id="chat-main-content"
                className={cn(
                  'min-w-0 min-h-0 overflow-hidden',
                  sourcePreviewVisible ? 'basis-1/2 w-1/2 flex-none' : 'flex-1',
                )}
              >
                <SingleChatBox
                  controller={controller}
                  stopOutputMessage={stopOutputMessage}
                  conversation={currentConversation}
                  clickDocumentButton={clickDocumentButton}
                  onOpenReferencePanel={openReferencePanel}
                  reasoning={reasoning}
                  agentMod={agentMod}
                  onEnableDeepReasoning={onEnableDeepReasoning}
                  onEnableMultiKbReasoning={onEnableMultiKbReasoning}
                  onEnableAgent={onEnableAgent}
                  refreshConversation={refreshCurrentConversation}
                />
              </div>

              <SourcePreviewPanel
                className={cn(
                  'h-full min-h-0 min-w-0 flex-none basis-1/2 w-1/2',
                  {
                    hidden: !sourcePreviewVisible,
                  },
                )}
                documentId={sourcePreviewDocumentId}
                chunk={sourcePreviewChunk}
                visible={sourcePreviewVisible}
                onClose={closeSourcePreviewPanel}
              />

              {/* 右侧溯源来源列表 */}
              <ReferenceSourcePanel
                className={cn('shrink-0', {
                  hidden: !referenceVisible,
                })}
                list={referenceList}
                onClose={closeReferencePanel}
                onOpenSourcePreview={openSourcePreviewPanel}
              />

              <AgentFilesPanel
                className={cn('shrink-0', {
                  hidden: !agentFilesVisible,
                })}
                tenantId={currentTenantId}
                conversationId={currentConversationId}
                visible={agentFilesVisible}
                onClose={closeAgentFilesPanel}
              />

              {/* 右侧设置面板 */}
              <ChatSettings
                className={cn('shrink-0', {
                  hidden: !settingVisible,
                })}
                switchSettingVisible={switchSettingVisible}
                onSubmit={form.handleSubmit(onSubmit, onInvalid)}
                loading={loading}
              />
            </div>
          </div>
        </div>

        {embedVisible && (
          <EmbedDialog
            visible={embedVisible}
            hideModal={hideEmbedModal}
            token={id!}
            from={SharedFrom.Chat}
            beta={beta}
            isAgent={false}
          ></EmbedDialog>
        )}

        {visible && (
          <PdfSheet
            visible={visible}
            hideModal={hideModal}
            documentId={documentId}
            chunk={selectedChunk}
          />
        )}
      </form>
    </Form>
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

      // 文档基本信息
      document_id: documentId,
      doc_id: documentId,
      document_name: documentName,
      doc_name: documentName,
      docnm_kwd: item.docnm_kwd || documentName,
      url: documentUrl,

      // 高亮信息
      positions: mergedPositions,
      content: mergedContent,

      // 保留 chunks
      chunks,
      // 当前点击的参考来源序号
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
      {/* 面板头部 */}
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

      {/* 来源列表 */}
      <div
        className="
          flex-1 overflow-y-auto overscroll-contain px-4 py-4
        "
      >
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
                  {/* 序号 */}
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
                            {/* 高亮预览 */}
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

                            {/* 显示原文 */}
                            <a
                              href={
                                documentUrl ||
                                `/document/${docId}?ext=${getExtension(docName)}&prefix=document`
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

                            {/* 下载文档 */}
                            <a
                              href={`/v1/document/get/${docId}?ext=${getExtension(docName)}`}
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
                      <div
                        className="
                          mt-1 pl-7 text-xs text-gray-400 dark:text-gray-500
                        "
                      >
                        引用 {count} 处
                      </div>
                    )}

                    {item.content && (
                      <div
                        className="
                          mt-2 line-clamp-3 pl-7
                          text-xs leading-5 text-gray-500 dark:text-gray-400
                        "
                      >
                        {item.content.replace(/\n/g, ' ')}
                      </div>
                    )}

                    {/* <div
                      className="
                        mt-1 truncate pl-7
                        text-xs text-gray-400 dark:text-gray-500
                      "
                    >
                      {documentUrl || '本地文档'}
                    </div> */}
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
      <div
        className="
          flex shrink-0 items-center justify-between
          px-3 pt-1 pb-0.5
        "
      >
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
