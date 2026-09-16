import EmbedDialog from '@/components/embed-dialog';
import { useShowEmbedModal } from '@/components/embed-dialog/use-show-embed-dialog';
import FileIcon from '@/components/file-icon';
import { KnowledgeBaseFormField } from '@/components/knowledge-base-item';
import NewDocumentLink from '@/components/new-document-link';
import PdfSheet from '@/components/pdf-drawer';
import { useClickDrawer } from '@/components/pdf-drawer/hooks';
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
import { IClientConversation } from '@/interfaces/database/chat';
import { cn } from '@/lib/utils';
import { getExtension } from '@/utils/document-util';
import {
  removeUselessFieldsFromValues,
  setLLMSettingEnabledValues,
} from '@/utils/form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useMount } from 'ahooks';
import { isEmpty, omit } from 'lodash';
import { LogOut } from 'lucide-react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
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

import DocumentPreviewer from '@/components/pdf-previewer';
import { message } from 'antd';

export default function Chat() {
  // 来源列表
  const [referenceVisible, setReferenceVisible] = useState(false);
  const [referenceList, setReferenceList] = useState<ReferenceDocumentItem[]>(
    [],
  );

  // 溯源高亮预览右侧栏
  const [sourcePreviewVisible, setSourcePreviewVisible] = useState(false);
  const [sourcePreviewDocumentId, setSourcePreviewDocumentId] = useState('');
  const [sourcePreviewChunk, setSourcePreviewChunk] = useState<any>(null);

  // 聊天设置
  const { visible: settingVisible, switchVisible: switchSettingVisible } =
    useSetModalState(false);

  // 打开聊天设置时，关闭来源列表和溯源预览
  useEffect(() => {
    if (settingVisible) {
      setReferenceVisible(false);

      setSourcePreviewVisible(false);
      setSourcePreviewDocumentId('');
      setSourcePreviewChunk(null);
    }
  }, [settingVisible]);

  // 打开来源列表
  const openReferencePanel = useCallback(
    (list: ReferenceDocumentItem[]) => {
      setReferenceList(list);
      setReferenceVisible(true);

      // 打开来源列表时，关闭高亮预览栏
      setSourcePreviewVisible(false);
      setSourcePreviewDocumentId('');
      setSourcePreviewChunk(null);

      // 打开来源列表时，关闭设置面板
      if (settingVisible) {
        switchSettingVisible();
      }
    },
    [settingVisible, switchSettingVisible],
  );

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

      // 打开高亮预览后关闭来源列表
      setReferenceVisible(false);

      // 打开高亮预览时，关闭设置面板
      if (settingVisible) {
        switchSettingVisible();
      }
    },
    [settingVisible, switchSettingVisible],
  );

  // 关闭溯源高亮预览右侧栏
  const closeSourcePreviewPanel = useCallback(() => {
    setSourcePreviewVisible(false);
    setSourcePreviewDocumentId('');
    setSourcePreviewChunk(null);
  }, []);
  // const [referenceVisible, setReferenceVisible] = useState(false);
  // const [referenceList, setReferenceList] = useState<ReferenceDocumentItem[]>(
  //   [],
  // );
  // // 溯源高亮预览右侧栏
  // const [sourcePreviewVisible, setSourcePreviewVisible] = useState(false);
  // const [sourcePreviewDocumentId, setSourcePreviewDocumentId] = useState('');
  // const [sourcePreviewChunk, setSourcePreviewChunk] = useState<any>(null);

  // // 打开来源列表
  // const openReferencePanel = useCallback((list: ReferenceDocumentItem[]) => {
  //   setReferenceList(list);
  //   setReferenceVisible(true);

  //   // 打开来源列表时，关闭高亮预览栏
  //   setSourcePreviewVisible(false);
  // }, []);

  // // 关闭来源列表
  // const closeReferencePanel = useCallback(() => {
  //   setReferenceVisible(false);
  // }, []);

  // // 打开溯源高亮预览右侧栏
  // const openSourcePreviewPanel = useCallback(
  //   (documentId: string, chunk: any) => {
  //     setSourcePreviewDocumentId(documentId);
  //     setSourcePreviewChunk(chunk);
  //     setSourcePreviewVisible(true);

  //     // 重点：打开高亮预览后关闭来源列表
  //     // 这样主内容和预览可以各占一半
  //     setReferenceVisible(false);
  //   },
  //   [],
  // );

  // // 关闭溯源高亮预览右侧栏
  // const closeSourcePreviewPanel = useCallback(() => {
  //   setSourcePreviewVisible(false);
  //   setSourcePreviewDocumentId('');
  //   setSourcePreviewChunk(null);
  // }, []);

  const { visible, hideModal, documentId, selectedChunk, clickDocumentButton } =
    useClickDrawer();

  const { id } = useParams();
  const { navigateToChatList } = useNavigatePage();
  const { data, refetch } = useFetchDialog();

  const { t } = useTranslation();
  const [currentConversation, setCurrentConversation] =
    useState<IClientConversation>({} as IClientConversation);

  const initializedRef = useRef(false);

  const { fetchConversationManually } = useFetchConversationManually();

  const { handleConversationCardClick, controller, stopOutputMessage } =
    useHandleClickConversationCard();

  const { isDebugMode, switchDebugMode } = useSwitchDebugMode();

  const { removeChatBox, addChatBox, chatBoxIds, hasSingleChatBox } =
    useAddChatBox(isDebugMode);

  const { showEmbedModal, hideEmbedModal, embedVisible, beta } =
    useShowEmbedModal();

  const { conversationId, isNew } = useGetChatSearchParams();

  const { data: dialogList } = useFetchConversationList();

  const currentConversationName = useMemo(() => {
    return dialogList.find((x) => x.id === conversationId)?.name;
  }, [conversationId, dialogList]);

  const formSchema = useChatSettingSchema();

  const { setDialog, loading } = useSetDialog();

  const [kbIds, setKbIds] = useState<string[]>([]);

  type FormSchemaType = z.infer<typeof formSchema>;

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
        prologue: '',
        empty_response: '',
        parameters: [],
        reasoning: false,
        agent_mod: false,
        project_compliance: false,
        experiment_report: false,
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

  const closeAfterSubmitRef = useRef(false);

  // async function onSubmit(values: FormSchemaType) {
  //   const nextValues: Record<string, any> = removeUselessFieldsFromValues(
  //     values,
  //     'llm_setting.',
  //   );

  //   const result = await setDialog({
  //     ...omit(data, 'operator_permission'),
  //     ...nextValues,
  //     dialog_id: id,
  //   });

  //   if (result !== 0) return;

  //   const { data: latestData } = await refetch();

  //   if (latestData && !isEmpty(latestData)) {
  //     const llmSettingEnabledValues = setLLMSettingEnabledValues(
  //       latestData.llm_setting,
  //     );

  //     form.reset({
  //       ...latestData,
  //       ...llmSettingEnabledValues,
  //     } as FormSchemaType);

  //     // setCurrentConversation(latestData as IClientConversation);
  //   }

  //   // 提交完成后关闭设置面板
  //   if (settingVisible) {
  //     switchSettingVisible();
  //   }
  // }
  async function onSubmit(
    values: FormSchemaType,
    options?: { silent?: boolean; successMessage?: string },
  ) {
    const nextValues = removeUselessFieldsFromValues(values, 'llm_setting.');

    const result = await setDialog(
      {
        ...omit(data, 'operator_permission'),
        ...nextValues,
        dialog_id: id,
      },
      options, // 透传给 setDialog
    );

    if (result !== 0) return;

    const { data: latestData } = await refetch();
    if (latestData && !isEmpty(latestData)) {
      const llmSettingEnabledValues = setLLMSettingEnabledValues(
        latestData.llm_setting,
      );
      form.reset({
        ...latestData,
        ...llmSettingEnabledValues,
      } as FormSchemaType);
    }

    // 提交完成后关闭设置面板（仅当设置面板打开时）
    if (settingVisible) {
      switchSettingVisible();
    }
  }

  const reasoning = !!form.watch('prompt_config.reasoning');
  const agentMod = !!form.watch('prompt_config.agent_mod');
  const projectCompliance = !!form.watch('prompt_config.project_compliance');
  const experimentReport = !!form.watch('prompt_config.experiment_report');

  const setMode = useCallback(
    async (
      nextReasoning: boolean,
      nextAgentMod: boolean,
      nextProjectCompliance: boolean,
      nextExperimentReport: boolean,
    ) => {
      const values = form.getValues();

      const nextPromptConfig = {
        ...values.prompt_config,
        reasoning: nextReasoning,
        agent_mod: nextAgentMod,
        project_compliance: nextProjectCompliance,
        experiment_report: nextExperimentReport,
      };

      const currentPromptConfig = values.prompt_config;

      if (
        !!currentPromptConfig.reasoning === nextReasoning &&
        !!currentPromptConfig.agent_mod === nextAgentMod &&
        !!currentPromptConfig.project_compliance === nextProjectCompliance &&
        !!currentPromptConfig.experiment_report === nextExperimentReport
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

      form.setValue('prompt_config.project_compliance', nextProjectCompliance, {
        shouldDirty: true,
        shouldTouch: true,
        shouldValidate: true,
      });

      form.setValue('prompt_config.experiment_report', nextExperimentReport, {
        shouldDirty: true,
        shouldTouch: true,
        shouldValidate: true,
      });

      const success = await onSubmit(
        {
          ...values,
          prompt_config: nextPromptConfig,
        },
        { silent: true },
      );

      if (success) {
        message.success('切换成功');
      }
    },
    [form, onSubmit],
  );

  const onEnableDeepReasoning = useCallback(() => {
    return setMode(true, false, false, false);
  }, [setMode]);

  const onEnableMultiKbReasoning = useCallback(() => {
    return setMode(false, false, false, false);
  }, [setMode]);

  const onEnableAgent = useCallback(() => {
    return setMode(false, true, false, false);
  }, [setMode]);

  const onEnableProjectCompliance = useCallback(() => {
    return setMode(false, false, true, false);
  }, [setMode]);

  const onEnableExperimentReport = useCallback(() => {
    return setMode(false, false, false, true);
  }, [setMode]);

  function onInvalid(errors: any) {
    console.log('Form validation failed:', errors);
  }

  // 切换会话时允许重新初始化表单
  useEffect(() => {
    initializedRef.current = false;
  }, [id, conversationId]);

  // 表单回显：只用于首次加载/切换会话
  useEffect(() => {
    if (!data || isEmpty(data)) return;
    if (initializedRef.current) return;

    initializedRef.current = true;

    const llmSettingEnabledValues = setLLMSettingEnabledValues(
      data.llm_setting,
    );

    const nextData = {
      ...data,
      ...llmSettingEnabledValues,
    };

    form.reset(nextData as FormSchemaType);
    // setCurrentConversation(data as IClientConversation);
  }, [data, form]);

  const fetchConversation: typeof handleConversationCardClick = useCallback(
    async (conversationId, isNew) => {
      if (conversationId && !isNew) {
        const conversation = await fetchConversationManually(conversationId);

        if (!isEmpty(conversation)) {
          setCurrentConversation(conversation);
        }
      }
    },
    [fetchConversationManually],
  );
  const refreshCurrentConversation = useCallback(
    async (targetConversationId?: string) => {
      const id = targetConversationId || conversationId;

      if (!id) return null;

      const conversation = await fetchConversationManually(id);

      if (!isEmpty(conversation)) {
        setCurrentConversation(conversation);
        return conversation;
      }

      return null;
    },
    [conversationId, fetchConversationManually],
  );

  const handleSessionClick: typeof handleConversationCardClick = useCallback(
    (conversationId, isNew) => {
      handleConversationCardClick(conversationId, isNew);
      fetchConversation(conversationId, isNew);
    },
    [fetchConversation, handleConversationCardClick],
  );

  const openChatSettings = useCallback(async () => {
    if (settingVisible) {
      switchSettingVisible();
      return;
    }

    const { data: latestData } = await refetch();

    if (latestData && !isEmpty(latestData)) {
      const llmSettingEnabledValues = setLLMSettingEnabledValues(
        latestData.llm_setting,
      );

      form.reset({
        ...latestData,
        ...llmSettingEnabledValues,
      } as FormSchemaType);

      // 不要在这里覆盖 currentConversation
      // setCurrentConversation(latestData as IClientConversation);

      initializedRef.current = true;
    }

    switchSettingVisible();
  }, [settingVisible, switchSettingVisible, refetch, form]);

  useMount(() => {
    fetchConversation(conversationId, isNew === 'true');
  });

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
        />
      </section>
    );
  }

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
            switchSettingVisible={openChatSettings}
          />

          <Card className="flex-1 min-w-0 bg-transparent border h-full">

            <CardContent className="flex p-0 h-full">
              <Card className="flex flex-col flex-1 bg-transparent min-w-0">
                <CardHeader className={cn('py-2 px-5')}>
                  <CardTitle className="flex justify-between items-center text-base">
                    <div className="flex items-center gap- flex-1 min-w-0 ml-[-8px]">
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
                  </CardTitle>
                </CardHeader>

                <CardContent className="flex-1 p-0 min-h-0">

                  <SingleChatBox
                    controller={controller}
                    stopOutputMessage={stopOutputMessage}
                    conversation={currentConversation}
                  />
                </CardContent>
              </Card>

              <ChatSettings
                className={cn({ hidden: !settingVisible })}
                switchSettingVisible={switchSettingVisible}
                onSubmit={form.handleSubmit(onSubmit, onInvalid)}
                loading={loading}
              />
            </CardContent>
          </Card>
        </div> */}

        {/* <div className="flex flex-1 min-h-0 pb-1 overflow-hidden"> */}
        <div className="flex flex-1 min-h-0 pb-1 overflow-hidden bg-[radial-gradient(circle_at_0%_20%,rgba(214,240,252,0.38)_0%,rgba(232,246,252,0.26)_20%,rgba(249,252,253,0)_48%),linear-gradient(90deg,rgba(247,251,253,1)_0%,rgba(249,252,253,1)_38%,rgba(246,250,252,1)_100%)] dark:bg-none dark:bg-transparent">
          {/* 左侧会话列表：自己内部滚动 */}
          <Sessions
            hasSingleChatBox={hasSingleChatBox}
            handleConversationCardClick={handleSessionClick}
            switchSettingVisible={openChatSettings}
          />

          <div className="flex flex-col flex-1 min-w-0 h-full min-h-0 overflow-hidden">
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
                  projectCompliance={projectCompliance}
                  experimentReport={experimentReport}
                  onEnableDeepReasoning={onEnableDeepReasoning}
                  onEnableMultiKbReasoning={onEnableMultiKbReasoning}
                  onEnableAgent={onEnableAgent}
                  onEnableProjectCompliance={onEnableProjectCompliance}
                  onEnableExperimentReport={onEnableExperimentReport}
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
          />
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

// export default function Chat() {
//   const { id } = useParams();
//   const { navigateToChatList } = useNavigatePage();
//   const { data } = useFetchDialog();
//   const { t } = useTranslation();

//   const [currentConversation, setCurrentConversation] =
//     useState<IClientConversation>({} as IClientConversation);

//   // 保存后最新的 dialog，防止旧 data 覆盖表单
//   const [latestDialog, setLatestDialog] = useState<any>(null);

//   // 保存后短时间内跳过旧 data reset
//   const justSavedRef = useRef(false);

//   const { fetchConversationManually } = useFetchConversationManually();

//   const { handleConversationCardClick, controller, stopOutputMessage } =
//     useHandleClickConversationCard();

//   const { visible: settingVisible, switchVisible: switchSettingVisible } =
//     useSetModalState(false);

//   const { isDebugMode, switchDebugMode } = useSwitchDebugMode();

//   const { removeChatBox, addChatBox, chatBoxIds, hasSingleChatBox } =
//     useAddChatBox(isDebugMode);

//   const { showEmbedModal, hideEmbedModal, embedVisible, beta } =
//     useShowEmbedModal();

//   const { conversationId, isNew } = useGetChatSearchParams();

//   const { data: dialogList } = useFetchConversationList();

//   const currentConversationName = useMemo(() => {
//     return dialogList.find((x) => x.id === conversationId)?.name;
//   }, [conversationId, dialogList]);

//   const formSchema = useChatSettingSchema();

//   const { setDialog, loading } = useSetDialog();

//   const [kbIds, setKbIds] = useState<string[]>([]);

//   type FormSchemaType = z.infer<typeof formSchema>;

//   const form = useForm<FormSchemaType>({
//     resolver: zodResolver(formSchema),
//     shouldUnregister: false,
//     defaultValues: {
//       name: '',
//       icon: '',
//       description: '',
//       kb_ids: [],
//       prompt_config: {
//         quote: true,
//         keyword: false,
//         tts: false,
//         use_kg: false,
//         refine_multiturn: true,
//         system: '',
//         prologue: '',
//         empty_response: '',
//         parameters: [],
//         reasoning: false,
//         cross_languages: [],
//         toc_enhance: false,
//       },
//       top_n: 8,
//       similarity_threshold: 0.2,
//       vector_similarity_weight: 0.2,
//       top_k: 1024,
//       meta_data_filter: {
//         method: DatasetMetadata.Disabled,
//         manual: [],
//       },
//     },
//   });

//   async function onSubmit(values: FormSchemaType) {
//     const nextValues: Record<string, any> = removeUselessFieldsFromValues(
//       values,
//       'llm_setting.',
//     );

//     const payload = {
//       ...omit(data, 'operator_permission'),
//       ...nextValues,
//       dialog_id: id,
//     };

//     console.log('====== submit payload ======');
//     console.log('submit prologue:', payload.prompt_config?.prologue);
//     console.log('submit empty_response:', payload.prompt_config?.empty_response);

//     const savedDialog = await setDialog(payload);

//     console.log('====== setDialog return ======');
//     console.log('savedDialog:', savedDialog);
//     console.log('saved prologue:', savedDialog?.prompt_config?.prologue);
//     console.log(
//       'saved empty_response:',
//       savedDialog?.prompt_config?.empty_response,
//     );

//     if (!savedDialog) return;

//     const nextDialog = {
//       ...savedDialog,
//       prompt_config: {
//         ...savedDialog.prompt_config,
//         ...nextValues.prompt_config,
//       },
//     };

//     justSavedRef.current = true;
//     setLatestDialog(nextDialog);

//     setCurrentConversation((prev) => ({
//       ...prev,
//       ...nextDialog,
//     }));

//     const llmSettingEnabledValues = setLLMSettingEnabledValues(
//       nextDialog.llm_setting,
//     );

//     form.reset({
//       ...nextDialog,
//       ...llmSettingEnabledValues,
//     } as FormSchemaType);

//     console.log('====== after submit form.reset ======');
//     console.log(
//       'form prologue:',
//       form.getValues('prompt_config.prologue'),
//     );
//     console.log(
//       'form empty_response:',
//       form.getValues('prompt_config.empty_response'),
//     );

//     setTimeout(() => {
//       justSavedRef.current = false;
//     }, 1000);
//   }

//   function onInvalid(errors: any) {
//     console.log('Form validation failed:', errors);
//   }

//   // 切换会话时清空保存后的本地数据，避免串数据
//   useEffect(() => {
//     setLatestDialog(null);
//     justSavedRef.current = false;
//   }, [conversationId]);

//   // 表单回显：优先使用保存后的 latestDialog，避免旧 data 覆盖
//   useEffect(() => {
//     if (!data || isEmpty(data)) return;

//     if (justSavedRef.current && latestDialog) {
//       console.log('====== skip old data reset after save ======');
//       console.log(
//         'latestDialog empty_response:',
//         latestDialog?.prompt_config?.empty_response,
//       );
//       return;
//     }

//     const sourceData = latestDialog ?? data;

//     console.log('====== form reset by useEffect ======');
//     console.log('reset source:', latestDialog ? 'latestDialog' : 'data');
//     console.log('reset prologue:', sourceData?.prompt_config?.prologue);
//     console.log(
//       'reset empty_response:',
//       sourceData?.prompt_config?.empty_response,
//     );

//     const llmSettingEnabledValues = setLLMSettingEnabledValues(
//       sourceData.llm_setting,
//     );

//     form.reset({
//       ...sourceData,
//       ...llmSettingEnabledValues,
//     } as FormSchemaType);
//   }, [data, latestDialog, form]);

//   const fetchConversation: typeof handleConversationCardClick = useCallback(
//     async (conversationId, isNew) => {
//       if (conversationId && !isNew) {
//         const conversation = await fetchConversationManually(conversationId);

//         if (!isEmpty(conversation)) {
//           setCurrentConversation(conversation);
//         }
//       }
//     },
//     [fetchConversationManually],
//   );

//   const handleSessionClick: typeof handleConversationCardClick = useCallback(
//     (conversationId, isNew) => {
//       handleConversationCardClick(conversationId, isNew);
//       fetchConversation(conversationId, isNew);
//     },
//     [fetchConversation, handleConversationCardClick],
//   );

//   useMount(() => {
//     fetchConversation(conversationId, isNew === 'true');
//   });

//   if (isDebugMode) {
//     return (
//       <section className="pt-14 h-[100vh] pb-24">
//         <div className="flex items-center justify-between px-10 pb-5">
//           <span className="text-2xl">
//             {t('chat.multipleModels')} ({chatBoxIds.length}/3)
//           </span>
//           <Button variant={'ghost'} onClick={switchDebugMode}>
//             {t('chat.exit')} <LogOut />
//           </Button>
//         </div>

//         <MultipleChatBox
//           chatBoxIds={chatBoxIds}
//           controller={controller}
//           removeChatBox={removeChatBox}
//           addChatBox={addChatBox}
//           stopOutputMessage={stopOutputMessage}
//           conversation={currentConversation}
//         />
//       </section>
//     );
//   }

//   return (
//     <Form {...form}>
//       <form
//         onSubmit={form.handleSubmit(onSubmit, onInvalid)}
//         className="h-full flex flex-col pr-5"
//       >
//         <div className="flex flex-1 min-h-0 pb-9">
//           <Sessions
//             hasSingleChatBox={hasSingleChatBox}
//             handleConversationCardClick={handleSessionClick}
//             switchSettingVisible={switchSettingVisible}
//           />

//           <Card className="flex-1 min-w-0 bg-transparent border h-full">
//             <CardContent className="flex p-0 h-full">
//               <Card className="flex flex-col flex-1 bg-transparent min-w-0">
//                 <CardHeader className={cn('py-2 px-5')}>
//                   <CardTitle className="flex justify-between items-center text-base">
//                     <div className="flex items-center gap-4 flex-1 min-w-0 ml-[-8px]">
//                       <div
//                         className={cn('flex items-center gap-2', {
//                           hidden: settingVisible,
//                         })}
//                       >
//                         <div className="w-[240px]">
//                           <KnowledgeBaseFormField hideLabel />
//                         </div>

//                         <SavingButton
//                           loading={loading}
//                           className="bg-white text-black hover:bg-gray-100 border"
//                         />
//                       </div>
//                     </div>
//                   </CardTitle>
//                 </CardHeader>

//                 <CardContent className="flex-1 p-0 min-h-[300px] pt-0">
//                   <SingleChatBox
//                     controller={controller}
//                     stopOutputMessage={stopOutputMessage}
//                     conversation={currentConversation}
//                   />
//                 </CardContent>
//               </Card>

//               <ChatSettings
//                 className={cn({ hidden: !settingVisible })}
//                 switchSettingVisible={switchSettingVisible}
//                 onSubmit={form.handleSubmit(onSubmit, onInvalid)}
//                 loading={loading}
//               />
//             </CardContent>
//           </Card>
//         </div>

//         {embedVisible && (
//           <EmbedDialog
//             visible={embedVisible}
//             hideModal={hideEmbedModal}
//             token={id!}
//             from={SharedFrom.Chat}
//             beta={beta}
//             isAgent={false}
//           />
//         )}
//       </form>
//     </Form>
//   );
// }
