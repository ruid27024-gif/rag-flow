import { IModalProps } from '@/interfaces/common';
import { IFeedbackRequestBody } from '@/interfaces/request/chat';
import { zodResolver } from '@hookform/resolvers/zod';

import { cn } from '@/lib/utils';
import { useCallback, useState } from 'react';
import { useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { z } from 'zod';
import { RAGFlowFormItem } from './ragflow-form';
import { ButtonLoading } from './ui/button';
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from './ui/dialog';
import { Form } from './ui/form';
import { Textarea } from './ui/textarea';

const FormId = 'feedback-dialog';

// const FeedbackDialog = ({
//   visible,
//   hideModal,
//   onOk,
//   loading,
// }: IModalProps<IFeedbackRequestBody>) => {
//   const { t } = useTranslation();
//   const FormSchema = z.object({
//     feedback: z
//       .string()
//       .min(1, {
//         message: t('common.namePlaceholder'),
//       })
//       .trim(),
//   });

//   const form = useForm<z.infer<typeof FormSchema>>({
//     resolver: zodResolver(FormSchema),
//     defaultValues: { feedback: '' },
//   });

//   const handleOk = useCallback(
//     async (data: z.infer<typeof FormSchema>) => {
//       return onOk?.({ thumbup: false, feedback: data.feedback });
//     },
//     [onOk],
//   );

//   return (
//     <Dialog open={visible} onOpenChange={hideModal}>
//       <DialogContent className="sm:max-w-[425px]">
//         <DialogHeader>
//           <DialogTitle>反馈描述</DialogTitle>
//         </DialogHeader>
//         <Form {...form}>
//           <form
//             onSubmit={(e) => {
//               e.stopPropagation();
//               form.handleSubmit(handleOk)(e);
//             }}
//             className="space-y-6"
//             id={FormId}
//           >
//             <RAGFlowFormItem name="feedback">
//               <Textarea> </Textarea>
//             </RAGFlowFormItem>
//           </form>
//         </Form>
//         <DialogFooter>
//           <ButtonLoading type="submit" form={FormId} loading={loading}>
//             {t('common.save')}
//           </ButtonLoading>
//         </DialogFooter>
//       </DialogContent>
//     </Dialog>
//   );
// };

const FeedbackDialog = ({
  visible,
  hideModal,
  onOk,
  loading,
}: IModalProps<IFeedbackRequestBody>) => {
  const { t } = useTranslation();
  const [selectedReason, setSelectedReason] = useState('');

  const feedbackOptions = ['信息不准确', '没有帮助', '其他'];

  const FormSchema = z.object({
    feedback: z.string().optional(),
  });

  const form = useForm<z.infer<typeof FormSchema>>({
    resolver: zodResolver(FormSchema),
    defaultValues: {
      feedback: '',
    },
  });

  const isOther = selectedReason === '其他';

  const handleOk = useCallback(
    async (data: z.infer<typeof FormSchema>) => {
      if (!selectedReason) {
        form.setError('feedback', {
          type: 'manual',
          message: '请选择反馈原因',
        });
        return;
      }

      const finalFeedback = isOther ? data.feedback?.trim() : selectedReason;

      if (isOther && !finalFeedback) {
        form.setError('feedback', {
          type: 'manual',
          message: '请输入反馈描述',
        });
        return;
      }

      return onOk?.({
        thumbup: false,
        feedback: finalFeedback || selectedReason,
      });
    },
    [onOk, selectedReason, isOther, form],
  );

  const handleOpenChange = useCallback(
    (open: boolean) => {
      if (!open) {
        setSelectedReason('');
        form.reset({ feedback: '' });
        hideModal?.();
      }
    },
    [hideModal, form],
  );

  return (
    <Dialog open={visible} onOpenChange={handleOpenChange}>
      <DialogContent
        className="
          sm:max-w-[425px]
          rounded-2xl
          bg-white
          p-6
          shadow-xl
          dark:bg-zinc-900
        "
      >
        <DialogHeader>
          <DialogTitle className="text-base font-semibold text-slate-900 dark:text-slate-100">
            反馈
          </DialogTitle>
        </DialogHeader>

        <Form {...form}>
          <form
            onSubmit={(e) => {
              e.stopPropagation();
              form.handleSubmit(handleOk)(e);
            }}
            className="space-y-4"
            id={FormId}
          >
            <div className="space-y-3">
              <div className="flex flex-wrap gap-2">
                {feedbackOptions.map((item) => {
                  const active = selectedReason === item;

                  return (
                    <button
                      key={item}
                      type="button"
                      onClick={() => {
                        setSelectedReason(item);
                        form.clearErrors('feedback');

                        if (item !== '其他') {
                          form.setValue('feedback', '');
                        }
                      }}
                      className={cn(
                        `
                          rounded-md
                          border
                          px-3
                          py-1
                          text-xs
                          transition-all
                          duration-200
                        `,
                        active
                          ? `
                            border-blue-500
                            bg-blue-500
                            text-white
                          `
                          : `
                            border-slate-300
                            bg-white
                            text-slate-700
                            hover:border-blue-400
                            hover:text-blue-600

                            dark:border-zinc-700
                            dark:bg-zinc-900
                            dark:text-zinc-300
                            dark:hover:border-blue-500
                            dark:hover:text-blue-400
                          `,
                      )}
                    >
                      {item}
                    </button>
                  );
                })}
              </div>

              {isOther && (
                <RAGFlowFormItem name="feedback">
                  <Textarea
                    placeholder="我们想知道你对此回答不满意的原因，你认为更好的回答是什么？"
                    className="
                      min-h-[100px]
                      resize-none
                      rounded-xl
                      border-blue-500
                      focus-visible:ring-blue-500
                    "
                  />
                </RAGFlowFormItem>
              )}

              {!isOther && (
                <RAGFlowFormItem name="feedback">
                  <div className="hidden" />
                </RAGFlowFormItem>
              )}
            </div>
          </form>
        </Form>

        <DialogFooter className="gap-2">
          <button
            type="button"
            onClick={() => handleOpenChange(false)}
            className="
              h-9
              rounded-full
              border
              border-slate-200
              bg-white
              px-5
              text-sm
              text-slate-700
              transition-colors
              hover:bg-slate-50
              dark:border-zinc-700
              dark:bg-zinc-900
              dark:text-zinc-300
              dark:hover:bg-zinc-800
            "
          >
            取消
          </button>

          <ButtonLoading
            type="submit"
            form={FormId}
            loading={loading}
            className="
              h-9
              rounded-full
              bg-blue-500
              px-5
              text-sm
              text-white
              hover:bg-blue-600
            "
          >
            提交
          </ButtonLoading>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
export default FeedbackDialog;
