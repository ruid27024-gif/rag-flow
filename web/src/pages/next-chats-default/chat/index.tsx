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

export default function Chat() {
  const { id } = useParams();
  const { navigateToChatList } = useNavigatePage();
  const { data } = useFetchDialog();
  const { t } = useTranslation();
  const [currentConversation, setCurrentConversation] =
    useState<IClientConversation>({} as IClientConversation);

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

  // 表单values的提交逻辑
  async function onSubmit(values: FormSchemaType) {
    // 移除llm_setting
    const nextValues: Record<string, any> = removeUselessFieldsFromValues(
      values,
      'llm_setting.',
    );

    // 调用 Hook 中的 setDialog 保存数据
    setDialog({
      ...omit(data, 'operator_permission'), // 保留原数据但剔除权限字段
      ...nextValues, // 合并新修改的值
      dialog_id: id, // 确保带上 ID
    });
  }

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

        <div className="flex flex-1 min-h-0 pb-1 overflow-hidden">
          {/* 左侧会话列表：自己内部滚动 */}
          <Sessions
            hasSingleChatBox={hasSingleChatBox}
            handleConversationCardClick={handleSessionClick}
            switchSettingVisible={switchSettingVisible}
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
              <div className="flex-1 min-w-0 min-h-0 overflow-hidden">
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

        {/* <Card className="flex-1 min-w-0 bg-transparent border h-full">

            <CardContent className="flex p-0 h-full">

              <Card className="flex flex-col flex-1 bg-transparent min-w-0">


                <CardHeader className={cn('py-2 px-5')}>

                  <CardTitle className="flex justify-between items-center text-base">
                    <div className="flex items-center gap-4 flex-1 min-w-0 ml-[-8px]">

                      <div
                        className={cn('flex items-center gap-2', {
                          hidden: settingVisible,
                        })}
                      >
                        <div className="w-[240px]">
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

                <CardContent className="flex-1 p-0 min-h-[300px] pt-0">
                  <SingleChatBox
                    controller={controller}
                    stopOutputMessage={stopOutputMessage}
                    conversation={currentConversation}
                  ></SingleChatBox>
                </CardContent>
              </Card>

              <ChatSettings
                className={cn({ hidden: !settingVisible })}
                switchSettingVisible={switchSettingVisible}
                onSubmit={form.handleSubmit(onSubmit, onInvalid)}
                loading={loading}
              ></ChatSettings>
            </CardContent>
          </Card>
        </div> */}
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
      </form>
    </Form>
  );
}
