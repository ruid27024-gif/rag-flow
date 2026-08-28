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

// type KnowledgeTagOption = {
//   id: number;
//   type_code: string;
//   option_code: string;
//   option_name: string;
//   sort_order?: number;
//   enabled?: boolean;
// };

// type KnowledgeTagType = {
//   id: number;
//   type_code: string;
//   type_name: string;
//   multi_select: boolean;
//   required: boolean;
//   sort_order?: number;
//   enabled?: boolean;
//   options: KnowledgeTagOption[];
// };

// function useFetchTagConfig() {
//   const [tagConfig, setTagConfig] = useState<KnowledgeTagType[]>([]);
//   const [loading, setLoading] = useState(false);

//   const fetchTagConfig = async () => {
//     try {
//       setLoading(true);

//       const res = await fetch('/v1/knowledge_tag/tag/config', {
//         method: 'GET',
//         headers: {
//           Authorization: getAuthorization() || '',
//           'Content-Type': 'application/json',
//         },
//         credentials: 'include',
//       });

//       const result = await res.json();

//       if (result.code === 0 || result.code === 200) {
//         setTagConfig(result.data || []);
//       } else {
//         message.error(result.message || '获取标签配置失败');
//       }
//     } catch (e) {
//       console.error(e);
//       message.error('获取标签配置请求失败');
//     } finally {
//       setLoading(false);
//     }
//   };

//   useEffect(() => {
//     fetchTagConfig();
//   }, []);

//   return {
//     tagConfig,
//     loading,
//   };
// }

// function buildUploadFormSchema(t: TFunction) {
//   const FormSchema = z.object({
//     fileList: z
//       .array(z.instanceof(File))
//       .min(1, { message: t('fileManager.pleaseUploadAtLeastOneFile') }),

//     // 标签格式：
//     // {
//     //   subject: ["medicine"],
//     //   keyword: ["ai", "imaging"]
//     // }
//     tags: z.record(z.string(), z.array(z.string())).optional(),
//   });

//   return FormSchema;
// }

// export type UploadFormSchemaType = z.infer<
//   ReturnType<typeof buildUploadFormSchema>
// >;

// const UploadFormId = 'UploadFormId';

// type UploadFormProps = {
//   submit: (values?: UploadFormSchemaType) => void;
// };

// function UploadForm({ submit }: UploadFormProps) {
//   const { t } = useTranslation();
//   const FormSchema = buildUploadFormSchema(t);

//   const form = useForm<UploadFormSchemaType>({
//     resolver: zodResolver(FormSchema),
//     defaultValues: {
//       fileList: [],
//       tags: {},
//     },
//   });

//   const { tagConfig, loading: tagLoading } = useFetchTagConfig();

//   const onSubmit = (values: UploadFormSchemaType) => {
//     const tags = values.tags || {};

//     // 前端简单校验 required 标签
//     for (const tagType of tagConfig) {
//       if (tagType.required) {
//         const selected = tags[tagType.type_code];

//         if (!selected || selected.length === 0) {
//           form.setError(`tags.${tagType.type_code}` as any, {
//             type: 'manual',
//             message: `请选择${tagType.type_name}`,
//           });
//           return;
//         }
//       }
//     }

//     submit({
//       fileList: values.fileList,
//       tags,
//     });
//   };

//   return (
//     <Form {...form}>
//       <form
//         onSubmit={form.handleSubmit(onSubmit)}
//         id={UploadFormId}
//         className="space-y-4"
//       >
//         <RAGFlowFormItem name="fileList" label={t('fileManager.file')}>
//           {(field) => (
//             <FileUploader
//               value={field.value}
//               onValueChange={field.onChange}
//               accept={{ '*': [] }}
//             />
//           )}
//         </RAGFlowFormItem>

//         {tagLoading && (
//           <div className="text-sm text-gray-400">标签配置加载中...</div>
//         )}

//         {!tagLoading &&
//           tagConfig.map((tagType) => {
//             const fieldName = `tags.${tagType.type_code}` as const;

//             return (
//               <RAGFlowFormItem
//                 key={tagType.type_code}
//                 name={fieldName}
//                 label={
//                   tagType.required
//                     ? `${tagType.type_name} *`
//                     : tagType.type_name
//                 }
//               >
//                 {(field) => {
//                   const value = Array.isArray(field.value) ? field.value : [];

//                   if (tagType.multi_select) {
//                     return (
//                       <div className="flex flex-wrap gap-2 rounded-md border border-input bg-background p-3">
//                         {tagType.options.map((option) => {
//                           const checked = value.includes(option.option_code);

//                           return (
//                             <label
//                               key={option.option_code}
//                               className="
//               inline-flex items-center gap-2
//               rounded-md border px-3 py-1.5
//               text-sm cursor-pointer
//               hover:bg-muted
//             "
//                             >
//                               <input
//                                 type="checkbox"
//                                 checked={checked}
//                                 onChange={(e) => {
//                                   if (e.target.checked) {
//                                     field.onChange([
//                                       ...value,
//                                       option.option_code,
//                                     ]);
//                                   } else {
//                                     field.onChange(
//                                       value.filter(
//                                         (x) => x !== option.option_code,
//                                       ),
//                                     );
//                                   }
//                                 }}
//                               />
//                               <span>{option.option_name}</span>
//                             </label>
//                           );
//                         })}
//                       </div>
//                     );
//                   }

//                   // 单选标签
//                   // 注意：虽然是单选，但也保存为数组，例如 ["medicine"]
//                   return (
//                     <select
//                       className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
//                       value={value[0] || ''}
//                       onChange={(e) => {
//                         const selected = e.target.value;
//                         field.onChange(selected ? [selected] : []);
//                       }}
//                     >
//                       <option value="">请选择{tagType.type_name}</option>

//                       {tagType.options.map((option) => (
//                         <option
//                           key={option.option_code}
//                           value={option.option_code}
//                         >
//                           {option.option_name}
//                         </option>
//                       ))}
//                     </select>
//                   );
//                 }}
//               </RAGFlowFormItem>
//             );
//           })}
//       </form>
//     </Form>
//   );
// }

// type FileUploadDialogProps = IModalProps<UploadFormSchemaType>;

// export function FileUploadDialog({
//   hideModal,
//   onOk,
//   loading,
// }: FileUploadDialogProps) {
//   const { t } = useTranslation();

//   return (
//     <Dialog open onOpenChange={hideModal}>
//       <DialogContent>
//         <DialogHeader>
//           <DialogTitle>{t('fileManager.uploadFile')}</DialogTitle>
//         </DialogHeader>

//         <UploadForm submit={onOk!} />

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

/**
 * 获取知识标签配置。
 */
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
    } catch (error) {
      console.error(error);
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

/**
 * 标准化前端版本号。
 *
 * 输入：
 * - 空值  -> v1.0
 * - 1     -> v1.0
 * - v1    -> v1.0
 * - 1.0   -> v1.0
 * - v1.0  -> v1.0
 * - 2.3   -> v2.3
 * - v2.3  -> v2.3
 */
function normalizeDocumentVersion(version?: string): string {
  let value = String(version || '')
    .trim()
    .toLowerCase();

  if (!value) {
    return 'v1.0';
  }

  if (value.startsWith('v')) {
    value = value.slice(1);
  }

  if (!value.includes('.')) {
    value = `${value}.0`;
  }

  const [majorText = '1', minorText = '0'] = value.split('.');

  const major = Number(majorText);
  const minor = Number(minorText);

  return `v${major}.${minor}`;
}

/**
 * 构建上传表单校验规则。
 */
function buildUploadFormSchema(t: TFunction) {
  return z.object({
    fileList: z.array(z.instanceof(File)).min(1, {
      message: t('fileManager.pleaseUploadAtLeastOneFile'),
    }),

    /**
     * 文档版本号。
     *
     * 支持：
     * 1
     * v1
     * 1.0
     * v1.0
     * 2.3
     * v2.3
     *
     * 未填写时默认为 v1.0。
     */
    version: z
      .string()
      .trim()
      .refine(
        (value) => {
          if (!value) {
            return true;
          }

          return /^v?\d+(?:\.\d+)?$/i.test(value);
        },
        {
          message: '版本号格式错误，请输入 v1.0、v1.1、v2.0 或 v2.3',
        },
      )
      .optional(),

    /**
     * 标签数据格式：
     *
     * {
     *   knowledge_level: ["public"],
     *   knowledge_category: ["pulping", "papermaking"]
     * }
     */
    tags: z.record(z.string(), z.array(z.string())).optional(),
  });
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

      // 默认版本号
      version: 'v1.0',

      tags: {},
    },
  });

  const { tagConfig, loading: tagLoading } = useFetchTagConfig();

  /**
   * 提交表单。
   */
  const onSubmit = (values: UploadFormSchemaType) => {
    const tags = values.tags || {};

    /**
     * 校验必填标签。
     */
    for (const tagType of tagConfig) {
      if (!tagType.required) {
        continue;
      }

      const selected = tags[tagType.type_code];

      if (!selected || selected.length === 0) {
        form.setError(`tags.${tagType.type_code}` as any, {
          type: 'manual',
          message: `请选择${tagType.type_name}`,
        });

        return;
      }
    }

    /**
     * 提交前统一格式化版本号。
     */
    const documentVersion = normalizeDocumentVersion(values.version);

    console.log(documentVersion);
    submit({
      fileList: values.fileList,
      version: documentVersion,
      tags,
    });
  };

  return (
    <Form {...form}>
      <form
        id={UploadFormId}
        className="space-y-4"
        onSubmit={form.handleSubmit(onSubmit)}
      >
        {/* 文件上传 */}
        <RAGFlowFormItem name="fileList" label={t('fileManager.file')}>
          {(field) => (
            <FileUploader
              value={field.value}
              onValueChange={field.onChange}
              accept={{ '*': [] }}
            />
          )}
        </RAGFlowFormItem>

        {/* 版本号 */}
        <RAGFlowFormItem name="version" label="版本号">
          {(field) => (
            <div className="space-y-1.5">
              <input
                type="text"
                value={field.value || ''}
                placeholder="请输入版本号，例如 v1.0"
                onChange={(event) => {
                  field.onChange(event.target.value);
                }}
                onBlur={field.onBlur}
                className="
                  h-9
                  w-full
                  rounded-md
                  border
                  border-input
                  bg-background
                  px-3
                  py-2
                  text-sm
                  text-foreground
                  outline-none
                  transition-colors
                  placeholder:text-muted-foreground
                  focus:border-[#00A870]
                  focus:ring-1
                  focus:ring-[#00A870]/30
                  disabled:cursor-not-allowed
                  disabled:opacity-50
                "
              />

              <div className="text-xs text-muted-foreground">
                默认版本为 v1.0，也可填写 v1.1、v2.0 或 v2.3。
                一次上传的所有文件共用该版本号。
              </div>
            </div>
          )}
        </RAGFlowFormItem>

        {/* 标签加载状态 */}
        {tagLoading && (
          <div className="text-sm text-gray-400">标签配置加载中...</div>
        )}

        {/* 动态标签表单 */}
        {!tagLoading &&
          tagConfig
            // 不展示已禁用的标签类型
            .filter((tagType) => tagType.enabled !== false)
            .map((tagType) => {
              const fieldName = `tags.${tagType.type_code}` as const;

              // 不展示已禁用的标签选项
              const enabledOptions =
                tagType.options?.filter((option) => option.enabled !== false) ||
                [];

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

                    /**
                     * 多选标签。
                     */
                    if (tagType.multi_select) {
                      return (
                        <div
                          className="
                            flex
                            flex-wrap
                            gap-2
                            rounded-md
                            border
                            border-input
                            bg-background
                            p-3
                          "
                        >
                          {enabledOptions.length > 0 ? (
                            enabledOptions.map((option) => {
                              const checked = value.includes(
                                option.option_code,
                              );

                              return (
                                <label
                                  key={option.option_code}
                                  className={`
                                      inline-flex
                                      cursor-pointer
                                      items-center
                                      gap-2
                                      rounded-md
                                      border
                                      px-3
                                      py-1.5
                                      text-sm
                                      transition-colors
                                      ${
                                        checked
                                          ? 'border-[#00A870] bg-[#00A870]/10 text-[#008f60]'
                                          : 'border-input hover:bg-muted'
                                      }
                                    `}
                                >
                                  <input
                                    type="checkbox"
                                    checked={checked}
                                    disabled={form.formState.isSubmitting}
                                    onChange={(event) => {
                                      if (event.target.checked) {
                                        field.onChange([
                                          ...value,
                                          option.option_code,
                                        ]);
                                      } else {
                                        field.onChange(
                                          value.filter(
                                            (optionCode) =>
                                              optionCode !== option.option_code,
                                          ),
                                        );
                                      }
                                    }}
                                  />

                                  <span>{option.option_name}</span>
                                </label>
                              );
                            })
                          ) : (
                            <span className="text-sm text-muted-foreground">
                              暂无可选项
                            </span>
                          )}
                        </div>
                      );
                    }

                    /**
                     * 单选标签。
                     *
                     * 虽然是单选，保存时仍然使用数组：
                     * ["public"]
                     */
                    return (
                      <select
                        value={value[0] || ''}
                        disabled={form.formState.isSubmitting}
                        onChange={(event) => {
                          const selected = event.target.value;

                          field.onChange(selected ? [selected] : []);
                        }}
                        className="
                          w-full
                          rounded-md
                          border
                          border-input
                          bg-background
                          px-3
                          py-2
                          text-sm
                          text-foreground
                          outline-none
                          transition-colors
                          focus:border-[#00A870]
                          focus:ring-1
                          focus:ring-[#00A870]/30
                          disabled:cursor-not-allowed
                          disabled:opacity-50
                        "
                      >
                        <option value="">请选择{tagType.type_name}</option>

                        {enabledOptions.map((option) => (
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

/**
 * 文件上传弹窗。
 */
export function FileUploadDialog({
  hideModal,
  onOk,
  loading,
}: FileUploadDialogProps) {
  const { t } = useTranslation();

  return (
    <Dialog
      open
      onOpenChange={(open) => {
        if (!open) {
          hideModal();
        }
      }}
    >
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
