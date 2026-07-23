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
    <ButtonLoading
      type="submit"
      loading={loading}
      className={cn(
        className,
        `
          !bg-white/25
          backdrop-blur-md

          !text-sky-700
          [-webkit-text-fill-color:#0369a1]

          border
          border-sky-300/50
          shadow-none

          hover:!bg-white/40
          hover:!text-sky-800
          hover:[-webkit-text-fill-color:#075985]
          hover:border-sky-400/70
          hover:shadow-sm
          hover:shadow-sky-200/50

          active:scale-[0.98]

          disabled:opacity-50
          disabled:cursor-not-allowed

          dark:!bg-transparent
          dark:!text-sky-300
          dark:[-webkit-text-fill-color:#7dd3fc]
          dark:border-sky-700/50
          dark:hover:!bg-sky-950/30
          dark:hover:[-webkit-text-fill-color:#bae6fd]
        `,
      )}
    >
      {t('common.save')}
    </ButtonLoading>
  );
}
