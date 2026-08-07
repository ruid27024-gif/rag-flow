import { ButtonLoading } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { IModalProps } from '@/interfaces/common';
import { getAuthorization } from '@/utils/authorization-util';
import { zodResolver } from '@hookform/resolvers/zod';
import { message } from 'antd';
import { TFunction } from 'i18next';
import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { z } from 'zod';
import { FileUploader } from '../file-uploader';
import { RAGFlowFormItem } from '../ragflow-form';
import { Form } from '../ui/form';

// function buildUploadFormSchema(t: TFunction) {
//   const FormSchema = z.object({
//     parseOnCreation: z.boolean().optional(),
//     fileList: z
//       .array(z.instanceof(File))
//       .min(1, { message: t('fileManager.pleaseUploadAtLeastOneFile') }),
//   });

//   return FormSchema;
// }

// export type UploadFormSchemaType = z.infer<
//   ReturnType<typeof buildUploadFormSchema>
// >;

// const UploadFormId = 'UploadFormId';

// type UploadFormProps = {
//   submit: (values?: UploadFormSchemaType) => void;
//   showParseOnCreation?: boolean;
// };
// function UploadForm({ submit, showParseOnCreation }: UploadFormProps) {
//   const { t } = useTranslation();
//   const FormSchema = buildUploadFormSchema(t);

//   type UploadFormSchemaType = z.infer<typeof FormSchema>;
//   const form = useForm<UploadFormSchemaType>({
//     resolver: zodResolver(FormSchema),
//     defaultValues: {
//       parseOnCreation: false,
//       fileList: [],
//     },
//   });

//   return (
//     <Form {...form}>
//       <form
//         onSubmit={form.handleSubmit(submit)}
//         id={UploadFormId}
//         className="space-y-4"
//       >
//         {showParseOnCreation && (
//           <RAGFlowFormItem
//             name="parseOnCreation"
//             label={t('fileManager.parseOnCreation')}
//           >
//             {(field) => (
//               <Switch
//                 onCheckedChange={field.onChange}
//                 checked={field.value}
//               ></Switch>
//             )}
//           </RAGFlowFormItem>
//         )}
//         <RAGFlowFormItem name="fileList" label={t('fileManager.file')}>
//           {(field) => (
//             <FileUploader
//               value={field.value}
//               onValueChange={field.onChange}
//               accept={{ '*': [] }}
//             />
//           )}
//         </RAGFlowFormItem>
//       </form>
//     </Form>
//   );
// }

// type FileUploadDialogProps = IModalProps<UploadFormSchemaType> &
//   Pick<UploadFormProps, 'showParseOnCreation'>;
// export function FileUploadDialog({
//   hideModal,
//   onOk,
//   loading,
//   showParseOnCreation = false,
// }: FileUploadDialogProps) {
//   const { t } = useTranslation();

//   return (
//     <Dialog open onOpenChange={hideModal}>
//       <DialogContent>
//         <DialogHeader>
//           <DialogTitle>{t('fileManager.uploadFile')}</DialogTitle>
//         </DialogHeader>
//         {/* <Tabs defaultValue="account">
//           <TabsList className="grid w-full grid-cols-2 mb-4">
//             <TabsTrigger value="account">{t('fileManager.local')}</TabsTrigger>
//             <TabsTrigger value="password">{t('fileManager.s3')}</TabsTrigger>
//           </TabsList>
//           <TabsContent value="account">
//             <UploadForm
//               submit={onOk!}
//               showParseOnCreation={showParseOnCreation}
//             ></UploadForm>
//           </TabsContent>
//           <TabsContent value="password">{t('common.comingSoon')}</TabsContent>
//         </Tabs> */}
//         <UploadForm
//           submit={onOk!}
//           showParseOnCreation={showParseOnCreation}
//         ></UploadForm>
//         <DialogFooter>
//           <ButtonLoading type="submit" loading={loading} form={UploadFormId}>
//             {t('common.save')}
//           </ButtonLoading>
//         </DialogFooter>
//       </DialogContent>
//     </Dialog>
//   );
// }

type KnowledgeTagOption = {
  id: number;
  type_code: string;
  option_code: string;
  option_name: string;
  sort_order?: number;
  enabled?: boolean;
};

type KnowledgeTagType = {
  id: number;
  type_code: string;
  type_name: string;
  multi_select: boolean;
  required: boolean;
  sort_order?: number;
  enabled?: boolean;
  options: KnowledgeTagOption[];
};

function useFetchTagConfig() {
  const [tagConfig, setTagConfig] = useState<KnowledgeTagType[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchTagConfig = async () => {
    try {
      setLoading(true);

      const res = await fetch('/v1/knowledge_tag/tag/config', {
        method: 'GET',
        headers: {
          Authorization: getAuthorization() || '',
          'Content-Type': 'application/json',
        },
        credentials: 'include',
      });

      const result = await res.json();

      if (result.code === 0 || result.code === 200) {
        setTagConfig(result.data || []);
      } else {
        message.error(result.message || '获取标签配置失败');
      }
    } catch (e) {
      console.error(e);
      message.error('获取标签配置请求失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTagConfig();
  }, []);

  return {
    tagConfig,
    loading,
  };
}

function buildUploadFormSchema(t: TFunction) {
  const FormSchema = z.object({
    fileList: z
      .array(z.instanceof(File))
      .min(1, { message: t('fileManager.pleaseUploadAtLeastOneFile') }),

    // 标签格式：
    // {
    //   subject: ["medicine"],
    //   keyword: ["ai", "imaging"]
    // }
    tags: z.record(z.string(), z.array(z.string())).optional(),
  });

  return FormSchema;
}

export type UploadFormSchemaType = z.infer<
  ReturnType<typeof buildUploadFormSchema>
>;

const UploadFormId = 'UploadFormId';

type UploadFormProps = {
  submit: (values?: UploadFormSchemaType) => void;
};

function UploadForm({ submit }: UploadFormProps) {
  const { t } = useTranslation();
  const FormSchema = buildUploadFormSchema(t);

  const form = useForm<UploadFormSchemaType>({
    resolver: zodResolver(FormSchema),
    defaultValues: {
      fileList: [],
      tags: {},
    },
  });

  const { tagConfig, loading: tagLoading } = useFetchTagConfig();

  const onSubmit = (values: UploadFormSchemaType) => {
    const tags = values.tags || {};

    // 前端简单校验 required 标签
    for (const tagType of tagConfig) {
      if (tagType.required) {
        const selected = tags[tagType.type_code];

        if (!selected || selected.length === 0) {
          form.setError(`tags.${tagType.type_code}` as any, {
            type: 'manual',
            message: `请选择${tagType.type_name}`,
          });
          return;
        }
      }
    }

    submit({
      fileList: values.fileList,
      tags,
    });
  };

  return (
    <Form {...form}>
      <form
        onSubmit={form.handleSubmit(onSubmit)}
        id={UploadFormId}
        className="space-y-4"
      >
        <RAGFlowFormItem name="fileList" label={t('fileManager.file')}>
          {(field) => (
            <FileUploader
              value={field.value}
              onValueChange={field.onChange}
              accept={{ '*': [] }}
            />
          )}
        </RAGFlowFormItem>

        {tagLoading && (
          <div className="text-sm text-gray-400">标签配置加载中...</div>
        )}

        {!tagLoading &&
          tagConfig.map((tagType) => {
            const fieldName = `tags.${tagType.type_code}` as const;

            return (
              <RAGFlowFormItem
                key={tagType.type_code}
                name={fieldName}
                label={
                  tagType.required
                    ? `${tagType.type_name} *`
                    : tagType.type_name
                }
              >
                {(field) => {
                  const value = Array.isArray(field.value) ? field.value : [];

                  if (tagType.multi_select) {
                    return (
                      <div className="flex flex-wrap gap-2 rounded-md border border-input bg-background p-3">
                        {tagType.options.map((option) => {
                          const checked = value.includes(option.option_code);

                          return (
                            <label
                              key={option.option_code}
                              className="
              inline-flex items-center gap-2
              rounded-md border px-3 py-1.5
              text-sm cursor-pointer
              hover:bg-muted
            "
                            >
                              <input
                                type="checkbox"
                                checked={checked}
                                onChange={(e) => {
                                  if (e.target.checked) {
                                    field.onChange([
                                      ...value,
                                      option.option_code,
                                    ]);
                                  } else {
                                    field.onChange(
                                      value.filter(
                                        (x) => x !== option.option_code,
                                      ),
                                    );
                                  }
                                }}
                              />
                              <span>{option.option_name}</span>
                            </label>
                          );
                        })}
                      </div>
                    );
                  }

                  // 单选标签
                  // 注意：虽然是单选，但也保存为数组，例如 ["medicine"]
                  return (
                    <select
                      className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                      value={value[0] || ''}
                      onChange={(e) => {
                        const selected = e.target.value;
                        field.onChange(selected ? [selected] : []);
                      }}
                    >
                      <option value="">请选择{tagType.type_name}</option>

                      {tagType.options.map((option) => (
                        <option
                          key={option.option_code}
                          value={option.option_code}
                        >
                          {option.option_name}
                        </option>
                      ))}
                    </select>
                  );
                }}
              </RAGFlowFormItem>
            );
          })}
      </form>
    </Form>
  );
}

type FileUploadDialogProps = IModalProps<UploadFormSchemaType>;

export function FileUploadDialog({
  hideModal,
  onOk,
  loading,
}: FileUploadDialogProps) {
  const { t } = useTranslation();

  return (
    <Dialog open onOpenChange={hideModal}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t('fileManager.uploadFile')}</DialogTitle>
        </DialogHeader>

        <UploadForm submit={onOk!} />

        <DialogFooter>
          <ButtonLoading type="submit" loading={loading} form={UploadFormId}>
            {t('common.save')}
          </ButtonLoading>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
