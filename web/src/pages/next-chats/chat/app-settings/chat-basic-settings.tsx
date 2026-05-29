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
      <div className="flex items-center gap-2 mb-4">
        {/* 短横线 */}
        <div className="h-4 w-1 bg-red-500 rounded-full"></div>
        <span className="text-sm font-bold text-gray-900">必填项-1</span>
      </div>
      <KnowledgeBaseFormField></KnowledgeBaseFormField>

      <div className="flex items-center gap-2 mb-4">
        {/* 短横线 */}
        <div className="h-4 w-1 bg-green-500 rounded-full"></div>
        <span className="text-sm font-bold text-gray-900">选填项-7</span>
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
            <FormLabel>{t('assistantName')}</FormLabel>
            <FormControl>
              <Input {...field}></Input>
            </FormControl>
            <FormMessage />
          </FormItem>
        )}
      />

      <FormField
        control={form.control}
        name="description"
        render={({ field }) => (
          <FormItem>
            <FormLabel>{t('description')}</FormLabel>
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
            {/* <FormLabel tooltip={t('setAnOpenerTip')}> */}
            <FormLabel>{t('setAnOpener')}</FormLabel>
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
            {/* <FormLabel tooltip={t('emptyResponseTip')}> */}
            <FormLabel>{t('emptyResponse')}</FormLabel>
            <FormControl>
              <Textarea {...field}></Textarea>
            </FormControl>
            <FormMessage />
          </FormItem>
        )}
      />

      <SwitchFormField
        name={'prompt_config.quote'}
        label={t('quote')}
        // tooltip={t('quoteTip')}
      ></SwitchFormField>
      <SwitchFormField
        name={'prompt_config.keyword'}
        label={t('keyword')}
        // tooltip={t('keywordTip')}
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
