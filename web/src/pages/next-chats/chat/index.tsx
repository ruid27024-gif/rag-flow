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
import { useChatSettingSchema } from './app-settings/use-chat-setting-schema';
import { MultipleChatBox } from './chat-box/multiple-chat-box';
import { SingleChatBox } from './chat-box/single-chat-box';
import { Sessions } from './sessions';
import { useAddChatBox } from './use-add-box';
import { useSwitchDebugMode } from './use-switch-debug-mode';

import DocumentPreviewer from '@/components/pdf-previewer';
import { message } from 'antd';
// import WorkspacePanel from './WorkspacePanel';
// console.log('WorkspacePanel =', WorkspacePanel);
import { DocPreviewer } from '@/components/document-preview/doc-preview';
import { getAuthorization } from '@/utils/authorization-util';
import {
  ChevronLeft,
  Download,
  Eye,
  File, // 👈 新增：表格
  FileArchive, // 已有：文本类
  FileImage, // 👈 新增：图片
  FileSpreadsheet, // 👈 新增：通用文件
  FileText,
  Loader2,
  X,
} from 'lucide-react';
import * as React from 'react';

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

  // ✅ 工作区侧边栏
  const [workspaceVisible, setWorkspaceVisible] = useState(false);

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
      setWorkspaceVisible(false);
    }
  }, [settingVisible]);

  // 打开工作区：关掉其它右侧面板
  const openWorkspace = useCallback(() => {
    setWorkspaceVisible(true);

    setReferenceVisible(false);
    setSourcePreviewVisible(false);
    setSourcePreviewDocumentId('');
    setSourcePreviewChunk(null);

    if (settingVisible) {
      switchSettingVisible();
    }
  }, [settingVisible, switchSettingVisible]);

  // 关闭工作区
  const closeWorkspace = useCallback(() => {
    setWorkspaceVisible(false);
  }, []);

  // 打开来源列表
  const openReferencePanel = useCallback(
    (list: ReferenceDocumentItem[]) => {
      setReferenceList(list);
      setReferenceVisible(true);

      // 打开来源列表时，关闭高亮预览栏
      setSourcePreviewVisible(false);
      setSourcePreviewDocumentId('');
      setSourcePreviewChunk(null);
      setWorkspaceVisible(false);

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
      setWorkspaceVisible(false);

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
        customer_complaint: false,
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

    if (result !== 0) return result;

    const { data: latestData } = await refetch();
    if (latestData && !isEmpty(latestData)) {
      const llmSettingEnabledValues = setLLMSettingEnabledValues(
        latestData.llm_setting,
      );
      form.reset({
        ...latestData,
        prompt_config: {
          ...latestData.prompt_config,
          ...values.prompt_config,
        },
        ...llmSettingEnabledValues,
      } as FormSchemaType);
    }

    // 提交完成后关闭设置面板（仅当设置面板打开时）
    if (settingVisible) {
      switchSettingVisible();
    }

    return result;
  }

  // ===================== 全局自动保存 =====================
  const autoSaveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isAutoSavingRef = useRef(false);
  const skipFirstWatchRef = useRef(true);

  useEffect(() => {
    const subscription = form.watch((values) => {
      // 首次渲染 & 切换会话时的 form.reset 不触发保存
      if (skipFirstWatchRef.current) return;
      if (isAutoSavingRef.current) return;

      if (autoSaveTimerRef.current) clearTimeout(autoSaveTimerRef.current);

      autoSaveTimerRef.current = setTimeout(async () => {
        isAutoSavingRef.current = true;
        try {
          await onSubmit(values as FormSchemaType, { silent: true });
        } catch (err) {
          console.error('自动保存失败:', err);
        } finally {
          // 延迟解锁，避免 onSubmit 里的 form.reset 再触发一轮
          setTimeout(() => {
            isAutoSavingRef.current = false;
          }, 600);
        }
      }, 500);
    });

    return () => {
      subscription.unsubscribe();
      if (autoSaveTimerRef.current) clearTimeout(autoSaveTimerRef.current);
    };
  }, [form, onSubmit]);

  // 表单回显完成后，才允许 watch 触发自动保存
  useEffect(() => {
    if (!data || isEmpty(data)) return;
    // 等 form.reset 完成，下一帧再解除跳过
    const timer = setTimeout(() => {
      skipFirstWatchRef.current = false;
    }, 300);
    return () => clearTimeout(timer);
  }, [data]);

  const reasoning = !!form.watch('prompt_config.reasoning');
  const agentMod = !!form.watch('prompt_config.agent_mod');
  const projectCompliance = !!form.watch('prompt_config.project_compliance');
  const experimentReport = !!form.watch('prompt_config.experiment_report');
  const customerComplaint = !!form.watch('prompt_config.customer_complaint');

  const setMode = useCallback(
    async (
      nextReasoning: boolean,
      nextAgentMod: boolean,
      nextProjectCompliance: boolean,
      nextExperimentReport: boolean,
      nextCustomerComplaint: boolean,
    ) => {
      const values = form.getValues();

      const nextPromptConfig = {
        ...values.prompt_config,
        reasoning: nextReasoning,
        agent_mod: nextAgentMod,
        project_compliance: nextProjectCompliance,
        experiment_report: nextExperimentReport,
        customer_complaint: nextCustomerComplaint,
      };

      const currentPromptConfig = values.prompt_config;

      if (
        !!currentPromptConfig.reasoning === nextReasoning &&
        !!currentPromptConfig.agent_mod === nextAgentMod &&
        !!currentPromptConfig.project_compliance === nextProjectCompliance &&
        !!currentPromptConfig.experiment_report === nextExperimentReport &&
        !!currentPromptConfig.customer_complaint === nextCustomerComplaint
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

      form.setValue('prompt_config.customer_complaint', nextCustomerComplaint, {
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
    return setMode(true, false, false, false, false);
  }, [setMode]);

  const onEnableMultiKbReasoning = useCallback(() => {
    return setMode(false, false, false, false, false);
  }, [setMode]);

  const onEnableAgent = useCallback(() => {
    return setMode(false, true, false, false, false);
  }, [setMode]);

  const onEnableProjectCompliance = useCallback(() => {
    return setMode(false, false, true, false, false);
  }, [setMode]);

  const onEnableExperimentReport = useCallback(() => {
    return setMode(false, false, false, true, false);
  }, [setMode]);

  const onEnableCustomerComplaint = useCallback(() => {
    return setMode(false, false, false, false, true);
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
    setWorkspaceVisible(false);
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

  const [isWelcomePage, setIsWelcomePage] = useState(false);
  // 👇 新增：侧边栏已激活的技能
  const [activeSkills, setActiveSkills] = useState<SkillItem[]>([]);
  const [activeSkillId, setActiveSkillId] = useState<string | null>(null);

  // 👇 新增：子组件往上传的加技能回调
  const handleAddSkillToSidebar = (skill: SkillItem) => {
    setActiveSkills((prev) =>
      prev.find((s) => s.id === skill.id) ? prev : [...prev, skill],
    );
  };

  // 👇 新增：从侧边栏移除
  const handleRemoveSkill = (skillId: string) => {
    setActiveSkills((prev) => prev.filter((s) => s.id !== skillId));
    setActiveSkillId((cur) => (cur === skillId ? null : cur));
  };

  return (
    <Form {...form}>
      <form
        onSubmit={form.handleSubmit(onSubmit, onInvalid)}
        className="h-full flex flex-col pr-5"
      >
        {/* <div className="flex flex-1 min-h-0 pb-1 overflow-hidden"> */}
        <div className="relative flex flex-1 min-h-0 pb-1 overflow-hidden">
          {/* <div
  className="
    relative flex flex-1 min-h-0 pb-1 overflow-hidden
    bg-[#F5FAFF]
    bg-[radial-gradient(ellipse_48%_105%_at_52%_62%,rgba(143,174,225,0.68)_0%,rgba(170,195,235,0.48)_38%,rgba(220,232,248,0.25)_68%,rgba(247,251,255,0)_100%),radial-gradient(ellipse_34%_75%_at_83%_10%,rgba(132,162,215,0.58)_0%,rgba(180,201,235,0.35)_42%,rgba(241,247,254,0)_100%),radial-gradient(ellipse_30%_100%_at_13%_100%,rgba(220,233,249,0.5)_0%,rgba(245,250,255,0)_100%),repeating-linear-gradient(to_right,transparent_0,transparent_98px,rgba(119,151,199,0.12)_99px,transparent_100px),repeating-linear-gradient(to_bottom,transparent_0,transparent_98px,rgba(119,151,199,0.1)_99px,transparent_100px)]
    dark:bg-none dark:bg-transparent
  "
> */}
          {/* 左侧会话列表：自己内部滚动 */}
          <Sessions
            hasSingleChatBox={hasSingleChatBox}
            handleConversationCardClick={handleSessionClick}
            switchSettingVisible={openChatSettings}
            isWelcomePage={isWelcomePage} // 👈 传给 Sessions
          />

          <div className="flex flex-col flex-1 min-w-0 h-full min-h-0 overflow-hidden">
            <div className="shrink-0 flex items-center px-5 py-0 mt-2 bg-transparent">
              <div className="flex items-center gap-2 flex-1 min-w-0">
                <div
                  className={cn('flex items-center gap-1', {
                    hidden:
                      settingVisible ||
                      referenceVisible ||
                      sourcePreviewVisible ||
                      workspaceVisible,
                  })}
                >
                  <div className="w-auto">
                    <KnowledgeBaseFormField
                      hideLabel
                      onChange={async (kbIds) => {
                        const values = form.getValues();
                        await onSubmit(
                          { ...values, kb_ids: kbIds },
                          { silent: true },
                        );
                      }}
                    />
                  </div>

                  {/* ❌ SavingButton 已删除 */}
                </div>
              </div>
            </div>

            <div className="flex flex-1 min-h-0 overflow-hidden">
              <div
                id="chat-main-content"
                className={cn(
                  'min-w-0 min-h-0 overflow-hidden',
                  // ✅ 打开工作区时，主内容区占 2/3
                  sourcePreviewVisible || workspaceVisible
                    ? 'basis-1/2 w-1/2 flex-none' // 👈 从 1/2 改为 2/3
                    : 'flex-1',
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
                  customerComplaint={customerComplaint}
                  onEnableDeepReasoning={onEnableDeepReasoning}
                  onEnableMultiKbReasoning={onEnableMultiKbReasoning}
                  onEnableAgent={onEnableAgent}
                  onEnableProjectCompliance={onEnableProjectCompliance}
                  onEnableExperimentReport={onEnableExperimentReport}
                  onEnableCustomerComplaint={onEnableCustomerComplaint}
                  refreshConversation={refreshCurrentConversation}
                  // ✅ 新增：点「工作区」按钮时触发
                  onOpenWorkspace={openWorkspace}
                  onWelcomePageChange={setIsWelcomePage} // 👈 新增
                  isWorkspaceOpen={workspaceVisible}
                  // 👇 新增
                  activeSkills={activeSkills}
                  onAddSkillToSidebar={handleAddSkillToSidebar}
                />
              </div>

              <SourcePreviewPanel
                className={cn(
                  'h-full min-h-0 min-w-0 flex-none basis-1/2 w-1/2',
                  { hidden: !sourcePreviewVisible },
                )}
                documentId={sourcePreviewDocumentId}
                chunk={sourcePreviewChunk}
                visible={sourcePreviewVisible}
                onClose={closeSourcePreviewPanel}
              />

              {/* ✅ 工作区面板 */}
              <WorkspacePanel
                className={cn(
                  'h-full min-h-0 min-w-0 flex-none basis-1/2 w-1/2', // 👈 从 1/2 改为 1/3
                  { hidden: !workspaceVisible },
                )}
                visible={workspaceVisible}
                onClose={closeWorkspace}
                dialogId={id!}
                conversationId={conversationId}
                isWelcomePage={isWelcomePage}
              />

              {/* 右侧溯源来源列表 */}
              <ReferenceSourcePanel
                className={cn('shrink-0', { hidden: !referenceVisible })}
                list={referenceList}
                onClose={closeReferencePanel}
                onOpenSourcePreview={openSourcePreviewPanel}
              />

              {/* 右侧设置面板 */}
              <ChatSettings
                className={cn('shrink-0', { hidden: !settingVisible })}
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

// 文件类型徽标：彩色圆角块 + 白色图形/文字
const FileBadge: React.FC<{ name: string; size?: number }> = ({
  name,
  size = 32,
}) => {
  const ext = (name.split('.').pop() || '').toLowerCase();

  const base =
    'flex shrink-0 items-center justify-center rounded-[7px] text-white';

  const style: React.CSSProperties = {
    width: size,
    height: size,
    fontSize: size * 0.4,
    fontWeight: 700,
    lineHeight: 1,
  };

  // Word / 文档
  if (['doc', 'docx', 'rtf', 'odt'].includes(ext)) {
    return (
      <div className={base} style={{ ...style, background: '#2B579A' }}>
        W
      </div>
    );
  }

  // PDF
  if (ext === 'pdf') {
    return (
      <div className={base} style={{ ...style, background: '#E5484D' }}>
        PDF
      </div>
    );
  }

  // 表格
  if (['xls', 'xlsx', 'csv'].includes(ext)) {
    return (
      <div className={base} style={{ ...style, background: '#217346' }}>
        X
      </div>
    );
  }

  // PPT
  if (['ppt', 'pptx'].includes(ext)) {
    return (
      <div className={base} style={{ ...style, background: '#D24726' }}>
        P
      </div>
    );
  }

  // 图片：橙色块 + 白色山形/太阳（内联 SVG，和截图一致）
  if (['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'bmp'].includes(ext)) {
    return (
      <div className={base} style={{ ...style, background: '#F5A623' }}>
        <svg
          width={size * 0.6}
          height={size * 0.6}
          viewBox="0 0 24 24"
          fill="none"
        >
          <rect
            x="3"
            y="4"
            width="18"
            height="16"
            rx="2"
            stroke="#fff"
            strokeWidth="1.8"
          />
          <circle cx="8.5" cy="9.5" r="1.6" fill="#fff" />
          <path
            d="M4 17l4.5-4.5 3.5 3.5 3-3L20 17"
            stroke="#fff"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </div>
    );
  }

  // 压缩包
  if (['zip', 'rar', '7z', 'tar', 'gz'].includes(ext)) {
    return (
      <div className={base} style={{ ...style, background: '#8E7CC3' }}>
        ZIP
      </div>
    );
  }

  // 文本 / Markdown
  if (['txt', 'md', 'log'].includes(ext)) {
    return (
      <div className={base} style={{ ...style, background: '#6B7280' }}>
        T
      </div>
    );
  }

  // 默认
  return (
    <div className={base} style={{ ...style, background: '#94A3B8' }}>
      <svg
        width={size * 0.55}
        height={size * 0.55}
        viewBox="0 0 24 24"
        fill="none"
      >
        <path
          d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8l-5-5z"
          stroke="#fff"
          strokeWidth="1.8"
          strokeLinejoin="round"
        />
        <path
          d="M14 3v5h5"
          stroke="#fff"
          strokeWidth="1.8"
          strokeLinejoin="round"
        />
      </svg>
    </div>
  );
};

const WorkspacePanel: React.FC<{
  className?: string;
  visible: boolean;
  onClose: () => void;
  dialogId?: string;
  conversationId?: string;
  isWelcomePage?: boolean;
}> = ({
  className,
  visible,
  onClose,
  dialogId,
  conversationId,
  isWelcomePage = false,
}) => {
  const [files, setFiles] = React.useState<any[]>([]);
  const [loading, setLoading] = React.useState(false);

  // 👇 当前预览的文件（null 表示看列表）
  const [previewFile, setPreviewFile] = React.useState<any>(null);

  React.useEffect(() => {
    if (!visible) return;
    if (!dialogId && !conversationId) return;

    let cancelled = false;

    (async () => {
      setLoading(true);
      try {
        const params = new URLSearchParams();
        if (dialogId) params.set('dialog_id', dialogId);
        if (conversationId) params.set('conversation_id', conversationId);

        const res = await fetch(
          `/v1/file/workspace-files?${params.toString()}`,
          {
            method: 'GET',
            headers: {
              Authorization: getAuthorization() || '',
              'Content-Type': 'application/json',
            },
            credentials: 'include',
          },
        );
        const result = await res.json();
        const list = Array.isArray(result) ? result : (result.data ?? []);
        if (!cancelled) setFiles(list);
      } catch (err) {
        console.error('拉取工作区文件失败', err);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [visible, dialogId, conversationId]);

  // 关闭工作区时清空预览状态
  React.useEffect(() => {
    if (!visible) setPreviewFile(null);
  }, [visible]);

  if (!visible) return null;

  // 拼公共参数
  const buildFileParams = (extra?: Record<string, string>) => {
    const params = new URLSearchParams();
    if (dialogId) params.set('dialog_id', dialogId);
    if (conversationId) params.set('conversation_id', conversationId);
    if (extra) {
      Object.entries(extra).forEach(([k, v]) => params.set(k, v));
    }
    return params;
  };

  // 预览：切换状态，不走 window.open
  const handlePreviewFile = (file: any) => {
    const params = buildFileParams({
      path: String(file.id || file.path || file.name || ''), // 👈 优先 id / path
      preview: '1',
    });
    const url = `/v1/file/workspace-file?${params.toString()}`;
    setPreviewFile({ ...file, _url: url });
  };

  // 下载
  const handleDownloadFile = async (file: any) => {
    try {
      const params = buildFileParams({
        path: String(file.id || file.path || file.name || ''), // 👈 优先 id / path
        preview: '0',
      });
      const url = `/v1/file/workspace-file?${params.toString()}`;

      const res = await fetch(url, {
        method: 'GET',
        headers: { Authorization: getAuthorization() || '' },
        credentials: 'include',
      });
      if (!res.ok) throw new Error('下载失败');

      const blob = await res.blob();
      const blobUrl = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = blobUrl;
      a.download = file.name || 'download';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(blobUrl);
    } catch (err) {
      console.error('下载失败', err);
      message.error('下载失败');
    }
  };
  // 根据文件名后缀返回对应图标
  const getFileIcon = (name: string) => {
    const ext = (name.split('.').pop() || '').toLowerCase();
    const cls = 'shrink-0 text-slate-400';

    if (['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'bmp'].includes(ext)) {
      return <FileImage size={16} className={cls} />;
    }
    if (['xls', 'xlsx', 'csv'].includes(ext)) {
      return <FileSpreadsheet size={16} className={cls} />;
    }
    if (['zip', 'rar', '7z', 'tar', 'gz'].includes(ext)) {
      return <FileArchive size={16} className={cls} />;
    }
    if (['txt', 'md', 'doc', 'docx', 'pdf', 'ppt', 'pptx'].includes(ext)) {
      return <FileText size={16} className={cls} />;
    }
    return <File size={16} className={cls} />;
  };

  return (
    <>
      <style>{`
        .workspace-docx-preview {
          font-family: "Microsoft YaHei", "PingFang SC", "SimSun", sans-serif;
          color: #1f2328;
          line-height: 1.75;
          font-size: 14px;
          word-break: break-word;
        }
        .workspace-docx-preview table {
          width: 100%;
          border-collapse: collapse;
          margin: 14px 0;
          table-layout: auto;
        }
        .workspace-docx-preview th,
        .workspace-docx-preview td {
          border: 1px solid #d0d7de;
          padding: 8px 12px;
          vertical-align: top;
          text-align: left;
        }
        .workspace-docx-preview th {
          background: #f6f8fa;
          font-weight: 600;
        }
        .workspace-docx-preview tr:nth-child(even) td {
          background: #fafbfc;
        }
        .workspace-docx-preview p { margin: 10px 0; }
        .workspace-docx-preview h1 { font-size: 22px; font-weight: 700; margin: 20px 0 12px; }
        .workspace-docx-preview h2 { font-size: 18px; font-weight: 700; margin: 18px 0 10px; }
        .workspace-docx-preview h3 { font-size: 16px; font-weight: 600; margin: 16px 0 8px; }
        .workspace-docx-preview h4 { font-size: 15px; font-weight: 600; margin: 14px 0 6px; }
        .workspace-docx-preview ul,
        .workspace-docx-preview ol { padding-left: 24px; margin: 8px 0; }
        .workspace-docx-preview li { margin: 4px 0; }
        .workspace-docx-preview img { max-width: 100%; height: auto; display: block; margin: 8px 0; }
        .workspace-docx-preview blockquote {
          border-left: 3px solid #d0d7de;
          padding-left: 12px;
          color: #57606a;
          margin: 12px 0;
        }
        .workspace-docx-preview hr { border: none; border-top: 1px solid #d0d7de; margin: 16px 0; }
        .workspace-docx-preview strong { font-weight: 700; }
        .workspace-docx-preview em { font-style: italic; }
      `}</style>
      <div className={cn('h-full min-h-0 p-2', className)}>
        <div
          className={cn(
            'flex h-full min-h-0 flex-col overflow-hidden rounded-2xl border',
            isWelcomePage
              ? 'border-[#8FC0E0]/40 dark:border-[#2F4A66]/60 bg-white dark:bg-[#0F2030]'
              : 'border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900',
          )}
        >
          {/* ============ 头部 ============ */}
          <div className="flex h-12 shrink-0 items-center justify-between border-b border-slate-200 px-4 dark:border-slate-700">
            {previewFile ? (
              // 预览模式：返回 + 文件名 + 下载 + 关闭
              <>
                <button
                  type="button"
                  onClick={() => setPreviewFile(null)}
                  className="flex shrink-0 items-center gap-1 rounded-md px-1.5 py-1 text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-800 dark:hover:bg-slate-800 dark:hover:text-slate-200"
                  title="返回列表"
                >
                  <ChevronLeft size={16} />
                  <span className="text-sm font-medium">返回</span>
                </button>

                <div
                  className="mx-2 min-w-0 flex-1 truncate text-right text-xs text-slate-500 dark:text-slate-400"
                  title={previewFile.name}
                >
                  {previewFile.name}
                </div>

                <button
                  type="button"
                  onClick={() => handleDownloadFile(previewFile)}
                  className="shrink-0 rounded-md p-1.5 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-800 dark:hover:text-slate-200"
                  title="下载"
                >
                  <Download size={18} />
                </button>

                <button
                  type="button"
                  onClick={onClose}
                  className="shrink-0 rounded-md p-1.5 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-800 dark:hover:text-slate-200"
                  title="关闭"
                >
                  <X size={18} />
                </button>
              </>
            ) : (
              // 列表模式：标题 + 关闭
              <>
                <div className="text-sm font-medium text-slate-700 dark:text-slate-200">
                  工作区 ({files.length})
                </div>
                <button
                  type="button"
                  onClick={onClose}
                  className="rounded-md p-1.5 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-800"
                >
                  <X size={18} />
                </button>
              </>
            )}
          </div>

          {/* ============ 内容：列表 or 预览 ============ */}
          {previewFile ? (
            <div className="min-h-0 flex-1 overflow-auto bg-slate-200 dark:bg-slate-950">
              <div className="mx-auto my-4 max-w-[880px] rounded-lg bg-white p-6 shadow-sm dark:bg-slate-900">
                <DocPreviewer
                  url={previewFile._url}
                  className="
          workspace-docx-preview
          !h-auto
          !min-h-0
          !w-full
          !overflow-visible
          !rounded-none
          !border-0
          !bg-transparent
          !p-0
        "
                />
              </div>
            </div>
          ) : (
            // 列表
            <div className="flex-1 overflow-auto p-3">
              {loading ? (
                <div className="flex items-center justify-center py-8 text-slate-400">
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  加载中…
                </div>
              ) : files.length === 0 ? (
                <div className="py-8 text-center text-sm text-slate-400">
                  暂无文件
                </div>
              ) : (
                <ul className="flex flex-col">
                  {files.map((file: any) => (
                    <li
                      key={file.id}
                      onClick={() => handlePreviewFile(file)}
                      className="
    group flex cursor-pointer items-center gap-3 rounded-lg px-2.5 py-2
    border-b border-slate-100 last:border-b-0
    dark:border-slate-800
    transition-colors hover:bg-slate-100 dark:hover:bg-slate-800
  "
                    >
                      <FileBadge name={file.name} size={32} />

                      <div className="min-w-0 flex-1">
                        <div
                          className="truncate text-[13px] text-slate-700 dark:text-slate-200"
                          title={file.name}
                        >
                          {file.name}
                        </div>
                        {file.size != null && (
                          <div className="text-[11px] text-slate-400">
                            {(file.size / 1024).toFixed(1)} KB
                          </div>
                        )}
                      </div>

                      <div className="flex shrink-0 items-center gap-0.5">
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            handlePreviewFile(file);
                          }}
                          title="预览"
                          className="flex h-7 w-7 items-center justify-center rounded-md text-slate-400 transition-colors hover:bg-slate-200 hover:text-slate-700 dark:hover:bg-slate-700 dark:hover:text-slate-200"
                        >
                          <Eye size={14} />
                        </button>

                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDownloadFile(file);
                          }}
                          title="下载"
                          className="flex h-7 w-7 items-center justify-center rounded-md text-slate-400 transition-colors hover:bg-slate-200 hover:text-slate-700 dark:hover:bg-slate-700 dark:hover:text-slate-200"
                        >
                          <Download size={14} />
                        </button>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>
      </div>
    </>
  );
};
