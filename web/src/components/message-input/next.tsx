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
import { Popover } from 'antd';
import { t } from 'i18next';
import {
  Bot,
  CircleStop,
  FileText,
  Folder,
  Layers3,
  Paperclip,
  Puzzle,
  Send,
  ShieldCheck,
  Sparkles,
  Upload,
  X,
} from 'lucide-react';
import * as React from 'react';
import { useEffect } from 'react';
import { toast } from 'sonner';
import type { ComplianceTemplate } from './ComplianceTemplatePopover';
import ComplianceTemplatePopover from './ComplianceTemplatePopover';
import type { SkillItem } from './SkillPopover';
import SkillPopover from './SkillPopover';

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

  // 👇 外部传入的当前模式状态
  reasoning?: boolean;
  agentMod?: boolean;
  projectCompliance?: boolean;
  experimentReport?: boolean;

  // 👇 允许外部覆盖最外层输入框样式（首页用来改圆角/高度）
  wrapperClassName?: string;

  // ✅ 合规模式下的两个按钮回调
  onClickComplianceFolder?: () => void;
  /** 点小面板某一项 / 点「查看模板」时触发，参数为该模板（没有则打开大弹窗的默认项） */
  onClickComplianceTemplate?: (tpl?: ComplianceTemplate) => void;

  // ✅ 小面板要展示的模板列表
  complianceTemplates?: ComplianceTemplate[];
  complianceTemplatesLoading?: boolean;
  isComplianceFolderOpen?: boolean; // 新增：工作区是否打开

  onSelectSkill?: (skill: SkillItem) => void;
  onClickSkill?: () => void; // 👈 新增：点「查看全部技能」时触发
  skillActive?: boolean; // 👈 新增：技能页是否打开（用于高亮）
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
  reasoning = false,
  agentMod = false,
  projectCompliance = false,
  experimentReport = false,
  wrapperClassName,
  onClickComplianceFolder,
  onClickComplianceTemplate,
  complianceTemplates = [],
  complianceTemplatesLoading = false,
  isComplianceFolderOpen = false,
  onSelectSkill,
  onClickSkill, // 👈 新增
  skillActive = false, // 👈 新增
}: IProps) {
  const [files, setFiles] = React.useState<File[]>([]);
  const [audioInputValue, setAudioInputValue] = React.useState<string | null>(
    null,
  );
  const [inputHeight, setInputHeight] = React.useState(130);
  const startYRef = React.useRef(0);
  const startHeightRef = React.useRef(120);

  /** ✅ 模板 Popover 开关 */
  const [templatePopoverOpen, setTemplatePopoverOpen] = React.useState(false);
  const [skillPopoverOpen, setSkillPopoverOpen] = React.useState(false);

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

  /** 根据外部状态计算当前选中的模式 */
  const activeMode = React.useMemo(() => {
    if (reasoning) {
      return {
        label: '深度推理',
        Icon: Sparkles,
        className:
          'border-blue-300 bg-blue-50 text-blue-600 dark:border-blue-700 dark:bg-blue-950/30 dark:text-blue-400',
      };
    }
    if (agentMod) {
      return {
        label: 'Agent Skills',
        Icon: Bot,
        className:
          'border-purple-300 bg-purple-50 text-purple-600 dark:border-purple-700 dark:bg-purple-950/30 dark:text-purple-400',
      };
    }
    if (projectCompliance) {
      return {
        label: '合规申报',
        Icon: ShieldCheck,
        className:
          'border-orange-300 bg-orange-50 text-orange-600 dark:border-orange-700 dark:bg-orange-950/30 dark:text-orange-400',
      };
    }
    if (experimentReport) {
      return {
        label: '实验报告',
        Icon: FileText,
        className:
          'border-cyan-300 bg-cyan-50 text-cyan-600 dark:border-cyan-700 dark:bg-cyan-950/30 dark:text-cyan-400',
      };
    }
    return {
      label: '多库并行',
      Icon: Layers3,
      className:
        'border-emerald-300 bg-emerald-50 text-emerald-600 dark:border-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-400',
    };
  }, [reasoning, agentMod, projectCompliance, experimentReport]);

  const ActiveIcon = activeMode.Icon;

  /** ✅ 是否显示「工作区 / 文件管理」按钮：合规、Agent、实验报告三种模式都显示 */
  const showWorkspaceButton = projectCompliance || agentMod || experimentReport;

  /** ✅ 是否显示「模板」按钮：仅合规模式显示 */
  const showTemplateButton = projectCompliance;

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

      <div
        className={cn(
          // 将 px-3 py-2 改为 px-5 py-4（如果觉得太大，可以改为 px-4 py-3）
          'relative flex w-full flex-col gap-2.5 rounded-3xl border border-input px-5 py-4 outline-none focus-within:ring-1 focus-within:ring-ring/50',
          wrapperClassName,
        )}
        style={{ height: inputHeight }}
      >
        {/* 顶部拖拽条 */}
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

        <Textarea
          value={value}
          onChange={onInputChange}
          placeholder={t('chat.messagePlaceholder')}
          className="
            min-h-10 flex-1 w-full resize-none overflow-y-auto border-0 bg-transparent p-0 shadow-none focus-visible:ring-0 dark:bg-transparent
            placeholder:text-[15px] placeholder:text-gray-500 dark:placeholder:text-gray-400
          "
          disabled={isUploading || disabled || sendLoading}
          onKeyDown={handleKeyDown}
        />

        <div className="flex items-center justify-between gap-1.5">
          {/* 左侧工具区：上传按钮 + 当前模式标记 + 工作区/模板按钮 */}
          <div className="flex items-center gap-2">
            {showUploadIcon && (
              <FileUploadTrigger asChild>
                <Button
                  type="button"
                  size="icon"
                  variant="ghost"
                  className="size-7 rounded-sm"
                  disabled={isUploading || sendLoading || disabled}
                  title="上传文件"
                >
                  <Paperclip className="size-3.5" />
                  <span className="sr-only">Attach file</span>
                </Button>
              </FileUploadTrigger>
            )}

            <span
              title={activeMode.label}
              className={cn(
                'inline-flex h-7 w-7 items-center justify-center rounded-md border transition-colors',
                activeMode.className,
              )}
            >
              <ActiveIcon className="h-3.5 w-3.5 shrink-0" />
            </span>

            {/* ✅ 合规 / Agent / 实验报告：都显示「工作区（文件管理）」按钮 */}
            {showWorkspaceButton && (
              <button
                type="button"
                onClick={onClickComplianceFolder}
                disabled={disabled || sendLoading}
                title="查看工作区文件"
                className={cn(
                  'inline-flex h-7 items-center gap-1.5 rounded-full border px-3 text-xs font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed',
                  isComplianceFolderOpen
                    ? 'border-blue-300 bg-blue-50 text-blue-600 dark:border-blue-700 dark:bg-blue-950/30 dark:text-blue-400'
                    : 'border-gray-200 bg-gray-50 text-gray-600 hover:border-gray-300 hover:bg-gray-100 dark:border-gray-700 dark:bg-gray-800/40 dark:text-gray-400 dark:hover:bg-gray-700/50',
                )}
              >
                <Folder className="h-3.5 w-3.5 shrink-0" />
                <span>工作区</span>
              </button>
            )}

            {/* ✅ 合规 / Agent / 实验报告：都显示「工作区（文件管理）」按钮 */}
            {/* ✅ Agent 模式：技能按钮（样式同模板按钮） */}
            {/* ✅ Agent 模式：技能按钮（popover 弹出技能列表） */}
            {agentMod && (
              <Popover
                trigger="click"
                placement="topLeft"
                arrow={false}
                open={skillPopoverOpen}
                onOpenChange={setSkillPopoverOpen}
                overlayInnerStyle={{
                  padding: 0,
                  borderRadius: 12,
                  boxShadow: '0 8px 30px rgba(0,0,0,0.12)',
                  overflow: 'hidden',
                }}
                content={
                  <SkillPopover
                    onSelect={(skill) => {
                      setSkillPopoverOpen(false);
                      onSelectSkill?.(skill);
                    }}
                    onViewAll={() => {
                      setSkillPopoverOpen(false);
                      onClickSkill?.();
                    }}
                  />
                }
              >
                <button
                  type="button"
                  disabled={disabled || sendLoading}
                  title="查看技能"
                  className={cn(
                    'inline-flex h-7 items-center gap-1.5 rounded-full border px-3 text-xs font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed',
                    skillPopoverOpen
                      ? 'border-blue-300 bg-blue-50 text-blue-600 dark:border-blue-700 dark:bg-blue-950/30 dark:text-blue-400'
                      : 'border-gray-200 bg-gray-50 text-gray-600 hover:border-gray-300 hover:bg-gray-100 dark:border-gray-700 dark:bg-gray-800/40 dark:text-gray-400 dark:hover:bg-gray-700/50',
                  )}
                >
                  <Puzzle className="h-3.5 w-3.5 shrink-0" />
                  <span>技能</span>
                </button>
              </Popover>
            )}

            {/* ✅ 仅合规模式：显示「模板」按钮 */}
            {showTemplateButton && (
              <Popover
                trigger="click"
                placement="topLeft"
                arrow={false}
                open={templatePopoverOpen}
                onOpenChange={setTemplatePopoverOpen}
                overlayInnerStyle={{
                  padding: 0,
                  borderRadius: 12,
                  boxShadow: '0 8px 30px rgba(0,0,0,0.12)',
                  overflow: 'hidden',
                }}
                content={
                  <ComplianceTemplatePopover
                    templates={complianceTemplates}
                    loading={complianceTemplatesLoading}
                    onSelect={(tpl) => {
                      setTemplatePopoverOpen(false);
                      onClickComplianceTemplate?.(tpl);
                    }}
                    onViewAll={() => {
                      setTemplatePopoverOpen(false);
                      onClickComplianceTemplate?.();
                    }}
                  />
                }
              >
                <button
                  type="button"
                  disabled={disabled || sendLoading}
                  title="查看合规模板"
                  className={cn(
                    'inline-flex h-7 items-center gap-1.5 rounded-full border px-3 text-xs font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed',
                    // 根据 templatePopoverOpen 状态切换颜色
                    templatePopoverOpen
                      ? 'border-blue-300 bg-blue-50 text-blue-600 dark:border-blue-700 dark:bg-blue-950/30 dark:text-blue-400'
                      : 'border-gray-200 bg-gray-50 text-gray-600 hover:border-gray-300 hover:bg-gray-100 dark:border-gray-700 dark:bg-gray-800/40 dark:text-gray-400 dark:hover:bg-gray-700/50',
                  )}
                >
                  <FileText className="h-3.5 w-3.5 shrink-0" />
                  <span>模板</span>
                </button>
              </Popover>
            )}
          </div>

          {/* 右侧发送/停止区 */}
          <div className="flex items-center gap-3">
            {sendLoading ? (
              <Button
                type="button"
                variant="ghost"
                onClick={stopOutputMessage}
                className="
                  size-7 rounded-sm
                  bg-transparent
                  text-red-500
                  shadow-none
                  hover:bg-red-50 hover:text-red-600
                  dark:hover:bg-red-950/40 dark:hover:text-red-400
                "
              >
                <CircleStop className="size-4" />
              </Button>
            ) : (
              <Button
                type="button"
                variant="ghost"
                onClick={submit}
                className="
                  size-7 rounded-sm
                  bg-transparent
                  text-gray-500
                  shadow-none
                  hover:bg-emerald-50 hover:text-emerald-600
                  dark:text-gray-400
                  dark:hover:bg-emerald-950/40 dark:hover:text-emerald-400
                  disabled:opacity-40
                  disabled:hover:bg-transparent
                "
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
