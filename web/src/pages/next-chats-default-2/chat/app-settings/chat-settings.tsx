import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { cn } from '@/lib/utils';
import { X } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import ChatBasicSetting from './chat-basic-settings';
import { ChatModelSettings } from './chat-model-settings';
import { ChatPromptEngine } from './chat-prompt-engine';
import { SavingButton } from './saving-button';

type ChatSettingsProps = {
  switchSettingVisible(): void;
  onSubmit: () => void;
  loading: boolean;
  className?: string;
};

export function ChatSettings({
  switchSettingVisible,
  onSubmit,
  loading,
  className,
}: ChatSettingsProps) {
  const { t } = useTranslation();

  return (
    <section className={cn('p-5  w-[440px] border-l flex flex-col', className)}>
      <div className="flex justify-between items-center text-base pb-2">
        {t('chat.chatSetting')}
        <X className="size-4 cursor-pointer" onClick={switchSettingVisible} />
      </div>
      <div className="flex-1 flex flex-col min-h-0">
        <section className="space-y-6 overflow-auto flex-1 pr-4 min-h-0">
          <ChatBasicSetting></ChatBasicSetting>
          <Separator />
          <ChatPromptEngine></ChatPromptEngine>
          <Separator />
          <ChatModelSettings></ChatModelSettings>
        </section>
        <div className="space-x-5 text-right pt-4">
          <Button variant={'outline'} onClick={switchSettingVisible}>
            {t('chat.cancel')}
          </Button>
          <SavingButton loading={loading}></SavingButton>
        </div>
      </div>
    </section>
  );
}
