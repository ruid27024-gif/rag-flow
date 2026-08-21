import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import { t } from 'i18next';
import { BrushCleaning } from 'lucide-react';
import { useCallback } from 'react';
import {
  ConfirmDeleteDialog,
  ConfirmDeleteDialogNode,
} from './confirm-delete-dialog';
import { Separator } from './ui/separator';

// export type BulkOperateItemType = {
//   id: string;
//   label: string;
//   icon?: React.ReactNode;
//   onClick?: () => void | Promise<void>;
//   disabled?: boolean;
//   disabledTitle?: string;
// };

// type BulkOperateBarProps = {
//   list: BulkOperateItemType[];
//   count: number;
//   className?: string;
// };

// export function BulkOperateBar({
//   list,
//   count,
//   className,
// }: BulkOperateBarProps) {
//   const isDeleteItem = useCallback((id: string) => {
//     return id === 'delete';
//   }, []);

//   return (
//     <Card className={cn('mb-4', className)}>
//       <CardContent className="p-1 pl-5 flex items-center gap-6">
//         <section className="text-text-sub-title-invert flex items-center gap-2">
//           <span>已选: {count} 个文件</span>
//           <BrushCleaning className="size-3" />
//         </section>
//         <Separator orientation={'vertical'} className="h-3"></Separator>
//         <ul className="flex gap-2">
//           {list.map((x) => (
//             <li
//               key={x.id}
//               className={cn({ ['text-state-error']: isDeleteItem(x.id) })}
//             >
//               <ConfirmDeleteDialog
//                 hidden={!isDeleteItem(x.id)}
//                 onOk={x.onClick}
//                 title={t('deleteModal.delFiles')}
//                 content={{
//                   title: t('common.deleteThem'),
//                   node: (
//                     <ConfirmDeleteDialogNode
//                       name={`${t('deleteModal.delFilesContent', { count })}`}
//                     ></ConfirmDeleteDialogNode>
//                   ),
//                 }}
//               >
//                 <Button
//                   variant={'ghost'}
//                   onClick={isDeleteItem(x.id) ? () => {} : x.onClick}
//                 >
//                   {x.icon} {x.label}
//                 </Button>
//               </ConfirmDeleteDialog>
//             </li>
//           ))}
//         </ul>
//       </CardContent>
//     </Card>
//   );
// }

type BulkOperateItem = {
  id: string;
  label: string;
  icon?: React.ReactNode;
  onClick?: () => void | Promise<void>;
  disabled?: boolean;
  disabledTitle?: string;
};

type BulkOperateBarProps = {
  list: BulkOperateItem[];
  count: number;
  className?: string;
};

export function BulkOperateBar({
  list,
  count,
  className,
}: BulkOperateBarProps) {
  const isDeleteItem = useCallback((id: string) => {
    return id === 'delete';
  }, []);

  return (
    <Card className={cn('mb-4', className)}>
      <CardContent className="flex items-center gap-6 p-1 pl-5">
        <section className="flex items-center gap-2 text-text-sub-title-invert">
          <span>已选: {count} 个文件</span>
          <BrushCleaning className="size-3" />
        </section>

        <Separator orientation="vertical" className="h-3" />

        <ul className="flex gap-2">
          {list.map((item) => {
            const isDelete = isDeleteItem(item.id);

            const button = (
              <Button
                variant="ghost"
                disabled={item.disabled}
                title={item.disabled ? item.disabledTitle : undefined}
                onClick={isDelete ? undefined : item.onClick}
              >
                {item.icon}
                {item.label}
              </Button>
            );

            return (
              <li
                key={item.id}
                className={cn({
                  'text-state-error': isDelete,
                })}
              >
                {isDelete ? (
                  item.disabled ? (
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <span>{button}</span>
                      </TooltipTrigger>
                      <TooltipContent>
                        <p>{item.disabledTitle || '当前用户没有删除权限'}</p>
                      </TooltipContent>
                    </Tooltip>
                  ) : (
                    <ConfirmDeleteDialog
                      onOk={item.onClick}
                      title={t('deleteModal.delFiles')}
                      content={{
                        title: t('common.deleteThem'),
                        node: (
                          <ConfirmDeleteDialogNode
                            name={`${t('deleteModal.delFilesContent', {
                              count,
                            })}`}
                          />
                        ),
                      }}
                    >
                      {button}
                    </ConfirmDeleteDialog>
                  )
                ) : item.disabled ? (
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <span>{button}</span>
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>{item.disabledTitle || '当前用户无权限操作'}</p>
                    </TooltipContent>
                  </Tooltip>
                ) : (
                  button
                )}
              </li>
            );
          })}
        </ul>
      </CardContent>
    </Card>
  );
}
