import { NextMessageInput } from '@/components/message-input/next';
import MessageItem from '@/components/message-item';
import { ModeToggleButtons } from '@/components/mode-toggle-buttons';
import { MessageType } from '@/constants/chat';
import {
  useFetchDialog,
  useGetChatSearchParams,
} from '@/hooks/use-chat-request';
import { useFetchUserInfo } from '@/hooks/use-user-setting-request';
import { getAuthorization } from '@/utils/authorization-util';
import { buildMessageUuidWithRole } from '@/utils/chat';
import { message } from 'antd';
import * as React from 'react';
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
import type { ComplianceTemplate } from './ComplianceTemplateDialog';
import ComplianceTemplateDialog from './ComplianceTemplateDialog';

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
  customerComplaint?: boolean;
  onEnableDeepReasoning?: () => void;
  onEnableMultiKbReasoning?: () => void;
  onEnableAgent?: () => void;
  onEnableProjectCompliance?: () => void | Promise<void>;
  onEnableExperimentReport?: () => void | Promise<void>;
  onEnableCustomerComplaint?: () => void | Promise<void>;
  refreshConversation?: () => Promise<any>;
  onOpenWorkspace?: () => void;
  onWelcomePageChange?: (isWelcome: boolean) => void; // 👈 新增
  isWorkspaceOpen?: boolean; // 👈 新增：从最外层传进来
  forceHideWelcome?: boolean;
  onClickSkill?: () => void; // 👈 新增
  onSelectSkill?: (skill: any) => void; // 👈 新增
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
  customerComplaint,
  onEnableDeepReasoning,
  onEnableMultiKbReasoning,
  onEnableAgent,
  onEnableProjectCompliance,
  onEnableExperimentReport,
  onEnableCustomerComplaint,
  refreshConversation,
  onOpenWorkspace,
  onWelcomePageChange, // 👈 新增
  isWorkspaceOpen = false, // 👈 新增
  forceHideWelcome = false,
  onClickSkill, // 👈 新增
  onSelectSkill, // 👈 新增
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

  const authHeaders = React.useMemo(
    () => ({
      Authorization: getAuthorization() || '',
      'Content-Type': 'application/json',
    }),
    [],
  );

  // ===================== 合规模板相关 =====================

  const [templateDialogVisible, setTemplateDialogVisible] =
    React.useState(false);
  const [complianceTemplates, setComplianceTemplates] = React.useState<
    ComplianceTemplate[]
  >([]);
  const [templateLoading, setTemplateLoading] = React.useState(false);
  /** 打开大弹窗时默认选中的模板 id */
  const [pendingTemplateId, setPendingTemplateId] = React.useState<
    string | null
  >(null);

  /** 拉取模板列表（幂等，只拉一次） */
  const loadComplianceTemplates = React.useCallback(async () => {
    if (complianceTemplates.length > 0) return;
    setTemplateLoading(true);
    try {
      const res = await fetch('/v1/file/templates', {
        method: 'GET',
        headers: authHeaders,
        credentials: 'include',
      });
      const result = await res.json();
      const list = Array.isArray(result) ? result : (result.data ?? []);

      setComplianceTemplates(
        list.map((item: any) => ({
          id: item.id,
          name: item.name,
          size: item.size,
          updatedAt: item.updatedAt,
        })),
      );
    } catch (err) {
      console.error('拉取模板失败', err);
    } finally {
      setTemplateLoading(false);
    }
  }, [authHeaders, complianceTemplates.length]);

  /** 组件挂载时预加载一次，这样点模板按钮立即有小面板数据 */
  React.useEffect(() => {
    loadComplianceTemplates();
  }, [loadComplianceTemplates]);

  /** 点小面板某一项 / 点「查看模板」 */
  const handleOpenComplianceTemplate = (tpl?: ComplianceTemplate) => {
    setPendingTemplateId(tpl?.id || null);
    setTemplateDialogVisible(true);
  };

  /** 工作区占位 */
  const handleOpenComplianceFolder = () => {
    onOpenWorkspace?.();
  };

  /** 下载模板 */
  const handleDownloadTemplate = async (tpl: ComplianceTemplate) => {
    try {
      const res = await fetch(
        `/v1/file/template-file?path=${encodeURIComponent(tpl.id)}&preview=0`,
        {
          method: 'GET',
          headers: authHeaders,
          credentials: 'include',
        },
      );
      if (!res.ok) throw new Error('下载失败');

      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = tpl.name;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error(err);
      message.error('下载失败');
    }
  };

  // ===================== 复制工具 =====================

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

  // ===================== 消息相关副作用 =====================

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
          content: item.content ?? item.answer ?? '',
          agentEvents,
          agent_events: item.agent_events || agentEvents,
        };
      });
      setDerivedMessages(normalizedMessages);
    }
  }, [conversation?.message, setDerivedMessages]);

  useEffect(() => {
    if (conversationId === '') {
      setDerivedMessages([]);
    }
  }, [conversationId, setDerivedMessages]);

  // ===================== 建议点击 =====================

  const handleSuggestionClick = (suggestion: string) => {
    setValue(suggestion);
  };

  const handleSuggestionDoubleClick = (suggestion: string) => {
    flushSync(() => {
      setValue(suggestion);
    });
    handlePressEnter(suggestion);
  };

  // ===================== 分享 =====================

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
      const targetMessage =
        typeof targetMessageOrId === 'string'
          ? { id: targetMessageOrId }
          : targetMessageOrId;

      const targetId = targetMessage?.id;
      const targetRole = targetMessage?.role;
      const targetContent =
        targetMessage?.content ?? targetMessage?.answer ?? '';

      const latestConversation = refreshConversation
        ? await refreshConversation(currentConversationId)
        : conversation;

      const latestMessages = latestConversation?.message || [];

      let realMessage: any = null;

      if (targetId) {
        realMessage = latestMessages.find((item: any) => item.id === targetId);
      }

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
      if (result.code !== 0) {
        message.error(result.message || '创建分享失败');
        return;
      }

      const shareUrl = result.data?.url;
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

  // ===================== Rebase =====================

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

  // ===================== 背景云 =====================

  // 真实判断（用于上报父组件）
  const internalWelcome = !conversationId || derivedMessages.length === 1;

  // 实际渲染用：技能页打开时强制视为非欢迎页 → 云不渲染
  const isWelcomePage = forceHideWelcome ? false : internalWelcome;

  useEffect(() => {
    onWelcomePageChange?.(internalWelcome);
  }, [internalWelcome, onWelcomePageChange]);
  const random = (min: number, max: number) =>
    Math.random() * (max - min) + min;

  const makeBlueClouds = () => {
    const blueColors = [
      [72, 111, 178],
      [102, 138, 195],
      [128, 162, 210],
    ];

    const whiteColors = [
      [245, 249, 254],
      [235, 242, 252],
      [252, 253, 255],
    ];

    return Array.from({ length: 20 }).map((_, index) => {
      const isBaseCloud = index < 2;
      const isBlue = isBaseCloud ? true : Math.random() < 0.85;
      const palette = isBlue ? blueColors : whiteColors;
      const color = palette[Math.floor(Math.random() * palette.length)];

      const dir = Math.random() > 0.5 ? 'right' : 'left';
      const duration = random(28, 45);
      const delay = random(-duration, 0);
      const scaleMax = random(1.15, 1.45);
      const scaleMin = random(0.7, 0.9);

      return {
        top: isBaseCloud ? random(-10, 30) : random(-30, 90),
        width: isBaseCloud ? random(60, 85) : random(28, 60),
        height: isBaseCloud ? random(55, 75) : random(28, 60),
        opacity: 1,
        backgroundColor: `rgba(${color[0]}, ${color[1]}, ${color[2]}, ${
          isBlue ? random(0.35, 0.6) : random(0.5, 0.8)
        })`,
        dir,
        duration,
        delay,
        scaleMax,
        scaleMin,
        isBaseCloud,
        isBlue,
      };
    });
  };

  const [blueClouds] = useState(makeBlueClouds);

  // ===================== 输入框 =====================

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
      wrapperClassName={
        isWelcomePage
          ? 'border border-white/70 bg-slate-200/40 backdrop-blur-xl shadow-sm shadow-slate-300/20 focus-within:border-white/90 focus-within:bg-slate-100/50 focus-within:ring-0 dark:border-slate-700/60 dark:bg-slate-800/50 dark:focus-within:border-slate-600'
          : ''
      }
      reasoning={reasoning}
      agentMod={agentMod}
      projectCompliance={projectCompliance}
      experimentReport={experimentReport}
      customerComplaint={customerComplaint}
      // onResetMode={onEnableMultiKbReasoning}
      onClickComplianceFolder={handleOpenComplianceFolder}
      // ✅ 小面板要展示的数据
      complianceTemplates={complianceTemplates}
      complianceTemplatesLoading={templateLoading}
      // ✅ 点小面板某一项 / 点「查看模板」都会走这个
      onClickComplianceTemplate={handleOpenComplianceTemplate}
      isComplianceFolderOpen={isWorkspaceOpen} // 👈 新增这一行
      onClickSkill={onClickSkill}
      onSelectSkill={onSelectSkill}
    />
  );

  // ===================== 渲染 =====================

  return (
    <>
      {isWelcomePage && (
        <>
          <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden dark:hidden">
            <div className="absolute inset-0 bg-[#EDF2FA]" />

            <div className="absolute inset-0 blur-[80px]">
              {/* 👇 左上角专属蓝云（更蓝版） */}
              <div
                className="absolute rounded-full"
                style={{
                  top: '-15%',
                  left: '-10%',
                  width: '48%',
                  height: '48%',
                  backgroundColor: 'rgba(37, 99, 235, 0.65)',
                  animation: 'breatheA 15s ease-in-out infinite',
                }}
              />
              {blueClouds.map((cloud, index) => {
                if (cloud.isBaseCloud) {
                  return (
                    <div
                      key={index}
                      className="absolute rounded-full"
                      style={{
                        top: `${cloud.top}%`,
                        left: index === 0 ? '25%' : '55%',
                        width: `${cloud.width}%`,
                        height: `${cloud.height}%`,
                        opacity: cloud.opacity,
                        backgroundColor: cloud.backgroundColor,
                      }}
                    />
                  );
                }

                return (
                  <div
                    key={index}
                    className="absolute rounded-full"
                    style={
                      {
                        top: `${cloud.top}%`,
                        left: 0,
                        width: `${cloud.width}vw`,
                        height: `${cloud.height}vw`,
                        opacity: cloud.opacity,
                        backgroundColor: cloud.backgroundColor,
                        animation: `${
                          cloud.dir === 'right' ? 'blowRight' : 'blowLeft'
                        } ${cloud.duration}s linear infinite`,
                        animationDelay: `${cloud.delay}s`,
                        willChange: 'transform',
                        '--scaleMin': cloud.scaleMin,
                        '--scaleMax': cloud.scaleMax,
                      } as React.CSSProperties
                    }
                  />
                );
              })}

              <div
                className="absolute h-[65%] w-[55%] rounded-full bg-[#f3f8fe]/95 animate-[breatheA_14s_ease-in-out_infinite]"
                style={{ top: '18%', left: '18%' }}
              />
              <div
                className="absolute h-[45%] w-[42%] rounded-full bg-[#f5f9fe]/90 animate-[breatheB_18s_ease-in-out_infinite]"
                style={{ top: '-8%', left: '-6%' }}
              />
              <div
                className="absolute h-[50%] w-[50%] rounded-full bg-[#f5f9fe]/90 animate-[breatheA_16s_ease-in-out_infinite]"
                style={{ bottom: '2%', right: '-4%' }}
              />
            </div>

            <div
              className="absolute inset-0
                bg-[repeating-linear-gradient(to_right,transparent_0,transparent_98px,rgba(119,151,199,0.08)_99px,transparent_100px),repeating-linear-gradient(to_bottom,transparent_0,transparent_98px,rgba(119,151,199,0.06)_99px,transparent_100px)]"
            />
          </div>

          <style>{`
            @keyframes blowRight {
              0%   { transform: translateX(-100vw) scale(var(--scaleMin, 0.85)); }
              50%  { transform: translateX(50vw)   scale(var(--scaleMax, 1.25)); }
              100% { transform: translateX(200vw)  scale(var(--scaleMin, 0.85)); }
            }
            @keyframes blowLeft {
              0%   { transform: translateX(200vw)  scale(var(--scaleMin, 0.85)); }
              50%  { transform: translateX(50vw)   scale(var(--scaleMax, 1.25)); }
              100% { transform: translateX(-100vw) scale(var(--scaleMin, 0.85)); }
            }
            @keyframes breatheA {
              0%   { transform: scale(1.15); }
              50%  { transform: scale(0.9); }
              100% { transform: scale(1.15); }
            }
            @keyframes breatheB {
              0%   { transform: scale(0.92); }
              50%  { transform: scale(1.15); }
              100% { transform: scale(0.92); }
            }
          `}</style>
        </>
      )}

      <section className="flex h-full min-h-0 w-full flex-col overflow-hidden">
        {isWelcomePage ? (
          <div className="flex flex-1 min-h-0 w-full items-center justify-center px-5">
            <div className="w-full max-w-[860px] translate-y-0">
              <div className="mb-12 flex items-center justify-center gap-6 text-center">
                <img
                  src="/hf_pic.png"
                  className="
                    h-[72px]
                    w-[72px]
                    object-contain
                    drop-shadow-[0_10px_18px_rgba(16,185,129,0.18)]
                  "
                />

                <div
                  className="
                    text-[48px]
                    font-normal
                    tracking-[0.18em]
                    leading-none
                    text-[#1a2c4a]
                    dark:text-slate-100
                  "
                >
                  恒丰纸业
                </div>
              </div>

              <div className="w-full max-w-[1000px] mx-auto">{inputBox}</div>

              <ModeToggleButtons
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
                disabled={disabled || sendLoading || isUploading}
                className="mt-5 justify-center"
              />
            </div>
          </div>
        ) : (
          <>
            <div
              ref={messageContainerRef}
              className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden [scrollbar-gutter:stable]"
            >
              <div className="mx-auto w-full max-w-[800px] px-5 pt-0 pb-4">
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

                <div ref={scrollRef} />
              </div>
            </div>

            <div className="shrink-0 w-full px-4 pb-2">
              {/* 强制压缩 inputBox 内部所有元素的上下内边距 */}
              <div className="mx-auto w-full max-w-[800px] rounded-xl [&_textarea]:py-2 [&_textarea]:min-h-[44px] [&>div]:py-1 [&>div]:pb-2">
                {inputBox}
              </div>
            </div>
          </>
        )}
      </section>

      {/* ✅ 合规模板大弹窗 */}
      <ComplianceTemplateDialog
        visible={templateDialogVisible}
        onClose={() => {
          setTemplateDialogVisible(false);
          setPendingTemplateId(null);
        }}
        templates={complianceTemplates}
        loading={templateLoading}
        defaultSelectedId={pendingTemplateId}
        onDownload={handleDownloadTemplate}
      />
    </>
  );
}
