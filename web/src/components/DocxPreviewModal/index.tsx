import { Download, X } from 'lucide-react';
import { useCallback, useEffect } from 'react';

import { DocPreviewer } from '@/components/document-preview/doc-preview';

interface DocxPreviewModalProps {
  url: string;
  fileName: string;
  onClose: () => void;
}

export default function DocxPreviewModal({
  url,
  fileName,
  onClose,
}: DocxPreviewModalProps) {
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose();
      }
    };

    document.addEventListener('keydown', handleKeyDown);

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [onClose]);

  const buildDownloadUrl = useCallback(() => {
    try {
      const parsed = new URL(url, window.location.origin);

      if (parsed.pathname.includes('/v1/file/template')) {
        parsed.searchParams.set('preview', '0');
      }

      return parsed.toString();
    } catch {
      return url;
    }
  }, [url]);

  const handleDownload = useCallback(() => {
    const downloadUrl = buildDownloadUrl();

    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = fileName || 'download';
    link.rel = 'noopener noreferrer';

    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }, [buildDownloadUrl, fileName]);

  return (
    <>
      <style>{`
        /* ============ docx 纸张：暗色环境 + A4 白纸 ============ */

        .docx-preview-content .docx-wrapper {
          background: transparent !important;
          padding: 28px 16px !important;
          display: flex !important;
          flex-direction: column !important;
          align-items: center !important;
          gap: 28px !important;
          min-height: 100% !important;
          box-sizing: border-box !important;
        }

        /* A4 比例白纸：620 × 1.414 ≈ 877 */
        .docx-preview-content .docx-wrapper > section.docx {
          background: #ffffff !important;
          color: #1f2328 !important;
          width: 620px !important;
          max-width: 100% !important;
          min-height: 877px !important;
          box-sizing: border-box !important;
          padding: 56px 64px !important;
          border-radius: 4px !important;
          margin: 0 auto !important;
          box-shadow:
            0 12px 40px rgba(0, 0, 0, 0.55),
            0 3px 10px rgba(0, 0, 0, 0.35) !important;
        }

        html:not(.dark) .docx-preview-content .docx-wrapper > section.docx {
          box-shadow:
            0 8px 24px rgba(0, 0, 0, 0.12),
            0 2px 6px rgba(0, 0, 0, 0.06) !important;
        }

        .docx-preview-content .docx-wrapper section.docx,
        .docx-preview-content .docx-wrapper section.docx * {
          color: #1f2328 !important;
        }

        .docx-preview-content .docx-wrapper section.docx h1,
        .docx-preview-content .docx-wrapper section.docx h2,
        .docx-preview-content .docx-wrapper section.docx h3,
        .docx-preview-content .docx-wrapper section.docx h4,
        .docx-preview-content .docx-wrapper section.docx strong {
          color: #111827 !important;
        }

        .docx-preview-content .docx-wrapper section.docx td,
        .docx-preview-content .docx-wrapper section.docx th {
          border-color: #d0d7de !important;
        }
        .docx-preview-content .docx-wrapper section.docx th {
          background: #f6f8fa !important;
        }
        .docx-preview-content .docx-wrapper section.docx tr:nth-child(even) td {
          background: #fafbfc !important;
        }
        .docx-preview-content .docx-wrapper section.docx a {
          color: #0969da !important;
        }

        .dark .docx-preview-content .docx-wrapper > section.docx {
          border: 1px solid rgba(255, 255, 255, 0.06) !important;
        }
      `}</style>

      {/* 遮罩 */}
      <div
        className="
          fixed inset-0 z-[9999]
          flex items-center justify-center
          bg-black/60 p-4
          backdrop-blur-sm
        "
        onMouseDown={(event) => {
          if (event.target === event.currentTarget) {
            onClose();
          }
        }}
      >
        {/* 卡片主体：宽度收到 700 */}
        <div
          className="
            flex h-[92vh] w-full max-w-[768px] flex-col overflow-hidden
            rounded-2xl
            border border-zinc-200 dark:border-zinc-800
            bg-white dark:bg-[#1e1e1e]
            shadow-2xl
          "
        >
          {/* 顶栏 */}
          <div
            className="
              flex h-11 shrink-0 items-center justify-between
              border-b border-zinc-200 dark:border-zinc-800
              bg-zinc-50 dark:bg-[#252525]
              px-4
            "
          >
            <div
              className="
                min-w-0 flex-1 truncate
                text-[13px] font-medium
                text-zinc-700 dark:text-zinc-300
              "
              title={fileName}
            >
              {fileName}
            </div>

            <div className="ml-3 flex shrink-0 items-center gap-1">
              <button
                type="button"
                onClick={handleDownload}
                className="
                  inline-flex items-center gap-1.5
                  rounded-md
                  px-2 py-1
                  text-[12px] font-medium
                  text-zinc-500 dark:text-zinc-400
                  transition-colors
                  hover:bg-zinc-100 dark:hover:bg-zinc-800
                  hover:text-zinc-900 dark:hover:text-zinc-100
                "
                aria-label="下载文件"
                title="下载"
              >
                <Download size={14} />
                <span>下载</span>
              </button>

              <button
                type="button"
                onClick={onClose}
                className="
                  inline-flex items-center justify-center
                  rounded-md
                  p-1.5
                  text-zinc-500 dark:text-zinc-400
                  transition-colors
                  hover:bg-zinc-100 dark:hover:bg-zinc-800
                  hover:text-zinc-900 dark:hover:text-zinc-100
                "
                aria-label="关闭预览"
                title="关闭"
              >
                <X size={16} />
              </button>
            </div>
          </div>

          {/* 内容区 */}
          <div
            className="
              docx-preview-content
              min-h-0 flex-1 overflow-hidden
              bg-zinc-100 dark:bg-[#1a1a1a]
            "
          >
            <DocPreviewer
              url={url}
              className="
                !h-full
                !min-h-0
                !w-full
                !overflow-auto
                rounded-none
                border-0
                !p-0
              "
            />
          </div>
        </div>
      </div>
    </>
  );
}
