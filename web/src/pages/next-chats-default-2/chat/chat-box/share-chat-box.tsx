import MessageItem from '@/components/message-item';
import { MessageType } from '@/constants/chat';
import { buildMessageUuidWithRole } from '@/utils/chat';
import { useMemo, useRef } from 'react';
import { buildMessageItemReference } from '../../utils';

type ShareChatBoxProps = {
  conversation: IClientConversation;
  clickDocumentButton?: any;
  onOpenReferencePanel?: any;
};

function normalizeRole(role: any) {
  const value = String(role || '').toLowerCase();

  if (value === 'assistant') {
    return MessageType.Assistant;
  }

  if (value === 'user') {
    return MessageType.User;
  }

  return role;
}

function isAssistantRole(role: any) {
  return (
    role === MessageType.Assistant ||
    String(role || '').toLowerCase() === 'assistant'
  );
}

/**
 * 如果分享快照里的 reference 已经挂在每条 assistant message 上，
 * 这里可以把它还原成 conversation.reference。
 *
 * 规则：
 * - 第 0 条 assistant 是开场白，不消耗 reference；
 * - 后续 assistant 依次对应 reference。
 */
function buildReferenceFromMessages(messages: any[]) {
  return messages
    .filter((item, index) => {
      if (!isAssistantRole(item.role)) return false;

      // 第 0 条 assistant 是开场白，不对应 reference
      if (index === 0) return false;

      return true;
    })
    .map((item) => item.reference || { chunks: [] });
}

export function ShareChatBox({
  conversation,
  clickDocumentButton,
  onOpenReferencePanel,
}: ShareChatBoxProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const messageContainerRef = useRef<HTMLDivElement>(null);

  /**
   * 分享页只展示后端快照里的消息。
   * 不依赖 URL conversationId，不显示欢迎页，不显示输入框。
   */
  const derivedMessages = useMemo(() => {
    const messages = conversation?.message || [];

    if (!Array.isArray(messages)) {
      return [];
    }

    return messages.map((item: any) => ({
      ...item,
      role: normalizeRole(item.role),
    }));
  }, [conversation]);

  /**
   * 优先使用 conversation.reference。
   * 如果没有，则从每条 assistant message.reference 中恢复。
   */
  const derivedReference = useMemo(() => {
    const reference = conversation?.reference;

    if (Array.isArray(reference) && reference.length > 0) {
      return reference;
    }

    return buildReferenceFromMessages(derivedMessages);
  }, [conversation?.reference, derivedMessages]);

  if (!derivedMessages.length) {
    return (
      <section className="flex h-full min-h-0 w-full items-center justify-center overflow-hidden">
        <Empty description="暂无分享内容" />
      </section>
    );
  }

  return (
    <section className="flex h-full min-h-0 w-full flex-col overflow-hidden">
      {/* 消息滚动区域 */}
      <div
        ref={messageContainerRef}
        className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden [scrollbar-gutter:stable]"
      >
        {/* 内容居中区域 */}
        <div className="max-w-[860px] mx-auto w-full px-5 pt-6 pb-8">
          {derivedMessages.map((message: any, i: number) => (
            <MessageItem
              loading={false}
              key={buildMessageUuidWithRole(message)}
              item={message}
              nickname=""
              avatar=""
              avatarDialog=""
              reference={buildMessageItemReference(
                {
                  message: derivedMessages,
                  reference: derivedReference,
                },
                message,
              )}
              clickDocumentButton={clickDocumentButton}
              onOpenReferencePanel={onOpenReferencePanel}
              index={i}
              /**
               * 分享页只读：
               * 不允许删除、重新生成
               */
              removeMessageById={undefined}
              regenerateMessage={undefined}
              sendLoading={false}
              /**
               * 分享页不显示头像
               */
              visibleAvatar={false}
              /**
               * 分享页不需要建议问题交互
               */
              onSuggestionClick={undefined}
              onSuggestionDoubleClick={undefined}
              /**
               * 分享页不需要再次分享
               */
              onShareMessage={undefined}
              isLastMessage={derivedMessages.length - 1 === i}
              hideAssistantButton
            />
          ))}

          <div ref={scrollRef} />
        </div>
      </div>
    </section>
  );
}
