import EmbedDialog from '@/components/embed-dialog';
import { useShowEmbedModal } from '@/components/embed-dialog/use-show-embed-dialog';
import { KnowledgeBaseFormField } from '@/components/knowledge-base-item';
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

export default function Chat() {
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

  const { visible: settingVisible, switchVisible: switchSettingVisible } =
    useSetModalState(false);

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

  async function onSubmit(values: FormSchemaType) {
    const nextValues: Record<string, any> = removeUselessFieldsFromValues(
      values,
      'llm_setting.',
    );

    const result = await setDialog({
      ...omit(data, 'operator_permission'),
      ...nextValues,
      dialog_id: id,
    });

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

      // setCurrentConversation(latestData as IClientConversation);
    }

    // 提交完成后关闭设置面板
    if (settingVisible) {
      switchSettingVisible();
    }
  }

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

        <div className="flex flex-1 min-h-0 pb-1 overflow-hidden">
          {/* 左侧会话列表：自己内部滚动 */}
          <Sessions
            hasSingleChatBox={hasSingleChatBox}
            handleConversationCardClick={handleSessionClick}
            switchSettingVisible={openChatSettings}
          />

          {/* 右侧整体区域 */}
          <div className="flex flex-col flex-1 min-w-0 h-full min-h-0 overflow-hidden">
            {/* 外部 Header，不参与滚动 */}
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

            {/* 主内容区 */}
            <div className="flex flex-1 min-h-0 overflow-hidden">
              {/* 左侧聊天主区域 */}
              <div
                id="chat-main-content"
                className="flex-1 min-w-0 min-h-0 overflow-hidden transition-[margin-right] duration-200"
              >
                <SingleChatBox
                  controller={controller}
                  stopOutputMessage={stopOutputMessage}
                  conversation={currentConversation}
                />
              </div>

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
      </form>
    </Form>
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
