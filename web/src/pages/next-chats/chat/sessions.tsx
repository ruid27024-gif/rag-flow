import { MoreButton } from '@/components/more-button';
import { PageHeader } from '@/components/page-header';
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
} from '@/components/ui/breadcrumb';
import { SearchInput } from '@/components/ui/input';
import { useSetModalState } from '@/hooks/common-hooks';
import { useNavigatePage } from '@/hooks/logic-hooks/navigate-hooks';
import {
  useFetchDialog,
  useGetChatSearchParams,
} from '@/hooks/use-chat-request';
import { cn } from '@/lib/utils';
import { Tooltip } from 'antd';
import { PanelLeftClose, PanelRightClose } from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useHandleClickConversationCard } from '../hooks/use-click-card';
import { useSelectDerivedConversationList } from '../hooks/use-select-conversation-list';
import { ConversationDropdown } from './conversation-dropdown';

import { Button } from '@/components/ui/button';
import {
  CheckSquare,
  ListFilter,
  Puzzle,
  Search,
  SettingsIcon,
  Square,
} from 'lucide-react';

import {
  useRemoveConversation,
  useRenameConversation,
} from '@/hooks/use-chat-request';

import { ConfirmDeleteDialog } from '@/components/confirm-delete-dialog';
import { IConversation } from '@/interfaces/database/chat';

type SessionProps = Pick<
  ReturnType<typeof useHandleClickConversationCard>,
  'handleConversationCardClick'
> & {
  switchSettingVisible(): void;
  hasSingleChatBox: boolean;
  isWelcomePage: boolean; // 👈 必传
  agentMod?: boolean;
  onOpenSkill?: () => void;
  onExitSkill?: () => void; // 👈 加回来
  skillActive?: boolean; // 👈 加回来
};
export function Sessions({
  hasSingleChatBox,
  handleConversationCardClick,
  switchSettingVisible,
  isWelcomePage = true, // 👈 新增
  agentMod = false,
  onOpenSkill,
  onExitSkill, // 👈 加回来
  skillActive = false, // 👈 加回来
}: SessionProps) {
  const { t } = useTranslation();
  const {
    list: conversationList,
    addTemporaryConversation,
    removeTemporaryConversation,
    handleInputChange,
    searchString,
  } = useSelectDerivedConversationList();
  const { data } = useFetchDialog();
  const { visible, switchVisible } = useSetModalState(true);

  const handleCardClick = useCallback(
    (conversationId: string, isNew: boolean) => () => {
      handleConversationCardClick(conversationId, isNew);
    },
    [handleConversationCardClick],
  );

  const { conversationId } = useGetChatSearchParams();
  const { navigateToChatList } = useNavigatePage();
  const { renameConversation } = useRenameConversation();

  const [editingConversationId, setEditingConversationId] =
    useState<string>('');
  const [editingConversationName, setEditingConversationName] = useState('');
  const renameInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (!editingConversationId) return;

    requestAnimationFrame(() => {
      const input = renameInputRef.current;
      if (!input) return;

      const length = input.value.length;

      input.focus();

      // 光标放到整个名字最后
      input.setSelectionRange(length, length);

      // 输入框滚动到最右侧，显示最后部分
      input.scrollLeft = input.scrollWidth;
    });
  }, [editingConversationId]);
  const handleStartRename = useCallback((conversation: IConversation) => {
    setEditingConversationId(conversation.id);
    setEditingConversationName(conversation.name || '');
  }, []);

  const handleCancelRename = useCallback(() => {
    setEditingConversationId('');
    setEditingConversationName('');
  }, []);

  const handleSaveRename = useCallback(
    async (conversation: IConversation) => {
      const name = editingConversationName.trim();

      if (!name) {
        handleCancelRename();
        return;
      }

      if (name === conversation.name) {
        handleCancelRename();
        return;
      }

      const code = await renameConversation({
        conversationId: conversation.id,
        name,
      });

      if (code === 0) {
        handleCancelRename();
      }
    },
    [editingConversationName, renameConversation, handleCancelRename],
  );

  const { removeConversation, loading: removeLoading } =
    useRemoveConversation();

  const [batchMode, setBatchMode] = useState(false);
  const [selectedConversationIds, setSelectedConversationIds] = useState<
    string[]
  >([]);

  const handleToggleSelectConversation = useCallback((id: string) => {
    setSelectedConversationIds((prev) => {
      if (prev.includes(id)) {
        return prev.filter((x) => x !== id);
      }

      return [...prev, id];
    });
  }, []);

  const handleSelectAll = useCallback(() => {
    setSelectedConversationIds(conversationList.map((x) => x.id));
  }, [conversationList]);

  const handleClearSelected = useCallback(() => {
    setSelectedConversationIds([]);
  }, []);

  const handleBatchDelete = useCallback(async () => {
    if (selectedConversationIds.length === 0) {
      return;
    }

    const code = await removeConversation(selectedConversationIds);

    if (code === 0) {
      setSelectedConversationIds([]);
      setBatchMode(false);
    }
  }, [removeConversation, selectedConversationIds]);

  const [showSearch, setShowSearch] = useState(false);

  // if (!visible) {
  //   return (
  //     <aside
  //       className="
  //       w-[40px] shrink-0
  //       bg-[#F6FAFF] dark:bg-slate-950
  //       border-r border-sky-100/80 dark:border-slate-800
  //       flex flex-col items-center
  //     "
  //     >
  //       <button
  //         type="button"
  //         onClick={switchVisible}
  //         className="
  //         mt-[76px]
  //         inline-flex size-8 items-center justify-center
  //         rounded-md
  //         text-slate-500 dark:text-slate-400
  //         hover:text-sky-700 dark:hover:text-sky-300
  //         hover:bg-sky-50 dark:hover:bg-sky-950/50
  //         transition-colors
  //       "
  //       >
  //         <PanelRightClose className="size-4" />
  //       </button>
  //     </aside>
  //   );
  // }
  if (!visible) {
    return (
      <aside
        className="
        w-[40px] shrink-0
        bg-transparent          {/* 👈 背景透明，去掉所有底色 */}
        flex flex-col items-center
      "
      >
        <button
          type="button"
          onClick={switchVisible}
          className="
          mt-3                   {/* 👈 位置跟展开态对齐 */}
          inline-flex size-8 items-center justify-center
          rounded-lg
          text-gray-500 dark:text-gray-400
          hover:text-gray-900 dark:hover:text-white
          hover:bg-gray-200/60 dark:hover:bg-zinc-800
          transition-colors
        "
        >
          {/* 如果 PanelLeftOpen 报错，就用你项目里已有的 PanelRightClose 或 Menu */}
          <PanelRightClose className="size-5" /> {/* 👈 统一 size-5 */}
        </button>
      </aside>
    );
  }
  return (
    <section
      className={cn(
        'relative pt-3 px-3 w-[260px] flex flex-col',
        isWelcomePage
          ? 'bg-gradient-to-b from-[#9FB3D1] via-[#B7C5DE] to-[#D4DDE9] dark:bg-none dark:bg-transparent border-r border-[#B8C6D6]/40 dark:border-[#2F3E52]/60 backdrop-blur-sm'
          : 'bg-[#f9f9f9] dark:bg-transparent border-r border-gray-200/60 dark:border-zinc-800',
      )}
    >
      <PageHeader>
        <div className="flex items-center justify-between w-full gap-2">
          {/* 左边：图标 + 标题 */}
          <Breadcrumb className="min-w-0 flex-1">
            <BreadcrumbList className="!flex-nowrap !items-center min-w-0">
              <BreadcrumbItem className="min-w-0 flex-1">
                <BreadcrumbLink
                  onClick={navigateToChatList}
                  className="group relative flex items-center gap-1 min-w-0 w-full"
                >
                  {/* 图标 —— 大小不变 */}
                  <img
                    src="/hf_pic.png"
                    alt=""
                    className="
                h-10 w-10
                object-contain
                shrink-0
                -ml-1
                drop-shadow-[0_2px_4px_rgba(16,185,129,0.18)]
              "
                  />

                  {/* 标题 —— 一行省略，hover 显示完整 */}
                  <span
                    className="
                text-2xl font-semibold
                text-[#064E3B]
                cursor-pointer
                truncate min-w-0
                transition-colors duration-200
                group-hover:text-[#047857]
              "
                  >
                    {data.name}
                  </span>

                  {/* Tooltip —— hover 显示完整名称 */}
                  <span
                    className="
                absolute left-0 top-full mt-2
                rounded-md
                bg-white px-3 py-1.5
                text-xs text-[#064E3B]
                border border-emerald-100
                shadow-sm
                opacity-0
                translate-y-1
                transition-all duration-200
                pointer-events-none
                group-hover:opacity-100
                group-hover:translate-y-0
                z-50
                max-w-[260px]
                break-all
              "
                  >
                    {data.name}
                  </span>
                </BreadcrumbLink>
              </BreadcrumbItem>
            </BreadcrumbList>
          </Breadcrumb>

          {/* 右边：收起按钮 */}
          <button
            type="button"
            onClick={switchVisible}
            className="
        inline-flex size-8 shrink-0 items-center justify-center
        rounded-lg
        text-gray-500 dark:text-gray-400
        hover:text-gray-900 dark:hover:text-white
        hover:bg-gray-200/60 dark:hover:bg-zinc-800
        transition-colors
      "
            title="收起侧边栏"
          >
            <PanelLeftClose className="size-5" />
          </button>
        </div>
      </PageHeader>

      {/* ===== Header ===== */}
      {/* <div className="flex items-center gap-2.5 mt-4 px-1 min-w-0">
        <RAGFlowAvatar
          avatar={data.icon}
          name={data.name}
          className="size-8 shrink-0"
        />
        <div className="flex flex-col min-w-0">
          <span className="truncate text-sm font-medium text-gray-800 dark:text-gray-100">
            {data.name}
          </span>
          <span className="text-[11px] text-gray-400 dark:text-gray-500">
            智能助手
          </span>
        </div>
      </div> */}

      {/* ===== New Chat Button ===== */}
      <div className="pt-3 w-full">
        <button
          onClick={() => {
            onExitSkill?.(); // 👈 加回来
            addTemporaryConversation();
          }}
          className="
      flex items-center justify-center
      h-11 w-full px-4
      rounded-full
      bg-white dark:bg-zinc-800
      border border-gray-200/70 dark:border-zinc-700/70
      shadow-[0_2px_8px_rgba(0,0,0,0.04)]  /* 更高级的柔和阴影 */
      hover:shadow-[0_4px_12px_rgba(0,0,0,0.08)]
      hover:bg-gray-50 dark:hover:bg-zinc-700/80
      active:scale-[0.98]
      transition-all duration-150
    "
        >
          <div className="flex items-center gap-2.5">
            {/* 带圈的加号图标 */}
            <span
              className="
        inline-flex size-5 items-center justify-center
        rounded-full border border-gray-400/80 dark:border-gray-500
        text-gray-600 dark:text-gray-300
      "
            >
              <svg
                className="size-3"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.5" /* 线加粗一点 */
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M12 5v14M5 12h14" />
              </svg>
            </span>

            {/* 字体大气的关键：字号15px、加重字重、颜色加深 */}
            <span className="text-[15px] font-medium tracking-wide text-gray-800 dark:text-gray-100">
              开启新对话
            </span>
          </div>
        </button>
      </div>

      {/* 👇 新增：agent 模式专属按钮 */}
      {/* 👇 agent 模式专属按钮：技能 */}
      {agentMod && (
        <div className="pt-2 w-full">
          <button
            type="button"
            onClick={onOpenSkill}
            className={cn(
              'group flex w-full items-center gap-2 px-3 py-2.5 rounded-lg transition-colors',
              skillActive
                ? 'bg-blue-50/80 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 font-medium'
                : 'text-gray-800 dark:text-gray-200 hover:bg-gray-200/50 dark:hover:bg-zinc-800/50',
            )}
          >
            <Puzzle
              className={cn(
                'size-4 shrink-0',
                skillActive
                  ? 'text-blue-600 dark:text-blue-400'
                  : 'text-gray-600 dark:text-gray-300',
              )}
              strokeWidth={2}
            />
            <span className="truncate text-[14px] tracking-wide">技能</span>
          </button>
        </div>
      )}

      {/* ===== Search ===== */}
      {showSearch && (
        <div className="mt-3">
          <SearchInput
            onChange={handleInputChange}
            value={searchString}
            placeholder="搜索历史对话"
            className="
        !border-transparent
        !bg-gray-100 dark:!bg-zinc-800
        !rounded-lg
        !h-9
        focus:!ring-1 focus:!ring-gray-300
      "
          />
        </div>
      )}

      {/* ===== Conversation Title + Manage ===== */}
      <div className="flex items-center justify-between mb-1 mt-4 px-3 pr-4 w-full">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-[14px] font-semibold text-gray-700 dark:text-gray-200">
            {t('chat.conversations')}
          </span>
          <span className="text-[12px] font-medium text-gray-500 dark:text-gray-400">
            {conversationList.length}
          </span>
        </div>

        <div className="flex items-center gap-1">
          {/* 控制搜索框显隐 */}
          <button
            type="button"
            title="搜索"
            className="
    inline-flex items-center justify-center
    p-1.5 rounded-md
    text-gray-600 dark:text-gray-300
    hover:text-gray-900 dark:hover:text-white
    hover:bg-gray-200/70 dark:hover:bg-zinc-800
    transition-colors
  "
            onClick={() => setShowSearch((v) => !v)}
          >
            <Search className="size-4" strokeWidth={2.2} />
          </button>

          {!batchMode ? (
            <button
              type="button"
              title="管理"
              className="
    inline-flex items-center justify-center
    p-1.5 rounded-md
    text-gray-600 dark:text-gray-300
    hover:text-gray-900 dark:hover:text-white
    hover:bg-gray-200/70 dark:hover:bg-zinc-800
    transition-colors
  "
              onClick={() => {
                setBatchMode(true);
                setSelectedConversationIds([]);
              }}
            >
              <ListFilter className="size-4" strokeWidth={2.2} />
            </button>
          ) : (
            <button
              type="button"
              className="
          inline-flex items-center justify-center
          p-1 rounded-md
          text-gray-400 dark:text-gray-500
          hover:text-gray-800 dark:hover:text-gray-200
          hover:bg-gray-200/60 dark:hover:bg-zinc-800/80
          transition-colors
        "
              onClick={() => {
                if (
                  conversationList.length > 0 &&
                  selectedConversationIds.length === conversationList.length
                ) {
                  handleClearSelected();
                } else {
                  handleSelectAll();
                }
              }}
            >
              {conversationList.length > 0 &&
              selectedConversationIds.length === conversationList.length ? (
                <CheckSquare className="size-4" />
              ) : (
                <Square className="size-4" />
              )}
            </button>
          )}
        </div>
      </div>
      {/* ===== Conversation List ===== */}
      {/* ===== Conversation List ===== */}
      <div className="space-y-1 flex-1 overflow-y-auto pr-1 [&::-webkit-scrollbar]:w-1 [&::-webkit-scrollbar-thumb]:bg-gray-300 [&::-webkit-scrollbar-thumb]:rounded-full">
        {conversationList.map((x) => {
          const checked = selectedConversationIds.includes(x.id);
          const isEditing = editingConversationId === x.id;
          const isActive = !skillActive && conversationId === x.id;

          return (
            <div
              key={x.id}
              onClick={
                isEditing
                  ? undefined
                  : batchMode
                    ? () => handleToggleSelectConversation(x.id)
                    : handleCardClick(x.id, x.is_new)
              }
              className={cn(
                // 1. 增大内边距，改为 py-2.5，增加间距 space-y-1
                'group flex items-center justify-between px-3 py-2.5 rounded-lg cursor-pointer transition-colors',
                // 2. 优化选中态和默认态的颜色，使用更清晰的 text-gray-800
                isActive
                  ? 'bg-blue-50/80 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 font-medium'
                  : 'text-gray-800 dark:text-gray-200 hover:bg-gray-200/50 dark:hover:bg-zinc-800/50',
                {
                  '!bg-blue-50/80 dark:!bg-blue-900/30': batchMode && checked,
                },
              )}
            >
              <div className="flex items-center gap-2 min-w-0 flex-1">
                {batchMode && (
                  <input
                    type="checkbox"
                    checked={checked}
                    className="size-4 shrink-0 accent-blue-500 rounded cursor-pointer"
                    onClick={(e) => e.stopPropagation()}
                    onChange={() => handleToggleSelectConversation(x.id)}
                  />
                )}

                {isEditing ? (
                  <input
                    ref={renameInputRef}
                    value={editingConversationName}
                    // 输入框也同步放大字号
                    className="flex-1 min-w-0 h-7 px-2 rounded bg-white dark:bg-zinc-900 text-[14px] text-gray-900 dark:text-white outline-none ring-1 ring-blue-500"
                    onClick={(e) => e.stopPropagation()}
                    onChange={(e) => setEditingConversationName(e.target.value)}
                    onBlur={() => handleSaveRename(x)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault();
                        handleSaveRename(x);
                      }
                      if (e.key === 'Escape') {
                        e.preventDefault();
                        handleCancelRename();
                      }
                    }}
                  />
                ) : (
                  <Tooltip title={x.name} placement="topLeft">
                    {/* 3. 字号从 13px 提升到 14px，增加右边距防止贴到按钮 */}
                    <div className="truncate text-[14px] tracking-wide pr-2">
                      {x.name}
                    </div>
                  </Tooltip>
                )}
              </div>

              {!batchMode && !isEditing && (
                <div
                  className={cn(
                    'shrink-0 transition-opacity',
                    isActive
                      ? 'opacity-100'
                      : 'opacity-0 group-hover:opacity-100',
                  )}
                >
                  <ConversationDropdown
                    conversation={x}
                    removeTemporaryConversation={removeTemporaryConversation}
                    onRename={handleStartRename}
                  >
                    {/* 4. 给 MoreButton 外层套一个带 hover 背景的容器，模拟 DeepSeek 的交互质感 */}
                    <div className="p-1 rounded-md hover:bg-gray-200/80 dark:hover:bg-zinc-700 transition-colors flex items-center justify-center">
                      <MoreButton className="size-4.5 text-gray-500 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-200" />
                    </div>
                  </ConversationDropdown>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* ===== Batch Delete Bar ===== */}
      {batchMode && (
        <div
          className="
          sticky bottom-0 z-10
          mt-2 px-2 py-2
          bg-white/90 dark:bg-zinc-950/90
          backdrop-blur
          border-t border-gray-200 dark:border-zinc-800
        "
        >
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-500 dark:text-gray-400">
              已选择 {selectedConversationIds.length} 项
            </span>

            <div className="flex items-center gap-2">
              <ConfirmDeleteDialog onOk={handleBatchDelete}>
                <button
                  type="button"
                  disabled={
                    selectedConversationIds.length === 0 || removeLoading
                  }
                  className={cn(
                    `
                    text-xs px-1 py-1
                    text-red-600 dark:text-red-400
                    hover:text-red-700 dark:hover:text-red-300
                    bg-transparent
                    transition-colors
                  `,
                    {
                      'opacity-40 cursor-not-allowed':
                        selectedConversationIds.length === 0 || removeLoading,
                    },
                  )}
                >
                  删除
                </button>
              </ConfirmDeleteDialog>

              <button
                type="button"
                className="
                text-xs px-2.5 py-1.5 rounded-md
                text-gray-600 dark:text-gray-300
                hover:bg-gray-100 dark:hover:bg-zinc-800
              "
                onClick={() => {
                  setBatchMode(false);
                  setSelectedConversationIds([]);
                }}
              >
                退出
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="p-4 mt-auto border-t border-gray-100 dark:border-gray-800">
        <Button
          type="button"
          onClick={switchSettingVisible}
          disabled={!hasSingleChatBox}
          variant="ghost" // 换成 ghost 幽灵按钮
          className="w-full justify-start gap-3 rounded-lg px-3 text-gray-600 hover:bg-gray-100 hover:text-gray-900 dark:text-gray-400 dark:hover:bg-gray-800"
        >
          {/* 假设你用的 lucide-react，可以引入一个 Settings 图标 */}
          <SettingsIcon className="h-4 w-4" />
          <span className="text-sm">{t('chat.chatSetting')}</span>
        </Button>
      </div>
    </section>
  );
}
