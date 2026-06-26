'use client';

import { KnowledgeBaseFormField } from '@/components/knowledge-base-item';
import { MetadataFilter } from '@/components/metadata-filter';
import { SwitchFormField } from '@/components/switch-fom-field';
import { TOCEnhanceFormField } from '@/components/toc-enhance-form-field';
import {
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { useTranslate } from '@/hooks/common-hooks';
import { useCallback } from 'react';
import { useFormContext } from 'react-hook-form';

export default function ChatBasicSetting() {
  const { t } = useTranslate('chat');
  const form = useFormContext();

  const llmId = 'llm_id';
  const prefix = 'llm_setting';
  const getFieldWithPrefix = useCallback(
    (name: string) => {
      return prefix ? `${prefix}.${name}` : name;
    },
    [prefix],
  );

  return (
    <div className="space-y-8 pt-2">
      <div className="mb-4 flex items-center gap-2">
        <span className="flex h-5 w-5 items-center justify-center rounded-full bg-red-500 text-xs font-semibold text-white shadow-sm">
          1
        </span>

        <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">
          必填项
        </span>
      </div>
      <KnowledgeBaseFormField></KnowledgeBaseFormField>

      <div className="mb-4 flex items-center gap-2">
        <span className="flex h-5 w-5 items-center justify-center rounded-full bg-green-500 text-xs font-semibold text-white shadow-sm">
          7
        </span>

        <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">
          选填项
        </span>
      </div>

      {/* <LLMFormField
        // options={options}
        name={llmId ?? getFieldWithPrefix('llm_id')}
      ></LLMFormField>

      <RerankFormFields></RerankFormFields> */}
      {/* <FormField
        control={form.control}
        name={'icon'}
        render={({ field }) => (
          <div className="space-y-6">
            <FormItem className="w-full">
              <FormLabel>{t('assistantAvatar')}</FormLabel>
              <FormControl>
                <AvatarUpload {...field}></AvatarUpload>
              </FormControl>
              <FormMessage />
            </FormItem>
          </div>
        )}
      /> */}
      <FormField
        control={form.control}
        name="name"
        render={({ field }) => (
          <FormItem>
            <FormLabel tooltip={t('assistantNameTip')}>
              {t('assistantName')}
            </FormLabel>
            <div className="relative">
              <FormControl>
                <Input {...field} maxLength={32} className="pr-14" />
              </FormControl>

              <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-xs text-slate-400 dark:text-slate-500">
                {field.value?.length || 0}/32
              </span>
            </div>
            <FormMessage />
          </FormItem>
        )}
      />

      {/* <FormField
        control={form.control}
        name="description"
        render={({ field }) => (
          <FormItem>
            <FormLabel tooltip={t('descriptionTip')}>{t('description')}</FormLabel>
            <FormControl>
              <Textarea {...field}></Textarea>
            </FormControl>
            <FormMessage />
          </FormItem>
        )}
      />

      <FormField
        control={form.control}
        name={'prompt_config.prologue'}
        render={({ field }) => (
          <FormItem>
            <FormLabel tooltip={t('setAnOpenerTip')}>
            <FormLabel tooltip={t('setAnOpenerTip')}>{t('setAnOpener')}</FormLabel>
            <FormControl>
              <Textarea {...field}></Textarea>
            </FormControl>
            <FormMessage />
          </FormItem>
        )}
      />

      <FormField
        control={form.control}
        name={'prompt_config.empty_response'}
        render={({ field }) => (
          <FormItem>
            <FormLabel tooltip={t('emptyResponseTip')}>
            <FormLabel tooltip={t('emptyResponseTip')}>{t('emptyResponse')}</FormLabel>
            <FormControl>
              <Textarea {...field}></Textarea>
            </FormControl>
            <FormMessage />
          </FormItem>
        )}
      /> */}

      <FormField
        control={form.control}
        name="description"
        render={({ field }) => (
          <FormItem>
            <FormLabel tooltip={t('descriptionTip')}>
              {t('description')}
            </FormLabel>
            <div className="relative">
              <FormControl>
                <Textarea {...field} maxLength={128} className="pb-7" />
              </FormControl>
              <span className="pointer-events-none absolute bottom-2 right-3 text-xs text-slate-400 dark:text-slate-500">
                {String(field.value || '').length}/128
              </span>
            </div>
            <FormMessage />
          </FormItem>
        )}
      />

      <FormField
        control={form.control}
        name={'prompt_config.prologue'}
        render={({ field }) => (
          <FormItem>
            <FormLabel tooltip={t('setAnOpenerTip')}>
              {t('setAnOpener')}
            </FormLabel>
            <div className="relative">
              <FormControl>
                <Textarea {...field} maxLength={128} className="pb-7" />
              </FormControl>
              <span className="pointer-events-none absolute bottom-2 right-3 text-xs text-slate-400 dark:text-slate-500">
                {String(field.value || '').length}/128
              </span>
            </div>
            <FormMessage />
          </FormItem>
        )}
      />

      <FormField
        control={form.control}
        name={'prompt_config.empty_response'}
        render={({ field }) => (
          <FormItem>
            <FormLabel tooltip={t('emptyResponseTip')}>
              {t('emptyResponse')}
            </FormLabel>
            <div className="relative">
              <FormControl>
                <Textarea {...field} maxLength={128} className="pb-7" />
              </FormControl>
              <span className="pointer-events-none absolute bottom-2 right-3 text-xs text-slate-400 dark:text-slate-500">
                {String(field.value || '').length}/128
              </span>
            </div>
            <FormMessage />
          </FormItem>
        )}
      />

      <SwitchFormField
        name={'prompt_config.quote'}
        label={t('quote')}
        tooltip={t('quoteTip')}
      ></SwitchFormField>
      <SwitchFormField
        name={'prompt_config.keyword'}
        label={t('keyword')}
        tooltip={t('keywordTip')}
      ></SwitchFormField>
      {/* <SwitchFormField
        name={'prompt_config.tts'}
        label={t('tts')}
        tooltip={t('ttsTip')}
      ></SwitchFormField> */}
      <TOCEnhanceFormField name="prompt_config.toc_enhance"></TOCEnhanceFormField>

      {/* <div className="flex items-center gap-2 mb-4">
        <div className="h-4 w-1 bg-blue-500 rounded-full"></div>
        <span className="text-sm font-bold text-gray-900">
          固定项（参数展示区域）
        </span>
      </div>
      <FormField
        control={form.control}
        name="prompt_config.system"
        render={({ field }) => (
          <FormItem>
            <FormLabel>{t('system')}</FormLabel>
            <FormControl>
              <Textarea
                {...field}
                rows={8}
                placeholder={t('messagePlaceholder')}
                className="overflow-y-auto"
              />
            </FormControl>
            <FormMessage />
          </FormItem>
        )}
      /> */}

      {/* <TavilyFormField></TavilyFormField> */}

      <MetadataFilter></MetadataFilter>
    </div>
  );
}
