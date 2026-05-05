import { ButtonLoading } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { useTranslation } from 'react-i18next';

type SaveButtonProps = {
  loading: boolean;
};

export function SavingButton({
  loading,
  className,
}: SaveButtonProps & { className?: string }) {
  const { t } = useTranslation();

  return (
    <ButtonLoading type="submit" loading={loading} className={cn(className)}>
      {t('common.save')}
    </ButtonLoading>
  );
}
