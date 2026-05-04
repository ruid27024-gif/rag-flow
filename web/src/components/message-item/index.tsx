import { ReactComponent as AssistantIcon } from '@/assets/svg/assistant.svg';
import { MessageType } from '@/constants/chat';
import {
  IMessage,
  IReference,
  IReferenceChunk,
  UploadResponseDataType,
} from '@/interfaces/database/chat';
import classNames from 'classnames';
import { memo, useCallback, useMemo } from 'react';

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
}: IProps) => {
  const { theme } = useTheme();
  const isAssistant = item.role === MessageType.Assistant;
  const isUser = item.role === MessageType.User;

  // 上传的文件
  const uploadedFiles = useMemo(() => {
    return item?.files ?? [];
  }, [item?.files]);

  // 获取建议列表
  const suggestionsList = useMemo(() => {
    if (loading) {
      return [];
    }
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
          <section className="flex gap-2 flex-1 flex-col">
            {isAssistant ? (
              index !== 0 && (
                <AssistantGroupButton
                  messageId={item.id}
                  content={item.content}
                  prompt={item.prompt}
                  showLikeButton={showLikeButton}
                  audioBinary={item.audio_binary}
                  showLoudspeaker={showLoudspeaker}
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

            {/* Show message content if there's any text besides the download */}
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
                  // 👇 核心优化：引入 PingFang SC (Mac/iOS) 和 Microsoft YaHei (Windows)
                  fontFamily: `-apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji"`,
                  fontSize: 16, // 16px 是阅读舒适区的标准大小
                  lineHeight: 1.75, // 1.75 的行高能带来极佳的呼吸感
                  fontWeight: 400, // 常规字重，清晰易读
                  letterSpacing: '0.01em', // 微调字间距，比 0.2px 更适应不同字号
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
            {isAssistant && suggestionsList.length > 0 && (
              <div className="mt-2.5 flex flex-col gap-2">
                {suggestionsList.map((suggestion, index) => (
                  <span
                    key={index}
                    // 1. 绑定点击事件：调用父组件传来的函数
                    onClick={() => onSuggestionClick?.(suggestion)}
                    // // 👇 样式全部改为 Tailwind 类名，并加入 dark 模式支持
                    // className="
                    //   px-3 py-1.5
                    //   text-sm text-gray-700
                    //   bg-gray-100 border border-gray-200
                    //   rounded-lg cursor-pointer select-none
                    //   transition-colors duration-200 ease-in-out

                    //   /* 白天模式悬停效果 */
                    //   hover:bg-blue-50 hover:border-blue-200

                    //   /* 🌙 黑夜模式样式 */
                    //   dark:bg-slate-800 dark:border-slate-700 dark:text-gray-200

                    //   /* 🌙 黑夜模式悬停效果 */
                    //   dark:hover:bg-slate-700 dark:hover:border-slate-600
                    // "

                    className="
                    text-sm cursor-pointer select-none
                    text-gray-600 hover:text-blue-600
                    dark:text-gray-400 dark:hover:text-blue-400
                  "
                  >
                    {suggestion}
                  </span>
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
