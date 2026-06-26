import { Separator } from '@/components/ui/separator';
import { cn } from '@/lib/utils';
import { X } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import ChatBasicSetting from './chat-basic-settings';
import { SavingButton } from './saving-button';

type ChatSettingsProps = {
  switchSettingVisible(): void;
  onSubmit: () => void;
  loading: boolean;
  className?: string;
};

export function ChatSettings({
  switchSettingVisible,
  loading,
  className,
}: ChatSettingsProps) {
  const { t } = useTranslation();

  const handleClose = (e: React.MouseEvent<HTMLButtonElement>) => {
    e.preventDefault();
    e.stopPropagation();
    switchSettingVisible();
  };

  return (
    <section className={cn('p-5 w-[440px] border-l flex flex-col', className)}>
      <div className="flex justify-between items-center text-base pb-2">
        <div className="flex items-center gap-2">
          <h2 className="font-medium text-gray-900 dark:text-gray-100">
            {t('chat.chatSetting')}
          </h2>
        </div>

        <button
          type="button"
          onClick={handleClose}
          className="inline-flex size-6 items-center justify-center rounded-md text-gray-500 hover:bg-gray-100 hover:text-gray-900 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-100"
        >
          <X className="size-4" />
        </button>
      </div>

      <div className="flex-1 flex flex-col min-h-0">
        <section className="space-y-6 overflow-auto flex-1 pr-4 min-h-0">
          <ChatBasicSetting />
          <Separator />
        </section>

        <div className="space-x-5 text-right pt-4">
          <button
            type="button"
            onClick={handleClose}
            className="inline-flex h-9 items-center justify-center rounded-md border border-input bg-background px-4 py-2 text-sm font-medium hover:bg-accent hover:text-accent-foreground"
          >
            {t('chat.cancel')}
          </button>

          <SavingButton loading={loading} />
        </div>
      </div>
    </section>
  );
}
