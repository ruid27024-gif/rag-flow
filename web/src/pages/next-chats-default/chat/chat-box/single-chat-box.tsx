import { NextMessageInput } from '@/components/message-input/next';
import MessageItem from '@/components/message-item';
import { MessageType } from '@/constants/chat';
import {
  useFetchDialog,
  useGetChatSearchParams,
} from '@/hooks/use-chat-request';
import { useFetchUserInfo } from '@/hooks/use-user-setting-request';
import { getAuthorization } from '@/utils/authorization-util';
import { buildMessageUuidWithRole } from '@/utils/chat';
import { message } from 'antd';
import { useEffect, useState } from 'react';
import { flushSync } from 'react-dom';
import { useNavigate, useParams } from 'umi';
import {
  useGetSendButtonDisabled,
  useSendButtonDisabled,
} from '../../hooks/use-button-disabled';
import { useCreateConversationBeforeUploadDocument } from '../../hooks/use-create-conversation';
import { useSendMessage } from '../../hooks/use-send-chat-message';
import { buildMessageItemReference } from '../../utils';
// interface IProps {
//   controller: AbortController;
//   stopOutputMessage(): void;
//   conversation: IClientConversation;
// }

interface IProps {
  controller: any;
  stopOutputMessage: () => void;
  conversation: any;
  clickDocumentButton?: (
    documentId: string,
    chunk: any,
    isPdf?: boolean,
    documentUrl?: string | null,
  ) => void;
  onOpenReferencePanel?: (list: ReferenceDocumentItem[]) => void;
  reasoning: boolean;
  agentMod: boolean;
  projectCompliance?: boolean;
  experimentReport?: boolean;
  onEnableDeepReasoning?: () => void;
  onEnableMultiKbReasoning?: () => void;
  onEnableAgent?: () => void;

  onEnableProjectCompliance?: () => void | Promise<void>;
  onEnableExperimentReport?: () => void | Promise<void>;
  refreshConversation?: () => Promise<any>;
}

export function SingleChatBox({
  controller,
  stopOutputMessage,
  conversation,
  clickDocumentButton,
  onOpenReferencePanel,
  reasoning,
  agentMod,
  projectCompliance,
  experimentReport,
  onEnableDeepReasoning,
  onEnableMultiKbReasoning,
  onEnableAgent,
  onEnableProjectCompliance, // ✅ 补上
  onEnableExperimentReport, // ✅ 补上
  refreshConversation,
}: IProps) {
  const {
    value,
    scrollRef,
    messageContainerRef,
    sendLoading,
    derivedMessages,
    isUploading,
    handleInputChange,
    setValue,
    handlePressEnter,
    regenerateMessage,
    removeMessageById,
    handleUploadFile,
    removeFile,
    setDerivedMessages,
  } = useSendMessage(controller);
  const { data: userInfo } = useFetchUserInfo();
  const { data: currentDialog } = useFetchDialog();
  const { createConversationBeforeUploadDocument } =
    useCreateConversationBeforeUploadDocument();
  const { conversationId } = useGetChatSearchParams();
  const disabled = useGetSendButtonDisabled();
  const sendDisabled = useSendButtonDisabled(value);
  const navigate = useNavigate();
  const { id } = useParams();
  const projectComplianceActive =
    projectCompliance && !reasoning && !agentMod && !experimentReport;
  const experimentReportActive =
    experimentReport && !reasoning && !agentMod && !projectCompliance;

  // const { visible, hideModal, documentId, selectedChunk, clickDocumentButton } =
  //   useClickDrawer();
  function fallbackCopyText(text: string) {
    const textarea = document.createElement('textarea');
    textarea.value = text;

    textarea.style.position = 'fixed';
    textarea.style.left = '-9999px';
    textarea.style.top = '-9999px';
    textarea.style.opacity = '0';

    document.body.appendChild(textarea);
    textarea.focus();
    textarea.select();

    try {
      const successful = document.execCommand('copy');
      document.body.removeChild(textarea);
      return successful;
    } catch (err) {
      document.body.removeChild(textarea);
      return false;
    }
  }
  // console.log('derivedMessages',derivedMessages);
  useEffect(() => {
    const messages = conversation?.message;

    if (Array.isArray(messages)) {
      const normalizedMessages = messages.map((item: any) => {
        const agentEvents =
          item.agentEvents ||
          item.agent_events ||
          (item.agent_event ? [item.agent_event] : []);

        return {
          ...item,

          // 兼容有些历史消息只有 answer，没有 content
          content: item.content ?? item.answer ?? '',

          // 统一前端字段
          agentEvents,

          // 保留后端字段
          agent_events: item.agent_events || agentEvents,
        };
      });

      setDerivedMessages(normalizedMessages);
    }
  }, [conversation?.message, setDerivedMessages]);

  useEffect(() => {
    // Clear the message list after deleting the conversation.
    if (conversationId === '') {
      setDerivedMessages([]);
    }
  }, [conversationId, setDerivedMessages]);

  // ✅ 新增：处理建议列表点击的函数
  // ✅ 修改：构造一个符合 ChangeEventHandler 的事件对象
  const handleSuggestionClick = (suggestion: string) => {
    setValue(suggestion);
  };

  // 双击：填入输入框并发送
  const handleSuggestionDoubleClick = (suggestion: string) => {
    flushSync(() => {
      setValue(suggestion);
    });

    handlePressEnter(suggestion);
  };

  const handleShareMessage = async (targetMessageOrId: any) => {
    const currentConversationId = conversation?.id || conversationId;

    if (!currentConversationId) {
      message.error('conversation_id 不存在');
      return;
    }

    if (!targetMessageOrId) {
      message.error('message 不存在');
      return;
    }

    try {
      /**
       * 兼容两种调用方式：
       * 1. handleShareMessage(item)
       * 2. handleShareMessage(item.id)
       */
      const targetMessage =
        typeof targetMessageOrId === 'string'
          ? { id: targetMessageOrId }
          : targetMessageOrId;

      const targetId = targetMessage?.id;
      const targetRole = targetMessage?.role;
      const targetContent =
        targetMessage?.content ?? targetMessage?.answer ?? '';

      console.log('share targetMessage:', targetMessage);
      console.log('share targetId:', targetId);
      console.log('share targetRole:', targetRole);
      console.log('share targetContent:', targetContent);

      /**
       * 分享前刷新 conversation
       */
      const latestConversation = refreshConversation
        ? await refreshConversation(currentConversationId)
        : conversation;

      console.log('latestConversation:', latestConversation);

      const latestMessages = latestConversation?.message || [];

      console.log(
        'latestMessages:',
        latestMessages.map((item: any) => ({
          id: item.id,
          role: item.role,
          content: String(item.content ?? item.answer ?? '').slice(0, 80),
        })),
      );

      let realMessage: any = null;

      /**
       * 1. 优先按 id 匹配
       */
      if (targetId) {
        realMessage = latestMessages.find((item: any) => item.id === targetId);
      }

      /**
       * 2. id 匹配不到，再按 role + content 匹配
       */
      if (!realMessage && targetContent) {
        realMessage = [...latestMessages].reverse().find((item: any) => {
          const itemContent = item.content ?? item.answer ?? '';

          if (!itemContent) return false;

          if (targetRole) {
            return item.role === targetRole && itemContent === targetContent;
          }

          return itemContent === targetContent;
        });
      }

      /**
       * 3. 仍然找不到，直接兜底取最后一条 assistant 消息
       *
       * 注意：
       * 如果你的分享按钮只出现在 assistant 消息上，这个兜底是安全的。
       * 如果 user 消息也有分享按钮，这里可能会分享最后一条 AI 回复。
       */
      if (!realMessage) {
        realMessage = [...latestMessages].reverse().find((item: any) => {
          const content = item.content ?? item.answer ?? '';
          return item.role === 'assistant' && content;
        });
      }

      if (!realMessage?.id) {
        message.error('消息还未同步完成，请稍后再试');
        return;
      }

      console.log('realMessage for share:', realMessage);

      const response = await fetch('/v1/conversation/share', {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          Authorization: getAuthorization() || '',
        },
        body: JSON.stringify({
          conversation_id: currentConversationId,
          message_id: realMessage.id,
        }),
      });

      const result = await response.json();

      console.log('share result:', result);

      if (result.code !== 0) {
        message.error(result.message || '创建分享失败');
        return;
      }

      const shareUrl = result.data?.url;

      console.log('shareUrl:', shareUrl);

      if (!shareUrl) {
        message.error('后端未返回分享链接');
        return;
      }

      try {
        if (navigator.clipboard && window.isSecureContext) {
          await navigator.clipboard.writeText(shareUrl);
          message.success('分享链接已复制');
        } else {
          const copied = fallbackCopyText(shareUrl);

          if (copied) {
            message.success('分享链接已复制');
          } else {
            message.warning(`分享链接已创建，请手动复制：${shareUrl}`);
          }
        }
      } catch (copyError) {
        console.error('复制失败:', copyError);
        message.warning(`分享链接已创建，请手动复制：${shareUrl}`);
      }
    } catch (error) {
      console.error(error);
      message.error('分享失败');
    }
  };
  // import { SunIcon, SmileIcon, MoonIcon, StarIcon } from 'lucide-react';

  const handleRebaseMessage = async (messageId: string) => {
    if (!conversationId) {
      message.error('conversation_id 不存在');
      return;
    }

    if (!messageId) {
      message.error('message_id 不存在');
      return;
    }

    try {
      const response = await fetch('/v1/conversation/rebase', {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          Authorization: getAuthorization() || '',
        },
        body: JSON.stringify({
          conversation_id: conversationId,
          message_id: messageId,
        }),
      });

      const result = await response.json();

      if (result.code !== 0) {
        message.error(result.message || '创建分支会话失败');
        return;
      }

      const newConversationId = result.data?.conversation_id || result.data?.id;

      if (!newConversationId) {
        message.error('后端未返回新的 conversation_id');
        return;
      }

      message.success('已创建新的分支会话');

      const currentPath = window.location.pathname;

      window.location.href = `${currentPath}?conversationId=${newConversationId}&isNew=false`;
    } catch (error) {
      console.error(error);
      message.error('创建分支会话失败');
    }
  };
  // 或者用简单 SVG：
  const SunIcon = () => (
    <svg
      className="w-6 h-6 text-yellow-500"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"
      />
    </svg>
  );

  const SmileIcon = () => (
    <svg
      className="w-6 h-6 text-blue-500"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M14.828 14.828a4 4 0 01-5.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
      />
    </svg>
  );

  const MoonIcon = () => (
    <svg
      className="w-6 h-6 text-indigo-500"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"
      />
    </svg>
  );

  const StarIcon = () => (
    <svg
      className="w-6 h-6 text-purple-500"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z"
      />
    </svg>
  );

  function useTime(updateInterval: number = 60000) {
    const [time, setTime] = useState(() => new Date());

    useEffect(() => {
      // ✅ 立即对齐当前时间
      setTime(new Date());

      const timer = setInterval(() => {
        setTime(new Date());
      }, updateInterval);

      return () => clearInterval(timer);
    }, [updateInterval]);

    return time;
  }

  const time = useTime(60_000);

  const hours = time.getHours();
  const minutes = time.getMinutes().toString().padStart(2, '0');

  let greeting = '';
  if (hours < 12) greeting = '早上好';
  else if (hours < 18) greeting = '下午好';
  else greeting = '晚上好';

  const TimeIcon =
    hours >= 5 && hours < 12
      ? SunIcon
      : hours >= 12 && hours < 18
        ? SmileIcon
        : hours >= 18 && hours < 22
          ? MoonIcon
          : StarIcon;
  //   useEffect(() => {
  //   if (visible) {
  //     console.log('PdfSheet documentId:', documentId);
  //     console.log('PdfSheet selectedChunk:', selectedChunk);
  //   }
  // }, [visible, documentId, selectedChunk]);

  const isWelcomePage = !conversationId || derivedMessages.length === 1;

  const inputBox = (
    <NextMessageInput
      disabled={disabled}
      sendDisabled={sendDisabled}
      sendLoading={sendLoading}
      value={value}
      onInputChange={handleInputChange}
      onPressEnter={handlePressEnter}
      conversationId={conversationId}
      createConversationBeforeUploadDocument={
        createConversationBeforeUploadDocument
      }
      stopOutputMessage={stopOutputMessage}
      onUpload={handleUploadFile}
      isUploading={isUploading}
      removeFile={removeFile}
      // 👇 状态传递
      reasoning={reasoning}
      agentMod={agentMod}
      projectCompliance={projectCompliance} // ✅ 补上
      experimentReport={experimentReport} // ✅ 补上
      // 👇 回调函数传递
      onEnableDeepReasoning={onEnableDeepReasoning}
      onEnableMultiKbReasoning={onEnableMultiKbReasoning}
      onEnableAgent={onEnableAgent}
      onEnableProjectCompliance={onEnableProjectCompliance} // ✅ 补上
      onEnableExperimentReport={onEnableExperimentReport} // ✅ 补上
    />
  );
  return (
    <section className="flex h-full min-h-0 w-full flex-col overflow-hidden">
      {isWelcomePage ? (
        /**
         * 欢迎页：
         * 图标 + 恒丰纸业 + 输入框 居中显示
         */
        <div className="flex flex-1 min-h-0 w-full items-center justify-center px-5">
          <div className="w-full max-w-[860px] -translate-y-8">
            {/* 简洁 Logo 标题 */}
            <div className="mb-8 flex items-center justify-center gap-4 text-center">
              <img
                src="/hf_pic.png"
                // alt="恒丰纸业"
                className="
    h-16
    w-16
    object-contain
    drop-shadow-[0_10px_18px_rgba(16,185,129,0.18)]
  "
              />

              <div
                className="
                text-4xl
                font-extrabold
                tracking-tight
                text-emerald-900
                dark:text-emerald-100
              "
                style={{
                  fontFamily: `"Ma Shan Zheng", KaiTi, STKaiti, FangSong, Georgia, "Times New Roman", serif`,
                }}
              >
                恒丰纸业
              </div>
            </div>

            {/* 居中的输入框，外层更直角一点 */}
            <div className="w-full">{inputBox}</div>
          </div>
        </div>
      ) : (
        /**
         * 正常对话：
         * 消息滚动区域 + 底部固定输入框
         */
        <>
          {/* 消息滚动区域：这一层是全宽的，所以滚动条会在最右侧 */}
          <div
            ref={messageContainerRef}
            className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden [scrollbar-gutter:stable]"
          >
            {/* 内容居中区域：只控制内容宽度，不负责滚动 */}
            <div className="mx-auto w-full max-w-[860px] px-5 pt-0 pb-4">
              {derivedMessages?.map((message, i) => (
                <MessageItem
                  loading={
                    message.role === MessageType.Assistant &&
                    sendLoading &&
                    derivedMessages.length - 1 === i
                  }
                  key={buildMessageUuidWithRole(message)}
                  item={message}
                  nickname={userInfo.nickname}
                  avatar={userInfo.avatar}
                  avatarDialog={currentDialog.icon}
                  reference={buildMessageItemReference(
                    {
                      message: derivedMessages,
                      reference: conversation.reference,
                    },
                    message,
                  )}
                  clickDocumentButton={clickDocumentButton}
                  onOpenReferencePanel={onOpenReferencePanel}
                  index={i}
                  removeMessageById={removeMessageById}
                  regenerateMessage={regenerateMessage}
                  sendLoading={sendLoading}
                  visibleAvatar={false}
                  onSuggestionClick={handleSuggestionClick}
                  onSuggestionDoubleClick={handleSuggestionDoubleClick}
                  onShareMessage={handleShareMessage}
                  onRebaseMessage={handleRebaseMessage}
                  isLastMessage={derivedMessages.length - 1 === i}
                />
              ))}

              {/* 用于滚动到底部的锚点 */}
              <div ref={scrollRef} />
            </div>
          </div>

          {/* 底部输入框：固定在底部，不参与滚动 */}
          <div className="shrink-0 w-full px-5 pb-4">
            <div
              className="
              mx-auto
              w-full
              max-w-[860px]
              rounded-xl
            "
            >
              {inputBox}
            </div>
          </div>
        </>
      )}

      {/* PDF 预览弹窗 */}
      {/* {visible && (
      <PdfSheet
        visible={visible}
        hideModal={hideModal}
        documentId={documentId}
        chunk={selectedChunk}
      />
    )} */}
    </section>
  );
}
