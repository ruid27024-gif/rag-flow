import EmbedDialog from '@/components/embed-dialog';
import { useShowEmbedModal } from '@/components/embed-dialog/use-show-embed-dialog';
import { KnowledgeBaseFormField } from '@/components/knowledge-base-item';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
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
  // const { data } = useFetchDialog();
  const { data, refetch } = useFetchDialog();

  console.log(data);
  const { t } = useTranslation();
  const [currentConversation, setCurrentConversation] =
    useState<IClientConversation>({} as IClientConversation);
  console.log('currentConversation', currentConversation);

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

  const USER_OVERRIDABLE_FIELDS = [
    'llm_id',
    'name',
    'description',
    'prologue',
    'empty_response',
    'icon',
    'rerank_id',
    'kb_ids',
  ];

  // 表单values的提交逻辑
  async function onSubmit(values: FormSchemaType) {
    // console.log("请求开始")
    // console.log("1. 用户提交的值:", values.llm_id);
    // 移除llm_setting
    const nextValues: Record<string, any> = removeUselessFieldsFromValues(
      values,
      'llm_setting.',
    );

    // console.log("2. 处理后要发送的值:", nextValues.llm_id);
    // 调用 Hook 中的 setDialog 保存数据
    setDialog({
      ...omit(data, 'operator_permission'), // 保留原数据但剔除权限字段
      ...nextValues, // 合并新修改的值
      dialog_id: id, // 确保带上 ID
    });

    // 2. ✅ 保存成功后，重新拉取数据
    const { data: newData } = await refetch();
    // 智能合并
    const mergedData = {
      ...newData,
      // 只覆盖允许的字段，且用户确实提交了值
      ...Object.fromEntries(
        Object.entries(nextValues).filter(
          ([key, value]) =>
            USER_OVERRIDABLE_FIELDS.includes(key) && // 在允许列表里
            value !== undefined &&
            value !== null &&
            value !== '',
        ),
      ),
    };

    // 3. ✅ 处理 llm_setting 并重置表单
    const llmSettingEnabledValues = setLLMSettingEnabledValues(
      mergedData.llm_setting,
    );
    const nextData = {
      ...mergedData,
      ...llmSettingEnabledValues,
    };
    // console.log("5. 最终重置表单的 llm_id:", nextData.llm_id);

    form.reset(nextData as FormSchemaType);
  }

  function onInvalid(errors: any) {
    console.log('Form validation failed:', errors);
  }

  // 表单回显（只用于初始化）
  useEffect(() => {
    // console.log("表单回显")
    if (data && Object.keys(data).length > 0 && !initialized) {
      const llmSettingEnabledValues = setLLMSettingEnabledValues(
        data.llm_setting,
      );
      const nextData = {
        ...data,
        ...llmSettingEnabledValues,
      };
      form.reset(nextData as FormSchemaType);
      setInitialized(true);
    }
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

  const [initialized, setInitialized] = useState(false);
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
        <div className="flex flex-1 min-h-0 pb-9">
          {/* 左边栏 */}
          <Sessions
            hasSingleChatBox={hasSingleChatBox}
            handleConversationCardClick={handleSessionClick}
            switchSettingVisible={switchSettingVisible}
          ></Sessions>

          {/* 右侧聊天栏目 */}
          <Card className="flex-1 min-w-0 bg-transparent border h-full">
            {/* 两个大卡片）默认从左到右横向排列 */}
            <CardContent className="flex p-0 h-full">
              {/* 左边的聊天主面板 */}
              <Card className="flex flex-col flex-1 bg-transparent min-w-0">
                {/* 聊天头部 */}
                {/* <CardHeader
                  className={cn('p-5', { 'border-b': hasSingleChatBox })}
                > */}

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

                    {/* <Button variant={'ghost'} onClick={switchDebugMode}>
                      <ArrowUpRight /> {t('chat.multipleModels')}
                    </Button> */}
                  </CardTitle>
                </CardHeader>
                {/* 消息展示区 */}
                <CardContent className="flex-1 p-0 min-h-0">
                  <SingleChatBox
                    controller={controller}
                    stopOutputMessage={stopOutputMessage}
                    conversation={currentConversation}
                  ></SingleChatBox>
                </CardContent>
              </Card>
              {/* 聊天设置右边栏 */}
              <ChatSettings
                className={cn({ hidden: !settingVisible })}
                switchSettingVisible={switchSettingVisible}
                onSubmit={form.handleSubmit(onSubmit, onInvalid)}
                loading={loading}
              ></ChatSettings>
            </CardContent>
          </Card>
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
      </form>
    </Form>
  );
}
