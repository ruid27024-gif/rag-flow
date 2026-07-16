'use client';

import {
  FileUpload,
  FileUploadDropzone,
  FileUploadItem,
  FileUploadItemDelete,
  FileUploadItemMetadata,
  FileUploadItemPreview,
  FileUploadItemProgress,
  FileUploadList,
  FileUploadTrigger,
  type FileUploadProps,
} from '@/components/file-upload';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/lib/utils';
import { t } from 'i18next';
import {
  CircleStop,
  Layers3,
  Paperclip,
  Send,
  Sparkles,
  Upload,
  X,
} from 'lucide-react';
import * as React from 'react';
import { useEffect } from 'react';
import { toast } from 'sonner';

interface IProps {
  disabled: boolean;
  value: string;
  sendDisabled: boolean;
  sendLoading: boolean;
  conversationId: string;
  uploadMethod?: string;
  isShared?: boolean;
  showUploadIcon?: boolean;
  isUploading?: boolean;
  onPressEnter(...prams: any[]): void;
  onInputChange: React.ChangeEventHandler<HTMLTextAreaElement>;
  createConversationBeforeUploadDocument?(message: string): Promise<any>;
  stopOutputMessage?(): void;
  onUpload?: NonNullable<FileUploadProps['onUpload']>;
  removeFile?(file: File): void;
  reasoning: boolean;
  agentMod: boolean;
  onEnableDeepReasoning?: () => void;
  onEnableMultiKbReasoning?: () => void;
  onEnableAgent?: () => void;
}

export function NextMessageInput({
  isUploading = false,
  value,
  sendDisabled,
  sendLoading,
  disabled,
  showUploadIcon = true,
  onUpload,
  onInputChange,
  stopOutputMessage,
  onPressEnter,
  removeFile,
  reasoning,
  agentMod,
  onEnableDeepReasoning,
  onEnableMultiKbReasoning,
  onEnableAgent,
}: IProps) {
  const [files, setFiles] = React.useState<File[]>([]);
  const [audioInputValue, setAudioInputValue] = React.useState<string | null>(
    null,
  );
  const [inputHeight, setInputHeight] = React.useState(120);
  const startYRef = React.useRef(0);
  const startHeightRef = React.useRef(120);

  useEffect(() => {
    if (audioInputValue !== null) {
      onInputChange({
        target: { value: audioInputValue },
      } as React.ChangeEvent<HTMLTextAreaElement>);

      setTimeout(() => {
        onPressEnter();
        setAudioInputValue(null);
      }, 0);
    }
  }, [audioInputValue, onInputChange, onPressEnter]);

  const onFileReject = React.useCallback((file: File, message: string) => {
    toast(message, {
      description: `"${file.name.length > 20 ? `${file.name.slice(0, 20)}...` : file.name}" has been rejected`,
    });
  }, []);

  const submit = React.useCallback(() => {
    if (isUploading) return;
    onPressEnter();
    setFiles([]);
  }, [isUploading, onPressEnter]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  const handleRemoveFile = React.useCallback(
    (file: File) => () => {
      removeFile?.(file);
    },
    [removeFile],
  );

  const handleResizeMouseDown = React.useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      e.preventDefault();

      startYRef.current = e.clientY;
      startHeightRef.current = inputHeight;

      const handleMouseMove = (event: MouseEvent) => {
        /**
         * 因为拖的是上边沿：
         * 鼠标往上移动，event.clientY 变小，高度增加
         * 鼠标往下移动，event.clientY 变大，高度减少
         */
        const deltaY = startYRef.current - event.clientY;
        const nextHeight = startHeightRef.current + deltaY;

        const minHeight = 90;
        const maxHeight = 360;

        const finalHeight = Math.min(
          Math.max(nextHeight, minHeight),
          maxHeight,
        );

        setInputHeight(finalHeight);
      };

      const handleMouseUp = () => {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);

        document.body.style.userSelect = '';
        document.body.style.cursor = '';
      };

      document.body.style.userSelect = 'none';
      document.body.style.cursor = 'ns-resize';

      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    },
    [inputHeight],
  );
  return (
    <FileUpload
      value={files}
      onValueChange={setFiles}
      onUpload={onUpload}
      onFileReject={onFileReject}
      className="relative w-full items-center "
      disabled={isUploading || disabled}
    >
      <FileUploadDropzone
        tabIndex={-1}
        // Prevents the dropzone from triggering on click
        onClick={(event) => event.preventDefault()}
        className="absolute top-0 left-0 z-0 flex size-full items-center justify-center rounded-none border-none bg-background/50 p-0 opacity-0 backdrop-blur transition-opacity duration-200 ease-out data-[dragging]:z-10 data-[dragging]:opacity-100"
      >
        <div className="flex flex-col items-center gap-1 text-center">
          <div className="flex items-center justify-center rounded-full border p-2.5">
            <Upload className="size-6 text-muted-foreground" />
          </div>
          <p className="font-medium text-sm">Drag & drop files here</p>
          <p className="text-muted-foreground text-xs">
            Upload max 5 files each up to 5MB
          </p>
        </div>
      </FileUploadDropzone>
      {/* <div
        className="relative flex w-full flex-col gap-2.5 rounded-md border border-input px-3 py-2 outline-none focus-within:ring-1 focus-within:ring-ring/50"
        style={{ height: inputHeight }}
      > */}
      <div
        className="relative flex w-full flex-col gap-2.5 rounded-3xl border border-input px-3 py-2 outline-none focus-within:ring-1 focus-within:ring-ring/50"
        style={{ height: inputHeight }}
      >
        {/* 顶部拖拽条：鼠标放到最外层输入框上边沿后上下拖动 */}
        <div
          onMouseDown={handleResizeMouseDown}
          className="absolute top-0 left-0 z-20 h-2 w-full cursor-ns-resize bg-transparent"
        />
        <FileUploadList
          orientation="horizontal"
          className="overflow-x-auto px-0 py-1"
        >
          {files.map((file, index) => (
            <FileUploadItem key={index} value={file} className="max-w-52 p-1.5">
              <FileUploadItemPreview className="size-8 [&>svg]:size-5">
                <FileUploadItemProgress variant="fill" />
              </FileUploadItemPreview>
              <FileUploadItemMetadata size="sm" />
              <FileUploadItemDelete asChild>
                <Button
                  type="button"
                  variant="secondary"
                  size="icon"
                  className="-top-1 -right-1 absolute size-4 shrink-0 cursor-pointer rounded-full"
                  onClick={handleRemoveFile(file)}
                >
                  <X className="size-2.5" />
                </Button>
              </FileUploadItemDelete>
            </FileUploadItem>
          ))}
        </FileUploadList>
        {/* <Textarea
          value={value}
          onChange={onInputChange}
          placeholder={t('chat.messagePlaceholder')}
          className="field-sizing-content min-h-10 w-full resize-none border-0 bg-transparent p-0 shadow-none focus-visible:ring-0 dark:bg-transparent"
          disabled={isUploading || disabled || sendLoading}
          onKeyDown={handleKeyDown}
        /> */}
        <Textarea
          value={value}
          onChange={onInputChange}
          placeholder={t('chat.messagePlaceholder')}
          className="min-h-10 flex-1 w-full resize-none overflow-y-auto border-0 bg-transparent p-0 shadow-none focus-visible:ring-0 dark:bg-transparent"
          disabled={isUploading || disabled || sendLoading}
          onKeyDown={handleKeyDown}
        />
        <div className="flex items-center justify-between gap-1.5">
          {/* 左侧工具区 */}
          <div className="flex items-center gap-2">
            {showUploadIcon && (
              <FileUploadTrigger asChild>
                <Button
                  type="button"
                  size="icon"
                  variant="ghost"
                  className="size-7 rounded-sm"
                  disabled={isUploading || sendLoading}
                >
                  <Paperclip className="size-3.5" />
                  <span className="sr-only">Attach file</span>
                </Button>
              </FileUploadTrigger>
            )}

            <div className="flex items-center gap-2">
              {/* 多库并行推理 */}
              <Button
                type="button"
                title="精确度高，速度快"
                size="sm"
                variant="outline"
                onClick={(event) => {
                  event.preventDefault();
                  event.stopPropagation();
                  onEnableMultiKbReasoning?.();
                }}
                disabled={isUploading || sendLoading || disabled}
                className={cn(
                  `
        h-8
        rounded-full
        border
        px-3
        text-xs
        font-medium
        transition-all
        duration-200
        shadow-none
        hover:bg-emerald-50
        hover:text-emerald-600
        hover:border-emerald-300
        dark:hover:bg-emerald-950/30
      `,
                  !reasoning && !agentMod
                    ? `
          border-emerald-300
          bg-emerald-50
          text-emerald-600
          shadow-sm
          dark:border-emerald-700
          dark:bg-emerald-950/30
          dark:text-emerald-400
        `
                    : `
          border-gray-200
          bg-transparent
          text-gray-500
          dark:border-gray-700
          dark:text-gray-400
        `,
                )}
              >
                <span
                  className={cn(
                    `
          mr-1.5
          inline-flex
          h-5 w-5
          items-center
          justify-center
          rounded-full
          transition-all
          duration-200
        `,
                    !reasoning && !agentMod
                      ? `
            scale-105
            bg-gradient-to-br
            from-emerald-400
            to-teal-500
            text-white
            shadow-sm
            shadow-emerald-300/50
            ring-1
            ring-emerald-200
            dark:ring-emerald-700
          `
                      : `
            bg-gray-100
            text-gray-400
            ring-1
            ring-gray-200
            dark:bg-gray-800
            dark:text-gray-500
            dark:ring-gray-700
          `,
                  )}
                >
                  <Layers3 className="h-3 w-3" />
                </span>
                多库并行
              </Button>

              {/* 深度推理 */}
              <Button
                type="button"
                size="sm"
                title="海量查询，速度慢"
                variant="outline"
                onClick={(event) => {
                  event.preventDefault();
                  event.stopPropagation();
                  onEnableDeepReasoning?.();
                }}
                disabled={isUploading || sendLoading || disabled}
                className={cn(
                  `
        h-8
        rounded-full
        border
        px-3
        text-xs
        font-medium
        transition-all
        duration-200
        shadow-none
        hover:bg-blue-50
        hover:text-blue-600
        hover:border-blue-300
        dark:hover:bg-blue-950/30
      `,
                  reasoning && !agentMod
                    ? `
          border-blue-300
          bg-blue-50
          text-blue-600
          shadow-sm
          dark:border-blue-700
          dark:bg-blue-950/30
          dark:text-blue-400
        `
                    : `
          border-gray-200
          bg-transparent
          text-gray-500
          dark:border-gray-700
          dark:text-gray-400
        `,
                )}
              >
                <span
                  className={cn(
                    `
          mr-1.5
          inline-flex
          h-5 w-5
          items-center
          justify-center
          rounded-full
          transition-all
          duration-200
        `,
                    reasoning && !agentMod
                      ? `
            scale-105
            bg-gradient-to-br
            from-blue-400
            to-indigo-500
            text-white
            shadow-sm
            shadow-blue-300/50
            ring-1
            ring-blue-200
            dark:ring-blue-700
          `
                      : `
            bg-gray-100
            text-gray-400
            ring-1
            ring-gray-200
            dark:bg-gray-800
            dark:text-gray-500
            dark:ring-gray-700
          `,
                  )}
                >
                  <Sparkles className="h-3 w-3" />
                </span>
                深度推理
              </Button>

              {/* Agent */}
              {/* <Button
                type="button"
                size="sm"
                title="Agent 模式"
                variant="outline"
                onClick={(event) => {
                  event.preventDefault();
                  event.stopPropagation();
                  onEnableAgent?.();
                }}
                disabled={isUploading || sendLoading || disabled}
                className={cn(
                  `
        h-8
        rounded-full
        border
        px-3
        text-xs
        font-medium
        transition-all
        duration-200
        shadow-none
        hover:bg-purple-50
        hover:text-purple-600
        hover:border-purple-300
        dark:hover:bg-purple-950/30
      `,
                  !reasoning && agentMod
                    ? `
          border-purple-300
          bg-purple-50
          text-purple-600
          shadow-sm
          dark:border-purple-700
          dark:bg-purple-950/30
          dark:text-purple-400
        `
                    : `
          border-gray-200
          bg-transparent
          text-gray-500
          dark:border-gray-700
          dark:text-gray-400
        `,
                )}
              >
                <span
                  className={cn(
                    `
          mr-1.5
          inline-flex
          h-5 w-5
          items-center
          justify-center
          rounded-full
          transition-all
          duration-200
        `,
                    !reasoning && agentMod
                      ? `
            scale-105
            bg-gradient-to-br
            from-purple-400
            to-fuchsia-500
            text-white
            shadow-sm
            shadow-purple-300/50
            ring-1
            ring-purple-200
            dark:ring-purple-700
          `
                      : `
            bg-gray-100
            text-gray-400
            ring-1
            ring-gray-200
            dark:bg-gray-800
            dark:text-gray-500
            dark:ring-gray-700
          `,
                  )}
                >
                  <Bot className="h-3 w-3" />
                </span>
                Agent Skills
              </Button> */}
            </div>
          </div>

          {/* 右侧发送/停止区 */}
          <div className="flex items-center gap-3">
            {sendLoading ? (
              <Button
                type="button"
                onClick={stopOutputMessage}
                className="size-7 rounded-sm"
              >
                <CircleStop className="size-4" />
              </Button>
            ) : (
              <Button
                type="button"
                onClick={submit}
                className="size-7 rounded-sm"
                disabled={
                  sendDisabled || isUploading || sendLoading || !value.trim()
                }
              >
                <Send className="size-4" />
                <span className="sr-only">Send message</span>
              </Button>
            )}
          </div>
        </div>
      </div>
    </FileUpload>
  );
}

{
  /* <div
          className={cn('flex items-center justify-between gap-1.5', {
            'justify-end': !showUploadIcon,
          })}
        >
          {showUploadIcon && (
            <FileUploadTrigger asChild>
              <Button
                type="button"
                size="icon"
                variant="ghost"
                className="size-7 rounded-sm"
                disabled={isUploading || sendLoading}
              >
                <Paperclip className="size-3.5" />
                <span className="sr-only">Attach file</span>
              </Button>
            </FileUploadTrigger>
          )}
          {sendLoading ? (
            <Button
              type="button"
              onClick={stopOutputMessage}
              className="size-5 rounded-sm"
            >
              <CircleStop />
            </Button>
          ) : (
            <div className="flex items-center gap-3">
              {/* <div className="bg-bg-input rounded-md hover:bg-bg-card p-1"> */
}
{
  /* <AudioButton
                onOk={(value) => {
                  setAudioInputValue(value);
                }}
              /> */
}
//       {/* </div> */}
//       <Button
//         type="button"
//         onClick={submit}
//         className="size-5 rounded-sm"
//         disabled={
//           sendDisabled || isUploading || sendLoading || !value.trim()
//         }
//       >
//         <Send />
//         <span className="sr-only">Send message</span>
//       </Button>
//     </div>
//   )}
// </div> */}
