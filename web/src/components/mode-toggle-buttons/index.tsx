import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import {
  Bot,
  FileText,
  HelpCircle,
  Layers3,
  MessageSquareWarning,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';
import * as React from 'react';

export interface ModeToggleButtonsProps {
  reasoning: boolean;
  agentMod: boolean;
  projectCompliance?: boolean;
  experimentReport?: boolean;
  customerComplaint?: boolean;
  onEnableDeepReasoning?: () => void;
  onEnableMultiKbReasoning?: () => void;
  onEnableAgent?: () => void;
  onEnableProjectCompliance?: () => void | Promise<void>;
  onEnableExperimentReport?: () => void | Promise<void>;
  onEnableCustomerComplaint?: () => void | Promise<void>;
  disabled?: boolean;
  className?: string;
}

const HELP_ITEMS = [
  {
    icon: Layers3,
    name: '多库并行',
    desc: '多个知识库同时检索，精确度高、速度快',
    color: 'text-emerald-400',
  },
  {
    icon: Sparkles,
    name: '深度推理',
    desc: '海量查询、速度较慢，适合复杂推理问题',
    color: 'text-blue-400',
  },
  {
    icon: Bot,
    name: 'Agent Skills',
    desc: 'Agent 模式，自动调用工具链完成任务',
    color: 'text-purple-400',
  },
  {
    icon: ShieldCheck,
    name: '合规申报',
    desc: '辅助项目申报与合规性审查',
    color: 'text-orange-400',
  },
  {
    icon: FileText,
    name: '实验报告',
    desc: '根据上下文自动生成实验报告',
    color: 'text-cyan-400',
  },
  {
    icon: MessageSquareWarning,
    name: '客诉问题',
    desc: '基于知识库分析客户投诉并给出处置建议',
    color: 'text-rose-400',
  },
];

export function ModeToggleButtons({
  reasoning,
  agentMod,
  projectCompliance,
  experimentReport,
  customerComplaint,
  onEnableDeepReasoning,
  onEnableMultiKbReasoning,
  onEnableAgent,
  onEnableProjectCompliance,
  onEnableExperimentReport,
  onEnableCustomerComplaint,
  disabled,
  className,
}: ModeToggleButtonsProps) {
  const [showHelp, setShowHelp] = React.useState(false);

  const isMultiKbMode =
    !reasoning &&
    !agentMod &&
    !projectCompliance &&
    !experimentReport &&
    !customerComplaint;
  const isDeepReasoningMode =
    reasoning &&
    !agentMod &&
    !projectCompliance &&
    !experimentReport &&
    !customerComplaint;
  const isAgentMode =
    !reasoning &&
    agentMod &&
    !projectCompliance &&
    !experimentReport &&
    !customerComplaint;
  const isProjectComplianceMode =
    !reasoning &&
    !agentMod &&
    projectCompliance &&
    !experimentReport &&
    !customerComplaint;
  const isExperimentReportMode =
    !reasoning &&
    !agentMod &&
    !projectCompliance &&
    experimentReport &&
    !customerComplaint;
  const isCustomerComplaintMode =
    !reasoning &&
    !agentMod &&
    !projectCompliance &&
    !experimentReport &&
    customerComplaint;

  const stop = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  /**
   * 基础（未选中）：灰边框 + 灰字
   * hover：边框/文字略加深
   */
  const baseBtn = cn(
    'h-9 gap-1.5 rounded-lg border px-3 text-sm font-normal shadow-none transition-colors',
    'border-gray-200 bg-white text-gray-500',
    'hover:border-gray-300 hover:text-gray-700 hover:bg-gray-50',
    'dark:border-gray-700 dark:bg-transparent dark:text-gray-400',
    'dark:hover:border-gray-500 dark:hover:text-gray-200 dark:hover:bg-transparent',
    'disabled:pointer-events-none disabled:opacity-50',
  );

  /**
   * 选中态：深边框 + 深字 + 加粗（纯灰度，无彩色）
   */
  const activeBtn = cn(
    'border-gray-400 bg-white text-gray-900 font-medium',
    'hover:border-gray-500 hover:text-gray-900 hover:bg-gray-50',
    'dark:border-gray-400 dark:bg-transparent dark:text-gray-100',
    'dark:hover:border-gray-300 dark:hover:text-white dark:hover:bg-transparent',
  );

  return (
    <div className={cn('flex flex-wrap items-center gap-2', className)}>
      <Button
        type="button"
        title="精确度高，速度快"
        size="sm"
        variant="outline"
        onClick={(e) => {
          stop(e);
          onEnableMultiKbReasoning?.();
        }}
        disabled={disabled}
        className={cn(baseBtn, isMultiKbMode && activeBtn)}
      >
        <Layers3 className="h-4 w-4 shrink-0" />
        多库并行
      </Button>

      <Button
        type="button"
        title="海量查询，速度慢"
        size="sm"
        variant="outline"
        onClick={(e) => {
          stop(e);
          onEnableDeepReasoning?.();
        }}
        disabled={disabled}
        className={cn(baseBtn, isDeepReasoningMode && activeBtn)}
      >
        <Sparkles className="h-4 w-4 shrink-0" />
        深度推理
      </Button>

      <Button
        type="button"
        title="Agent 模式"
        size="sm"
        variant="outline"
        onClick={(e) => {
          stop(e);
          onEnableAgent?.();
        }}
        disabled={disabled}
        className={cn(baseBtn, isAgentMode && activeBtn)}
      >
        <Bot className="h-4 w-4 shrink-0" />
        Agent Skills
      </Button>

      <Button
        type="button"
        title="辅助项目申报与合规审查"
        size="sm"
        variant="outline"
        onClick={(e) => {
          stop(e);
          onEnableProjectCompliance?.();
        }}
        disabled={disabled}
        className={cn(baseBtn, isProjectComplianceMode && activeBtn)}
      >
        <ShieldCheck className="h-4 w-4 shrink-0" />
        合规申报
      </Button>

      <Button
        type="button"
        title="自动生成实验报告"
        size="sm"
        variant="outline"
        onClick={(e) => {
          stop(e);
          onEnableExperimentReport?.();
        }}
        disabled={disabled}
        className={cn(baseBtn, isExperimentReportMode && activeBtn)}
      >
        <FileText className="h-4 w-4 shrink-0" />
        实验报告
      </Button>

      <Button
        type="button"
        title="基于知识库分析客户投诉"
        size="sm"
        variant="outline"
        onClick={(e) => {
          stop(e);
          onEnableCustomerComplaint?.();
        }}
        disabled={disabled}
        className={cn(baseBtn, isCustomerComplaintMode && activeBtn)}
      >
        <MessageSquareWarning className="h-4 w-4 shrink-0" />
        客诉问题
      </Button>

      {/* 帮助 */}
      <div
        className="relative"
        onMouseEnter={() => setShowHelp(true)}
        onMouseLeave={() => setShowHelp(false)}
      >
        <Button
          type="button"
          size="sm"
          variant="outline"
          className={cn(baseBtn, 'cursor-help')}
        >
          <HelpCircle className="h-4 w-4 shrink-0" />
          帮助
        </Button>

        {showHelp && (
          <div
            className="
              absolute top-full right-0 z-50 mt-3 w-[340px]
              animate-in fade-in-0 zoom-in-95 duration-150
            "
          >
            <div
              className="
                absolute right-6 bottom-full h-2 w-2 translate-y-1/2
                rotate-45 bg-gray-900
              "
            />

            <div
              className="
                relative rounded-xl bg-gray-900 p-3 text-xs text-gray-200
                shadow-2xl ring-1 ring-black/20
                dark:bg-gray-900 dark:ring-white/10
              "
            >
              <div className="mb-2 px-1 text-[13px] font-semibold text-white">
                功能说明
              </div>

              <div className="border-t border-gray-700/70 pt-2 dark:border-gray-800" />

              <div className="space-y-2.5">
                {HELP_ITEMS.map((item) => {
                  const Icon = item.icon;
                  return (
                    <div
                      key={item.name}
                      className="flex items-start gap-2.5 px-1"
                    >
                      <span className={cn('mt-[3px] shrink-0', item.color)}>
                        <Icon className="h-3.5 w-3.5" />
                      </span>
                      <div className="min-w-0 flex-1 leading-snug">
                        <div className={cn('font-medium', item.color)}>
                          {item.name}
                        </div>
                        <div className="mt-0.5 text-gray-400 dark:text-gray-500">
                          {item.desc}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
