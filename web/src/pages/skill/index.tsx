// src/pages/skill/index.tsx
import { cn } from '@/lib/utils';
import {
  BarChart3,
  BookMarked,
  BookOpenCheck,
  Bot,
  Briefcase,
  Calculator,
  Calendar,
  ChevronLeft,
  ClipboardList,
  Code2,
  Database,
  FileCode2,
  FileEdit,
  FileSpreadsheet,
  FileText,
  Globe,
  GraduationCap,
  Image as ImageIcon,
  Languages,
  Lightbulb,
  LineChart,
  Mail,
  Megaphone,
  Mic,
  Newspaper,
  Palette,
  Plus,
  Presentation,
  ScanText,
  Search,
  Sparkles,
  Table2,
  TrendingUp,
  Video,
} from 'lucide-react';
import React, { useMemo, useState } from 'react';
import { useNavigate, useParams } from 'umi';
import WelcomeCloudBg from '../next-chats-default/welcome-cloud-bg';

// ============ 技能类型 ============
export interface SkillItem {
  id: string;
  name: string;
  description: string;
  icon: React.ComponentType<{ className?: string; strokeWidth?: number }>;
  category: string;
  badge?: '官方' | '社区';
}

// ============ 技能数据 ============
const ALL_SKILLS: SkillItem[] = [
  // Office办公
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

  // 内容创作
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
    id: 'guizang-ppt',
    name: '归藏 PPT',
    description: 'AI 设计博主「归藏」出品，帮你制作有品味的网页版 PPT',
    icon: Presentation,
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
    id: 'podcast-writer',
    name: '播客文案',
    description: '撰写播客稿、访谈提纲和口播文案',
    icon: Mic,
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

  // 资讯研究
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
    id: 'image-collect',
    name: '图文信息收集',
    description: '按主题收集图片和文字资料，整理成图文并茂的内容',
    icon: BookMarked,
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
    id: 'industry-report',
    name: '行业研究报告',
    description: '收集行业数据，生成结构化的行业分析与趋势报告',
    icon: LineChart,
    category: '资讯研究',
    badge: '官方',
  },

  // 投资理财
  {
    id: 'stock-analysis',
    name: '股票深度分析',
    description: '综合基本面、消息面和资金面分析个股，提供投资参考',
    icon: TrendingUp,
    category: '投资理财',
    badge: '官方',
  },
  {
    id: 'financial-report',
    name: '财报解读',
    description: '解析上市公司财报，提炼关键财务指标和经营亮点',
    icon: FileSpreadsheet,
    category: '投资理财',
    badge: '官方',
  },
  {
    id: 'fund-analysis',
    name: '基金分析',
    description: '分析基金持仓、收益和风险，辅助基金筛选',
    icon: BarChart3,
    category: '投资理财',
    badge: '官方',
  },
  {
    id: 'macro-econ',
    name: '宏观经济解读',
    description: '解读宏观经济数据，分析对市场的影响',
    icon: Globe,
    category: '投资理财',
    badge: '官方',
  },

  // 数据分析
  {
    id: 'data-analysis',
    name: '数据分析',
    description: '对上传的表格、数据集进行统计分析与洞察提取',
    icon: BarChart3,
    category: '数据分析',
    badge: '官方',
  },
  {
    id: 'data-viz',
    name: '数据可视化',
    description: '将数据转化为折线图、柱状图、饼图等可视化图表',
    icon: LineChart,
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
    id: 'report-builder',
    name: '报表生成',
    description: '自动生成日报、周报、月报，支持数据模板',
    icon: FileSpreadsheet,
    category: '数据分析',
    badge: '官方',
  },

  // 方案写作
  {
    id: 'solution-writer',
    name: '方案写作',
    description: '撰写项目方案、实施方案和解决方案文档',
    icon: Briefcase,
    category: '方案写作',
    badge: '官方',
  },
  {
    id: 'business-plan',
    name: '商业计划书',
    description: '生成完整的商业计划书，含市场分析、商业模式和财务预测',
    icon: Briefcase,
    category: '方案写作',
    badge: '官方',
  },
  {
    id: 'prd-writer',
    name: '需求文档',
    description: '撰写产品需求文档（PRD），包含功能列表和交互说明',
    icon: ClipboardList,
    category: '方案写作',
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

  // 实用工具
  {
    id: 'web-builder',
    name: '网页制作',
    description: '根据需求搭建网页应用，支持活动页、数据看板和实用工具',
    icon: Globe,
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
    id: 'calculator',
    name: '数学计算',
    description: '处理复杂公式计算、单位换算与数学推导',
    icon: Calculator,
    category: '实用工具',
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
    id: 'json-helper',
    name: 'JSON 处理',
    description: '格式化、校验和转换 JSON 数据',
    icon: FileCode2,
    category: '实用工具',
    badge: '官方',
  },
  {
    id: 'agent-builder',
    name: 'Agent 构建',
    description: '可视化搭建智能体工作流，支持工具调用和多步推理',
    icon: Bot,
    category: '实用工具',
    badge: '官方',
  },

  // 学习教育
  {
    id: 'study-plan',
    name: '开学季学习计划',
    description: '根据目标制定学期学习计划，拆分任务和里程碑',
    icon: GraduationCap,
    category: '学习教育',
    badge: '官方',
  },
  {
    id: 'paper-writer',
    name: '论文写作',
    description: '辅助撰写论文，支持文献综述、研究方法和结论整理',
    icon: FileText,
    category: '学习教育',
    badge: '官方',
  },
  {
    id: 'concept-explain',
    name: '概念解释',
    description: '用通俗语言解释专业概念，配合举例和类比',
    icon: Lightbulb,
    category: '学习教育',
    badge: '官方',
  },
  {
    id: 'quiz-generator',
    name: '习题生成',
    description: '根据知识点生成练习题，附答案和解析',
    icon: BookOpenCheck,
    category: '学习教育',
    badge: '官方',
  },
];

// ============ 页面 ============
const SkillPage: React.FC = () => {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();

  const [keyword, setKeyword] = useState('');
  const [activeCategory, setActiveCategory] = useState<string>('推荐');

  const categories = useMemo(() => {
    const counts = new Map<string, number>();
    ALL_SKILLS.forEach((s) => {
      counts.set(s.category, (counts.get(s.category) || 0) + 1);
    });
    return [
      { name: '推荐', count: ALL_SKILLS.length },
      { name: '自定义', count: 0 },
      ...Array.from(counts.entries()).map(([name, count]) => ({ name, count })),
    ];
  }, []);

  const filteredSkills = useMemo(() => {
    const kw = keyword.trim().toLowerCase();
    return ALL_SKILLS.filter((s) => {
      const matchCategory =
        activeCategory === '推荐' || s.category === activeCategory;
      const matchKeyword =
        !kw ||
        s.name.toLowerCase().includes(kw) ||
        s.description.toLowerCase().includes(kw) ||
        s.category.toLowerCase().includes(kw);
      return matchCategory && matchKeyword;
    });
  }, [keyword, activeCategory]);

  const handleUseSkill = (skill: SkillItem) => {
    console.log('use skill:', skill.id);
  };

  const handleBackToChat = () => {
    // 返回到对话页
    navigate(id ? `/chat/${id}` : '/');
  };

  return (
    // 整个页面自己管背景
    <div className="relative h-screen w-full overflow-hidden bg-[#EDF2FA] dark:bg-[#1a1a1a]">
      {/* 云背景（自己渲染） */}
      <WelcomeCloudBg />

      {/* 内容区，滚自己的 */}
      <div className="relative z-10 h-full overflow-y-auto">
        <div className="mx-auto w-full max-w-[1080px] px-6 py-8">
          {/* ===== 顶部 ===== */}
          <div className="flex items-center gap-4">
            {/* 返回按钮 */}
            <button
              type="button"
              onClick={handleBackToChat}
              className="
                inline-flex size-9 shrink-0 items-center justify-center rounded-full
                text-slate-600 hover:bg-slate-200/60
                dark:text-slate-300 dark:hover:bg-slate-800
                transition-colors
              "
              title="返回对话"
            >
              <ChevronLeft className="size-5" />
            </button>

            <h1 className="text-2xl font-semibold text-slate-900 dark:text-slate-100">
              技能
            </h1>

            <div className="relative ml-auto w-[220px]">
              <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" />
              <input
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                placeholder="搜索"
                className="
                  h-9 w-full rounded-full border border-slate-200 bg-white pl-9 pr-3
                  text-[13px] text-slate-700 outline-none
                  placeholder:text-slate-400
                  focus:border-slate-300
                  dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200
                "
              />
            </div>

            <button
              type="button"
              className="
                inline-flex h-9 shrink-0 items-center gap-1 rounded-full
                bg-slate-900 px-4 text-[13px] font-medium text-white
                transition-colors hover:bg-slate-800
                dark:bg-white dark:text-slate-900 dark:hover:bg-slate-200
              "
            >
              <Plus className="size-4" />
              <span>新建</span>
            </button>
          </div>

          {/* ===== 分类标签 ===== */}
          <div className="mt-6 flex items-center gap-1.5 overflow-x-auto [&::-webkit-scrollbar]:hidden">
            {categories.map((cat) => {
              const isActive = activeCategory === cat.name;
              return (
                <button
                  key={cat.name}
                  type="button"
                  onClick={() => setActiveCategory(cat.name)}
                  className={cn(
                    'shrink-0 rounded-full px-3.5 py-1.5 text-[13px] transition-colors',
                    isActive
                      ? 'bg-slate-900 text-white dark:bg-white dark:text-slate-900'
                      : 'text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800',
                  )}
                >
                  {cat.name}
                  {cat.count > 0 && (
                    <span
                      className={cn(
                        'ml-0.5',
                        isActive
                          ? 'text-white/70 dark:text-slate-900/60'
                          : 'text-slate-400',
                      )}
                    >
                      :{cat.count}
                    </span>
                  )}
                </button>
              );
            })}
          </div>

          {/* ===== 卡片网格 ===== */}
          <div className="mt-6 pb-8">
            {filteredSkills.length === 0 ? (
              <div className="flex h-40 items-center justify-center text-sm text-slate-400">
                没有找到匹配的技能
              </div>
            ) : (
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {filteredSkills.map((skill) => {
                  const Icon = skill.icon;
                  return (
                    <div
                      key={skill.id}
                      className="
                        group flex flex-col gap-3 rounded-2xl
                        border border-slate-200 bg-white p-4
                        transition-all
                        hover:border-slate-300 hover:shadow-[0_4px_16px_rgba(15,23,42,0.06)]
                        dark:border-slate-800 dark:bg-slate-900
                        dark:hover:border-slate-700
                      "
                    >
                      <div className="flex items-center gap-3">
                        <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-200">
                          <Icon className="size-5" strokeWidth={2} />
                        </span>

                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-1.5 min-w-0">
                            <span className="truncate text-[14px] font-medium text-slate-900 dark:text-slate-100">
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
                          <div className="mt-0.5 text-[11px] text-slate-400">
                            {skill.category}
                          </div>
                        </div>
                      </div>

                      <p className="line-clamp-2 min-h-[40px] text-[12.5px] leading-5 text-slate-500 dark:text-slate-400">
                        {skill.description}
                      </p>

                      <div className="mt-auto flex justify-end">
                        <button
                          type="button"
                          onClick={() => handleUseSkill(skill)}
                          className="
                            inline-flex h-7 items-center rounded-full
                            border border-slate-200 bg-white px-3
                            text-[12px] text-slate-700
                            transition-colors
                            hover:border-slate-300 hover:bg-slate-50
                            dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200
                            dark:hover:bg-slate-800
                          "
                        >
                          使用
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default SkillPage;
