import { DocumentParserType } from '@/constants/knowledge';
import { useTranslate } from '@/hooks/common-hooks';
import { useFetchKnowledgeList } from '@/hooks/use-knowledge-request';
import { useBuildQueryVariableOptions } from '@/pages/agent/hooks/use-get-begin-query';
import { UserOutlined } from '@ant-design/icons';
import { Avatar as AntAvatar, Form, Select, Space } from 'antd';
import { toLower } from 'lodash';
import { useMemo } from 'react';
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

export function KnowledgeBaseFormField({
  showVariable = false,
  hideLabel = false,
}: {
  showVariable?: boolean;
  hideLabel?: boolean;
}) {
  const form = useFormContext();
  const { t } = useTranslation();

  const { list: knowledgeList } = useFetchKnowledgeList(true);

  const filteredKnowledgeList = knowledgeList.filter(
    (x) => x.parser_id !== DocumentParserType.Tag,
  );

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
      // render={({ field }) => (

      //   <FormItem>
      //     {!hideLabel && (
      //       <FormLabel tooltip={t('chat.knowledgeBasesTip')} required>
      //         {t('chat.knowledgeBases')}
      //       </FormLabel>
      //     )}
      //     <FormControl>

      //       {/* <MultiSelect
      //         options={options}
      //         onValueChange={field.onChange}
      //         placeholder={t('chat.knowledgeBasesMessage')}
      //         variant="inverted"
      //         maxCount={100}
      //         defaultValue={field.value}
      //         {...field}

      //         nowrap={true}
      //       /> */}

      //       <MultiSelect
      //         options={options}
      //         onValueChange={field.onChange}
      //         placeholder={t('chat.knowledgeBasesMessage')}
      //         variant="inverted"
      //         maxCount={100}
      //         defaultValue={field.value}
      //         {...field}
      //         // 1. 添加一个自定义类名，方便定位
      //         className="hover-expand-multiselect"
      //         // 2. 定义默认的内联样式（默认折叠状态）
      //         style={{
      //           maxHeight: '40px',      // 限制高度为一行（根据实际 padding 调整）
      //           overflow: 'hidden',     // 隐藏超出部分
      //           transition: 'max-height 0.3s ease-in-out', // 添加高度变化的动画
      //           cursor: 'pointer',      // 鼠标变成手型，提示可交互
      //         }}
      //       />
      //     </FormControl>
      //   </FormItem>
      // )}
      render={({ field }) => {
        // 1. 计算数量：如果是数组则取长度，否则为 0
        const count = Array.isArray(field.value) ? field.value.length : 0;

        return (
          <FormItem>
            {!hideLabel && (
              <FormLabel tooltip={t('chat.knowledgeBasesTip')} required>
                {t('chat.knowledgeBases')}
              </FormLabel>
            )}
            <FormControl>
              <div className="relative w-full">
                {' '}
                {/* 添加相对定位容器 */}
                <MultiSelect
                  options={options}
                  onValueChange={field.onChange}
                  placeholder={t('chat.knowledgeBasesMessage')}
                  variant="inverted"
                  maxCount={100}
                  defaultValue={field.value}
                  {...field}
                  className="hover-expand-multiselect"
                  style={{
                    maxHeight: '10px',
                    overflow: 'hidden',
                    transition: 'max-height 0.3s ease-in-out',
                    cursor: 'pointer',
                  }}
                />
                <div
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    height: '20px', // 稍微高一点点，更显大气
                    padding: '0 8px',
                    marginLeft: '8px',
                    fontSize: '12px', // 稍微大一点，更易读
                    fontWeight: '700',
                    color: '#831843',
                    // 核心：更鲜亮的渐变色
                    background:
                      'linear-gradient(135deg, #FF9A9E 0%, #FECFEF 99%, #FECFEF 100%)', // 粉色系
                    // 核心：多层阴影制造立体感
                    boxShadow:
                      '0px 2px 4px rgba(255, 154, 158, 0.4), inset 0px 1px 2px rgba(255,255,255,0.6)',
                    borderRadius: '12px', // 稍微圆润一点
                    border: '1px solid rgba(255,255,255,0.6)', // 亮边框
                    position: 'relative',
                    overflow: 'hidden',
                    textShadow: '0px 1px 0px rgba(255, 100, 100, 0.3)', // 文字投影
                  }}
                >
                  {/* 高光：模拟顶部的反光 */}
                  <div
                    style={{
                      position: 'absolute',
                      top: '0',
                      left: '0',
                      right: '0',
                      height: '50%',
                      background:
                        'linear-gradient(to bottom, rgba(255,255,255,0.8) 0%, rgba(255,255,255,0.1) 100%)',
                      borderRadius: '12px 12px 50% 50% / 12px 12px 0 0',
                      pointerEvents: 'none',
                    }}
                  ></div>

                  <span style={{ position: 'relative', zIndex: 1 }}>
                    {count}已选
                  </span>
                </div>
              </div>
            </FormControl>
          </FormItem>
        );
      }}
    />
  );
}
