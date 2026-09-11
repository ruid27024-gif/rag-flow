import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Spin } from '@/components/ui/spin';
import { cn } from '@/lib/utils';
import { getAuthorization } from '@/utils/authorization-util';
import { message } from 'antd';
import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  SearchTag,
  SearchTagFieldValue,
  createEmptySearchTag,
} from './search-tag';

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

function useFetchTagConfig() {
  const [tagConfig, setTagConfig] = useState<KnowledgeTagType[]>([]);

  const [loading, setLoading] = useState(false);

  const fetchTagConfig = useCallback(async () => {
    try {
      setLoading(true);

      const res = await fetch('/v1/knowledge_tag/tag/config', {
        method: 'GET',
        credentials: 'include',
        headers: {
          Authorization: getAuthorization() || '',
          'Content-Type': 'application/json',
        },
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
    void fetchTagConfig();
  }, [fetchTagConfig]);

  return {
    tagConfig,
    loading,
  };
}

interface SearchTagSelectorProps {
  /**
   * 父组件传入的当前标签值。
   *
   * 允许为空，组件内部会使用空标签兜底。
   */
  value?: SearchTag;

  /**
   * 是否正在保存标签
   */
  saving?: boolean;

  className?: string;

  /**
   * 只修改父组件中的本地状态
   */
  onChange: (value: SearchTag) => void;

  /**
   * 保存完整标签到后端
   */
  onSubmit: (value: SearchTag) => Promise<void> | void;
}

export function SearchTagSelector({
  value,
  saving = false,
  className,
  onChange,
  onSubmit,
}: SearchTagSelectorProps) {
  const { tagConfig, loading } = useFetchTagConfig();

  /**
   * value 可能在父组件异步加载 SearchData 时为 undefined。
   * 所有读取和提交都使用 safeValue，避免：
   *
   * Cannot read properties of undefined
   */
  const safeValue = useMemo(() => value ?? createEmptySearchTag(), [value]);

  const filters = useMemo<FilterCollection[]>(() => {
    const fixedFields = new Set([
      'version',
      'author',
      'school',
      'publish_date',
    ]);

    const dynamicFilters: FilterCollection[] = tagConfig
      .filter((item) => !fixedFields.has(item.type_code))
      .slice()
      .sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0))
      .map((item) => ({
        type: item.multi_select ? 'checkbox' : 'radio',

        field: item.type_code,
        label: item.type_name,
        required: item.required,

        list: (item.options || [])
          .slice()
          .sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0))
          .map((option) => ({
            id: option.option_name,
            label: option.option_name,
            count: option.count,
          })),
      }));

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

  /**
   * 只修改本地状态，不请求后端。
   */
  const updateField = useCallback(
    (field: string, fieldValue: SearchTagFieldValue) => {
      const nextTag: SearchTag = {
        ...safeValue,
        [field]: fieldValue,
      };

      onChange(nextTag);
    },
    [onChange, safeValue],
  );

  return (
    <div
      className={cn(
        'space-y-4 rounded-xl border border-border bg-bg-card p-4',
        className,
      )}
    >
      <div className="flex items-center justify-between">
        <div className="text-sm font-medium text-text-primary">标签筛选</div>

        {loading && (
          <div className="text-xs text-text-secondary">标签加载中...</div>
        )}

        {!loading && saving && (
          <div className="text-xs text-text-secondary">保存中...</div>
        )}
      </div>

      {!loading &&
        filters.map((filter) => {
          /**
           * 这里必须使用 safeValue，
           * 不能直接使用 value。
           */
          const currentValue = safeValue[filter.field];

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
                        disabled={saving}
                        onClick={() => {
                          const nextValue = checked
                            ? selectedValues.filter(
                                (selected) => selected !== item.id,
                              )
                            : [...selectedValues, item.id];

                          updateField(filter.field, nextValue);
                        }}
                        className={cn(
                          'rounded-md border px-2 py-1 text-xs transition-colors',
                          checked
                            ? 'border-primary bg-primary/10 text-primary'
                            : 'border-border bg-bg-card text-text-secondary',
                          saving && 'cursor-not-allowed opacity-60',
                        )}
                      >
                        {item.label}

                        {typeof item.count === 'number' && ` (${item.count})`}
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
                        disabled={saving}
                        onClick={() => {
                          updateField(filter.field, checked ? '' : item.id);
                        }}
                        className={cn(
                          'rounded-md border px-2 py-1 text-xs transition-colors',
                          checked
                            ? 'border-primary bg-primary text-white'
                            : 'border-border bg-bg-card text-text-secondary',
                          saving && 'cursor-not-allowed opacity-60',
                        )}
                      >
                        {item.label}

                        {typeof item.count === 'number' && ` (${item.count})`}
                      </button>
                    );
                  })}
                </div>
              </div>
            );
          }

          /**
           * 文本字段
           */
          if (filter.type === 'text') {
            const textValue =
              typeof currentValue === 'string' ? currentValue : '';

            return (
              <div key={filter.field} className="space-y-2">
                <div className="text-sm text-text-primary">{filter.label}</div>

                <Input
                  value={textValue}
                  disabled={saving}
                  placeholder={filter.placeholder}
                  onChange={(event) => {
                    updateField(filter.field, event.target.value);
                  }}
                />
              </div>
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
                <div className="text-sm text-text-primary">{filter.label}</div>

                <div className="flex gap-2">
                  <Input
                    type="date"
                    disabled={saving}
                    value={dateValue[0] || ''}
                    onChange={(event) => {
                      updateField(filter.field, [
                        event.target.value,
                        dateValue[1] || '',
                      ]);
                    }}
                  />

                  <Input
                    type="date"
                    disabled={saving}
                    value={dateValue[1] || ''}
                    onChange={(event) => {
                      updateField(filter.field, [
                        dateValue[0] || '',
                        event.target.value,
                      ]);
                    }}
                  />
                </div>
              </div>
            );
          }

          return null;
        })}

      <div className="flex justify-end">
        <Button
          type="button"
          disabled={loading || saving}
          onClick={() => {
            void onSubmit(safeValue);
          }}
        >
          {saving && (
            <div className="mr-2 size-4">
              <Spin size="small" />
            </div>
          )}

          {saving ? '保存中' : '保存标签'}
        </Button>
      </div>
    </div>
  );
}
