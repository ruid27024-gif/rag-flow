import { ReactComponent as AssistantIcon } from '@/assets/svg/assistant.svg';
import { MessageType } from '@/constants/chat';
import {
  IMessage,
  IReference,
  IReferenceChunk,
  UploadResponseDataType,
} from '@/interfaces/database/chat';
import classNames from 'classnames';
import { memo, useCallback, useMemo, useRef } from 'react';

import { IRegenerateMessage, IRemoveMessageById } from '@/hooks/logic-hooks';
import { cn } from '@/lib/utils';
import MarkdownContent from '../markdown-content';
import { ReferenceDocumentList } from '../next-message-item/reference-document-list';
import { UploadedMessageFiles } from '../next-message-item/uploaded-message-files';
import {
  PDFDownloadButton,
  extractPDFDownloadInfo,
  removePDFDownloadInfo,
} from '../pdf-download-button';
import { RAGFlowAvatar } from '../ragflow-avatar';
import { useTheme } from '../theme-provider';
import { AssistantGroupButton, UserGroupButton } from './group-button';
import styles from './index.less';

interface IProps extends Partial<IRemoveMessageById>, IRegenerateMessage {
  item: IMessage;
  reference: IReference;
  loading?: boolean;
  sendLoading?: boolean;
  visibleAvatar?: boolean;
  nickname?: string;
  avatar?: string;
  avatarDialog?: string | null;
  clickDocumentButton?: (documentId: string, chunk: IReferenceChunk) => void;
  index: number;
  showLikeButton?: boolean;
  showLoudspeaker?: boolean;
  onSuggestionClick?: (text: string) => void;
  onSuggestionDoubleClick?: (text: string) => void;
}

const MessageItem = ({
  item,
  reference,
  loading = false,
  avatar,
  avatarDialog,
  sendLoading = false,
  clickDocumentButton,
  index,
  removeMessageById,
  regenerateMessage,
  showLikeButton = true,
  showLoudspeaker = true,
  visibleAvatar = true,
  onSuggestionClick,
  onSuggestionDoubleClick,
}: IProps) => {
  const { theme } = useTheme();
  const isAssistant = item.role === MessageType.Assistant;
  const isUser = item.role === MessageType.User;

  console.log('🔍 item:', item);
  console.log('🔍 reference:', reference);
  // 上传的文件
  const uploadedFiles = useMemo(() => {
    return item?.files ?? [];
  }, [item?.files]);

  // 获取建议列表
  const suggestionsList = useMemo(() => {
    // if (loading) {
    //   return [];
    // }

    return item?.suggestions ?? [];
  }, [item?.suggestions, loading]);

  // console.log('🔍 原始 Reference 对象:', reference);
  const referenceDocumentList = useMemo(() => {
    if (loading) {
      return [];
    }
    return reference?.doc_aggs ?? [];
  }, [reference?.doc_aggs, loading]);

  // 将 item 转为格式化后的 JSON 字符串打印
  // console.log('🔍 完整的 Item 数据:', JSON.stringify(item, null, 2));
  // Extract PDF download info from message content
  const pdfDownloadInfo = useMemo(
    () => extractPDFDownloadInfo(item.content),
    [item.content],
  );
  // console.log('🔍 PDF下载信息:', pdfDownloadInfo);

  // If we have PDF download info, extract the remaining text
  const messageContent = useMemo(() => {
    if (!pdfDownloadInfo) return item.content;

    // Remove the JSON part from the content to avoid showing it
    return removePDFDownloadInfo(item.content, pdfDownloadInfo);
  }, [item.content, pdfDownloadInfo]);

  const handleRegenerateMessage = useCallback(() => {
    regenerateMessage?.(item);
  }, [regenerateMessage, item]);

  const suggestionClickTimerRef = useRef<ReturnType<typeof setTimeout> | null>(
    null,
  );

  //   const mockDownloadInfo = {
  //   base64: "JVBERi0xLjQKJeLjz9MKMiAwIG9iago8PCAvVHlwZSAvQ2F0YWxvZyAvUGFnZXMgMyAwIFIgPj4KZW5kb2JqCjMgMCBvYmoKPDwgL1R5cGUgL1BhZ2VzIC9LaWRzIFsgNCAwIFIgXSAvQ291bnQgMSA+PgplbmRvYmoKNCAwIG0KPDwgL1R5cGUgL1BhZ2UgL1BhcmVudCAzIDAgUiAvUmVzb3VyY2VzIDw8IC9Gb250IDw8IC9GMSA1IDAgUiA+PiA+PiAvQ29udGVudHMgNiAwIFIgPj4KZW5kb2JqCjUgMCBvYmoKPDwgL1R5cGUgL0ZvbnQgL1N1YnR5cGUgL1R5cGUxIC9CYXNlRm9udCAvSGVsdmV0aWNhID4+CmVuZG9iago2IDAgbwo8PCAvTGVuZ3RoIDQ0ID4+CnN0cmVhbQoKvUYxIDEyIFRmCjEwMCAxMDAgVGQKKFJhZ0Zsb3chKSBUagplbmRzdHJlYW0KZW5kb2JqCjEgMCBvYmoKPDwgL1R5cGUgL0NhdGFsb2cgL1BhZ2VzIDMgMCBSID4+CmVuZG9iago=",
  //   filename: "mock-document.pdf",
  //   mime_type: "application/pdf",
  // };

  return (
    <div
      className={classNames(styles.messageItem, {
        [styles.messageItemLeft]: item.role === MessageType.Assistant,
        [styles.messageItemRight]: item.role === MessageType.User,
      })}
    >
      <section
        className={classNames(styles.messageItemSection, {
          [styles.messageItemSectionLeft]: item.role === MessageType.Assistant,
          [styles.messageItemSectionRight]: item.role === MessageType.User,
        })}
      >
        <div
          className={classNames(styles.messageItemContent, {
            [styles.messageItemContentReverse]: item.role === MessageType.User,
          })}
        >
          {visibleAvatar &&
            (item.role === MessageType.User ? (
              <RAGFlowAvatar
                className="size-10"
                avatar={avatar ?? '/logo.svg'}
                isPerson
              />
            ) : avatarDialog ? (
              <RAGFlowAvatar
                className="size-10"
                avatar={avatarDialog}
                isPerson
              />
            ) : (
              <AssistantIcon />
            ))}

          {/* // 消息上的按钮 */}
          {/* <section className="flex gap-2 flex-1 flex-col"> */}
          <section
            className={classNames('flex gap-2 flex-col min-w-0', {
              'flex-1': item.role === MessageType.Assistant,
              'items-end': item.role === MessageType.User,
            })}
          >
            {isAssistant ? (
              index !== 0 && (
                <AssistantGroupButton
                  messageId={item.id}
                  content={item.content}
                  prompt={item.prompt}
                  showLikeButton={showLikeButton}
                  audioBinary={item.audio_binary}
                  // showLoudspeaker={showLoudspeaker}
                  showLoudspeaker={false}
                ></AssistantGroupButton>
              )
            ) : (
              <UserGroupButton
                content={item.content}
                messageId={item.id}
                removeMessageById={removeMessageById}
                regenerateMessage={regenerateMessage && handleRegenerateMessage}
                sendLoading={sendLoading}
              ></UserGroupButton>
            )}

            {/* <PDFDownloadButton
                  downloadInfo={mockDownloadInfo}
                /> */}

            {/* Show PDF download button if download info is present */}
            {pdfDownloadInfo && (
              <PDFDownloadButton
                downloadInfo={pdfDownloadInfo}
                className="mb-2"
              />
            )}

            {messageContent && (
              <div
                className={cn(
                  isAssistant
                    ? theme === 'dark'
                      ? styles.messageTextDark
                      : styles.messageText
                    : styles.messageUserText,
                  { '!bg-bg-card': !isAssistant },
                )}
                style={{
                  fontFamily: `-apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji"`,
                  fontSize: 16,
                  lineHeight: 1.75,
                  fontWeight: 400,
                  letterSpacing: '0.01em',
                }}
              >
                <MarkdownContent
                  loading={loading}
                  content={messageContent}
                  reference={reference}
                  clickDocumentButton={clickDocumentButton}
                ></MarkdownContent>
              </div>
            )}
            {isAssistant && referenceDocumentList.length > 0 && (
              <ReferenceDocumentList
                list={referenceDocumentList}
              ></ReferenceDocumentList>
            )}
            {/* {isAssistant && suggestionsList.length > 0 && (
              <div className="mt-2.5 flex flex-col gap-2">
                {suggestionsList.map((suggestion, index) => (
                  <span
                    key={index}
                    // 1. 绑定点击事件：调用父组件传来的函数
                    onClick={() => onSuggestionClick?.(suggestion)}
                    className="
                      text-sm cursor-pointer select-none
                      text-blue-600 hover:text-blue-800
                      dark:text-blue-400 dark:hover:text-blue-300
                    "
                  >
                    {suggestion}
                  </span>
                ))}
              </div>
            )} */}

            {isAssistant && suggestionsList.length > 0 && (
              <div
                className="
                  mt-4
                  w-full
                  max-w-[850px]
                  border-t
                  border-gray-200/70
                  dark:border-gray-700/50
                "
              >
                {suggestionsList.map((suggestion, index) => (
                  <div
                    key={index}
                    onClick={() => {
                      if (suggestionClickTimerRef.current) {
                        clearTimeout(suggestionClickTimerRef.current);
                      }

                      suggestionClickTimerRef.current = setTimeout(() => {
                        // 单击：只进入输入框
                        onSuggestionClick?.(suggestion);
                        suggestionClickTimerRef.current = null;
                      }, 220);
                    }}
                    onDoubleClick={() => {
                      if (suggestionClickTimerRef.current) {
                        clearTimeout(suggestionClickTimerRef.current);
                        suggestionClickTimerRef.current = null;
                      }

                      // 双击：直接发送
                      onSuggestionDoubleClick?.(suggestion);
                    }}
                    className="
                      group
                      flex
                      cursor-pointer
                      select-none
                      items-start
                      gap-3
                      border-b
                      border-gray-200/70
                      py-3
                      text-sm
                      leading-6
                      text-gray-900
                      transition-colors
                      hover:bg-gray-50/70
                      dark:border-gray-700/50
                      dark:text-gray-100
                      dark:hover:bg-white/5
                    "
                  >
                    {/* 左侧小箭头 */}
                    <span
                      className="
                        mt-0.5
                        shrink-0
                        text-base
                        leading-6
                        text-gray-400
                        transition-colors
                        group-hover:text-gray-600
                        dark:text-gray-500
                        dark:group-hover:text-gray-300
                      "
                    >
                      ↳
                    </span>

                    {/* 建议文字 */}
                    <span
                      className="
                        min-w-0
                        flex-1
                        break-words
                        text-gray-900
                        dark:text-gray-100
                      "
                    >
                      {suggestion}
                    </span>
                  </div>
                ))}
              </div>
            )}
            {isUser &&
              Array.isArray(uploadedFiles) &&
              uploadedFiles.length > 0 && (
                <UploadedMessageFiles
                  files={uploadedFiles as UploadResponseDataType[]}
                ></UploadedMessageFiles>
              )}
          </section>
        </div>
      </section>
    </div>
  );
};

export default memo(MessageItem);
