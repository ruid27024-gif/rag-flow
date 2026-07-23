import { MoreButton } from '@/components/more-button';
import { PageHeader } from '@/components/page-header';
import { RAGFlowAvatar } from '@/components/ragflow-avatar';
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
} from '@/components/ui/breadcrumb';
import { Button } from '@/components/ui/button';
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
import { PanelLeftClose, PanelRightClose } from 'lucide-react';
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
> & { switchSettingVisible(): void; hasSingleChatBox: boolean };
export function Sessions({
  hasSingleChatBox,
  handleConversationCardClick,
  switchSettingVisible,
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

  if (!visible) {
    return (
      <aside
        className="
    w-[40px] shrink-0
    flex flex-col items-center

    bg-white/15
    backdrop-blur-xl
    border-r border-sky-200/50

    dark:bg-transparent
    dark:border-zinc-800/60
    dark:backdrop-blur-none
  "
      >
        <button
          type="button"
          onClick={switchVisible}
          className="
    mt-[76px]
    inline-flex size-8 items-center justify-center
    rounded-md

    text-sky-600
    hover:text-sky-800
    hover:bg-white/35

    dark:text-slate-400
    dark:hover:text-sky-300
    dark:hover:bg-sky-950/30

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
                className="group relative inline-flex items-center cursor-pointer"
              >
                <img
                  src="/hengyue.png"
                  alt="恒丰纸业"
                  className="
    h-10
    w-auto
    object-contain
    bg-transparent
    transition-opacity duration-200
    group-hover:opacity-85
  "
                />

                <span
                  className="
              absolute left-0 top-full mt-2
              whitespace-nowrap
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

      {/* ===== New Chat Button ===== */}
      <div className="flex flex-col gap-2 mb-0 pt-3 w-full">
        <button
          onClick={addTemporaryConversation}
          className="
          flex items-center justify-center gap-2
          h-[35px] w-full px-4
          rounded-md
          border border-gray-200 dark:border-zinc-700
          bg-gray-100 dark:bg-zinc-800
          text-gray-700 dark:text-gray-300
          hover:bg-blue-50 dark:hover:bg-blue-950
          hover:border-blue-300 dark:hover:border-blue-700
          hover:text-blue-600 dark:hover:text-blue-400
          hover:shadow-sm
          transition-all duration-300
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
      <div className="flex flex-col gap-2 mb-1 pt-3 w-full">
        <SearchInput
          onChange={handleInputChange}
          value={searchString}
          placeholder="搜索历史对话"
        />
      </div>

      {/* ===== Conversation Title + Manage ===== */}
      <div className="flex items-center justify-between mb-2 mt-4 px-1 w-full">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-sm font-medium text-gray-800 dark:text-gray-200">
            {t('chat.conversations')}
          </span>

          <span
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
          </span>
        </div>

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
      </div>

      {/* ===== Conversation List ===== */}
      <div className="space-y-1 flex-1 overflow-auto pr-1">
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
                  ? 'bg-[#EAF4FF] hover:bg-[#DDEEFF] dark:bg-blue-950/40 dark:hover:bg-blue-950/60'
                  : 'bg-transparent hover:bg-gray-100 dark:hover:bg-zinc-800',
                {
                  '!bg-blue-50 dark:!bg-blue-950/40': batchMode && checked,
                },
              )}
            >
              <CardContent className="px-2 py-2 flex justify-between items-center group gap-2">
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
      <div className="py-2">
        <Button
          className="w-full"
          type="button"
          onClick={switchSettingVisible}
          disabled={!hasSingleChatBox}
          variant="outline"
        >
          {t('chat.chatSetting')}
        </Button>
      </div>
    </section>
  );
}
