import { DocumentParserType } from '@/constants/knowledge';
import { useTranslate } from '@/hooks/common-hooks';
import { useFetchKnowledgeList } from '@/hooks/use-knowledge-request';
import { useBuildQueryVariableOptions } from '@/pages/agent/hooks/use-get-begin-query';
import { UserOutlined } from '@ant-design/icons';
import { Avatar as AntAvatar, Form, Select, Space } from 'antd';
import { toLower } from 'lodash';
import { useMemo, useRef } from 'react';
import { useFormContext } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { RAGFlowAvatar } from './ragflow-avatar';
import { FormControl, FormField, FormItem, FormLabel } from './ui/form';
import { MultiSelect } from './ui/multi-select';

interface KnowledgeBaseItemProps {
  label?: string;
  tooltipText?: string;
  name?: string;
  required?: boolean;
  onChange?(): void;
}

const KnowledgeBaseItem = ({
  label,
  tooltipText,
  name,
  required = true,
  onChange,
}: KnowledgeBaseItemProps) => {
  const { t } = useTranslate('chat');

  const { list: knowledgeList } = useFetchKnowledgeList(true);

  const filteredKnowledgeList = knowledgeList.filter(
    (x) => x.parser_id !== DocumentParserType.Tag,
  );

  const knowledgeOptions = filteredKnowledgeList.map((x) => ({
    label: (
      <Space>
        <AntAvatar size={20} icon={<UserOutlined />} src={x.avatar} />
        {x.name}
      </Space>
    ),
    value: x.id,
  }));

  return (
    <Form.Item
      label={label || t('knowledgeBases')}
      name={name || 'kb_ids'}
      tooltip={tooltipText || t('knowledgeBasesTip')}
      rules={[
        {
          required,
          message: t('knowledgeBasesMessage'),
          type: 'array',
        },
      ]}
    >
      <Select
        mode="multiple"
        options={knowledgeOptions}
        placeholder={t('knowledgeBasesMessage')}
        onChange={onChange}
      ></Select>
    </Form.Item>
  );
};

export default KnowledgeBaseItem;

function buildQueryVariableOptionsByShowVariable(showVariable?: boolean) {
  return showVariable ? useBuildQueryVariableOptions : () => [];
}

// export function KnowledgeBaseFormField({
//   showVariable = false,
//   hideLabel = false,
// }: {
//   showVariable?: boolean;
//   hideLabel?: boolean;
// }) {
//   const form = useFormContext();
//   const { t } = useTranslation();

//   const { list: knowledgeList } = useFetchKnowledgeList(true);

//   const filteredKnowledgeList = knowledgeList.filter(
//     (x) => x.parser_id !== DocumentParserType.Tag,
//   );

//   const nextOptions = buildQueryVariableOptionsByShowVariable(showVariable)();

//   const knowledgeOptions = filteredKnowledgeList.map((x) => ({
//     label: x.name,
//     value: x.id,
//     icon: () => (
//       <RAGFlowAvatar className="size-4 mr-2" avatar={x.avatar} name={x.name} />
//     ),
//   }));

//   const options = useMemo(() => {
//     if (showVariable) {
//       return [
//         {
//           label: t('knowledgeDetails.dataset'),
//           options: knowledgeOptions,
//         },
//         ...nextOptions.map((x) => {
//           return {
//             ...x,
//             options: x.options
//               .filter((y) => toLower(y.type).includes('string'))
//               .map((x) => ({
//                 ...x,
//                 icon: () => (
//                   <RAGFlowAvatar
//                     className="size-4 mr-2"
//                     avatar={x.label}
//                     name={x.label}
//                   />
//                 ),
//               })),
//           };
//         }),
//       ];
//     }

//     return knowledgeOptions;
//   }, [knowledgeOptions, nextOptions, showVariable, t]);

//   const [isHovering, setIsHovering] = useState(false);

//   return (
//     <FormField
//       control={form.control}
//       name="kb_ids"
//       // render={({ field }) => (

//       //   <FormItem>
//       //     {!hideLabel && (
//       //       <FormLabel tooltip={t('chat.knowledgeBasesTip')} required>
//       //         {t('chat.knowledgeBases')}
//       //       </FormLabel>
//       //     )}
//       //     <FormControl>

//       //       {/* <MultiSelect
//       //         options={options}
//       //         onValueChange={field.onChange}
//       //         placeholder={t('chat.knowledgeBasesMessage')}
//       //         variant="inverted"
//       //         maxCount={100}
//       //         defaultValue={field.value}
//       //         {...field}

//       //         nowrap={true}
//       //       /> */}

//       //       <MultiSelect
//       //         options={options}
//       //         onValueChange={field.onChange}
//       //         placeholder={t('chat.knowledgeBasesMessage')}
//       //         variant="inverted"
//       //         maxCount={100}
//       //         defaultValue={field.value}
//       //         {...field}
//       //         // 1. 添加一个自定义类名，方便定位
//       //         className="hover-expand-multiselect"
//       //         // 2. 定义默认的内联样式（默认折叠状态）
//       //         style={{
//       //           maxHeight: '40px',      // 限制高度为一行（根据实际 padding 调整）
//       //           overflow: 'hidden',     // 隐藏超出部分
//       //           transition: 'max-height 0.3s ease-in-out', // 添加高度变化的动画
//       //           cursor: 'pointer',      // 鼠标变成手型，提示可交互
//       //         }}
//       //       />
//       //     </FormControl>
//       //   </FormItem>
//       // )}
//       render={({ field }) => {
//         // 1. 计算数量：如果是数组则取长度，否则为 0
//         const count = Array.isArray(field.value) ? field.value.length : 0;

//         return (
//           <FormItem>
//             {!hideLabel && (
//               <FormLabel tooltip={t('chat.knowledgeBasesTip')} required>
//                 {t('chat.knowledgeBases')}
//               </FormLabel>
//             )}
//             <FormControl>
//               <div className="relative w-full">
//                 {' '}
//                 {/* 添加相对定位容器 */}
//                 {/* <MultiSelect
//                   options={options}
//                   onValueChange={field.onChange}
//                   placeholder={t('chat.knowledgeBasesMessage')}
//                   variant="inverted"
//                   maxCount={100}
//                   defaultValue={field.value}
//                   {...field}
//                   className="hover-expand-multiselect"
//                   style={{
//                     maxHeight: '36px',
//                     overflow: 'hidden',
//                     transition: 'max-height 0.3s ease-in-out',
//                     cursor: 'pointer',
//                   }}
//                 /> */}
//                 <div
//   className="relative w-full"
//   onMouseEnter={() => setIsHovering(true)}
//   onMouseLeave={() => setIsHovering(false)}
// >
//   <MultiSelect
//     options={options}
//     onValueChange={field.onChange}
//     placeholder={t('chat.knowledgeBasesMessage')}
//     variant="inverted"
//     maxCount={isHovering ? 100 : 1}
//     defaultValue={field.value}
//     {...field}
//   />

// </div>
//                 <div
//                   style={{
//                     display: 'inline-flex',
//                     alignItems: 'center',
//                     justifyContent: 'center',
//                     height: '20px', // 稍微高一点点，更显大气
//                     padding: '0 8px',
//                     marginLeft: '8px',
//                     fontSize: '12px', // 稍微大一点，更易读
//                     fontWeight: '700',
//                     color: '#831843',
//                     // 核心：更鲜亮的渐变色
//                     background:
//                       'linear-gradient(135deg, #FF9A9E 0%, #FECFEF 99%, #FECFEF 100%)', // 粉色系
//                     // 核心：多层阴影制造立体感
//                     boxShadow:
//                       '0px 2px 4px rgba(255, 154, 158, 0.4), inset 0px 1px 2px rgba(255,255,255,0.6)',
//                     borderRadius: '12px', // 稍微圆润一点
//                     border: '1px solid rgba(255,255,255,0.6)', // 亮边框
//                     position: 'relative',
//                     overflow: 'hidden',
//                     textShadow: '0px 1px 0px rgba(255, 100, 100, 0.3)', // 文字投影
//                   }}
//                 >
//                   {/* 高光：模拟顶部的反光 */}
//                   <div
//                     style={{
//                       position: 'absolute',
//                       top: '0',
//                       left: '0',
//                       right: '0',
//                       height: '50%',
//                       background:
//                         'linear-gradient(to bottom, rgba(255,255,255,0.8) 0%, rgba(255,255,255,0.1) 100%)',
//                       borderRadius: '12px 12px 50% 50% / 12px 12px 0 0',
//                       pointerEvents: 'none',
//                     }}
//                   ></div>

//                   <span style={{ position: 'relative', zIndex: 1 }}>
//                     {count}已选
//                   </span>
//                 </div>
//               </div>
//             </FormControl>
//           </FormItem>
//         );
//       }}
//     />
//   );
// }

export function KnowledgeBaseFormField({
  showVariable = false,
  hideLabel = false,
}: {
  showVariable?: boolean;
  hideLabel?: boolean;
}) {
  const form = useFormContext();
  const { t } = useTranslation();

  const multiSelectRef = useRef<HTMLDivElement>(null);

  const { list: knowledgeList } = useFetchKnowledgeList(true);

  const groupPriorityMap: Record<string, number> = {
    全局参考库: 1,
    工艺研究一室: 2,
    工艺研究二室: 3,
    工艺研究三室: 4,
    新品事业部研发部: 5,
  };

  const getGroupPriority = (groupName?: string | null) => {
    if (!groupName) return 999;

    return groupPriorityMap[groupName] ?? 6;
  };

  const filteredKnowledgeList = useMemo(() => {
    return [...knowledgeList]
      .filter((x) => x.parser_id !== DocumentParserType.Tag)
      .sort((a, b) => {
        const groupNameA = a.group_name || '';
        const groupNameB = b.group_name || '';

        const priorityA = getGroupPriority(groupNameA);
        const priorityB = getGroupPriority(groupNameB);

        // 1. 先按照指定 group_name 优先级排序
        if (priorityA !== priorityB) {
          return priorityA - priorityB;
        }

        // 2. 如果都是 else，也就是 priority = 6，则按 group_name 排序
        // 这样相同 group_name 会排在一起
        if (groupNameA !== groupNameB) {
          return groupNameA.localeCompare(groupNameB, 'zh-CN');
        }

        // 3. 同一个 group_name 下，再按知识库 name 排序
        return a.name.localeCompare(b.name, 'zh-CN');
      });
  }, [knowledgeList]);

  // const filteredKnowledgeList = knowledgeList.filter(
  //   (x) => x.parser_id !== DocumentParserType.Tag,
  // );

  const nextOptions = buildQueryVariableOptionsByShowVariable(showVariable)();

  const knowledgeOptions = filteredKnowledgeList.map((x) => ({
    label: x.name,
    value: x.id,
    icon: () => (
      <RAGFlowAvatar className="size-4 mr-2" avatar={x.avatar} name={x.name} />
    ),
  }));

  const options = useMemo(() => {
    if (showVariable) {
      return [
        {
          label: t('knowledgeDetails.dataset'),
          options: knowledgeOptions,
        },
        ...nextOptions.map((x) => {
          return {
            ...x,
            options: x.options
              .filter((y) => toLower(y.type).includes('string'))
              .map((x) => ({
                ...x,
                icon: () => (
                  <RAGFlowAvatar
                    className="size-4 mr-2"
                    avatar={x.label}
                    name={x.label}
                  />
                ),
              })),
          };
        }),
      ];
    }

    return knowledgeOptions;
  }, [knowledgeOptions, nextOptions, showVariable, t]);

  return (
    <FormField
      control={form.control}
      name="kb_ids"
      render={({ field }) => {
        const count = Array.isArray(field.value) ? field.value.length : 0;

        const openMultiSelect = () => {
          const trigger = multiSelectRef.current?.querySelector(
            'button,[role="combobox"]',
          ) as HTMLElement | null;

          trigger?.click();
        };

        return (
          <FormItem>
            {!hideLabel && (
              <FormLabel tooltip={t('chat.knowledgeBasesTip')} required>
                {t('chat.knowledgeBases')}
              </FormLabel>
            )}

            <FormControl>
              <div className="relative inline-flex h-9 items-center">
                <button
                  type="button"
                  className="
  group inline-flex h-9 items-center gap-2 rounded-lg
  border border-sky-300/50 bg-white/20 px-3.5
  text-sm font-medium text-sky-800
  shadow-none backdrop-blur-md
  transition-all duration-200 ease-out

  hover:border-sky-400/60 hover:bg-white/35 hover:text-sky-900 hover:shadow-sm
  active:scale-[0.98] active:bg-sky-100/40

  focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-300/60 focus-visible:ring-offset-1

  dark:border-sky-700/50 dark:bg-transparent dark:text-sky-300
  dark:hover:border-sky-600 dark:hover:bg-sky-950/30 dark:hover:text-sky-200
  dark:active:bg-sky-900/30

                "
                  onClick={openMultiSelect}
                >
                  {/* 书籍图标 */}
                  <svg
                    className="h-4 w-4 text-sky-600 dark:text-sky-400"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
                    />
                  </svg>

                  <span>知识库</span>

                  {/* 数字徽章：保持深色背景+白色文字，在黑白模式下都清晰 */}
                  <span className="inline-flex h-5 min-w-5 items-center justify-center rounded-md border border-sky-300/50 bg-sky-100/60 px-1.5 text-xs font-bold text-sky-800 shadow-sm dark:border-sky-700/60 dark:bg-sky-950/40 dark:text-sky-300">
                    {count ?? 0}
                  </span>

                  <span className="text-xs font-medium text-sky-600 tracking-wide dark:text-sky-400">
                    已选
                  </span>

                  {/* 下拉箭头 */}
                  <svg
                    className="ml-0.5 h-3.5 w-3.5 text-sky-500 transition-transform duration-200 group-hover:rotate-180 dark:text-sky-500"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2.5}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M19 9l-7 7-7-7"
                    />
                  </svg>
                </button>

                {/* 隐藏的 MultiSelect 触发器 */}
                <div
                  ref={multiSelectRef}
                  className="pointer-events-none absolute left-0 top-full z-10 h-0 w-0 overflow-hidden opacity-0"
                >
                  <MultiSelect
                    options={options}
                    onValueChange={field.onChange}
                    placeholder={t('chat.knowledgeBasesMessage')}
                    variant="inverted"
                    maxCount={0}
                    defaultValue={field.value}
                    {...field}
                  />
                </div>
              </div>
            </FormControl>
          </FormItem>
        );
      }}
    />
  );
}
