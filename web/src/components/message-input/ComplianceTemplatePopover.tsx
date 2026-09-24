import { FileText, LayoutGrid } from 'lucide-react';
import React from 'react';

export interface ComplianceTemplate {
  id: string;
  name: string;
  path?: string;
  size?: number;
  updatedAt?: string;
}

interface Props {
  templates: ComplianceTemplate[];
  onSelect?: (tpl: ComplianceTemplate) => void;
  onViewAll: () => void;
}

/** 按后缀返回图标颜色和描述，模仿截图里的分组风格 */
function getFileMeta(name: string) {
  const suffix = (name.split('.').pop() || '').toLowerCase();
  const map: Record<string, { color: string; label: string }> = {
    pdf: { color: '#e74c3c', label: 'PDF 文档处理' },
    doc: { color: '#2b7cd3', label: 'Word 文档处理工具' },
    docx: { color: '#2b7cd3', label: 'Word 文档处理工具' },
    xls: { color: '#4caf50', label: 'Excel 电子表格处理工具' },
    xlsx: { color: '#4caf50', label: 'Excel 电子表格处理工具' },
    csv: { color: '#4caf50', label: 'CSV 表格处理' },
    ppt: { color: '#e67e22', label: 'PPT 演示文稿' },
    pptx: { color: '#e67e22', label: 'PPT 演示文稿' },
    png: { color: '#9b59b6', label: '图像处理' },
    jpg: { color: '#9b59b6', label: '图像处理' },
    jpeg: { color: '#9b59b6', label: '图像处理' },
    webp: { color: '#9b59b6', label: '图像处理' },
    svg: { color: '#9b59b6', label: '图像处理' },
    txt: { color: '#6b7280', label: '文本文件' },
  };
  return map[suffix] || { color: '#6b7280', label: '文件' };
}

const ComplianceTemplatePopover: React.FC<Props> = ({
  templates,
  onSelect,
  onViewAll,
}) => {
  return (
    <div className="w-[300px] overflow-hidden rounded-xl bg-white dark:bg-slate-900">
      {/* 列表 */}
      <div className="max-h-[320px] overflow-y-auto p-1.5">
        {templates.length === 0 ? (
          <div className="p-4 text-center text-sm text-gray-400">暂无模板</div>
        ) : (
          templates.slice(0, 6).map((tpl) => {
            const meta = getFileMeta(tpl.name);
            return (
              <div
                key={tpl.id}
                onClick={() => onSelect?.(tpl)}
                className="flex cursor-pointer items-center gap-3 rounded-lg px-2.5 py-2 transition-colors hover:bg-gray-100 dark:hover:bg-slate-800"
              >
                <div
                  className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md"
                  style={{
                    background: `${meta.color}1a`,
                    color: meta.color,
                  }}
                >
                  <FileText size={16} />
                </div>

                <div className="min-w-0 flex-1">
                  <div className="truncate text-[13px] font-medium text-gray-800 dark:text-slate-100">
                    {tpl.name}
                  </div>
                  <div className="truncate text-[11px] text-gray-400">
                    {meta.label}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* 底部按钮 */}
      <div className="border-t border-gray-100 p-1.5 dark:border-slate-800">
        <button
          type="button"
          onClick={onViewAll}
          className="flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-left text-[13px] text-gray-700 transition-colors hover:bg-gray-100 dark:text-slate-200 dark:hover:bg-slate-800"
        >
          <LayoutGrid size={16} />
          <span>查看所有模板</span>
        </button>
      </div>
    </div>
  );
};

export default ComplianceTemplatePopover;
