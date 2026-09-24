import {
  FileImageOutlined,
  FileOutlined,
  FilePdfOutlined,
  FileTextOutlined,
  FileWordOutlined,
} from '@ant-design/icons';
import { Empty, Spin, Tooltip, message, theme } from 'antd';
import { Copy, Download, X } from 'lucide-react';
import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';

import { DocPreviewer } from '@/components/document-preview/doc-preview';
import { getAuthorization } from '@/utils/authorization-util';

export interface ComplianceTemplate {
  id: string;
  name: string;
  path?: string;
  size?: number;
  updatedAt?: string;
}

interface Props {
  visible: boolean;
  onClose: () => void;
}

const ComplianceTemplateDialog: React.FC<Props> = ({ visible, onClose }) => {
  const { token } = theme.useToken();

  const authHeaders = useMemo(
    () => ({
      Authorization: getAuthorization() || '',
      'Content-Type': 'application/json',
    }),
    [],
  );

  const [templates, setTemplates] = useState<ComplianceTemplate[]>([]);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState<ComplianceTemplate | null>(null);

  /** 预览容器 ref：复制时从这里提取文本 */
  const previewRef = useRef<HTMLDivElement>(null);

  const getSuffix = (name?: string) => {
    if (!name) return '';
    const idx = name.lastIndexOf('.');
    return idx === -1 ? '' : name.slice(idx).toLowerCase();
  };

  /** 拼预览 URL，带上 token（如果后端支持 query 传 token） */
  const buildPreviewUrl = useCallback((path: string) => {
    const auth = getAuthorization() || '';
    return `/v1/file/template-file?path=${encodeURIComponent(
      path,
    )}&preview=1&token=${encodeURIComponent(auth)}`;
  }, []);

  /** 下载 URL */
  const buildDownloadUrl = useCallback((path: string) => {
    const auth = getAuthorization() || '';
    return `/v1/file/template-file?path=${encodeURIComponent(
      path,
    )}&preview=0&token=${encodeURIComponent(auth)}`;
  }, []);

  /** 拉模板列表 */
  const loadTemplates = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetch('/v1/file/templates', {
        method: 'GET',
        headers: authHeaders,
        credentials: 'include',
      });
      const result = await res.json();

      if (!res.ok || (result.code !== undefined && result.code !== 0)) {
        throw new Error(result.message || '获取模板列表失败');
      }

      const list: ComplianceTemplate[] = Array.isArray(result)
        ? result
        : result.data || [];

      setTemplates(list);
      if (list.length > 0) {
        setSelected(list[0]);
      }
    } catch (e: any) {
      message.error(e.message || '获取模板列表失败');
    } finally {
      setLoading(false);
    }
  }, [authHeaders]);

  useEffect(() => {
    if (visible) {
      loadTemplates();
    } else {
      setTemplates([]);
      setSelected(null);
    }
  }, [visible, loadTemplates]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    if (visible) {
      document.addEventListener('keydown', onKey);
    }
    return () => document.removeEventListener('keydown', onKey);
  }, [visible, onClose]);

  /** 下载 */
  const handleDownload = useCallback(() => {
    if (!selected) return;
    const url = buildDownloadUrl(selected.id);
    const a = document.createElement('a');
    a.href = url;
    a.download = selected.name;
    a.rel = 'noopener noreferrer';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  }, [selected, buildDownloadUrl]);

  /** 复制：复制选中文件内所有内容 */
  const handleCopy = useCallback(async () => {
    if (!selected) return;
    try {
      const root = previewRef.current;
      if (!root) return;

      // DocPreviewer 内部的渲染容器 class 是 template-docx-preview
      const contentEl = root.querySelector('.template-docx-preview') || root;

      const text = (contentEl as HTMLElement).innerText || '';

      if (!text.trim()) {
        message.warning('暂无可复制内容');
        return;
      }

      await navigator.clipboard.writeText(text);
      message.success('已复制文件内容');
    } catch {
      message.error('复制失败');
    }
  }, [selected]);

  if (!visible) return null;

  const getFileIcon = (name: string) => {
    const suffix = getSuffix(name);
    if (suffix === '.docx' || suffix === '.doc') {
      return <FileWordOutlined style={{ color: '#2b7cd3' }} />;
    }
    if (suffix === '.pdf') {
      return <FilePdfOutlined style={{ color: '#e74c3c' }} />;
    }
    if (['.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg'].includes(suffix)) {
      return <FileImageOutlined style={{ color: '#4caf50' }} />;
    }
    if (suffix === '.txt') {
      return <FileTextOutlined style={{ color: '#6b7280' }} />;
    }
    return <FileOutlined style={{ color: '#6b7280' }} />;
  };

  return (
    <>
      <style>{`
        .template-docx-preview table {
          width: 100%;
          border-collapse: collapse;
          margin: 12px 0;
        }

        .template-docx-preview th,
        .template-docx-preview td {
          border: 1px solid #d0d7de;
          padding: 6px 10px;
          vertical-align: top;
        }

        .template-docx-preview th {
          background: #f6f8fa;
          font-weight: 600;
        }

        .template-docx-preview p {
          margin: 8px 0;
        }

        .template-docx-preview h1,
        .template-docx-preview h2,
        .template-docx-preview h3,
        .template-docx-preview h4 {
          margin-top: 16px;
          margin-bottom: 8px;
          font-weight: 600;
        }

        .template-docx-preview ul,
        .template-docx-preview ol {
          padding-left: 22px;
        }

        .template-docx-preview img {
          max-width: 100%;
        }
      `}</style>

      <div
        className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/60 p-4"
        onMouseDown={(e) => {
          if (e.target === e.currentTarget) onClose();
        }}
      >
        <div
          className="flex h-[88vh] w-full max-w-6xl flex-col overflow-hidden rounded-xl shadow-2xl"
          style={{ background: token.colorBgContainer }}
        >
          {/* 顶部标题栏：只留标题 + 关闭 */}
          <div
            className="flex h-12 shrink-0 items-center justify-between px-4"
            style={{ borderBottom: `1px solid ${token.colorBorderSecondary}` }}
          >
            <div
              className="min-w-0 flex-1 truncate text-sm font-medium"
              style={{ color: token.colorText }}
              title={selected?.name}
            >
              合规申报模板{selected ? ` · ${selected.name}` : ''}
            </div>

            <div className="ml-3 flex shrink-0 items-center gap-1">
              <button
                type="button"
                onClick={onClose}
                className="rounded-md p-1.5 transition-colors"
                style={{ color: token.colorTextSecondary }}
                aria-label="关闭"
              >
                <X size={18} />
              </button>
            </div>
          </div>

          {/* 主体 */}
          <div className="flex flex-1 min-h-0">
            {/* 左侧列表 */}
            <div
              className="w-[260px] shrink-0 overflow-y-auto p-3"
              style={{ borderRight: `1px solid ${token.colorBorderSecondary}` }}
            >
              {loading ? (
                <div className="p-6 text-center">
                  <Spin size="small" />
                </div>
              ) : templates.length ? (
                templates.map((tpl) => {
                  const isSelected = selected?.id === tpl.id;
                  return (
                    <div
                      key={tpl.id}
                      onClick={() => setSelected(tpl)}
                      className="flex h-10 cursor-pointer items-center gap-2 rounded-lg px-2.5 text-[13px] select-none"
                      style={{
                        color: isSelected ? '#1677ff' : token.colorText,
                        background: isSelected
                          ? 'rgba(22, 119, 255, 0.08)'
                          : 'transparent',
                      }}
                    >
                      <span className="inline-flex w-4 shrink-0">
                        {getFileIcon(tpl.name)}
                      </span>
                      <Tooltip title={tpl.name}>
                        <span className="flex-1 truncate">{tpl.name}</span>
                      </Tooltip>
                    </div>
                  );
                })
              ) : (
                <Empty
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                  description="暂无模板"
                />
              )}
            </div>

            {/* 右侧预览 */}
            <div className="flex flex-1 min-w-0 flex-col">
              {/* 预览标题栏：文件名 + 复制 + 下载 */}
              <div
                className="flex h-11 shrink-0 items-center justify-between gap-3 px-4"
                style={{
                  borderBottom: `1px solid ${token.colorBorderSecondary}`,
                }}
              >
                <div
                  className="truncate text-sm font-medium"
                  style={{ color: token.colorText }}
                >
                  {selected?.name || '请选择模板'}
                </div>

                <div className="flex shrink-0 items-center gap-1">
                  <Tooltip title="复制内容">
                    <button
                      type="button"
                      onClick={handleCopy}
                      disabled={!selected}
                      className="rounded-md p-1.5 transition-colors disabled:opacity-40"
                      style={{ color: token.colorTextSecondary }}
                      aria-label="复制内容"
                    >
                      <Copy size={16} />
                    </button>
                  </Tooltip>

                  <Tooltip title="下载">
                    <button
                      type="button"
                      onClick={handleDownload}
                      disabled={!selected}
                      className="rounded-md p-1.5 transition-colors disabled:opacity-40"
                      style={{ color: token.colorTextSecondary }}
                      aria-label="下载"
                    >
                      <Download size={16} />
                    </button>
                  </Tooltip>
                </div>
              </div>

              {/* 预览内容：全部交给 DocPreviewer */}
              <div
                ref={previewRef}
                className="min-h-0 flex-1 overflow-hidden bg-slate-200"
              >
                {selected ? (
                  <DocPreviewer
                    url={buildPreviewUrl(selected.id)}
                    className="template-docx-preview !h-full !min-h-0 !w-full !overflow-auto rounded-none border-0"
                  />
                ) : (
                  <div className="flex h-full items-center justify-center">
                    <Empty description="请选择左侧模板" />
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
};

export default ComplianceTemplateDialog;
