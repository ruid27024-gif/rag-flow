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
import { PanelLeftClose, PanelRightClose } from 'lucide-react';
import { useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { useHandleClickConversationCard } from '../hooks/use-click-card';
import { useSelectDerivedConversationList } from '../hooks/use-select-conversation-list';
import { ConversationDropdown } from './conversation-dropdown';

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

  if (!visible) {
    return (
      <PanelRightClose
        className="cursor-pointer size-4 mt-8"
        onClick={switchVisible}
      />
    );
  }

  return (
    <section
      className="
      pt-1 px-4 w-[266px] flex flex-col
      bg-white dark:bg-zinc-900
      border-r border-gray-200 dark:border-zinc-800
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

      {/* ===== Title ===== */}
      <div className="flex items-center justify-between mb-2 mt-4 px-1 w-full">
        <span className="text-sm font-medium text-gray-800 dark:text-gray-200">
          {t('chat.conversations')}
        </span>
        <span
          className="
          text-xs font-medium
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

      {/* ===== Conversation List ===== */}
      <div className="space-y-2 flex-1 overflow-auto">
        {conversationList.map((x) => (
          <Card
            key={x.id}
            onClick={handleCardClick(x.id, x.is_new)}
            className={cn(
              'cursor-pointer rounded-md border-none shadow-none',
              'bg-transparent',
              'hover:bg-gray-100 dark:hover:bg-zinc-800',
              {
                'bg-gray-200 dark:bg-zinc-700': conversationId === x.id,
              },
            )}
          >
            <CardContent className="px-3 py-2 flex justify-between items-center group gap-1">
              <div className="truncate text-gray-900 dark:text-white">
                {x.name}
              </div>
              <ConversationDropdown
                conversation={x}
                removeTemporaryConversation={removeTemporaryConversation}
              >
                <MoreButton />
              </ConversationDropdown>
            </CardContent>
          </Card>
        ))}
      </div>

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
