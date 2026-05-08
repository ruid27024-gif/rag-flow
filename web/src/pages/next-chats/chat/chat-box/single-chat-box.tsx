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

  return (
    <section className="flex flex-col p-5 h-full">
      {/* 消息滚动区域 */}
      <div ref={messageContainerRef} className="flex-1 overflow-auto min-h-0">
        <div className="w-full pr-5">
          {/* 🎯 核心判断：没有对话ID 或 有对话ID但消息为空时显示欢迎页 */}
          {!conversationId || derivedMessages.length === 1 ? (
            // ✅ 情况 A：显示带昵称的欢迎页
            /* 外层容器 */

            <div
              className="
  relative overflow-hidden
  p-8                    /* 基础内边距 */
  py-16                  /* 覆盖：上下内边距增加到 4rem（64px），高度变高 */
  rounded-3xl
  bg-gradient-to-b from-green-50/50 to-white dark:from-green-900/20 dark:to-gray-900
  border border-green-100 dark:border-green-900/30
  text-center space-y-4
  mt-12
"
            >
              {/* 装饰性背景光晕 */}
              <div className="absolute top-0 left-1/2 -translate-x-1/2 w-64 h-64 bg-green-400/20 blur-3xl rounded-full pointer-events-none" />

              <h1 className="relative text-4xl sm:text-5xl font-extrabold text-green-900 dark:text-green-100 tracking-tight">
                恒丰纸业智能小助手
                <span className="ml-2 inline-block animate-bounce text-green-600">
                  <TimeIcon />
                </span>
              </h1>

              <p className="relative text-lg text-gray-600 dark:text-gray-400">
                欢迎回来，
                <span className="font-bold text-pink-700 dark:text-green-400">
                  {userInfo?.nickname}
                </span>
                <span className="mx-2 opacity-40">|</span>
                <span className="font-mono text-sm text-green-700 bg-white/50 dark:bg-black/20 px-2 py-0.5 rounded">
                  {hours}:{minutes}
                </span>
              </p>
            </div>
          ) : (
            // ✅ 情况 B：有对话ID且消息不为空，正常渲染对话气泡
            derivedMessages?.map((message, i) => (
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
              />
            ))
          )}
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
        />
      )}
    </section>
  );
}
