// // src/pages/next-search/search-setting.tsx

// import {
//   LlmSettingFieldItems,
//   LlmSettingSchema,
// } from '@/components/llm-setting-items/next';
// import { MetadataFilterSchema } from '@/components/metadata-filter';
// import { Button } from '@/components/ui/button';
// import { SingleFormSlider } from '@/components/ui/dual-range-slider';
// import {
//   Form,
//   FormControl,
//   FormField,
//   FormItem,
//   FormLabel,
//   FormMessage,
// } from '@/components/ui/form';
// import { Input } from '@/components/ui/input';
// import {
//   MultiSelect,
//   MultiSelectOptionType,
// } from '@/components/ui/multi-select';
// import { RAGFlowSelect } from '@/components/ui/select';
// import { Spin } from '@/components/ui/spin';
// import { Switch } from '@/components/ui/switch';
// import { useFetchKnowledgeList } from '@/hooks/use-knowledge-request';
// import {
//   useComposeLlmOptionsByModelTypes,
//   useSelectLlmOptionsByModelType,
// } from '@/hooks/use-llm-request';
// import { useFetchTenantInfo } from '@/hooks/use-user-setting-request';
// import { IKnowledge } from '@/interfaces/database/knowledge';
// import { cn } from '@/lib/utils';
// import { zodResolver } from '@hookform/resolvers/zod';
// import { X } from 'lucide-react';
// import { useCallback, useEffect, useMemo, useState } from 'react';
// import { useForm, useWatch } from 'react-hook-form';
// import { useTranslation } from 'react-i18next';
// import { z } from 'zod';
// import { LlmModelType } from '../dataset/dataset/constant';
// import {
//   ISearchAppDetailProps,
//   IUpdateSearchProps,
//   IllmSettingProps,
//   useUpdateSearch,
// } from '../next-searches/hooks';
// // import {
// //   LlmSettingFieldItems,
// //   LlmSettingSchema,
// // } from './search-setting-aisummery-config';

// interface SearchSettingProps {
//   open: boolean;
//   setOpen: (open: boolean) => void;
//   className?: string;
//   data: ISearchAppDetailProps;
// }

// const SearchSettingFormSchema = z
//   .object({
//     search_id: z.string().optional(),
//     name: z.string().min(1, 'Name is required'),
//     avatar: z.string().optional(),
//     description: z.string().optional(),
//     search_config: z.object({
//       kb_ids: z.array(z.string()).min(1, 'At least one dataset is required'),
//       vector_similarity_weight: z.number().min(0).max(1),
//       web_search: z.boolean(),
//       similarity_threshold: z.number(),
//       use_kg: z.boolean(),
//       rerank_id: z.string(),
//       use_rerank: z.boolean(),
//       top_k: z.number(),
//       summary: z.boolean(),
//       llm_setting: z.object(LlmSettingSchema),
//       related_search: z.boolean(),
//       query_mindmap: z.boolean(),
//       ...MetadataFilterSchema,
//     }),
//   })
//   .superRefine((data, ctx) => {
//     if (data.search_config.use_rerank && !data.search_config.rerank_id) {
//       ctx.addIssue({
//         path: ['search_config', 'rerank_id'],
//         message: 'Rerank model is required when rerank is enabled',
//         code: z.ZodIssueCode.custom,
//       });
//     }

//     if (data.search_config.summary && !data.search_config.llm_setting?.llm_id) {
//       ctx.addIssue({
//         path: ['search_config', 'llm_setting', 'llm_id'],
//         message: 'Model is required when AI Summary is enabled',
//         code: z.ZodIssueCode.custom,
//       });
//     }
//   });
// type SearchSettingFormData = z.infer<typeof SearchSettingFormSchema>;
// const SearchSetting: React.FC<SearchSettingProps> = ({
//   open = false,
//   setOpen,
//   className,
//   data,
// }) => {
//   const [width0, setWidth0] = useState('w-[440px]');
//   const { search_config } = data || {};
//   const { llm_setting } = search_config || {};
//   const formMethods = useForm<SearchSettingFormData>({
//     resolver: zodResolver(SearchSettingFormSchema),
//   });

//   const [datasetList, setDatasetList] = useState<MultiSelectOptionType[]>([]);
//   const [datasetSelectEmbdId, setDatasetSelectEmbdId] = useState('');
//   const { t } = useTranslation();
//   const descriptionDefaultValue = t('search.descriptionValue');
//   const resetForm = useCallback(() => {
//     formMethods.reset({
//       search_id: data?.id,
//       name: data?.name || '',
//       avatar: data?.avatar || '',
//       description: data?.description || descriptionDefaultValue,
//       search_config: {
//         kb_ids: search_config?.kb_ids || [],
//         vector_similarity_weight:
//           (search_config?.vector_similarity_weight
//             ? 1 - search_config?.vector_similarity_weight
//             : 0.3) || 0.3,
//         web_search: search_config?.web_search || false,
//         doc_ids: [],
//         similarity_threshold: search_config?.similarity_threshold || 0.2,
//         use_kg: false,
//         rerank_id: search_config?.rerank_id || '',
//         use_rerank: search_config?.rerank_id ? true : false,
//         top_k: search_config?.top_k || 1024,
//         summary: search_config?.summary || false,
//         chat_id: search_config?.chat_id || '',
//         llm_setting: {
//           llm_id: search_config?.chat_id || '',
//           parameter: llm_setting?.parameter,
//           temperature: llm_setting?.temperature || 0,
//           top_p: llm_setting?.top_p || 0,
//           frequency_penalty: llm_setting?.frequency_penalty || 0,
//           presence_penalty: llm_setting?.presence_penalty || 0,
//           temperatureEnabled: llm_setting?.temperature ? true : false,
//           topPEnabled: llm_setting?.top_p ? true : false,
//           presencePenaltyEnabled: llm_setting?.presence_penalty ? true : false,
//           frequencyPenaltyEnabled: llm_setting?.frequency_penalty
//             ? true
//             : false,
//         },
//         chat_settingcross_languages: [],
//         highlight: false,
//         keyword: false,
//         related_search: search_config?.related_search || false,
//         query_mindmap: search_config?.query_mindmap || false,
//         meta_data_filter: search_config?.meta_data_filter,
//       },
//     });
//   }, [data, search_config, llm_setting, formMethods, descriptionDefaultValue]);

//   useEffect(() => {
//     resetForm();
//   }, [resetForm]);

//   useEffect(() => {
//     if (!open) {
//       setTimeout(() => {
//         setWidth0('w-0 hidden');
//       }, 500);
//     } else {
//       setWidth0('w-[440px]');
//     }
//   }, [open]);

//   const { list: datasetListOrigin } = useFetchKnowledgeList();

//   useEffect(() => {
//     const datasetListMap = datasetListOrigin.map((item: IKnowledge) => {
//       return {
//         label: item.name,
//         suffix: (
//           <div className="text-xs px-4 p-1 bg-bg-card text-text-secondary rounded-lg border border-bg-card">
//             {item.embd_id}
//           </div>
//         ),
//         value: item.id,
//         disabled:
//           item.embd_id !== datasetSelectEmbdId && datasetSelectEmbdId !== '',
//       };
//     });
//     setDatasetList(datasetListMap);
//   }, [datasetListOrigin, datasetSelectEmbdId]);

//   const handleDatasetSelectChange = (
//     value: string[],
//     onChange: (value: string[]) => void,
//   ) => {
//     console.log(value);
//     if (value.length) {
//       const data = datasetListOrigin?.find((item) => item.id === value[0]);
//       setDatasetSelectEmbdId(data?.embd_id ?? '');
//     } else {
//       setDatasetSelectEmbdId('');
//     }
//     formMethods.setValue('search_config.kb_ids', value);
//     onChange?.(value);
//   };

//   const allOptions = useSelectLlmOptionsByModelType();
//   const rerankModelOptions = useMemo(() => {
//     return allOptions[LlmModelType.Rerank];
//   }, [allOptions]);

//   const aiSummeryModelOptions = useComposeLlmOptionsByModelTypes([
//     LlmModelType.Chat,
//     LlmModelType.Image2text,
//   ]);

//   const rerankModelDisabled = useWatch({
//     control: formMethods.control,
//     name: 'search_config.use_rerank',
//   });
//   const aiSummaryDisabled = useWatch({
//     control: formMethods.control,
//     name: 'search_config.summary',
//   });

//   const { updateSearch } = useUpdateSearch();
//   const [formSubmitLoading, setFormSubmitLoading] = useState(false);
//   const { data: systemSetting } = useFetchTenantInfo();
//   const onSubmit = async (
//     formData: IUpdateSearchProps & { tenant_id: string },
//   ) => {
//     try {
//       setFormSubmitLoading(true);
//       const { search_config, ...other_formdata } = formData;
//       const {
//         llm_setting,
//         vector_similarity_weight,
//         use_rerank,
//         rerank_id,
//         ...other_config
//       } = search_config;
//       const llmSetting = {
//         // llm_id: llm_setting.llm_id,
//         parameter: llm_setting.parameter,
//         temperature: llm_setting.temperature,
//         top_p: llm_setting.top_p,
//         frequency_penalty: llm_setting.frequency_penalty,
//         presence_penalty: llm_setting.presence_penalty,
//       } as IllmSettingProps;

//       await updateSearch({
//         ...other_formdata,
//         search_config: {
//           ...other_config,
//           chat_id: llm_setting.llm_id,
//           vector_similarity_weight: 1 - vector_similarity_weight,
//           rerank_id: use_rerank ? rerank_id : '',
//           llm_setting: { ...llmSetting },
//         },
//         tenant_id: systemSetting.tenant_id,
//       });
//       setOpen(false);
//     } catch (error) {
//       console.error('Failed to update search:', error);
//     } finally {
//       setFormSubmitLoading(false);
//     }
//   };
//   return (
//     <div
//       className={cn(
//         'text-text-primary border p-4 pb-12 rounded-lg',
//         {
//           'animate-fade-in-right': open,
//           'animate-fade-out-right': !open,
//         },
//         width0,
//         className,
//       )}
//       style={{ maxHeight: 'calc(100dvh - 170px)' }}
//     >
//       <div className="flex justify-between items-center text-base mb-8">
//         <div className="text-text-primary">{t('search.searchSettings')}</div>
//         <div onClick={() => setOpen(false)}>
//           <X size={16} className="text-text-primary cursor-pointer" />
//         </div>
//       </div>
//       <div
//         style={{ maxHeight: 'calc(100dvh - 270px)' }}
//         className="overflow-y-auto scrollbar-auto p-1 text-text-secondary"
//       >
//         <Form {...formMethods}>
//           <form
//             onSubmit={formMethods.handleSubmit(
//               (data) => {
//                 console.log('Form submitted with data:', data);
//                 onSubmit(data as unknown as IUpdateSearchProps);
//               },
//               (errors) => {
//                 console.log('Validation errors:', errors);
//               },
//             )}
//             className="space-y-6"
//           >
//             {/* Name */}
//             <FormField
//               control={formMethods.control}
//               name="name"
//               render={({ field }) => (
//                 <FormItem>
//                   <FormLabel>
//                     <span className="text-destructive mr-1"> *</span>
//                     {/* {t('search.name')} */ '搜索主题'}
//                   </FormLabel>
//                   <FormControl>
//                     <Input placeholder={t('search.name')} {...field} />
//                   </FormControl>
//                   <FormMessage />
//                 </FormItem>
//               )}
//             />
//             {/* Avatar */}
//             {/* <FormField
//               control={formMethods.control}
//               name="avatar"
//               render={({ field }) => (
//                 <FormItem>
//                   <FormLabel>{t('search.avatar')}</FormLabel>
//                   <FormControl>
//                     <AvatarUpload {...field}></AvatarUpload>
//                   </FormControl>
//                   <FormMessage />
//                 </FormItem>
//               )}
//             /> */}
//             {/* Description */}
//             {/* <FormField
//               control={formMethods.control}
//               name="description"
//               render={({ field }) => (
//                 <FormItem>
//                   <FormLabel>{t('search.description')}</FormLabel>
//                   <FormControl>
//                     <Textarea
//                       placeholder={descriptionDefaultValue}
//                       {...field}
//                       onFocus={() => {
//                         if (field.value === descriptionDefaultValue) {
//                           field.onChange('');
//                         }
//                       }}
//                       onBlur={() => {
//                         if (field.value === '') {
//                           field.onChange(descriptionDefaultValue);
//                         }
//                       }}
//                     />
//                   </FormControl>
//                   <FormMessage />
//                 </FormItem>
//               )}
//             /> */}
//             {/* Datasets */}
//             <FormField
//               control={formMethods.control}
//               name="search_config.kb_ids"
//               rules={{ required: 'Datasets is required' }}
//               render={({ field }) => (
//                 <FormItem>
//                   <FormLabel>
//                     <span className="text-destructive mr-1"> *</span>
//                     {t('search.datasets')}
//                   </FormLabel>
//                   <FormControl className="bg-bg-input">
//                     <MultiSelect
//                       options={datasetList}
//                       onValueChange={(value) => {
//                         handleDatasetSelectChange(value, field.onChange);
//                       }}
//                       showSelectAll={false}
//                       placeholder={t('chat.knowledgeBasesMessage')}
//                       maxCount={10}
//                       defaultValue={field.value}
//                       {...field}
//                     />
//                   </FormControl>
//                   <FormMessage />
//                 </FormItem>
//               )}
//             />
//             {/* <MetadataFilter prefix="search_config."></MetadataFilter> */}
//             {/* <SimilaritySliderFormField
//               // isTooltipShown
//               similarityName="search_config.similarity_threshold"
//               vectorSimilarityWeightName="search_config.vector_similarity_weight"
//               numberInputClassName="rounded-sm"
//             ></SimilaritySliderFormField> */}
//             {/* Rerank Model */}
//             <FormField
//               control={formMethods.control}
//               name="search_config.use_rerank"
//               render={({ field }) => (
//                 <FormItem className="flex flex-row items-start space-x-3 space-y-0">
//                   <FormControl>
//                     <Switch
//                       checked={field.value}
//                       onCheckedChange={field.onChange}
//                     />
//                   </FormControl>
//                   <FormLabel>{t('search.rerankModel')}</FormLabel>
//                 </FormItem>
//               )}
//             />
//             {rerankModelDisabled && (
//               <>
//                 <FormField
//                   control={formMethods.control}
//                   name={'search_config.rerank_id'}
//                   // rules={{ required: 'Model is required' }}
//                   render={({ field }) => (
//                     <FormItem className="flex flex-col">
//                       <FormLabel>
//                         <span className="text-destructive mr-1"> *</span>
//                         {t('chat.model')}
//                       </FormLabel>
//                       <FormControl>
//                         <RAGFlowSelect
//                           {...field}
//                           options={rerankModelOptions}
//                           triggerClassName={'bg-bg-input'}
//                           // disabled={disabled}
//                           placeholder={t('chat.model')}
//                         />
//                       </FormControl>
//                       <FormMessage />
//                     </FormItem>
//                   )}
//                 />
//                 <FormField
//                   control={formMethods.control}
//                   name="search_config.top_k"
//                   render={({ field }) => (
//                     <FormItem>
//                       <FormLabel>Top K</FormLabel>
//                       <div
//                         className={cn(
//                           'flex items-center gap-4 justify-between',
//                           className,
//                         )}
//                       >
//                         <FormControl>
//                           <SingleFormSlider
//                             {...field}
//                             max={2048}
//                             min={0}
//                             step={1}
//                           ></SingleFormSlider>
//                         </FormControl>
//                         <FormControl>
//                           <Input
//                             type={'number'}
//                             className="h-7 w-20 bg-bg-card border border-border-button rounded-sm"
//                             max={2048}
//                             min={0}
//                             step={1}
//                             {...field}
//                           ></Input>
//                         </FormControl>
//                       </div>
//                       <FormMessage />
//                     </FormItem>
//                   )}
//                 />
//               </>
//             )}
//             {/* AI Summary */}
//             <FormField
//               control={formMethods.control}
//               name="search_config.summary"
//               render={({ field }) => (
//                 <FormItem className="flex flex-row items-start space-x-3 space-y-0">
//                   <FormControl>
//                     <Switch
//                       checked={field.value}
//                       onCheckedChange={field.onChange}
//                     />
//                   </FormControl>
//                   <FormLabel>{t('search.AISummary')}</FormLabel>
//                 </FormItem>
//               )}
//             />
//             {aiSummaryDisabled && (
//               // <LlmSettingFieldItems
//               //   prefix="search_config.llm_setting"
//               //   options={aiSummeryModelOptions}
//               // ></LlmSettingFieldItems>
//               <LlmSettingFieldItems
//                 prefix="search_config.llm_setting"
//                 options={aiSummeryModelOptions}
//                 showFields={[
//                   'temperature',
//                   'top_p',
//                   'presence_penalty',
//                   'frequency_penalty',
//                 ]}
//               ></LlmSettingFieldItems>
//             )}
//             {/* Feature Controls */}
//             {/* <FormField
//               control={formMethods.control}
//               name="search_config.web_search"
//               render={({ field }) => (
//                 <FormItem className="flex flex-row items-start space-x-3 space-y-0">
//                   <FormControl>
//                     <Switch
//                       checked={field.value}
//                       onCheckedChange={field.onChange}
//                     />
//                   </FormControl>
//                   <FormLabel>{t('search.enableWebSearch')}</FormLabel>
//                 </FormItem>
//               )}
//             /> */}

//             {/* <FormField
//               control={formMethods.control}
//               name="search_config.related_search"
//               render={({ field }) => (
//                 <FormItem className="flex flex-row items-start space-x-3 space-y-0">
//                   <FormControl>
//                     <Switch
//                       checked={field.value}
//                       onCheckedChange={field.onChange}
//                     />
//                   </FormControl>
//                   <FormLabel>{t('search.enableRelatedSearch')}</FormLabel>
//                 </FormItem>
//               )}
//             /> */}
//             {/* <FormField
//               control={formMethods.control}
//               name="search_config.query_mindmap"
//               render={({ field }) => (
//                 <FormItem className="flex flex-row items-start space-x-3 space-y-0">
//                   <FormControl>
//                     <Switch
//                       checked={field.value}
//                       onCheckedChange={field.onChange}
//                     />
//                   </FormControl>
//                   <FormLabel>{t('search.showQueryMindmap')}</FormLabel>
//                 </FormItem>
//               )}
//             /> */}
//             {/* Submit Button */}
//             <div className="flex justify-end"></div>
//             <div className="flex justify-end gap-2 absolute bottom-1 right-3 bg-bg-base w-[calc(100%-1em)] py-2">
//               <Button
//                 type="reset"
//                 variant={'transparent'}
//                 onClick={() => {
//                   resetForm();
//                   setOpen(false);
//                 }}
//               >
//                 {t('search.cancelText')}
//               </Button>
//               <Button type="submit" disabled={formSubmitLoading}>
//                 {formSubmitLoading && (
//                   <div className="size-4">
//                     <Spin size="small" />
//                   </div>
//                 )}
//                 {t('search.okText')}
//               </Button>
//             </div>
//           </form>
//         </Form>
//       </div>
//     </div>
//   );
// };

// export { SearchSetting };

import {
  LlmSettingFieldItems,
  LlmSettingSchema,
} from '@/components/llm-setting-items/next';
import { MetadataFilterSchema } from '@/components/metadata-filter';
import { Button } from '@/components/ui/button';
import { SingleFormSlider } from '@/components/ui/dual-range-slider';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import {
  MultiSelect,
  MultiSelectOptionType,
} from '@/components/ui/multi-select';
import { RAGFlowSelect } from '@/components/ui/select';
import { Spin } from '@/components/ui/spin';
import { Switch } from '@/components/ui/switch';
import { useFetchKnowledgeList } from '@/hooks/use-knowledge-request';
import {
  useComposeLlmOptionsByModelTypes,
  useSelectLlmOptionsByModelType,
} from '@/hooks/use-llm-request';
import { useFetchTenantInfo } from '@/hooks/use-user-setting-request';
import { IKnowledge } from '@/interfaces/database/knowledge';
import { cn } from '@/lib/utils';
import { getAuthorization } from '@/utils/authorization-util';
import { zodResolver } from '@hookform/resolvers/zod';
import { message } from 'antd';
import { X } from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useForm, useWatch } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { z } from 'zod';
import { LlmModelType } from '../dataset/dataset/constant';
import {
  ISearchAppDetailProps,
  IUpdateSearchProps,
  IllmSettingProps,
  useUpdateSearch,
} from '../next-searches/hooks';

interface SearchSettingProps {
  open: boolean;
  setOpen: (open: boolean) => void;
  className?: string;
  data: ISearchAppDetailProps;
}

interface FilterOption {
  id: string;
  label: string;
  count?: number;
}

interface FilterCollection {
  type: 'checkbox' | 'radio' | 'text' | 'date-range';
  field: string;
  label: string;
  list?: FilterOption[];
  placeholder?: string;
  multiple?: boolean;
  required?: boolean;
}

interface KnowledgeTagOption {
  option_code: string;
  option_name: string;
  sort_order?: number;
  count?: number;
}

interface KnowledgeTagType {
  multi_select: boolean;
  required?: boolean;
  sort_order?: number;
  type_code: string;
  type_name: string;
  options?: KnowledgeTagOption[];
}

interface TagConfigResponse {
  code: number;
  message?: string;
  data?: KnowledgeTagType[];
}

/**
 * 标签配置接口
 */
function useFetchTagConfig() {
  const [tagConfig, setTagConfig] = useState<KnowledgeTagType[]>([]);

  const [loading, setLoading] = useState(false);

  const fetchTagConfig = useCallback(async () => {
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

      if (!res.ok) {
        throw new Error(`请求失败：${res.status}`);
      }

      const result = (await res.json()) as TagConfigResponse;

      if (result.code === 0 || result.code === 200) {
        setTagConfig(result.data || []);
      } else {
        message.error(result.message || '获取标签配置失败');
      }
    } catch (error) {
      console.error('获取标签配置失败：', error);

      message.error('获取标签配置请求失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTagConfig();
  }, [fetchTagConfig]);

  return {
    tagConfig,
    loading,
    refetch: fetchTagConfig,
  };
}

/**
 * tag 中的文本或者选择值
 */
const TagItemValueSchema = z.union([z.string(), z.array(z.string())]);

/**
 * tag 表单结构
 *
 * meta_data_filter 与 tag 是两个不同的字段。
 */
const TagSchema = z
  .object({
    suffix: TagItemValueSchema.default([]),

    run_status: TagItemValueSchema.default([]),

    version: z.string().default(''),

    document_status: TagItemValueSchema.default([]),

    applicable_lines: TagItemValueSchema.default([]),

    knowledge_category: TagItemValueSchema.default([]),

    knowledge_level: TagItemValueSchema.default([]),

    knowledge_type: TagItemValueSchema.default([]),

    author: z.string().default(''),

    school: z.string().default(''),

    publish_date: z.array(z.string()).default([]),
  })
  .catchall(TagItemValueSchema);

const SearchSettingFormSchema = z
  .object({
    search_id: z.string().optional(),

    name: z.string().min(1, 'Name is required'),

    avatar: z.string().optional(),

    description: z.string().optional(),

    search_config: z.object({
      kb_ids: z.array(z.string()).min(1, 'At least one dataset is required'),

      tag: TagSchema,

      vector_similarity_weight: z.number().min(0).max(1),

      web_search: z.boolean(),

      similarity_threshold: z.number(),

      use_kg: z.boolean(),

      rerank_id: z.string(),

      use_rerank: z.boolean(),

      top_k: z.number(),

      summary: z.boolean(),

      chat_id: z.string().optional(),

      llm_setting: z.object(LlmSettingSchema),

      related_search: z.boolean(),

      query_mindmap: z.boolean(),

      /**
       * 原来的 meta_data_filter 保留
       */
      ...MetadataFilterSchema,

      /**
       * 兼容原表单中存在的字段
       */
      doc_ids: z.array(z.string()).optional(),

      chat_settingcross_languages: z.array(z.string()).optional(),

      highlight: z.boolean().optional(),

      keyword: z.boolean().optional(),
    }),
  })
  .superRefine((data, ctx) => {
    if (data.search_config.use_rerank && !data.search_config.rerank_id) {
      ctx.addIssue({
        path: ['search_config', 'rerank_id'],
        message: 'Rerank model is required when rerank is enabled',
        code: z.ZodIssueCode.custom,
      });
    }

    if (data.search_config.summary && !data.search_config.llm_setting?.llm_id) {
      ctx.addIssue({
        path: ['search_config', 'llm_setting', 'llm_id'],
        message: 'Model is required when AI Summary is enabled',
        code: z.ZodIssueCode.custom,
      });
    }
  });

type SearchSettingFormData = z.infer<typeof SearchSettingFormSchema>;

type TagValue = z.infer<typeof TagSchema>;

const emptyTag: TagValue = {
  suffix: [],
  run_status: [],
  version: '',
  document_status: [],
  applicable_lines: [],
  knowledge_category: [],
  knowledge_level: [],
  knowledge_type: [],
  author: '',
  school: '',
  publish_date: [],
};

const SearchSetting: React.FC<SearchSettingProps> = ({
  open = false,
  setOpen,
  className,
  data,
}) => {
  const { tagConfig, loading: tagConfigLoading } = useFetchTagConfig();

  const [width0, setWidth0] = useState('w-[440px]');

  const { search_config } = data || {};

  const { llm_setting } = search_config || {};

  const { t } = useTranslation();

  const descriptionDefaultValue = t('search.descriptionValue');

  const formMethods = useForm<SearchSettingFormData>({
    resolver: zodResolver(SearchSettingFormSchema),
    defaultValues: {
      search_id: data?.id || '',
      name: data?.name || '',
      avatar: data?.avatar || '',
      description: data?.description || descriptionDefaultValue,

      search_config: {
        kb_ids: [],

        tag: emptyTag,

        vector_similarity_weight: 0.3,

        web_search: false,

        similarity_threshold: 0.2,

        use_kg: false,

        rerank_id: '',

        use_rerank: false,

        top_k: 1024,

        summary: false,

        chat_id: '',

        related_search: false,

        query_mindmap: false,

        doc_ids: [],

        chat_settingcross_languages: [],

        highlight: false,

        keyword: false,

        meta_data_filter: {},

        llm_setting: {
          llm_id: '',
          parameter: undefined,
          temperature: 0,
          top_p: 0,
          frequency_penalty: 0,
          presence_penalty: 0,
          temperatureEnabled: false,
          topPEnabled: false,
          presencePenaltyEnabled: false,
          frequencyPenaltyEnabled: false,
        },
      },
    },
  });

  /**
   * 动态生成标签筛选项
   */
  const tagFilters = useMemo<FilterCollection[]>(() => {
    /**
     * 以下字段使用固定控件，不使用后端 options
     */
    const fixedFields = new Set([
      'version',
      'author',
      'school',
      'publish_date',
    ]);

    /**
     * 根据后端 tag config 动态生成标签
     */
    const dynamicFilters: FilterCollection[] = tagConfig
      .filter((tag) => !fixedFields.has(tag.type_code))
      .sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0))
      .map((tag) => {
        const options: FilterOption[] = (tag.options || [])
          .slice()
          .sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0))
          .map((option) => ({
            id: option.option_name,
            label: option.option_name,
            count: option.count,
          }));

        return {
          type: tag.multi_select ? 'checkbox' : 'radio',

          field: tag.type_code,

          label: tag.type_name,

          list: options,

          multiple: tag.multi_select,

          required: tag.required,
        };
      });

    /**
     * 固定字段
     */
    const fixedFilters: FilterCollection[] = [
      {
        type: 'text',
        field: 'version',
        label: '版本',
        placeholder: '请输入版本',
      },
      {
        type: 'text',
        field: 'author',
        label: '作者',
        placeholder: '请输入作者姓名',
      },
      {
        type: 'text',
        field: 'school',
        label: '学校',
        placeholder: '请输入学校名称',
      },
      {
        type: 'date-range',
        field: 'publish_date',
        label: '发布时间',
      },
    ];

    return [...dynamicFilters, ...fixedFilters];
  }, [tagConfig]);

  const [datasetList, setDatasetList] = useState<MultiSelectOptionType[]>([]);

  const [datasetSelectEmbdId, setDatasetSelectEmbdId] = useState('');

  const resetForm = useCallback(() => {
    /**
     * 如果 ISearchAppDetailProps 暂时没有 tag 类型，
     * 使用兼容读取，避免类型报错。
     */
    const oldConfig = (search_config || {}) as typeof search_config & {
      tag?: Partial<TagValue>;
    };

    const oldTag = oldConfig.tag || {};

    formMethods.reset({
      search_id: data?.id || '',

      name: data?.name || '',

      avatar: data?.avatar || '',

      description: data?.description || descriptionDefaultValue,

      search_config: {
        kb_ids: search_config?.kb_ids || [],

        tag: {
          ...emptyTag,
          ...oldTag,

          suffix: oldTag.suffix || [],

          run_status: oldTag.run_status || [],

          version: typeof oldTag.version === 'string' ? oldTag.version : '',

          document_status: oldTag.document_status || [],

          applicable_lines: oldTag.applicable_lines || [],

          knowledge_category: oldTag.knowledge_category || [],

          knowledge_level: oldTag.knowledge_level || [],

          knowledge_type: oldTag.knowledge_type || [],

          author: typeof oldTag.author === 'string' ? oldTag.author : '',

          school: typeof oldTag.school === 'string' ? oldTag.school : '',

          publish_date: Array.isArray(oldTag.publish_date)
            ? oldTag.publish_date
            : [],
        },

        vector_similarity_weight:
          search_config?.vector_similarity_weight !== undefined
            ? 1 - search_config.vector_similarity_weight
            : 0.3,

        web_search: search_config?.web_search || false,

        doc_ids: [],

        similarity_threshold: search_config?.similarity_threshold ?? 0.2,

        use_kg: search_config?.use_kg || false,

        rerank_id: search_config?.rerank_id || '',

        use_rerank: Boolean(search_config?.rerank_id),

        top_k: search_config?.top_k ?? 1024,

        summary: search_config?.summary || false,

        chat_id: search_config?.chat_id || '',

        llm_setting: {
          llm_id: search_config?.chat_id || '',

          parameter: llm_setting?.parameter,

          temperature: llm_setting?.temperature ?? 0,

          top_p: llm_setting?.top_p ?? 0,

          frequency_penalty: llm_setting?.frequency_penalty ?? 0,

          presence_penalty: llm_setting?.presence_penalty ?? 0,

          temperatureEnabled: Boolean(llm_setting?.temperature),

          topPEnabled: Boolean(llm_setting?.top_p),

          presencePenaltyEnabled: Boolean(llm_setting?.presence_penalty),

          frequencyPenaltyEnabled: Boolean(llm_setting?.frequency_penalty),
        },

        chat_settingcross_languages: [],

        highlight: false,

        keyword: false,

        related_search: search_config?.related_search || false,

        query_mindmap: search_config?.query_mindmap || false,

        /**
         * 原来的 meta_data_filter 保留
         */
        meta_data_filter: search_config?.meta_data_filter,
      },
    });
  }, [data, search_config, llm_setting, formMethods, descriptionDefaultValue]);

  useEffect(() => {
    resetForm();
  }, [resetForm]);

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout> | undefined;

    if (!open) {
      timer = setTimeout(() => {
        setWidth0('w-0 hidden');
      }, 500);
    } else {
      setWidth0('w-[440px]');
    }

    return () => {
      if (timer) {
        clearTimeout(timer);
      }
    };
  }, [open]);

  const { list: datasetListOrigin } = useFetchKnowledgeList();

  useEffect(() => {
    const datasetListMap = datasetListOrigin.map((item: IKnowledge) => ({
      label: item.name,

      suffix: (
        <div className="text-xs px-4 p-1 bg-bg-card text-text-secondary rounded-lg border border-bg-card">
          {item.embd_id}
        </div>
      ),

      value: item.id,

      disabled:
        item.embd_id !== datasetSelectEmbdId && datasetSelectEmbdId !== '',
    }));

    setDatasetList(datasetListMap);
  }, [datasetListOrigin, datasetSelectEmbdId]);

  const handleDatasetSelectChange = (
    value: string[],
    onChange: (value: string[]) => void,
  ) => {
    if (value.length > 0) {
      const selectedDataset = datasetListOrigin?.find(
        (item) => item.id === value[0],
      );

      setDatasetSelectEmbdId(selectedDataset?.embd_id || '');
    } else {
      setDatasetSelectEmbdId('');
    }

    formMethods.setValue('search_config.kb_ids', value, {
      shouldDirty: true,
      shouldValidate: true,
    });

    onChange(value);
  };

  const allOptions = useSelectLlmOptionsByModelType();

  const rerankModelOptions = useMemo(() => {
    return allOptions[LlmModelType.Rerank];
  }, [allOptions]);

  const aiSummeryModelOptions = useComposeLlmOptionsByModelTypes([
    LlmModelType.Chat,
    LlmModelType.Image2text,
  ]);

  const rerankModelDisabled = useWatch({
    control: formMethods.control,
    name: 'search_config.use_rerank',
  });

  const aiSummaryDisabled = useWatch({
    control: formMethods.control,
    name: 'search_config.summary',
  });

  const tagValue = useWatch({
    control: formMethods.control,
    name: 'search_config.tag',
  });

  const { updateSearch } = useUpdateSearch();

  const [formSubmitLoading, setFormSubmitLoading] = useState(false);

  const { data: systemSetting } = useFetchTenantInfo();

  const onSubmit = async (formData: SearchSettingFormData) => {
    try {
      setFormSubmitLoading(true);

      const { search_config, ...otherFormData } = formData;

      const {
        llm_setting,
        vector_similarity_weight,
        use_rerank,
        rerank_id,
        ...otherConfig
      } = search_config;

      const llmSetting = {
        parameter: llm_setting.parameter,

        temperature: llm_setting.temperature,

        top_p: llm_setting.top_p,

        frequency_penalty: llm_setting.frequency_penalty,

        presence_penalty: llm_setting.presence_penalty,
      } as IllmSettingProps;

      await updateSearch({
        ...otherFormData,

        search_config: {
          ...otherConfig,

          chat_id: llm_setting.llm_id,

          vector_similarity_weight: 1 - vector_similarity_weight,

          rerank_id: use_rerank ? rerank_id : '',

          llm_setting: {
            ...llmSetting,
          },

          meta_data_filter: search_config.meta_data_filter,

          tag: {
            ...search_config.tag,
          },
        },

        tenant_id: systemSetting?.tenant_id || '',
      } as IUpdateSearchProps & {
        tenant_id: string;
      });

      setOpen(false);
    } catch (error) {
      console.error('Failed to update search:', error);
    } finally {
      setFormSubmitLoading(false);
    }
  };

  return (
    <div
      className={cn(
        'text-text-primary border p-4 pb-12 rounded-lg',
        {
          'animate-fade-in-right': open,

          'animate-fade-out-right': !open,
        },
        width0,
        className,
      )}
      style={{
        maxHeight: 'calc(100dvh - 170px)',
      }}
    >
      <div className="flex justify-between items-center text-base mb-8">
        <div className="text-text-primary">{t('search.searchSettings')}</div>

        <div onClick={() => setOpen(false)}>
          <X size={16} className="text-text-primary cursor-pointer" />
        </div>
      </div>

      <div
        style={{
          maxHeight: 'calc(100dvh - 270px)',
        }}
        className="overflow-y-auto scrollbar-auto p-1 text-text-secondary"
      >
        <Form {...formMethods}>
          <form
            onSubmit={formMethods.handleSubmit(
              async (formData) => {
                console.log('Form submitted with data:', formData);

                await onSubmit(formData);
              },
              (errors) => {
                console.log('Validation errors:', errors);
              },
            )}
            className="space-y-6"
          >
            {/* Name */}
            <FormField
              control={formMethods.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>
                    <span className="text-destructive mr-1">*</span>
                    搜索主题
                  </FormLabel>

                  <FormControl>
                    <Input placeholder={t('search.name')} {...field} />
                  </FormControl>

                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Datasets */}
            <FormField
              control={formMethods.control}
              name="search_config.kb_ids"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>
                    <span className="text-destructive mr-1">*</span>
                    {t('search.datasets')}
                  </FormLabel>

                  <FormControl className="bg-bg-input">
                    <MultiSelect
                      options={datasetList}
                      onValueChange={(value) => {
                        handleDatasetSelectChange(value, field.onChange);
                      }}
                      showSelectAll={false}
                      placeholder={t('chat.knowledgeBasesMessage')}
                      maxCount={10}
                      value={field.value}
                    />
                  </FormControl>

                  <FormMessage />
                </FormItem>
              )}
            />

            {/* 标签筛选 */}
            <div className="space-y-4 rounded-lg border p-3">
              <div className="text-sm font-medium text-text-primary">
                标签筛选
              </div>

              {tagConfigLoading && (
                <div className="text-sm text-text-secondary">标签加载中...</div>
              )}

              {!tagConfigLoading &&
                tagFilters.map((filter) => {
                  const currentValue =
                    tagValue?.[filter.field as keyof TagValue];

                  /**
                   * 多选
                   */
                  if (filter.type === 'checkbox') {
                    const selectedValues = Array.isArray(currentValue)
                      ? currentValue
                      : [];

                    return (
                      <div key={filter.field} className="space-y-2">
                        <div className="text-sm text-text-primary">
                          {filter.label}

                          {filter.required && (
                            <span className="ml-1 text-destructive">*</span>
                          )}
                        </div>

                        <div className="flex flex-wrap gap-2">
                          {filter.list?.map((item) => {
                            const checked = selectedValues.includes(item.id);

                            return (
                              <button
                                key={item.id}
                                type="button"
                                onClick={() => {
                                  const nextValue = checked
                                    ? selectedValues.filter(
                                        (value) => value !== item.id,
                                      )
                                    : [...selectedValues, item.id];

                                  formMethods.setValue(
                                    `search_config.tag.${filter.field}` as any,
                                    nextValue,
                                    {
                                      shouldDirty: true,
                                      shouldValidate: true,
                                    },
                                  );
                                }}
                                className={cn(
                                  'rounded-md border px-2 py-1 text-xs',
                                  checked
                                    ? 'border-primary bg-transparent text-primary'
                                    : 'border-border bg-bg-card text-text-secondary',
                                )}
                              >
                                {item.label}

                                {typeof item.count === 'number' &&
                                  ` (${item.count})`}
                              </button>
                            );
                          })}
                        </div>
                      </div>
                    );
                  }

                  /**
                   * 单选
                   */
                  if (filter.type === 'radio') {
                    const selectedValue =
                      typeof currentValue === 'string' ? currentValue : '';

                    return (
                      <div key={filter.field} className="space-y-2">
                        <div className="text-sm text-text-primary">
                          {filter.label}

                          {filter.required && (
                            <span className="ml-1 text-destructive">*</span>
                          )}
                        </div>

                        <div className="flex flex-wrap gap-2">
                          {filter.list?.map((item) => {
                            const checked = selectedValue === item.id;

                            return (
                              <button
                                key={item.id}
                                type="button"
                                onClick={() => {
                                  formMethods.setValue(
                                    `search_config.tag.${filter.field}` as any,
                                    item.id,
                                    {
                                      shouldDirty: true,
                                      shouldValidate: true,
                                    },
                                  );
                                }}
                                className={cn(
                                  'rounded-md border px-2 py-1 text-xs',
                                  checked
                                    ? 'border-primary bg-primary text-white'
                                    : 'border-border bg-bg-card text-text-secondary',
                                )}
                              >
                                {item.label}

                                {typeof item.count === 'number' &&
                                  ` (${item.count})`}
                              </button>
                            );
                          })}
                        </div>
                      </div>
                    );
                  }

                  /**
                   * 文本输入
                   */
                  if (filter.type === 'text') {
                    return (
                      <FormField
                        key={filter.field}
                        control={formMethods.control}
                        name={`search_config.tag.${filter.field}` as any}
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel>{filter.label}</FormLabel>

                            <FormControl>
                              <Input
                                {...field}
                                value={field.value || ''}
                                placeholder={filter.placeholder}
                              />
                            </FormControl>

                            <FormMessage />
                          </FormItem>
                        )}
                      />
                    );
                  }

                  /**
                   * 日期范围
                   */
                  if (filter.type === 'date-range') {
                    const dateValue = Array.isArray(currentValue)
                      ? currentValue
                      : ['', ''];

                    return (
                      <div key={filter.field} className="space-y-2">
                        <div className="text-sm text-text-primary">
                          {filter.label}
                        </div>

                        <div className="flex gap-2">
                          <Input
                            type="date"
                            value={dateValue[0] || ''}
                            onChange={(event) => {
                              formMethods.setValue(
                                `search_config.tag.${filter.field}` as any,
                                [event.target.value, dateValue[1] || ''],
                                {
                                  shouldDirty: true,
                                  shouldValidate: true,
                                },
                              );
                            }}
                          />

                          <Input
                            type="date"
                            value={dateValue[1] || ''}
                            onChange={(event) => {
                              formMethods.setValue(
                                `search_config.tag.${filter.field}` as any,
                                [dateValue[0] || '', event.target.value],
                                {
                                  shouldDirty: true,
                                  shouldValidate: true,
                                },
                              );
                            }}
                          />
                        </div>
                      </div>
                    );
                  }

                  return null;
                })}
            </div>

            {/* Rerank Model */}
            <FormField
              control={formMethods.control}
              name="search_config.use_rerank"
              render={({ field }) => (
                <FormItem className="flex flex-row items-start space-x-3 space-y-0">
                  <FormControl>
                    <Switch
                      checked={field.value}
                      onCheckedChange={field.onChange}
                    />
                  </FormControl>

                  <FormLabel>{t('search.rerankModel')}</FormLabel>
                </FormItem>
              )}
            />

            {rerankModelDisabled && (
              <>
                <FormField
                  control={formMethods.control}
                  name="search_config.rerank_id"
                  render={({ field }) => (
                    <FormItem className="flex flex-col">
                      <FormLabel>
                        <span className="text-destructive mr-1">*</span>
                        {t('chat.model')}
                      </FormLabel>

                      <FormControl>
                        <RAGFlowSelect
                          {...field}
                          options={allOptions[LlmModelType.Rerank]}
                          triggerClassName="bg-bg-input"
                          placeholder={t('chat.model')}
                        />
                      </FormControl>

                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={formMethods.control}
                  name="search_config.top_k"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Top K</FormLabel>

                      <div
                        className={cn(
                          'flex items-center gap-4 justify-between',
                          className,
                        )}
                      >
                        <FormControl>
                          <SingleFormSlider
                            {...field}
                            max={2048}
                            min={0}
                            step={1}
                          />
                        </FormControl>

                        <Input
                          type="number"
                          className="h-7 w-20 bg-bg-card border border-border-button rounded-sm"
                          max={2048}
                          min={0}
                          step={1}
                          {...field}
                          onChange={(event) => {
                            field.onChange(Number(event.target.value));
                          }}
                        />
                      </div>

                      <FormMessage />
                    </FormItem>
                  )}
                />
              </>
            )}

            {/* AI Summary */}
            <FormField
              control={formMethods.control}
              name="search_config.summary"
              render={({ field }) => (
                <FormItem className="flex flex-row items-start space-x-3 space-y-0">
                  <FormControl>
                    <Switch
                      checked={field.value}
                      onCheckedChange={field.onChange}
                    />
                  </FormControl>

                  <FormLabel>{t('search.AISummary')}</FormLabel>
                </FormItem>
              )}
            />

            {aiSummaryDisabled && (
              <LlmSettingFieldItems
                prefix="search_config.llm_setting"
                options={aiSummeryModelOptions}
                showFields={[
                  'temperature',
                  'top_p',
                  'presence_penalty',
                  'frequency_penalty',
                ]}
              />
            )}

            {/* Submit */}
            <div className="h-14" />

            <div className="flex justify-end gap-2 absolute bottom-1 right-3 bg-bg-base w-[calc(100%-1em)] py-2">
              <Button
                type="reset"
                variant="transparent"
                onClick={() => {
                  resetForm();
                  setOpen(false);
                }}
              >
                {t('search.cancelText')}
              </Button>

              <Button
                type="submit"
                disabled={formSubmitLoading || tagConfigLoading}
              >
                {formSubmitLoading && (
                  <div className="size-4">
                    <Spin size="small" />
                  </div>
                )}

                {t('search.okText')}
              </Button>
            </div>
          </form>
        </Form>
      </div>
    </div>
  );
};

export { SearchSetting };
