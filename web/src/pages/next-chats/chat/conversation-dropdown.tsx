import { ConfirmDeleteDialog } from '@/components/confirm-delete-dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  useGetChatSearchParams,
  useRemoveConversation,
} from '@/hooks/use-chat-request';
import { IConversation } from '@/interfaces/database/chat';
import { Pencil, Trash2 } from 'lucide-react';
import { MouseEventHandler, PropsWithChildren, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { useChatUrlParams } from '../hooks/use-chat-url';

// export function ConversationDropdown({
//   children,
//   conversation,
//   removeTemporaryConversation,
// }: PropsWithChildren & {
//   conversation: IConversation;
//   removeTemporaryConversation?: (conversationId: string) => void;
// }) {
//   const { t } = useTranslation();
//   const { setConversationBoth } = useChatUrlParams();
//   const { removeConversation } = useRemoveConversation();
//   const { isNew } = useGetChatSearchParams();

//   const handleDelete: MouseEventHandler<HTMLDivElement> =
//     useCallback(async () => {
//       if (isNew === 'true' && removeTemporaryConversation) {
//         removeTemporaryConversation(conversation.id);
//       } else {
//         const code = await removeConversation([conversation.id]);
//         if (code === 0) {
//           setConversationBoth('', '');
//         }
//       }
//     }, [
//       conversation.id,
//       isNew,
//       removeConversation,
//       removeTemporaryConversation,
//       setConversationBoth,
//     ]);

//   return (
//     <DropdownMenu>
//       <DropdownMenuTrigger asChild>{children}</DropdownMenuTrigger>
//       <DropdownMenuContent>
//         <ConfirmDeleteDialog onOk={handleDelete}>
//           <DropdownMenuItem
//             className="text-state-error"
//             onSelect={(e) => {
//               e.preventDefault();
//             }}
//             onClick={(e) => {
//               e.stopPropagation();
//             }}
//           >
//             {t('common.delete')} <Trash2 />
//           </DropdownMenuItem>
//         </ConfirmDeleteDialog>
//       </DropdownMenuContent>
//     </DropdownMenu>
//   );
// }

export function ConversationDropdown({
  children,
  conversation,
  removeTemporaryConversation,
  onRename,
}: PropsWithChildren & {
  conversation: IConversation;
  removeTemporaryConversation?: (conversationId: string) => void;
  onRename?: (conversation: IConversation) => void;
}) {
  const { t } = useTranslation();
  const { setConversationBoth } = useChatUrlParams();
  const { removeConversation } = useRemoveConversation();
  const { isNew } = useGetChatSearchParams();

  const handleDelete: MouseEventHandler<HTMLDivElement> =
    useCallback(async () => {
      if (isNew === 'true' && removeTemporaryConversation) {
        removeTemporaryConversation(conversation.id);
      } else {
        const code = await removeConversation([conversation.id]);
        if (code === 0) {
          setConversationBoth('', '');
        }
      }
    }, [
      conversation.id,
      isNew,
      removeConversation,
      removeTemporaryConversation,
      setConversationBoth,
    ]);

  const handleRenameClick = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      e.preventDefault();
      e.stopPropagation();
      onRename?.(conversation);
    },
    [conversation, onRename],
  );

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>{children}</DropdownMenuTrigger>

      <DropdownMenuContent>
        {/* 重命名 */}
        <DropdownMenuItem
          onSelect={(e) => {
            e.preventDefault();
          }}
          onClick={handleRenameClick}
        >
          {t('common.rename') || '重命名'} <Pencil />
        </DropdownMenuItem>

        {/* 删除 */}
        <ConfirmDeleteDialog onOk={handleDelete}>
          <DropdownMenuItem
            className="text-state-error"
            onSelect={(e) => {
              e.preventDefault();
            }}
            onClick={(e) => {
              e.stopPropagation();
            }}
          >
            {t('common.delete')} <Trash2 />
          </DropdownMenuItem>
        </ConfirmDeleteDialog>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
