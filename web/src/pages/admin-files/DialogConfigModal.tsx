import { KnowledgeBaseFormField } from '@/components/knowledge-base-item';
import { MetadataFilter } from '@/components/metadata-filter';
import { SwitchFormField } from '@/components/switch-fom-field';
import { TOCEnhanceFormField } from '@/components/toc-enhance-form-field';
import { Button } from '@/components/ui/button';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import message from '@/components/ui/message';
import { Modal } from '@/components/ui/modal/modal';
import { Separator } from '@/components/ui/separator';
import { Textarea } from '@/components/ui/textarea';
import { DatasetMetadata } from '@/constants/chat';
import { ChatModelSettings } from '@/pages/next-chats/chat/app-settings/chat-model-settings';
import { ChatPromptEngine } from '@/pages/next-chats/chat/app-settings/chat-prompt-engine';
import { useChatSettingSchema } from '@/pages/next-chats/chat/app-settings/use-chat-setting-schema';
import {
  removeUselessFieldsFromValues,
  setLLMSettingEnabledValues,
} from '@/utils/form';
import { zodResolver } from '@hookform/resolvers/zod';
import { omit } from 'lodash';
import { useEffect, useState } from 'react';
import { useForm, useFormContext } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { z } from 'zod';

function AdminChatBasicSetting() {
  const { t } = useTranslation();
  const form = useFormContext();

  return (
    <div className="space-y-8">
      {/* Excluded AvatarUpload */}
      <FormField
        control={form.control}
        name="name"
        render={({ field }) => (
          <FormItem>
            <FormLabel required>{t('chat.assistantName')}</FormLabel>
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
            <FormLabel>{t('chat.description')}</FormLabel>
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
            {/* <FormLabel tooltip={t('chat.emptyResponseTip')}> */}
            <FormLabel>{t('chat.emptyResponse')}</FormLabel>
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
            <FormLabel>
              {/* <FormLabel tooltip={t('chat.setAnOpenerTip')}> */}
              {t('chat.setAnOpener')}
            </FormLabel>
            <FormControl>
              <Textarea {...field}></Textarea>
            </FormControl>
            <FormMessage />
          </FormItem>
        )}
      />
      <SwitchFormField
        name={'prompt_config.quote'}
        label={t('chat.quote')}
        // tooltip={t('chat.quoteTip')}
      ></SwitchFormField>
      <SwitchFormField
        name={'prompt_config.keyword'}
        label={t('chat.keyword')}
        // tooltip={t('chat.keywordTip')}
      ></SwitchFormField>
      <SwitchFormField
        name={'prompt_config.tts'}
        label={t('chat.tts')}
        // tooltip={t('chat.ttsTip')}
      ></SwitchFormField>
      <TOCEnhanceFormField name="prompt_config.toc_enhance"></TOCEnhanceFormField>
      {/* <TavilyFormField></TavilyFormField> */}
      <KnowledgeBaseFormField></KnowledgeBaseFormField>
      <MetadataFilter></MetadataFilter>
    </div>
  );
}

interface DialogConfigModalProps {
  open: boolean;
  onCancel: () => void;
}

export function DialogConfigModal({ open, onCancel }: DialogConfigModalProps) {
  const { t } = useTranslation();
  const formSchema = useChatSettingSchema();
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<any>(null);

  type FormSchemaType = z.infer<typeof formSchema>;

  const form = useForm<FormSchemaType>({
    resolver: zodResolver(formSchema),
    shouldUnregister: true,
    defaultValues: {
      name: '',
      icon: '',
      description: '',
      kb_ids: [],
      prompt_config: {
        quote: true,
        keyword: false,
        tts: false,
        use_kg: false,
        refine_multiturn: true,
        system: '',
        parameters: [],
        reasoning: false,
        cross_languages: [],
        toc_enhance: false,
      },
      top_n: 8,
      similarity_threshold: 0.2,
      vector_similarity_weight: 0.2,
      top_k: 1024,
      meta_data_filter: {
        method: DatasetMetadata.Disabled,
        manual: [],
      },
    },
  });

  const fetchData = async () => {
    try {
      const response = await fetch('/v1/debug/config');
      const res = await response.json();
      if (res.retcode === 0) {
        setData(res.data);
      } else {
        message.error(res.error || 'Fetch config failed');
      }
    } catch (error) {
      console.error(error);
      message.error('Fetch config failed');
    }
  };

  useEffect(() => {
    if (open) {
      fetchData();
    }
  }, [open]);

  useEffect(() => {
    if (data) {
      const parsedData = { ...data };
      ['kb_ids', 'prompt_config', 'llm_setting', 'meta_data_filter'].forEach(
        (key) => {
          if (typeof parsedData[key] === 'string') {
            try {
              parsedData[key] = JSON.parse(parsedData[key]);
            } catch (e) {
              console.error(`Failed to parse ${key}`, e);
            }
          }
        },
      );

      const llmSettingEnabledValues = setLLMSettingEnabledValues(
        parsedData.llm_setting,
      );

      const nextData = {
        ...parsedData,
        ...llmSettingEnabledValues,
      };
      // Merge with default values to ensure all fields exist
      const mergedData = {
        ...form.getValues(),
        ...nextData,
        // Ensure prompt_config is merged correctly
        prompt_config: {
          ...form.getValues().prompt_config,
          ...(nextData.prompt_config || {}),
        },
      };
      form.reset(mergedData);
    }
  }, [data, form]);

  async function onSubmit(values: FormSchemaType) {
    setLoading(true);
    try {
      const nextValues: Record<string, any> = removeUselessFieldsFromValues(
        values,
        'llm_setting.',
      );

      const payload = {
        ...data,
        ...omit(data, 'operator_permission'), // Just in case data has it
        ...nextValues,
      };

      // Stringify fields that should be strings in the JSON file
      ['kb_ids', 'prompt_config', 'llm_setting', 'meta_data_filter'].forEach(
        (key) => {
          if (typeof payload[key] !== 'string') {
            try {
              payload[key] = JSON.stringify(payload[key]);
            } catch (e) {
              console.error(`Failed to stringify ${key}`, e);
            }
          }
        },
      );

      const response = await fetch('/v1/debug/config', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });
      const res = await response.json();

      if (res.retcode === 0) {
        message.success(t('message.modified'));
        onCancel();
      } else {
        message.error(res.error || 'Update failed');
      }
    } catch (error) {
      console.error(error);
      message.error('Update failed');
    } finally {
      setLoading(false);
    }
  }

  function onInvalid(errors: any) {
    console.log('Form validation failed:', errors);
  }

  return (
    <Modal
      title="统一配置管理"
      open={open}
      onCancel={onCancel}
      showfooter={false}
      className="w-[1000px] max-w-[calc(100vw-2rem)]"
    >
      <div className="p-4">
        <Form {...form}>
          <form
            onSubmit={form.handleSubmit(onSubmit, onInvalid)}
            className="flex-1 flex flex-col min-h-0"
          >
            <section className="space-y-6 flex-1 min-h-0">
              <AdminChatBasicSetting />
              <Separator />
              <ChatPromptEngine />
              <Separator />
              <ChatModelSettings />
            </section>
            <div className="flex justify-end gap-4 pt-8 pb-4">
              <Button type="button" variant={'outline'} onClick={onCancel}>
                {t('common.cancel')}
              </Button>
              <Button type="submit" loading={loading}>
                {t('common.save')}
              </Button>
            </div>
          </form>
        </Form>
      </div>
    </Modal>
  );
}
