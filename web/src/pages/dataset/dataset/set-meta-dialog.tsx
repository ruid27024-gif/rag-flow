import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { TagRenameId } from '@/constants/knowledge';
import { IModalProps } from '@/interfaces/common';
import { useTranslation } from 'react-i18next';

import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

import { ButtonLoading } from '@/components/ui/button';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { IDocumentInfo } from '@/interfaces/database/document';
import Editor, { loader } from '@monaco-editor/react';
import DOMPurify from 'dompurify';
import { omit } from 'lodash';
import { useEffect } from 'react';

loader.config({ paths: { vs: '/vs' } });

export function SetMetaDialog({
  hideModal,
  onOk,
  loading,
  initialMetaData,
}: IModalProps<any> & { initialMetaData?: IDocumentInfo['meta_fields'] }) {
  const { t } = useTranslation();

  const FormSchema = z.object({
    author: z.string().optional(),
    school: z.string().optional(),
    publish_time: z.string().optional(),
    meta: z
      .string()
      .min(1, {
        message: t('knowledgeDetails.pleaseInputJson'),
      })
      .trim()
      .refine(
        (value) => {
          try {
            JSON.parse(value);
            return true;
          } catch (error) {
            return false;
          }
        },
        { message: t('knowledgeDetails.pleaseInputJson') },
      ),
  });

  const form = useForm<z.infer<typeof FormSchema>>({
    resolver: zodResolver(FormSchema),
    defaultValues: {
      author: '',
      school: '',
      source: '',
      publish_time: '',
      meta: '{}',
    },
  });

  async function onSubmit(data: z.infer<typeof FormSchema>) {
    let metaObj = {};
    try {
      metaObj = JSON.parse(data.meta);
    } catch (error) {
      console.error(error);
    }

    const finalMeta = {
      ...metaObj,
      author: data.author,
      school: data.school,
      source: data.source,
      publish_time: data.publish_time,
    };

    const ret = await onOk?.(JSON.stringify(finalMeta));
    if (ret) {
      hideModal?.();
    }
  }

  useEffect(() => {
    if (initialMetaData) {
      form.setValue('author', initialMetaData.author || '');
      form.setValue('school', initialMetaData.school || '');
      form.setValue('source', initialMetaData.source || '');
      form.setValue('publish_time', initialMetaData.publish_time || '');
      const rest = omit(initialMetaData, [
        'author',
        'school',
        'source',
        'publish_time',
      ]);
      form.setValue('meta', JSON.stringify(rest, null, 4));
    }
  }, [form, initialMetaData]);

  return (
    <Dialog open onOpenChange={hideModal}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t('knowledgeDetails.setMetaData')}</DialogTitle>
        </DialogHeader>
        <Form {...form}>
          <form
            onSubmit={form.handleSubmit(onSubmit)}
            className="space-y-6"
            id={TagRenameId}
          >
            <FormField
              control={form.control}
              name="author"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>作者</FormLabel>
                  <FormControl>
                    <Input {...field} placeholder="请输入作者" />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="school"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>学校</FormLabel>
                  <FormControl>
                    <Input {...field} placeholder="请输入学校" />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="publish_time"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>发布日期</FormLabel>
                  <FormControl>
                    <Input {...field} placeholder="请输入发布日期" />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="meta"
              render={({ field }) => (
                <FormItem>
                  <FormLabel
                    tooltip={
                      <div
                        dangerouslySetInnerHTML={{
                          __html: DOMPurify.sanitize(
                            t('knowledgeDetails.documentMetaTips'),
                          ),
                        }}
                      ></div>
                    }
                  >
                    {t('knowledgeDetails.metaData')}
                  </FormLabel>
                  <FormControl>
                    <Editor
                      height={200}
                      defaultLanguage="json"
                      theme="vs-dark"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </form>
        </Form>
        <DialogFooter>
          <ButtonLoading type="submit" form={TagRenameId} loading={loading}>
            {t('common.save')}
          </ButtonLoading>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
