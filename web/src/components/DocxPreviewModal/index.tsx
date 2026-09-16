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

  // 构造下载链接：把 preview 改成 0，让后端返回 attachment
  const buildDownloadUrl = useCallback(() => {
    try {
      // url 可能是相对地址，用当前 origin 兜底解析
      const parsed = new URL(url, window.location.origin);

      // 只有命中模板接口时才需要改 preview
      if (parsed.pathname.includes('/v1/file/template')) {
        parsed.searchParams.set('preview', '0');
      }

      return parsed.toString();
    } catch {
      // URL 解析失败时原样返回，靠 <a download> 兜底
      return url;
    }
  }, [url]);

  const handleDownload = useCallback(() => {
    const downloadUrl = buildDownloadUrl();

    // blob: / data: 这类 URL 直接把 download 属性交给 <a> 即可
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = fileName || 'download';
    link.rel = 'noopener noreferrer';

    // 对于跨域 URL，download 属性可能被浏览器忽略，
    // 但后端返回 attachment 时仍然会下载
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }, [buildDownloadUrl, fileName]);

  return (
    <div
      className="
        fixed inset-0 z-[9999]
        flex items-center justify-center
        bg-black/60 p-4
      "
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) {
          onClose();
        }
      }}
    >
      <div
        className="
          flex
          h-[92vh]
          w-full
          max-w-5xl
          flex-col
          overflow-hidden
          rounded-xl
          bg-slate-100
          shadow-2xl
        "
      >
        {/* 顶部标题栏 */}
        <div
          className="
            flex
            h-12
            shrink-0
            items-center
            justify-between
            border-b
            border-slate-200
            bg-white
            px-4
            dark:border-slate-700
            dark:bg-slate-900
          "
        >
          <div
            className="
              min-w-0
              flex-1
              truncate
              text-sm
              font-medium
              text-slate-700
              dark:text-slate-200
            "
            title={fileName}
          >
            {fileName}
          </div>

          {/* 操作区：下载 + 关闭 */}
          <div className="ml-3 flex shrink-0 items-center gap-1">
            <button
              type="button"
              onClick={handleDownload}
              className="
                rounded-md
                p-1.5
                text-slate-400
                transition-colors
                hover:bg-slate-100
                hover:text-slate-700
                dark:hover:bg-slate-800
                dark:hover:text-slate-200
              "
              aria-label="下载文件"
              title="下载"
            >
              <Download size={18} />
            </button>

            <button
              type="button"
              onClick={onClose}
              className="
                rounded-md
                p-1.5
                text-slate-400
                transition-colors
                hover:bg-slate-100
                hover:text-slate-700
                dark:hover:bg-slate-800
                dark:hover:text-slate-200
              "
              aria-label="关闭预览"
              title="关闭"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* 内容区域 */}
        <div
          className="
            min-h-0
            flex-1
            overflow-hidden
            bg-slate-200
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
              p-6
            "
          />
        </div>
      </div>
    </div>
  );
}
