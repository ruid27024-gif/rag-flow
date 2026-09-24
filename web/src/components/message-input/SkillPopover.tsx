// src/components/message-input/SkillPopover.tsx
'use client';

import { cn } from '@/lib/utils';
import {
  BarChart3,
  BookOpenCheck,
  Bot,
  Calculator,
  Calendar,
  ClipboardList,
  Code2,
  Database,
  FileEdit,
  FileText,
  Globe,
  Image as ImageIcon,
  Languages,
  Loader2,
  Mail,
  Megaphone,
  Newspaper,
  Palette,
  Presentation,
  ScanText,
  Sparkles,
  Table2,
  TrendingUp,
  Video,
} from 'lucide-react';
import * as React from 'react';

export interface SkillItem {
  id: string;
  name: string;
  description: string;
  icon: React.ComponentType<{ className?: string; strokeWidth?: number }>;
  category: string;
  badge?: '官方' | '社区';
}

// ============ 技能数据（可换成接口） ============
export const ALL_SKILLS: SkillItem[] = [
  {
    id: 'ppt',
    name: 'PPT',
    description: '创建、编辑与优化 PPT，支持内容编排、图表排版与备注管理',
    icon: Presentation,
    category: 'Office办公',
    badge: '官方',
  },
  {
    id: 'excel',
    name: 'Excel',
    description: '创建、整理和分析表格，支持清洗、计算、统计和图表制作',
    icon: Table2,
    category: 'Office办公',
    badge: '官方',
  },
  {
    id: 'word',
    name: 'Word 文档',
    description: '生成、编辑和格式化 Word 文档，支持大纲、目录与样式管理',
    icon: FileText,
    category: 'Office办公',
    badge: '官方',
  },
  {
    id: 'doc-scan',
    name: '文档图片扫描',
    description: '使用奇克扫描王 AI 处理文档证件图片，切边矫正，高清归档',
    icon: ScanText,
    category: 'Office办公',
    badge: '官方',
  },
  {
    id: 'email-assistant',
    name: '邮件助手',
    description: '起草、回复和总结邮件，支持多语言和语气调整',
    icon: Mail,
    category: 'Office办公',
    badge: '官方',
  },
  {
    id: 'scheduler',
    name: '日程管理',
    description: '创建日程、提醒，智能安排会议时间，避免冲突',
    icon: Calendar,
    category: 'Office办公',
    badge: '官方',
  },
  {
    id: 'meeting-notes',
    name: '会议纪要',
    description: '将会议内容整理成结构化纪要，提取待办事项和决议',
    icon: ClipboardList,
    category: 'Office办公',
    badge: '官方',
  },
  {
    id: 'xiaohongshu-cover',
    name: '归藏小红书公众号封面制作',
    description:
      'AI 设计博主「归藏」出品，帮你生成高质量小红书组图与公众号封面',
    icon: ImageIcon,
    category: '内容创作',
    badge: '社区',
  },
  {
    id: 'kazike-writer',
    name: '卡兹克公众号写作',
    description: '用「数字生命卡兹克」的个人风格撰写有活人感的公众号长文',
    icon: FileEdit,
    category: '内容创作',
    badge: '社区',
  },
  {
    id: 'image-gen',
    name: '图像生成',
    description: '根据文字描述生成图片，支持多种风格和尺寸',
    icon: Palette,
    category: '内容创作',
    badge: '官方',
  },
  {
    id: 'video-script',
    name: '视频脚本',
    description: '生成短视频分镜脚本，包含画面、台词和时长建议',
    icon: Video,
    category: '内容创作',
    badge: '官方',
  },
  {
    id: 'marketing-copy',
    name: '营销文案',
    description: '撰写广告语、活动文案和品牌宣传内容',
    icon: Megaphone,
    category: '内容创作',
    badge: '官方',
  },
  {
    id: 'daily-news',
    name: '每日资讯简报',
    description: '每天汇总全球重点资讯，按关注领域整理成简报',
    icon: Newspaper,
    category: '资讯研究',
    badge: '官方',
  },
  {
    id: 'paper-track',
    name: '论文推荐与追踪',
    description: '发现前沿论文并生成速览报告，支持关键词订阅',
    icon: BookOpenCheck,
    category: '资讯研究',
    badge: '官方',
  },
  {
    id: 'web-search',
    name: '联网搜索',
    description: '实时检索互联网信息，获取最新资讯、新闻和数据',
    icon: Globe,
    category: '资讯研究',
    badge: '官方',
  },
  {
    id: 'stock-analysis',
    name: '股票深度分析',
    description: '综合基本面、消息面和资金面分析个股，提供投资参考',
    icon: TrendingUp,
    category: '投资理财',
    badge: '官方',
  },
  {
    id: 'data-analysis',
    name: '数据分析',
    description: '对上传的表格、数据集进行统计分析与洞察提取',
    icon: BarChart3,
    category: '数据分析',
    badge: '官方',
  },
  {
    id: 'sql-helper',
    name: 'SQL 助手',
    description: '根据需求生成 SQL 查询语句，支持主流数据库',
    icon: Database,
    category: '数据分析',
    badge: '官方',
  },
  {
    id: 'code-interpreter',
    name: '代码执行',
    description: '运行 Python 代码，完成数据处理、计算与可视化',
    icon: Code2,
    category: '方案写作',
    badge: '官方',
  },
  {
    id: 'translator',
    name: '翻译助手',
    description: '多语言互译，保留专业术语和语气风格',
    icon: Languages,
    category: '实用工具',
    badge: '官方',
  },
  {
    id: 'calculator',
    name: '数学计算',
    description: '处理复杂公式计算、单位换算与数学推导',
    icon: Calculator,
    category: '实用工具',
    badge: '官方',
  },
  {
    id: 'prompt-enhance',
    name: '提示词优化',
    description: '自动润色和增强你的提示词，获得更好的模型输出',
    icon: Sparkles,
    category: '实用工具',
    badge: '社区',
  },
  {
    id: 'agent-builder',
    name: 'Agent 构建',
    description: '可视化搭建智能体工作流，支持工具调用和多步推理',
    icon: Bot,
    category: '实用工具',
    badge: '官方',
  },
];

// ============ Popover 内容组件 ============
interface SkillPopoverProps {
  skills?: SkillItem[];
  loading?: boolean;
  onSelect?: (skill: SkillItem) => void;
  onViewAll?: () => void;
}

const SkillPopover: React.FC<SkillPopoverProps> = ({
  skills = ALL_SKILLS,
  loading = false,
  onSelect,
  onViewAll,
}) => {
  // 小面板里最多展示 8 个
  const displaySkills = skills.slice(0, 8);

  return (
    <div className="w-[320px]">
      {/* 头部 */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-gray-100 dark:border-gray-800">
        <span className="text-xs font-medium text-gray-700 dark:text-gray-200">
          技能
        </span>
        <span className="text-[11px] text-gray-400">{skills.length}</span>
      </div>

      {/* 列表 */}
      <div className="max-h-[320px] overflow-y-auto">
        {loading ? (
          <div className="flex items-center justify-center py-8 text-gray-400">
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            <span className="text-xs">加载中…</span>
          </div>
        ) : displaySkills.length === 0 ? (
          <div className="py-8 text-center text-xs text-gray-400">暂无技能</div>
        ) : (
          <ul className="py-1">
            {displaySkills.map((skill) => {
              const Icon = skill.icon;
              return (
                <li key={skill.id}>
                  <button
                    type="button"
                    onClick={() => onSelect?.(skill)}
                    className="
                      group flex w-full items-start gap-2.5 px-3 py-2
                      text-left transition-colors
                      hover:bg-gray-50 dark:hover:bg-gray-800/60
                    "
                  >
                    <span
                      className="
                      mt-0.5 flex size-7 shrink-0 items-center justify-center
                      rounded-md bg-slate-100 text-slate-600
                      dark:bg-slate-800 dark:text-slate-300
                    "
                    >
                      <Icon className="size-3.5" strokeWidth={2} />
                    </span>

                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-1.5">
                        <span className="truncate text-[13px] font-medium text-gray-800 dark:text-gray-100">
                          {skill.name}
                        </span>
                        {skill.badge && (
                          <span
                            className={cn(
                              'shrink-0 rounded px-1 py-0.5 text-[10px] leading-none',
                              skill.badge === '官方'
                                ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300'
                                : 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400',
                            )}
                          >
                            {skill.badge}
                          </span>
                        )}
                      </div>
                      <p className="mt-0.5 line-clamp-1 text-[11px] text-gray-400">
                        {skill.description}
                      </p>
                    </div>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>

      {/* 底部：查看全部 */}
      <div className="border-t border-gray-100 dark:border-gray-800">
        <button
          type="button"
          onClick={onViewAll}
          className="
            flex w-full items-center justify-center py-2
            text-xs font-medium text-blue-600 hover:bg-blue-50
            dark:text-blue-400 dark:hover:bg-blue-950/30
            transition-colors
          "
        >
          查看全部技能
        </button>
      </div>
    </div>
  );
};

export default SkillPopover;
