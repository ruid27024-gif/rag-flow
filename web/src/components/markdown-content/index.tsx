import Image from '@/components/image';
import SvgIcon from '@/components/svg-icon';
import { IReference, IReferenceChunk } from '@/interfaces/database/chat';
import { getExtension } from '@/utils/document-util';
import DOMPurify from 'dompurify';
import {
  AlertCircle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Wrench,
} from 'lucide-react';
import { Fragment, useCallback, useEffect, useMemo, useState } from 'react';
import Markdown from 'react-markdown';
import reactStringReplace from 'react-string-replace';
import SyntaxHighlighter from 'react-syntax-highlighter';
import rehypeKatex from 'rehype-katex';
import rehypeRaw from 'rehype-raw';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import { visitParents } from 'unist-util-visit-parents';

import { useTranslation } from 'react-i18next';

import DocxPreviewModal from '@/components/DocxPreviewModal';
import { HomeIcon } from '@/components/svg-icon';
import 'katex/dist/katex.min.css'; // `rehype-katex` does not import the CSS for you
import * as React from 'react';

import {
  File,
  FileArchive,
  FileImage,
  FileSpreadsheet,
  FileText,
  Presentation,
} from 'lucide-react';

import { useFetchDocumentThumbnailsByIds } from '@/hooks/use-document-request';
import {
  currentReg,
  preprocessLaTeX,
  replaceTextByOldReg,
  showImage,
} from '@/utils/chat';
import classNames from 'classnames';
import { omit } from 'lodash';
import { Paperclip } from 'lucide-react';
import { Button } from '../ui/button';
import {
  HoverCard,
  HoverCardContent,
  HoverCardTrigger,
} from '../ui/hover-card';
import styles from './index.less';

// 在组件外部或顶部定义颜色映射
const getNumberColor = (num: number) => {
  const colors = [
    'bg-blue-500', // 1: 蓝色
    'bg-green-500', // 2: 绿色
    'bg-yellow-500', // 3: 黄色
    'bg-purple-500', // 4: 紫色
    'bg-pink-500', // 5: 粉色
    'bg-orange-500', // 6: 橙色
    'bg-teal-500', // 7: 青色
    'bg-red-500', // 8: 红色
    'bg-indigo-500', // 9: 靛蓝
    'bg-cyan-500', // 10: 青色
  ];
  return colors[(num - 1) % colors.length];
};

const getChunkIndex = (match: string) => Number(match);

type ThinkSegment =
  | {
      type: 'text';
      content: string;
    }
  | {
      type: 'think';
      content: string;
      done: boolean;
    };
type AgentEventStatus = 'running' | 'success' | 'error';

export type AgentEvent = {
  type: string;
  name?: string;
  title?: string;
  summary?: string;
  status?: AgentEventStatus;
  elapsed_time?: number | null;
  display?: string;
  arguments?: any;
  result?: any;
  download_url?: string;
  filename?: string;
  error?: string;
  delta?: string;
};

const AgentFileDownloads = ({ events }: { events?: AgentEvent[] }) => {
  const files = useMemo(() => {
    const list = (events || [])
      .map((event) => {
        const { downloadUrl, filename } = getAgentFileInfo(event);

        if (!downloadUrl) {
          return null;
        }

        return {
          downloadUrl,
          filename: filename || '文件',
        };
      })
      .filter(Boolean) as {
      downloadUrl: string;
      filename: string;
    }[];

    // 去重，避免流式过程中重复展示同一个文件
    const map = new Map<string, { downloadUrl: string; filename: string }>();

    list.forEach((file) => {
      map.set(file.downloadUrl, file);
    });

    return Array.from(map.values());
  }, [events]);

  if (!files.length) {
    return null;
  }

  return (
    <div
      className="
        mt-4
        rounded-xl
        border border-emerald-200
        bg-emerald-50/70
        p-3
        dark:border-emerald-800
        dark:bg-emerald-950/30
      "
    >
      <div
        className="
          mb-2
          text-sm
          font-semibold
          text-emerald-700
          dark:text-emerald-300
        "
      >
        生成的文件
      </div>

      <div className="space-y-2">
        {files.map((file, index) => (
          <a
            key={`${file.downloadUrl}-${index}`}
            href={file.downloadUrl}
            target="_blank"
            rel="noopener noreferrer"
            download={file.filename || undefined}
            className="
              flex
              items-center
              justify-between
              rounded-lg
              border border-emerald-200
              bg-white
              px-3 py-2
              text-sm
              text-emerald-700
              hover:bg-emerald-50
              dark:border-emerald-800
              dark:bg-slate-950
              dark:text-emerald-300
              dark:hover:bg-emerald-950/40
            "
          >
            <span className="truncate">{file.filename || '下载文件'}</span>

            <span className="ml-3 shrink-0 text-xs">下载</span>
          </a>
        ))}
      </div>
    </div>
  );
};

/**
 * 将内容按 <think>...</think> 拆分
 * 支持流式输出：
 * 1. 完整：<think>xxx</think>
 * 2. 未闭合：<think>xxx
 */
function splitThinkContent(content: string): ThinkSegment[] {
  const segments: ThinkSegment[] = [];

  if (!content) {
    return segments;
  }

  let rest = content;

  while (rest.length > 0) {
    // 支持 <think> 或 <think xxx="xxx">
    const startMatch = rest.match(/<think\b[^>]*>/i);

    // 没有 think，剩余全部作为普通文本
    if (!startMatch || startMatch.index === undefined) {
      if (rest) {
        segments.push({
          type: 'text',
          content: rest,
        });
      }
      break;
    }

    const thinkStartIndex = startMatch.index;

    // think 前面的普通内容
    if (thinkStartIndex > 0) {
      segments.push({
        type: 'text',
        content: rest.slice(0, thinkStartIndex),
      });
    }

    // 去掉 <think ...>
    const afterThinkStart = rest.slice(thinkStartIndex + startMatch[0].length);

    const endMatch = afterThinkStart.match(/<\/think>/i);

    // 流式场景：还没收到 </think>
    if (!endMatch || endMatch.index === undefined) {
      segments.push({
        type: 'think',
        content: afterThinkStart,
        done: false,
      });
      break;
    }

    const thinkEndIndex = endMatch.index;

    // think 内容，已经收到 </think>
    segments.push({
      type: 'think',
      content: afterThinkStart.slice(0, thinkEndIndex),
      done: true,
    });

    // 继续处理 </think> 后面的内容
    rest = afterThinkStart.slice(thinkEndIndex + endMatch[0].length);
  }

  return segments;
}

type SourceGroup =
  | { type: 'plain'; content: string }
  | { type: 'heading'; heading: string; content: string };

function splitBySourceHeading(text: string): SourceGroup[] {
  const groups: SourceGroup[] = [];

  // 此时 text 里已经是被替换好的 <source-heading>xxx</source-heading>
  const regex = /<source-heading>([\s\S]*?)<\/source-heading>/g;

  const matches: { start: number; end: number; heading: string }[] = [];
  let match: RegExpExecArray | null;

  while ((match = regex.exec(text)) !== null) {
    matches.push({
      start: match.index,
      end: match.index + match[0].length,
      heading: match[1],
    });
  }

  // 没有找到 source-heading，整段作为普通内容
  if (matches.length === 0) {
    return [{ type: 'plain', content: text }];
  }

  // 第一个 heading 之前的内容（通常为空或前导文本）
  if (matches[0].start > 0) {
    groups.push({ type: 'plain', content: text.slice(0, matches[0].start) });
  }

  // 每个 heading 到下一个 heading 之间的内容，归入该 heading
  for (let i = 0; i < matches.length; i++) {
    const current = matches[i];
    const next = matches[i + 1];
    const contentEnd = next ? next.start : text.length;

    groups.push({
      type: 'heading',
      heading: current.heading,
      content: text.slice(current.end, contentEnd),
    });
  }

  return groups;
}

function isVisibleAgentEvent(event: AgentEvent) {
  if (!event) return false;

  // 正式回答增量不展示在工具调用列表里
  if (event.type === 'answer_delta') {
    return false;
  }

  return true;
}

function formatAgentElapsedTime(seconds?: number | null) {
  if (seconds === undefined || seconds === null) {
    return '';
  }

  const ms = seconds * 1000;

  if (ms < 1000) {
    return `${Math.round(ms)}ms`;
  }

  return `${seconds.toFixed(2)}s`;
}

function getAgentEventTitle(event: AgentEvent) {
  if (event.title) {
    return event.title;
  }

  const name = event.name || event.type || '';

  if (name === 'agent_start') return 'Agent 启动';
  if (name === 'base_next_step') return '分析任务';
  if (name === 'before_read_skill') return '准备读取 Skill';
  if (name === 'read_skill') return '阅读 Skill';
  if (name === 'read_skill_error') return '读取 Skill 失败';
  if (name === 'enter_skill_phase') return '进入 Skill';
  if (name === 'skill_next_step') return 'Skill 决策';
  if (name === 'before_skill_tool_call') return '准备调用工具';
  if (name === 'skill_tool_call') return '工具调用';
  if (name === 'search_my_dateset') return '检索知识库';
  if (name === 'write_file') return '写入文件';
  if (name === 'skill_reflection') return '反思整理';
  if (name === 'skill_summary') return 'Skill 总结';
  if (name === 'skill_no_tool_answer') return '生成回答';
  if (name === 'agent_error') return 'Agent 执行异常';
  if (name === 'agent_done') return 'Agent 完成';

  return 'Agent 步骤';
}

function getAgentEventSummary(event: AgentEvent) {
  if (event.summary) {
    return event.summary;
  }

  const args = event.arguments || {};

  return (
    args.skill_name ||
    args.skill ||
    args.tool ||
    args.query ||
    args.filename ||
    event.error ||
    event.name ||
    ''
  );
}

function getAgentFileInfo(event: AgentEvent) {
  const downloadUrl =
    event.download_url ||
    event.arguments?.download_url ||
    event.result?.download_url ||
    event.arguments?.result?.download_url ||
    event.arguments?.output?.download_url ||
    event.arguments?.json?.download_url;

  const filename =
    event.filename ||
    event.arguments?.filename ||
    event.result?.filename ||
    event.arguments?.result?.filename ||
    event.arguments?.output?.filename ||
    event.arguments?.json?.filename;

  return {
    downloadUrl,
    filename,
  };
}

const AgentToolCalls = ({ events }: { events?: AgentEvent[] }) => {
  const [open, setOpen] = useState(true);
  const [openItems, setOpenItems] = useState<Record<number, boolean>>({});

  const visibleEvents = useMemo(() => {
    return (events || []).filter(isVisibleAgentEvent);
  }, [events]);

  if (!visibleEvents.length) {
    return null;
  }

  return (
    <div
      className="
        my-3
        rounded-xl
        border border-slate-200
        bg-slate-50/80
        p-2
        dark:border-slate-700
        dark:bg-slate-900/50
      "
    >
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="
          flex w-full items-center justify-between
          px-2 py-1
          text-sm font-medium
          text-slate-700
          dark:text-slate-200
        "
      >
        <span className="flex items-center gap-2">
          <Wrench className="h-4 w-4" />

          <span>工具调用</span>

          <span
            className="
              rounded-full
              bg-slate-200 px-1.5 py-0.5
              text-xs text-slate-600
              dark:bg-slate-700 dark:text-slate-300
            "
          >
            {visibleEvents.length}
          </span>
        </span>

        {open ? (
          <ChevronDown className="h-4 w-4 text-slate-500" />
        ) : (
          <ChevronRight className="h-4 w-4 text-slate-500" />
        )}
      </button>

      {open && (
        <div className="mt-2 space-y-2">
          {visibleEvents.map((event, index) => {
            const title = getAgentEventTitle(event);
            const summary = getAgentEventSummary(event);
            const cost = formatAgentElapsedTime(event.elapsed_time);
            const isError =
              event.status === 'error' ||
              event.type === 'agent_error' ||
              event.name === 'agent_error';

            const itemOpen = openItems[index] ?? false;
            const { downloadUrl, filename } = getAgentFileInfo(event);

            return (
              <div
                key={`${event.type}-${event.name || ''}-${index}`}
                className={classNames(
                  `
                    overflow-hidden
                    rounded-lg
                    border
                    bg-white
                    dark:bg-slate-950
                  `,
                  isError
                    ? 'border-red-300 dark:border-red-800'
                    : 'border-slate-200 dark:border-slate-700',
                )}
              >
                <button
                  type="button"
                  onClick={() =>
                    setOpenItems((prev) => ({
                      ...prev,
                      [index]: !itemOpen,
                    }))
                  }
                  className="
                    flex w-full items-center gap-2
                    px-3 py-2
                    text-left
                    text-sm
                  "
                >
                  {isError ? (
                    <AlertCircle className="h-4 w-4 shrink-0 text-red-500" />
                  ) : (
                    <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-500" />
                  )}

                  <div className="min-w-0 flex-1">
                    <div className="flex min-w-0 items-center gap-1">
                      <span className="shrink-0 font-medium text-slate-800 dark:text-slate-100">
                        {title}
                      </span>

                      {summary && (
                        <>
                          <span className="shrink-0 text-slate-400">---</span>

                          <span
                            className="
                              truncate
                              text-slate-600
                              dark:text-slate-300
                            "
                            title={String(summary)}
                          >
                            {String(summary)}
                          </span>
                        </>
                      )}
                    </div>
                  </div>

                  {cost && (
                    <span className="shrink-0 text-xs text-slate-400">
                      {cost}
                    </span>
                  )}

                  {itemOpen ? (
                    <ChevronDown className="h-4 w-4 shrink-0 text-slate-400" />
                  ) : (
                    <ChevronRight className="h-4 w-4 shrink-0 text-slate-400" />
                  )}
                </button>

                {itemOpen && (
                  <div
                    className="
      border-t border-slate-100
      px-4 py-3
      text-sm leading-7
      text-slate-600
      dark:border-slate-800
      dark:text-slate-300
    "
                  >
                    {event.display ? (
                      <pre
                        className="
          whitespace-pre-wrap
          break-words
          text-xs leading-6
          text-slate-500
          dark:text-slate-400
        "
                      >
                        {event.display}
                      </pre>
                    ) : (
                      <pre
                        className="
          whitespace-pre-wrap
          break-words
          text-xs leading-6
          text-slate-500
          dark:text-slate-400
        "
                      >
                        {JSON.stringify(event, null, 2)}
                      </pre>
                    )}

                    {downloadUrl && (
                      <div className="mt-3">
                        <a
                          href={downloadUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          download={filename || undefined}
                          className="
            inline-flex
            items-center
            rounded-md
            bg-[#018B8D]
            px-3 py-1.5
            text-sm font-medium
            text-white
            hover:bg-[#017476]
          "
                        >
                          下载文件：{filename || '文件'}
                        </a>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

function getMarkdownFileName(href: string, children: React.ReactNode): string {
  const childrenText =
    typeof children === 'string' && children.trim() ? children.trim() : '';

  // 如果 children 里已经带扩展名（如 xxx.docx），直接用
  if (childrenText && /\.[a-z0-9]+$/i.test(childrenText)) {
    return childrenText;
  }

  // 否则从 URL 里解析文件名
  try {
    const parsedUrl = new URL(href, window.location.origin);

    // 兼容 /v1/file/workspace-file?path=xxx.docx
    // 兼容 /v1/file/template?path=xxx.docx
    const pathParam = parsedUrl.searchParams.get('path');
    if (pathParam) {
      const decodedPath = decodeURIComponent(pathParam);
      const name = decodedPath.split('/').filter(Boolean).pop();
      if (name) return name;
    }

    // 兼容 /v1/file/template/xxx.docx
    const pathname = decodeURIComponent(parsedUrl.pathname);
    const nameFromPath = pathname.split('/').filter(Boolean).pop();
    if (nameFromPath) return nameFromPath;
  } catch {
    // ignore
  }

  // 兜底：返回 children 或默认文案
  return childrenText || '查看文件';
}

function getMarkdownFileExtension(fileName: string, href: string): string {
  try {
    const parsedUrl = new URL(href, window.location.origin);

    const extFromQuery = parsedUrl.searchParams.get('ext') || '';

    if (extFromQuery) {
      return extFromQuery.replace('.', '').toLowerCase();
    }
  } catch {
    // 使用文件名解析扩展名
  }

  const lastDotIndex = fileName.lastIndexOf('.');

  if (lastDotIndex === -1) {
    return '';
  }

  return fileName.slice(lastDotIndex + 1).toLowerCase();
}
function isFileMarkdownLink(href?: string): boolean {
  if (!href) {
    return false;
  }

  return (
    href.includes('/document/') ||
    href.includes('/v1/file/template') ||
    href.includes('/v1/file/workspace-file') // 👈 新增这一行
  );
}

interface MarkdownFileLinkProps {
  href?: string;
  children?: React.ReactNode;
  [key: string]: any;
}

function MarkdownFileLink({
  href = '',
  children,
  ...props
}: MarkdownFileLinkProps) {
  const [docxPreviewOpen, setDocxPreviewOpen] = useState(false);

  const [loading, setLoading] = useState(false);

  const fileName = getMarkdownFileName(href, children);

  const extension = getMarkdownFileExtension(fileName, href);

  const isDocx = extension === 'docx';

  const handleClick = useCallback(
    (event: React.MouseEvent<HTMLAnchorElement>) => {
      // 只有 DOCX 使用前端预览
      if (!isDocx) {
        // DOC、PDF、图片等保持默认行为
        return;
      }

      event.preventDefault();

      if (loading) {
        return;
      }

      setDocxPreviewOpen(true);
    },
    [isDocx, loading],
  );

  const META: Record<
    string,
    {
      Icon: any;
      iconCls: string;
      label: string;
    }
  > = {
    pdf: {
      Icon: FileText,
      iconCls: 'bg-red-50 text-red-500 dark:bg-red-500/10 dark:text-red-400',
      label: 'PDF',
    },
    doc: {
      Icon: FileText,
      iconCls:
        'bg-blue-50 text-blue-500 dark:bg-blue-500/10 dark:text-blue-400',
      label: 'DOC',
    },
    docx: {
      Icon: FileText,
      iconCls:
        'bg-blue-50 text-blue-500 dark:bg-blue-500/10 dark:text-blue-400',
      label: 'DOCX',
    },
    xls: {
      Icon: FileSpreadsheet,
      iconCls:
        'bg-emerald-50 text-emerald-500 dark:bg-emerald-500/10 dark:text-emerald-400',
      label: 'XLS',
    },
    xlsx: {
      Icon: FileSpreadsheet,
      iconCls:
        'bg-emerald-50 text-emerald-500 dark:bg-emerald-500/10 dark:text-emerald-400',
      label: 'XLSX',
    },
    csv: {
      Icon: FileSpreadsheet,
      iconCls:
        'bg-emerald-50 text-emerald-500 dark:bg-emerald-500/10 dark:text-emerald-400',
      label: 'CSV',
    },
    ppt: {
      Icon: Presentation,
      iconCls:
        'bg-orange-50 text-orange-500 dark:bg-orange-500/10 dark:text-orange-400',
      label: 'PPT',
    },
    pptx: {
      Icon: Presentation,
      iconCls:
        'bg-orange-50 text-orange-500 dark:bg-orange-500/10 dark:text-orange-400',
      label: 'PPTX',
    },
    zip: {
      Icon: FileArchive,
      iconCls:
        'bg-amber-50 text-amber-500 dark:bg-amber-500/10 dark:text-amber-400',
      label: 'ZIP',
    },
    rar: {
      Icon: FileArchive,
      iconCls:
        'bg-amber-50 text-amber-500 dark:bg-amber-500/10 dark:text-amber-400',
      label: 'RAR',
    },
    '7z': {
      Icon: FileArchive,
      iconCls:
        'bg-amber-50 text-amber-500 dark:bg-amber-500/10 dark:text-amber-400',
      label: '7Z',
    },
    png: {
      Icon: FileImage,
      iconCls:
        'bg-purple-50 text-purple-500 dark:bg-purple-500/10 dark:text-purple-400',
      label: 'PNG',
    },
    jpg: {
      Icon: FileImage,
      iconCls:
        'bg-purple-50 text-purple-500 dark:bg-purple-500/10 dark:text-purple-400',
      label: 'JPG',
    },
    jpeg: {
      Icon: FileImage,
      iconCls:
        'bg-purple-50 text-purple-500 dark:bg-purple-500/10 dark:text-purple-400',
      label: 'JPEG',
    },
    webp: {
      Icon: FileImage,
      iconCls:
        'bg-purple-50 text-purple-500 dark:bg-purple-500/10 dark:text-purple-400',
      label: 'WEBP',
    },
    txt: {
      Icon: FileText,
      iconCls:
        'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400',
      label: 'TXT',
    },
  };

  const { Icon, iconCls, label } = META[extension] ?? {
    Icon: File,
    iconCls:
      'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400',
    label: extension ? extension.toUpperCase() : 'FILE',
  };

  return (
    <>
      <div className="mt-1 mb-3">
        <a
          {...props}
          href={href}
          target="_blank"
          rel="noopener noreferrer"
          onClick={handleClick}
          title={isDocx ? `预览 ${fileName}` : `打开 ${fileName}`}
          className="
      group inline-flex h-12 w-full max-w-[300px]
      items-center gap-2.5
      rounded-lg border border-slate-200
      bg-white px-2.5
      no-underline
      transition-colors
      hover:border-slate-300 hover:bg-slate-50
      dark:border-slate-700 dark:bg-slate-900
      dark:hover:border-slate-600 dark:hover:bg-slate-800
    "
        >
          {/* 文件图标 */}
          <span
            className={`
        flex h-7 w-7 shrink-0
        items-center justify-center
        rounded-md
        ${iconCls}
      `}
          >
            <Icon size={16} strokeWidth={1.8} aria-hidden="true" />
          </span>

          {/* 文件名 */}
          <span className="min-w-0 flex-1">
            <span
              className="
          block truncate
          text-[13px] font-medium leading-[17px]
          text-slate-700
          dark:text-slate-200
        "
              title={fileName}
            >
              {loading ? '正在加载…' : fileName}
            </span>

            <span
              className="
          block text-[10px] leading-[12px]
          text-slate-400
          dark:text-slate-500
        "
            >
              {isDocx ? '点击预览' : label}
            </span>
          </span>
        </a>
      </div>

      {docxPreviewOpen && isDocx && (
        <DocxPreviewModal
          url={href}
          fileName={fileName}
          onClose={() => {
            setDocxPreviewOpen(false);
            setLoading(false);
          }}
        />
      )}
    </>
  );
}

function CollapsibleSourceSection({
  heading,
  children,
}: {
  heading: string;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(true);

  return (
    <div className="my-2">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="
          group/source
          flex w-full items-center gap-3
          cursor-pointer select-none
          text-left
          text-xl font-bold
          text-black dark:text-white
          transition-colors
          hover:opacity-80
        "
      >
        <HomeIcon name="datasets" width="20" />

        <span className="flex-1">{heading}</span>

        <ChevronRight
          className={`
            h-5 w-5 shrink-0 text-gray-400
            transition-transform duration-200
            ${open ? 'rotate-90' : 'rotate-0'}
          `}
        />
      </button>

      {open && <div className="mt-2">{children}</div>}
    </div>
  );
}

const MarkdownContent = ({
  reference,
  clickDocumentButton,
  content,
  agentEvents,
  hideThinkWhenAgentEvents = true,
}: {
  content: string;
  loading?: boolean;
  reference: IReference;
  agentEvents?: AgentEvent[];

  /**
   * 新 Agent 后端有 agentEvents 时，默认隐藏 answer 里的 <think>，
   * 避免「工具调用面板」和「思考过程」重复显示。
   *
   * 老后端没有 agentEvents 时，不受影响，仍然显示 think。
   */
  hideThinkWhenAgentEvents?: boolean;

  clickDocumentButton?: (documentId: string, chunk: IReferenceChunk) => void;
}) => {
  const { t } = useTranslation();

  const { setDocumentIds, data: fileThumbnails } =
    useFetchDocumentThumbnailsByIds();

  // think 外的正文替换
  const replaceSourceHeading = useCallback((text: string) => {
    const replaceHeadingOutsideThink = (segment: string) => {
      return segment.replace(
        /(【(?:从[^】]+来说|综合总结)】)/g,
        (_match, heading) => {
          const displayHeading = heading
            .replace(/^【从(.+?)来说】$/, '$1')
            .replace(/^【(.+?)】$/, '$1');

          return `\n\n<source-heading>${displayHeading}</source-heading>\n\n`;
        },
      );
    };

    let result = '';
    let cursor = 0;
    const lowerText = text.toLowerCase();

    while (cursor < text.length) {
      const thinkStart = lowerText.indexOf('<think', cursor);

      // 后面没有 think，剩余内容全部是正文，正常替换
      if (thinkStart === -1) {
        result += replaceHeadingOutsideThink(text.slice(cursor));
        break;
      }

      // think 前面的正文，正常替换
      result += replaceHeadingOutsideThink(text.slice(cursor, thinkStart));

      const openTagEnd = text.indexOf('>', thinkStart);

      // 流式场景：<think 标签还没完整，后面都按 think 原样保留
      if (openTagEnd === -1) {
        result += text.slice(thinkStart);
        break;
      }

      const closeTagStart = lowerText.indexOf('</think>', openTagEnd + 1);

      // 流式场景：think 还没闭合，think 到结尾都原样保留
      if (closeTagStart === -1) {
        result += text.slice(thinkStart);
        break;
      }

      // 完整 think 块，原样保留，不替换里面的标题
      result += text.slice(thinkStart, closeTagStart + '</think>'.length);

      cursor = closeTagStart + '</think>'.length;
    }

    return result.replace(/^\n+/, '');
  }, []);

  // 换行治理：普通缩进文本转换成更标准的 Markdown 结构
  // 换行治理：普通缩进文本转换成更标准的 Markdown 结构
  const normalizeIndentedTextToMarkdown = useCallback((text: string) => {
    if (!text) return text;

    const normalizeOutsideThink = (segment: string) => {
      const lines = segment.replace(/\r\n/g, '\n').split('\n');

      const sectionTitles = new Set(['标准', '外文', '文献', '综合总结']);

      const processedLines: { text: string; isTable: boolean }[] = [];

      for (let i = 0; i < lines.length; i++) {
        const raw = lines[i];
        const trimmed = raw.trim();

        if (!trimmed) {
          processedLines.push({ text: '', isTable: false });
          continue;
        }

        // 👇 核心改动：检测是否为表格行（以 | 开头）
        const isTable = /^\s*\|/.test(raw) || /^\|\s*---/.test(trimmed);

        // 已经是 Markdown / HTML 的，不处理
        if (
          /^(\s*)(#{1,6}\s|[-*+]\s|\d+\.\s|>\s|```)/.test(raw) ||
          /^<source-heading>/i.test(trimmed) ||
          /^<\/source-heading>/i.test(trimmed) ||
          isTable // 表格行直接保留原样
        ) {
          processedLines.push({ text: raw, isTable });
          continue;
        }

        const indentLength = raw.match(/^\s*/)?.[0]?.length ?? 0;
        let outText = trimmed;

        // 独立一级标题：标准、外文、文献、综合总结
        if (indentLength === 0 && sectionTitles.has(trimmed)) {
          outText = `## ${trimmed}`;
        }
        // 无缩进 + 冒号结尾：一级标题
        else if (indentLength === 0 && /[：:]$/.test(trimmed)) {
          outText = `## ${trimmed.replace(/[：:]$/, '')}`;
        }
        // 有缩进 + 冒号结尾：二级标题
        else if (indentLength > 0 && /[：:]$/.test(trimmed)) {
          outText = `### ${trimmed.replace(/[：:]$/, '')}`;
        }

        processedLines.push({ text: outText, isTable: false });
      }

      // 👇 智能拼接：表格行之间用 \n，其他情况用 \n\n
      let output = '';
      for (let i = 0; i < processedLines.length; i++) {
        output += processedLines[i].text;
        if (i < processedLines.length - 1) {
          const current = processedLines[i];
          const next = processedLines[i + 1];
          if (current.isTable && next.isTable) {
            output += '\n';
          } else {
            output += '\n\n';
          }
        }
      }
      return output;
    };

    let result = '';
    let cursor = 0;
    const lowerText = text.toLowerCase();

    while (cursor < text.length) {
      const thinkStart = lowerText.indexOf('<think', cursor);

      // 后面没有 think，剩余内容正常处理
      if (thinkStart === -1) {
        result += normalizeOutsideThink(text.slice(cursor));
        break;
      }

      // think 前面的正文正常处理
      result += normalizeOutsideThink(text.slice(cursor, thinkStart));

      const openTagEnd = text.indexOf('>', thinkStart);

      // 流式场景：<think 标签还没完整，后面全部原样保留
      if (openTagEnd === -1) {
        result += text.slice(thinkStart);
        break;
      }

      const closeTagStart = lowerText.indexOf('</think>', openTagEnd + 1);

      // 流式场景：think 还没闭合，think 到结尾全部原样保留
      if (closeTagStart === -1) {
        result += text.slice(thinkStart);
        break;
      }

      // 完整 think 块，原样保留，不做任何 normalize
      result += text.slice(thinkStart, closeTagStart + '</think>'.length);

      cursor = closeTagStart + '</think>'.length;
    }

    return result;
  }, []);

  // 库名称治理
  const contentWithCursor = useMemo(() => {
    let text = content || '';

    if (text === '') {
      text = t('chat.searching');
    }

    // 先整理标题和正文段落
    text = normalizeIndentedTextToMarkdown(text);
    // 只替换 think 外面的来源标题
    text = replaceSourceHeading(text);

    text = DOMPurify.sanitize(text, {
      ADD_TAGS: ['think', 'section', 'source-heading'],
      ADD_ATTR: ['class'],
    });

    const nextText = replaceTextByOldReg(text);

    /**
     * 重点：
     * 这里不要再使用 replaceThinkToSection
     * 否则 <think> 会被提前转成别的标签，后面就无法折叠处理
     */
    return preprocessLaTeX(nextText);
  }, [content, t, normalizeIndentedTextToMarkdown, replaceSourceHeading]);

  const segments = useMemo(() => {
    return splitThinkContent(contentWithCursor);
  }, [contentWithCursor]);

  const showAgentToolCalls = useMemo(() => {
    return (agentEvents || []).some(isVisibleAgentEvent);
  }, [agentEvents]);

  useEffect(() => {
    const docAggs = reference?.doc_aggs;
    setDocumentIds(Array.isArray(docAggs) ? docAggs.map((x) => x.doc_id) : []);
  }, [reference, setDocumentIds]);

  const handleDocumentButtonClick = useCallback(
    (
      documentId: string,
      chunk: IReferenceChunk,
      isPdf: boolean,
      documentUrl?: string,
    ) =>
      () => {
        if (!isPdf) {
          if (!documentUrl) {
            return;
          }
          window.open(documentUrl, '_blank');
        } else {
          clickDocumentButton?.(documentId, chunk);
        }
      },
    [clickDocumentButton],
  );

  // const rehypeWrapReference = () => {
  //   return function wrapTextTransform(tree: any) {
  //     visitParents(tree, 'text', (node, ancestors) => {
  //       const latestAncestor = ancestors.at(-1);

  //       if (
  //         latestAncestor.tagName !== 'custom-typography' &&
  //         latestAncestor.tagName !== 'code'
  //       ) {
  //         node.type = 'element';
  //         node.tagName = 'custom-typography';
  //         node.properties = {};
  //         node.children = [{ type: 'text', value: node.value }];
  //       }
  //     });
  //   };
  // };

  const rehypeWrapReference = () => {
    return function wrapTextTransform(tree: any) {
      visitParents(tree, 'text', (node, ancestors) => {
        const skipTags = new Set([
          'custom-typography',
          'code',
          'pre',
          'source-heading',
          'think',
          'script',
          'style',
          'a', // 关键
        ]);

        const shouldSkip = ancestors.some((ancestor: any) => {
          return ancestor?.tagName && skipTags.has(ancestor.tagName);
        });

        if (shouldSkip) {
          return;
        }

        node.type = 'element';
        node.tagName = 'custom-typography';
        node.properties = {};
        node.children = [{ type: 'text', value: node.value }];
      });
    };
  };

  const getReferenceInfo = useCallback(
    (chunkIndex: number) => {
      const chunks = reference?.chunks ?? [];
      const chunkItem = chunks[chunkIndex];

      const docIndex = reference?.doc_aggs?.findIndex(
        (x) => x?.doc_id === chunkItem?.document_id,
      );

      const document = reference?.doc_aggs?.[docIndex];
      const documentId = document?.doc_id;
      const documentUrl = document?.url;
      const fileThumbnail = documentId ? fileThumbnails[documentId] : '';
      const fileExtension = documentId ? getExtension(document?.doc_name) : '';
      const imageId = chunkItem?.image_id;

      return {
        documentUrl,
        fileThumbnail,
        fileExtension,
        imageId,
        chunkItem,
        documentId,
        document,
        docIndex,
      };
    },
    [fileThumbnails, reference],
  );

  const getPopoverContent = useCallback(
    (chunkIndex: number) => {
      const {
        documentUrl,
        fileThumbnail,
        fileExtension,
        imageId,
        chunkItem,
        documentId,
        document,
      } = getReferenceInfo(chunkIndex);

      return (
        <div key={chunkItem?.id} className="flex gap-2">
          {imageId && (
            <HoverCard>
              <HoverCardTrigger>
                <Image id={imageId} className={styles.referenceChunkImage} />
              </HoverCardTrigger>

              <HoverCardContent>
                <Image id={imageId} className={styles.referenceImagePreview} />
              </HoverCardContent>
            </HoverCard>
          )}

          <div className="space-y-2 max-w-[40vw]">
            <div
              dangerouslySetInnerHTML={{
                __html: DOMPurify.sanitize(chunkItem?.content ?? ''),
              }}
              className={classNames(styles.chunkContentText)}
            />

            {documentId && (
              <section className="flex gap-1">
                {fileThumbnail ? (
                  <img
                    src={fileThumbnail}
                    alt=""
                    className={styles.fileThumbnail}
                  />
                ) : (
                  <SvgIcon name={`file-icon/${fileExtension}`} width={24} />
                )}

                <Button
                  variant="link"
                  className="text-wrap p-0"
                  onClick={handleDocumentButtonClick(
                    documentId,
                    chunkItem,
                    fileExtension === 'pdf',
                    documentUrl,
                  )}
                >
                  {document?.doc_name}
                </Button>
              </section>
            )}
          </div>
        </div>
      );
    },
    [getReferenceInfo, handleDocumentButtonClick],
  );

  const renderReference = useCallback(
    (text: string) => {
      const replacedText = reactStringReplace(text, currentReg, (match, i) => {
        const chunkIndex = getChunkIndex(match);

        const {
          documentUrl,
          fileExtension,
          imageId,
          chunkItem,
          documentId,
          docIndex,
        } = getReferenceInfo(chunkIndex);

        const docType = chunkItem?.doc_type;

        return showImage(docType) ? (
          <section key={i}>
            <Image
              id={imageId}
              className={styles.referenceInnerChunkImage}
              onClick={
                documentId
                  ? handleDocumentButtonClick(
                      documentId,
                      chunkItem,
                      fileExtension === 'pdf',
                      documentUrl,
                    )
                  : () => {}
              }
            />
          </section>
        ) : (
          <HoverCard key={i}>
            <HoverCardTrigger asChild>
              <span
                className="
                reference-badge
                mx-0.5
                inline-flex
                h-4
                w-4
                shrink-0
                cursor-pointer
                items-center
                justify-center
                rounded-full
                bg-gray-200              /* 浅色模式：浅灰背景 */
                dark:bg-gray-700         /* 暗黑模式：深灰背景 */
                text-[10px]
                font-semibold
                leading-none
                text-gray-700            /* 浅色模式：深灰文字 */
                dark:text-gray-300       /* 暗黑模式：浅灰文字 */
                align-middle
                indent-0
                [text-indent:0]
              "
                style={{
                  textIndent: 0,
                }}
              >
                {docIndex + 1}
              </span>
            </HoverCardTrigger>

            <HoverCardContent className="max-w-3xl">
              {getPopoverContent(chunkIndex)}
            </HoverCardContent>
          </HoverCard>
        );
      });

      return replacedText;
    },
    [getPopoverContent, getReferenceInfo, handleDocumentButtonClick],
  );

  // const markdownComponents = useMemo(
  //   () =>
  //     ({
  //       /**
  //        * 兜底：
  //        * 如果 Markdown 真的解析到了 think，隐藏它。
  //        * 因为 think 已经在外层 splitThinkContent 里手动渲染了。
  //        */
  //       think: () => null,

  //       'source-heading': ({ children }: { children: React.ReactNode }) => (
  //         <div
  //           className="
  //     mt-5 mb-3
  //     flex items-center gap-3
  //     text-lg font-extrabold
  //     text-[#018B8D] dark:text-[#018B8D]
  //     indent-0
  //     [&_*]:indent-0
  //   "
  //           style={{ textIndent: 0 }}
  //         >
  //           <HomeIcon name="datasets" width="20" />

  //           <span className="indent-0" style={{ textIndent: 0 }}>
  //             {children}
  //           </span>
  //         </div>
  //       ),
  //       h2: ({ children }: { children: React.ReactNode }) => (
  //         <h2
  //           className="
  //           mt-5 mb-3

  //           text-lg font-extrabold leading-7
  //           text-gray-900 dark:text-gray-100
  //           indent-0
  //           [&_*]:indent-0
  //         "
  //           style={{ textIndent: 0 }}
  //         >
  //           {children}
  //         </h2>
  //       ),

  //               h3: ({ children }: { children: React.ReactNode }) => (
  //         <h3
  //           className="
  //           mt-4 mb-2
  //           ml-[2em]         /* 关键：向右侧推后 2 个字符宽度 */
  //           text-base font-bold leading-7
  //           text-gray-900 dark:text-gray-100
  //           indent-0
  //           [&_*]:indent-0
  //         "
  //           style={{ textIndent: 0 }}
  //         >
  //           {children}
  //         </h3>
  //       ),

  //       a: (props: any) => {
  //         if (isFileMarkdownLink(props.href)) {
  //           return <MarkdownFileLink {...props} />;
  //         }

  //         return (
  //           <a
  //             {...props}
  //             target="_blank"
  //             rel="noopener noreferrer"
  //             className="
  //       text-[#018B8D] underline
  //       hover:text-[#017476]
  //     "
  //           />
  //         );
  //       },
  //       p: ({ children }: { children: React.ReactNode }) => (
  //         <p
  //           className="
  //     my-2
  //     text-[15px]
  //     leading-8
  //     text-gray-800
  //     indent-[2em]
  //     dark:text-gray-200
  //   "
  //         >
  //           {children}
  //         </p>
  //       ),

  //       ul: ({ children }: { children: React.ReactNode }) => (
  //         <ul
  //           className="
  //     my-2
  //     ml-[2em]
  //     list-disc
  //     space-y-2
  //     pl-4
  //     text-gray-800
  //     dark:text-gray-200
  //     indent-0
  //   "
  //         >
  //           {children}
  //         </ul>
  //       ),

  //       ol: ({ children }: { children: React.ReactNode }) => (
  //         <ol
  //           className="
  //     my-2
  //     ml-[2em]
  //     list-decimal
  //     space-y-2
  //     pl-4
  //     text-gray-800
  //     dark:text-gray-200
  //     indent-0
  //   "
  //         >
  //           {children}
  //         </ol>
  //       ),

  //       li: ({ children }: { children: React.ReactNode }) => (
  //         <li
  //           className="
  //     pl-1
  //     text-[15px]
  //     leading-8
  //     text-gray-800
  //     marker:text-[#018B8D]
  //     dark:text-gray-200

  //     indent-0
  //     [&_*]:indent-0
  //     [&>p]:my-0
  //     [&>p]:indent-0
  //     [&_p]:indent-0
  //   "
  //         >
  //           {children}
  //         </li>
  //       ),

  //       // 自定义引用包裹
  //       'custom-typography': ({ children }: { children: string }) => {
  //         return renderReference(children);
  //       },

  //       // 代码块
  //       code(props: any) {
  //         const { children, className, ...rest } = props;
  //         const restProps = omit(rest, 'node');
  //         const match = /language-(\w+)/.exec(className || '');

  //         return match ? (
  //           <SyntaxHighlighter
  //             {...restProps}
  //             PreTag="div"
  //             language={match[1]}
  //             wrapLongLines
  //             className="rounded-md my-2"
  //           >
  //             {String(children).replace(/\n$/, '')}
  //           </SyntaxHighlighter>
  //         ) : (
  //           <code
  //             {...restProps}
  //             className={classNames(
  //               className,
  //               'text-wrap',
  //               'px-1.5 py-0.5',
  //               'bg-gray-100 dark:bg-gray-800',
  //               'rounded',
  //               'text-sm',
  //             )}
  //           >
  //             {children}
  //           </code>
  //         );
  //       },
  //     }) as any,
  //   [renderReference],
  // );

  const markdownComponents = useMemo(
    () =>
      ({
        think: () => null,

        'source-heading': ({ children }: { children: React.ReactNode }) => (
          <div
            className="
            mt-8 mb-4
            flex items-center gap-3
            text-xl font-bold
            text-black dark:text-white  /* 👈 改成纯黑/纯白 */
            indent-0
            [&_*]:indent-0
          "
            style={{ textIndent: 0 }}
          >
            <HomeIcon name="datasets" width="20" />
            <span className="indent-0" style={{ textIndent: 0 }}>
              {children}
            </span>
          </div>
        ),

        // ====== H2：主标题，字重最大，颜色最深 ======
        // ====== H2：主标题，字号最大，特粗，颜色稳重但不过黑 ======
        // ====== H2：主标题，20px，特粗，纯黑 ======
        h2: ({ children }: { children: React.ReactNode }) => (
          <h2
            className="
            mt-6 mb-3
            text-xl font-extrabold leading-8     /* 20px，字重最高 */
            text-black dark:text-white           /* 关键：纯黑（暗黑模式纯白） */
            indent-0
            [&_*]:indent-0
          "
            style={{ textIndent: 0 }}
          >
            {children}
          </h2>
        ),

        // ====== H3：副标题，17px，粗体，纯黑 ======
        h3: ({ children }: { children: React.ReactNode }) => (
          <h3
            className="
            mt-5 mb-2
            text-[17px] font-bold leading-7      /* 17px，比正文(15px)大 */
            text-black dark:text-white           /* 关键：纯黑（暗黑模式纯白） */
            indent-0
            [&_*]:indent-0
          "
            style={{ textIndent: 0 }}
          >
            {children}
          </h3>
        ),

        a: (props: any) => {
          if (isFileMarkdownLink(props.href)) {
            return <MarkdownFileLink {...props} />;
          }
          return (
            <a
              {...props}
              target="_blank"
              rel="noopener noreferrer"
              className="
              text-[#018B8D] underline underline-offset-4
              decoration-[#018B8D]/30 hover:decoration-[#018B8D]
              transition-colors
            "
            />
          );
        },

        p: ({ children }: { children: React.ReactNode }) => (
          <p
            className="
            my-4
            text-[15px]
            leading-7
            text-gray-800
            dark:text-gray-200
            indent-0
          "
            style={{ textIndent: 0 }}
          >
            {children}
          </p>
        ),

        ul: ({ children }: { children: React.ReactNode }) => (
          <ul
            className="
            my-4
            ml-5
            list-disc
            space-y-2
            text-gray-800
            dark:text-gray-200
            indent-0
          "
          >
            {children}
          </ul>
        ),

        ol: ({ children }: { children: React.ReactNode }) => (
          <ol
            className="
            my-4
            ml-5
            list-decimal
            space-y-2
            text-gray-800
            dark:text-gray-200
            indent-0
          "
          >
            {children}
          </ol>
        ),

        li: ({ children }: { children: React.ReactNode }) => (
          <li
            className="
            pl-1
            text-[15px]
            leading-7
            text-gray-800
            marker:text-gray-400 dark:marker:text-gray-500   /* 关键：黑点变灰点 */
            dark:text-gray-200
            indent-0
            [&_*]:indent-0
            [&>p]:my-0
            [&>p]:indent-0
            [&_p]:indent-0
          "
          >
            {children}
          </li>
        ),
        span: ({ children, className, ...rest }: any) => {
          // 👇 附件标签（带图标）
          if (className === 'md-attachment-label') {
            return (
              <span className="mt-6 -mb-2 flex items-center gap-1.5 font-semibold text-blue-600 dark:text-blue-400">
                <Paperclip className="h-4 w-4" />
                {children}
              </span>
            );
          }

          // 👇 新增：纯蓝文字（不带图标）
          if (className === 'md-blue-text') {
            return (
              <span className="mt-2 block font-semibold text-blue-600 dark:text-blue-400">
                {children}
              </span>
            );
          }

          return <span {...rest}>{children}</span>;
        },

        table: ({ children }: { children: React.ReactNode }) => (
          <div className="my-4 w-full overflow-x-auto">
            <table className="w-full border-collapse table-fixed">
              {children}
            </table>
          </div>
        ),

        thead: ({ children }: { children: React.ReactNode }) => (
          <thead className="bg-slate-50 dark:bg-slate-800/60">{children}</thead>
        ),

        th: ({ children, ...props }: any) => {
          const text = String(children);
          const isFirstCol = text === '字段';

          return (
            <th
              className="
        border border-slate-200 px-3 py-2 text-left
        text-[14px] font-semibold
        text-slate-800
        dark:border-slate-700
        dark:text-slate-100
      "
              style={{ width: isFirstCol ? '30%' : '70%' }}
              {...props}
            >
              {children}
            </th>
          );
        },

        td: ({ children, ...props }: any) => (
          <td
            className="
      border border-slate-200 px-3 py-2
      text-[14px]
      text-slate-700
      dark:border-slate-700
      dark:text-slate-200
    "
            {...props}
          >
            {children}
          </td>
        ),

        'custom-typography': ({ children }: { children: string }) => {
          return renderReference(children);
        },

        code(props: any) {
          const { children, className, ...rest } = props;
          const restProps = omit(rest, 'node');
          const match = /language-(\w+)/.exec(className || '');

          return match ? (
            <SyntaxHighlighter
              {...restProps}
              PreTag="div"
              language={match[1]}
              wrapLongLines
              className="rounded-lg my-4 !bg-gray-50 dark:!bg-gray-900 border border-gray-100 dark:border-gray-800"
            >
              {String(children).replace(/\n$/, '')}
            </SyntaxHighlighter>
          ) : (
            <code
              {...restProps}
              className={classNames(
                className,
                'text-wrap',
                'px-1.5 py-0.5',
                'bg-gray-100 dark:bg-gray-800',
                'rounded-md',
                'text-sm font-mono',
                'text-[#018B8D] dark:text-[#20B2AA]',
              )}
            >
              {children}
            </code>
          );
        },
      }) as any,
    [renderReference],
  );

  return (
    <div className={styles.markdownContentWrapper}>
      {showAgentToolCalls && <AgentToolCalls events={agentEvents} />}

      {segments.map((segment, index) => {
        if (segment.type === 'think') {
          const hasAnswerAfterThink = segments
            .slice(index + 1)
            .some(
              (item) => item.type === 'text' && item.content.trim().length > 0,
            );

          /**
           * 规则：
           * 有 </think>，并且 </think> 后面有正式文字 => 思考完成
           * 其他情况 => 正在思考
           */
          const isThinking = !(segment.done && hasAnswerAfterThink);

          return (
            <details
              open={true}
              key={`think-${index}`}
              className="
                group
                my-2
                text-sm
                text-gray-400
                dark:text-gray-500
              "
            >
              <summary
                className="
                  flex
                  cursor-pointer
                  select-none
                  list-none
                  items-center
                  gap-1
                  text-sm
                  font-normal
                  text-gray-400
                  dark:text-gray-500
                  [&::-webkit-details-marker]:hidden
                "
              >
                <span className="flex items-center gap-1.5">
                  <svg
                    className={`h-5 w-5 text-blue-600 dark:text-blue-400 ${
                      isThinking ? 'animate-[spin_2.6s_linear_infinite]' : ''
                    }`}
                    viewBox="0 0 24 24"
                    fill="none"
                    xmlns="http://www.w3.org/2000/svg"
                  >
                    {/* 第一条对角线 */}
                    <ellipse
                      cx="12"
                      cy="12"
                      rx="8"
                      ry="3.2"
                      stroke="currentColor"
                      strokeWidth="1.7"
                      transform="rotate(45 12 12)"
                    />
                    {/* 第二条对角线 */}
                    <ellipse
                      cx="12"
                      cy="12"
                      rx="8"
                      ry="3.2"
                      stroke="currentColor"
                      strokeWidth="1.7"
                      transform="rotate(-45 12 12)"
                    />
                    {/* 中心圆点 */}
                    <circle cx="12" cy="12" r="1.8" fill="currentColor" />
                  </svg>

                  <span className="text-[15px] font-medium text-gray-400 dark:text-gray-500">
                    {isThinking ? '正在思考' : '思考完成'}
                  </span>
                </span>

                {isThinking && (
                  <span className="ml-1 inline-flex gap-0.5">
                    <span className="animate-bounce">.</span>
                    <span className="animate-bounce [animation-delay:150ms]">
                      .
                    </span>
                    <span className="animate-bounce [animation-delay:300ms]">
                      .
                    </span>
                  </span>
                )}

                <ChevronRight
                  className="
                    h-4 w-4
                    text-text-secondary
                    transition-transform duration-300 ease-out
                    group-open:rotate-90
                  "
                />
              </summary>

              <div
                className="
                  mt-3
                  whitespace-pre-wrap
                  leading-7
                  text-gray-400
                  dark:text-gray-500
                "
              >
                {segment.content}
              </div>
            </details>
          );
        }

        // ====== 关键：text 段按 source-heading 二次切分 ======
        const sourceGroups = splitBySourceHeading(segment.content);

        return (
          <Fragment key={`text-${index}`}>
            {sourceGroups.map((group, gi) => {
              if (group.type === 'plain') {
                return (
                  <Markdown
                    key={`plain-${gi}`}
                    rehypePlugins={[
                      rehypeWrapReference,
                      rehypeKatex,
                      rehypeRaw,
                    ]}
                    remarkPlugins={[remarkGfm, remarkMath]}
                    components={markdownComponents}
                  >
                    {group.content}
                  </Markdown>
                );
              }

              return (
                <CollapsibleSourceSection
                  key={`heading-${gi}`}
                  heading={group.heading}
                >
                  <Markdown
                    rehypePlugins={[
                      rehypeWrapReference,
                      rehypeKatex,
                      rehypeRaw,
                    ]}
                    remarkPlugins={[remarkGfm, remarkMath]}
                    components={markdownComponents}
                  >
                    {group.content}
                  </Markdown>
                </CollapsibleSourceSection>
              );
            })}
          </Fragment>
        );
      })}

      <AgentFileDownloads events={agentEvents} />
    </div>
  );
};

export default MarkdownContent;
