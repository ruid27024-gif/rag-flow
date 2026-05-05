import { NextMessageInput } from '@/components/message-input/next';
import MessageItem from '@/components/message-item';
import PdfSheet from '@/components/pdf-drawer';
import { useClickDrawer } from '@/components/pdf-drawer/hooks';
import { MessageType } from '@/constants/chat';
import {
  useFetchDialog,
  useGetChatSearchParams,
} from '@/hooks/use-chat-request';
import { useFetchUserInfo } from '@/hooks/use-user-setting-request';
import { IClientConversation } from '@/interfaces/database/chat';
import { buildMessageUuidWithRole } from '@/utils/chat';
import { useEffect, useState } from 'react';
import {
  useGetSendButtonDisabled,
  useSendButtonDisabled,
} from '../../hooks/use-button-disabled';
import { useCreateConversationBeforeUploadDocument } from '../../hooks/use-create-conversation';
import { useSendMessage } from '../../hooks/use-send-chat-message';
import { buildMessageItemReference } from '../../utils';

interface IProps {
  controller: AbortController;
  stopOutputMessage(): void;
  conversation: IClientConversation;
}

export function SingleChatBox({
  controller,
  stopOutputMessage,
  conversation,
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
  const { visible, hideModal, documentId, selectedChunk, clickDocumentButton } =
    useClickDrawer();

  // console.log(derivedMessages);
  useEffect(() => {
    const messages = conversation?.message;
    if (Array.isArray(messages)) {
      setDerivedMessages(messages);
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

    // 2. 直接调用现有的发送逻辑
    handlePressEnter();
  };

  // import { SunIcon, SmileIcon, MoonIcon, StarIcon } from 'lucide-react';

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

  if (!conversation?.id) {
    // ✅ 情况 A：只有一条消息，显示带昵称的欢迎页
    return (
      <div
        className="
          flex flex-col items-center justify-center
          min-h-[60vh] w-full px-4
          animate-in fade-in slide-in-from-bottom-4 duration-700
        "
      >
        {/* 标题 */}
        <h1
          className="
              text-5xl sm:text-6xl font-extrabold
              mb-4 tracking-tight
              bg-gradient-to-r from-blue-500 via-indigo-500 to-purple-500
              bg-clip-text text-transparent
              dark:text-white
              
            "
        >
          您好, {userInfo?.nickname || '新朋友'}
          <span
            className="
                inline-block
                ml-2
                align-middle
                animate-[bounce_5s_ease-in-out_infinite]
              "
          >
            <TimeIcon />
          </span>
          <span className="ml-3 text-2xl font-medium text-gray-400 dark:text-gray-500">
            {greeting} · {hours}:{minutes}
          </span>
        </h1>

        {/* 副标题 */}
        <p
          className="
            text-2xl sm:text-3xl
            font-medium
            mb-2
            leading-tight
            bg-gradient-to-r from-green-800 to-teal-600
            dark:from-green-500 dark:to-teal-400
          "
          style={{
            backgroundClip: 'text',
            WebkitBackgroundClip: 'text',
            color: 'transparent',
            WebkitTextFillColor: 'transparent',
            /* 强制指定渐变色：深绿 -> 青绿 */
            backgroundImage:
              'linear-gradient(to right, #166534, #059669, #0d9488)',
          }}
        >
          我是恒丰纸业统一配置问答智能小助手
        </p>

        <p
          className="
              text-[#14b8a6] dark:text-[#2dd4bf]
              text-base sm:text-lg
              mb-6
              leading-snug
            "
        >
          左上方选择您的知识库😊
        </p>

        {/* 快捷操作 */}
        <div className="flex gap-3 flex-wrap justify-center">
          <button
            onClick={() => handleSuggestionClick('帮我写一份周报')}
            className="
                px-5 py-2.5
                rounded-full
                bg-white dark:bg-gray-800
                text-gray-700 dark:text-gray-200
                text-sm font-medium
                border border-gray-200 dark:border-gray-700
                shadow-sm
                hover:shadow-md hover:-translate-y-0.5
                transition-all duration-200
              "
          >
            📄 帮我写一份周报
          </button>

          <button
            onClick={() => handleSuggestionClick('帮我制定计划')}
            className="
                px-5 py-2.5
                rounded-full
                bg-white dark:bg-gray-800
                text-gray-700 dark:text-gray-200
                text-sm font-medium
                border border-gray-200 dark:border-gray-700
                shadow-sm
                hover:shadow-md hover:-translate-y-0.5
                transition-all duration-200
              "
          >
            📅 帮我制定计划
          </button>
        </div>
      </div>
    );
  }

  return (
    <section className="flex flex-col p-5 h-full">
      {/* 消息滚动区域 */}
      <div ref={messageContainerRef} className="flex-1 overflow-auto min-h-0">
        <div className="w-full pr-5">
          {/* {derivedMessages?.map((message, i) => {
            return (
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
                index={i}
                removeMessageById={removeMessageById}
                regenerateMessage={regenerateMessage}
                sendLoading={sendLoading}
                visibleAvatar={false}
                onSuggestionClick={handleSuggestionClick}

              ></MessageItem>
            );
          })} */}

          {derivedMessages?.map((message, i) => {
            // 🎯 核心逻辑：判断是否只有一条消息（即初始状态）
            const isOnlyWelcomeMessage =
              derivedMessages.length === 1 && i === 0;
            console.log(derivedMessages.length);

            if (isOnlyWelcomeMessage) {
              // ✅ 情况 A：只有一条消息，显示带昵称的欢迎页
              return (
                <div
                  className="
          flex flex-col items-center justify-center
          min-h-[60vh] w-full px-4
          animate-in fade-in slide-in-from-bottom-4 duration-700
        "
                >
                  {/* 标题 */}
                  <h1
                    className="
              text-5xl sm:text-6xl font-extrabold
              mb-4 tracking-tight
              bg-gradient-to-r from-blue-500 via-indigo-500 to-purple-500
              bg-clip-text text-transparent
              dark:text-white
              
            "
                  >
                    您好, {userInfo?.nickname || '新朋友'}
                    <span
                      className="
                inline-block
                ml-2
                align-middle
                animate-[bounce_5s_ease-in-out_infinite]
              "
                    >
                      <TimeIcon />
                    </span>
                    <span className="ml-3 text-2xl font-medium text-gray-400 dark:text-gray-500">
                      {greeting} · {hours}:{minutes}
                    </span>
                  </h1>

                  {/* 副标题 */}
                  <p
                    className="
            text-2xl sm:text-3xl
            font-medium
            mb-2
            leading-tight
            bg-gradient-to-r from-green-800 to-teal-600
            dark:from-green-500 dark:to-teal-400
          "
                    style={{
                      backgroundClip: 'text',
                      WebkitBackgroundClip: 'text',
                      color: 'transparent',
                      WebkitTextFillColor: 'transparent',
                      /* 强制指定渐变色：深绿 -> 青绿 */
                      backgroundImage:
                        'linear-gradient(to right, #166534, #059669, #0d9488)',
                    }}
                  >
                    我是恒丰纸业统一配置问答智能小助手
                  </p>

                  <p
                    className="
              text-[#14b8a6] dark:text-[#2dd4bf]
              text-base sm:text-lg
              mb-6
              leading-snug
            "
                  >
                    左上方选择您的知识库😊
                  </p>

                  {/* 快捷操作 */}
                  <div className="flex gap-3 flex-wrap justify-center">
                    <button
                      onClick={() => handleSuggestionClick('帮我写一份周报')}
                      className="
                px-5 py-2.5
                rounded-full
                bg-white dark:bg-gray-800
                text-gray-700 dark:text-gray-200
                text-sm font-medium
                border border-gray-200 dark:border-gray-700
                shadow-sm
                hover:shadow-md hover:-translate-y-0.5
                transition-all duration-200
              "
                    >
                      📄 帮我写一份周报
                    </button>

                    <button
                      onClick={() => handleSuggestionClick('帮我制定计划')}
                      className="
                px-5 py-2.5
                rounded-full
                bg-white dark:bg-gray-800
                text-gray-700 dark:text-gray-200
                text-sm font-medium
                border border-gray-200 dark:border-gray-700
                shadow-sm
                hover:shadow-md hover:-translate-y-0.5
                transition-all duration-200
              "
                    >
                      📅 帮我制定计划
                    </button>
                  </div>
                </div>
              );
            }

            // ✅ 情况 B：有多条消息，正常渲染对话气泡
            return (
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
                index={i}
                removeMessageById={removeMessageById}
                regenerateMessage={regenerateMessage}
                sendLoading={sendLoading}
                visibleAvatar={false}
                onSuggestionClick={handleSuggestionClick}
              ></MessageItem>
            );
          })}
        </div>
        {/* 用于滚动到底部的锚点 */}
        <div ref={scrollRef} />
      </div>
      {/* 底部输入框 */}
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
      />
      {/* PDF 预览弹窗 */}
      {visible && (
        <PdfSheet
          visible={visible}
          hideModal={hideModal}
          documentId={documentId}
          chunk={selectedChunk}
        ></PdfSheet>
      )}
    </section>
  );
}
