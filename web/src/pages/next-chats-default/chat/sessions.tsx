import { MoreButton } from '@/components/more-button';
import { PageHeader } from '@/components/page-header';
import { RAGFlowAvatar } from '@/components/ragflow-avatar';
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
} from '@/components/ui/breadcrumb';
import { Card, CardContent } from '@/components/ui/card';
import { SearchInput } from '@/components/ui/input';
import { useSetModalState } from '@/hooks/common-hooks';
import { useNavigatePage } from '@/hooks/logic-hooks/navigate-hooks';
import {
  useFetchDialog,
  useGetChatSearchParams,
} from '@/hooks/use-chat-request';
import { cn } from '@/lib/utils';
import { Tooltip } from 'antd';
import {
  ChevronDown,
  ChevronUp,
  PanelLeftClose,
  PanelRightClose,
} from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useHandleClickConversationCard } from '../hooks/use-click-card';
import { useSelectDerivedConversationList } from '../hooks/use-select-conversation-list';
import { ConversationDropdown } from './conversation-dropdown';

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
  toolbar?: ReactNode;
};
export function Sessions({
  hasSingleChatBox,
  handleConversationCardClick,
  switchSettingVisible,
  toolbar,
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

  const [conversationCollapsed, setConversationCollapsed] = useState(false);
  if (!visible) {
    return (
      <aside
        className="
        w-[40px] shrink-0
        bg-[#F7FBF9] dark:bg-zinc-950
        border-r border-emerald-100/80 dark:border-emerald-950/70
        flex flex-col items-center
      "
      >
        <button
          type="button"
          onClick={switchVisible}
          className="
          mt-[76px]
          inline-flex size-8 items-center justify-center
          rounded-md
          text-gray-500 dark:text-gray-400
          hover:text-emerald-700 dark:hover:text-emerald-300
          hover:bg-emerald-50 dark:hover:bg-emerald-950/50
          transition-colors
        "
        >
          <PanelRightClose className="size-4" />
        </button>
      </aside>
    );
  }
  return (
    <section
      className="
      pt-1 px-4 w-[266px] flex flex-col
      bg-white/35 dark:bg-zinc-950/35
      backdrop-blur-xl
      border-r border-emerald-100/70 dark:border-emerald-950/60
    "
    >
      {/* ===== Breadcrumb ===== */}
      <PageHeader>
        <Breadcrumb>
          <BreadcrumbList className="!items-start">
            <BreadcrumbItem>
              <BreadcrumbLink
                onClick={navigateToChatList}
                className="group relative inline-flex items-center"
              >
                <span
                  className="
                  text-2xl font-semibold
                  text-[#064E3B]
                  cursor-pointer
                  transition-colors duration-200
                  group-hover:text-[#047857]
                "
                >
                  {t('chat.chat')}
                </span>

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
                "
                >
                  点击返回导航页面
                </span>
              </BreadcrumbLink>
            </BreadcrumbItem>
          </BreadcrumbList>
        </Breadcrumb>
      </PageHeader>

      {/* ===== Header ===== */}
      <div className="flex items-center justify-between mt-6 pr-5">
        <div className="flex gap-3 items-center min-w-0">
          <RAGFlowAvatar
            avatar={data.icon}
            name={data.name}
            className="size-8"
          />
          <span className="flex-1 truncate text-gray-900 dark:text-white">
            {data.name}
          </span>
        </div>

        <PanelLeftClose
          className="cursor-pointer size-4 text-gray-500 dark:text-gray-400 hover:text-black dark:hover:text-white"
          onClick={switchVisible}
        />
      </div>

      {/* ===== Knowledge Base Toolbar ===== */}
      {toolbar && <div className="mt-4 w-full">{toolbar}</div>}

      {/* ===== New Chat Button ===== */}
      <div className="flex flex-col gap-2 mb-0 pt-3 w-full">
        <button
          type="button"
          onClick={addTemporaryConversation}
          className="
              flex h-[35px] w-full items-center justify-start gap-2
              rounded-md
              bg-transparent
              px-3
              text-sm font-medium
              text-gray-700 dark:text-gray-300
              shadow-none
              transition-all duration-300

              hover:bg-white/70 dark:hover:bg-white/10
              hover:text-blue-600 dark:hover:text-blue-400
              hover:shadow-[0_4px_14px_rgba(15,23,42,0.10)]
              dark:hover:shadow-[0_4px_14px_rgba(0,0,0,0.35)]

              active:scale-[0.98]
              active:bg-white/80 dark:active:bg-white/15
              active:shadow-[0_6px_18px_rgba(15,23,42,0.14)]

              focus-visible:outline-none
              focus-visible:ring-2
              focus-visible:ring-blue-200/70 dark:focus-visible:ring-blue-800/70
            "
        >
          <svg
            className="w-4 h-4"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
          <span className="text-sm font-medium">新建对话</span>
        </button>
      </div>

      {/* ===== Search ===== */}
      <div className="mb-1 pt-2 w-full">
        <div className="mb-1 pt-2 w-full">
          <SearchInput
            onChange={handleInputChange}
            value={searchString}
            placeholder="搜索历史对话"
            className="
          h-[35px] w-full
          rounded-md

          !border-none
          !bg-transparent
          !shadow-none

          px-3
          text-sm
          text-gray-700 dark:text-gray-300
          transition-all duration-300

          hover:!border-none
          hover:!bg-white/70 dark:hover:!bg-white/10
          hover:shadow-[0_4px_14px_rgba(15,23,42,0.10)]
          dark:hover:shadow-[0_4px_14px_rgba(0,0,0,0.35)]

          focus:!border-none
          focus:!shadow-none
          focus-visible:!border-none
          focus-visible:!outline-none

          focus-within:!border-none
          focus-within:!bg-white/80 dark:focus-within:!bg-white/10
          focus-within:shadow-[0_4px_14px_rgba(15,23,42,0.12)]
          focus-within:ring-2
          focus-within:ring-blue-200/70 dark:focus-within:ring-blue-800/70

          placeholder:text-gray-400
        "
          />
        </div>
      </div>

      {/* ===== Conversation Title + Manage ===== */}
      <div className="flex items-center justify-between mb-2 mt-4 px-1 w-full">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-sm font-medium text-gray-800 dark:text-gray-200">
            {t('chat.conversations')}
          </span>

          {/* <span
            className="
              text-[11px] font-medium
              text-blue-600 dark:text-blue-400
              bg-blue-50 dark:bg-blue-950
              px-2 py-0.5
              rounded-full
              border border-blue-100 dark:border-blue-800
            "
          >
            {conversationList.length}
          </span> */}
        </div>

        <div className="flex items-center gap-1">
          {!batchMode ? (
            <button
              type="button"
              className="
                text-xs px-2 py-1 rounded-md
                text-gray-500 dark:text-gray-400
                hover:text-red-600 dark:hover:text-red-400
                hover:bg-red-50 dark:hover:bg-red-950
                transition-colors
              "
              onClick={() => {
                setBatchMode(true);
                setSelectedConversationIds([]);
                setConversationCollapsed(false); // 进入管理时自动展开
              }}
            >
              管理
            </button>
          ) : (
            <button
              type="button"
              className="
                text-xs px-2 py-1 rounded-md
                text-blue-600 dark:text-blue-400
                hover:bg-blue-50 dark:hover:bg-blue-950
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
              selectedConversationIds.length === conversationList.length
                ? '取消全选'
                : '全选'}
            </button>
          )}

          <button
            type="button"
            aria-label={conversationCollapsed ? '展开对话' : '收起对话'}
            title={conversationCollapsed ? '展开对话' : '收起对话'}
            className="
              inline-flex size-7 items-center justify-center
              rounded-md
              text-gray-400 dark:text-gray-500
              transition-all duration-200
              hover:bg-gray-100 dark:hover:bg-zinc-800
              hover:text-gray-700 dark:hover:text-gray-200
            "
            onClick={() => {
              setConversationCollapsed((prev) => !prev);
            }}
          >
            {conversationCollapsed ? (
              <ChevronDown className="size-4" />
            ) : (
              <ChevronUp className="size-4" />
            )}
          </button>
        </div>
      </div>

      {/* ===== Conversation List ===== */}

      <div
        className={cn(
          'space-y-1 overflow-auto pr-1 transition-all duration-300',
          conversationCollapsed
            ? 'max-h-0 flex-none overflow-hidden opacity-0'
            : 'flex-1 opacity-100',
        )}
      >
        {conversationList.map((x) => {
          const checked = selectedConversationIds.includes(x.id);
          const isEditing = editingConversationId === x.id;

          return (
            <Card
              key={x.id}
              onClick={
                isEditing
                  ? undefined
                  : batchMode
                    ? () => handleToggleSelectConversation(x.id)
                    : handleCardClick(x.id, x.is_new)
              }
              className={cn(
                'cursor-pointer rounded-md border-none shadow-none transition-colors',
                conversationId === x.id
                  ? 'bg-[#E8F7F3] hover:bg-[#E0F2ED] dark:bg-emerald-950/40 dark:hover:bg-emerald-950/60'
                  : 'bg-transparent hover:bg-gray-100 dark:hover:bg-zinc-800',
                {
                  '!bg-blue-50 dark:!bg-blue-950/40': batchMode && checked,
                },
              )}
            >
              <CardContent className="pl-[2em] pr-2 py-2 flex justify-between items-center group gap-2">
                <div className="flex items-center gap-2 min-w-0 flex-1">
                  {batchMode && (
                    <input
                      type="checkbox"
                      checked={checked}
                      className="
                      h-3.5 w-3.5 shrink-0
                      accent-blue-500
                      cursor-pointer
                    "
                      onClick={(e) => {
                        e.stopPropagation();
                      }}
                      onChange={() => {
                        handleToggleSelectConversation(x.id);
                      }}
                    />
                  )}

                  {isEditing ? (
                    <input
                      ref={renameInputRef}
                      value={editingConversationName}
                      className="
                      flex-1 min-w-0 h-7 px-2
                      rounded-md
                      border border-blue-500
                      bg-white dark:bg-zinc-900
                      text-sm text-gray-900 dark:text-white
                      outline-none
                    "
                      onClick={(e) => {
                        e.stopPropagation();
                      }}
                      onChange={(e) => {
                        setEditingConversationName(e.target.value);
                      }}
                      onBlur={() => {
                        handleSaveRename(x);
                      }}
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
                      <div
                        className={cn(
                          'truncate text-sm text-gray-900 dark:text-white',
                          batchMode ? 'max-w-[185px]' : 'max-w-[200px]',
                        )}
                      >
                        {x.name}
                      </div>
                    </Tooltip>
                  )}
                </div>

                {!batchMode && !isEditing && (
                  <ConversationDropdown
                    conversation={x}
                    removeTemporaryConversation={removeTemporaryConversation}
                    onRename={handleStartRename}
                  >
                    <MoreButton />
                  </ConversationDropdown>
                )}
              </CardContent>
            </Card>
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

      {/* ===== Footer ===== */}
      {/* <div className="py-2">
        <Button
          className="w-full"
          type="button"
          onClick={switchSettingVisible}
          disabled={!hasSingleChatBox}
          variant="outline"
        >
          {t('chat.chatSetting')}
        </Button>
      </div> */}
    </section>
  );
}
