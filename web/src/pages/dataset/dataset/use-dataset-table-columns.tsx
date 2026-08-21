import { FileIcon } from '@/components/icon-font';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Progress } from '@/components/ui/progress';
import { Switch } from '@/components/ui/switch';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { RunningStatus } from '@/constants/knowledge';
import { useNavigatePage } from '@/hooks/logic-hooks/navigate-hooks';
import { useSetDocumentStatus } from '@/hooks/use-document-request';
import { IDocumentInfo } from '@/interfaces/database/document';
import { cn } from '@/lib/utils';
import { useDataSourceInfo } from '@/pages/user-setting/data-source/contant';
// import { formatDate } from '@/utils/date';
import { CurrentUserRole } from '@/hooks/use-document-request';
import { getAuthorization } from '@/utils/authorization-util';
import { CheckOutlined, CloseOutlined, DownOutlined } from '@ant-design/icons';
import { ColumnDef } from '@tanstack/table-core';
import { Modal, Select, Tag, message } from 'antd';
import { ArrowUpDown, Edit, LockKeyhole, MonitorUp } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { DatasetActionCell } from './dataset-action-cell';
import { UseChangeDocumentParserShowType } from './use-change-document-parser';
import { UseRenameDocumentShowType } from './use-rename-document';
import { UseSaveMetaShowType } from './use-save-meta';

type UseDatasetTableColumnsType = UseChangeDocumentParserShowType &
  UseRenameDocumentShowType &
  UseSaveMetaShowType & {
    showLog: (record: IDocumentInfo) => void;
    readonly?: boolean;
    documents?: IDocumentInfo[];
    currentUserRole?: CurrentUserRole | null;
  };

type TagOptionSchema = {
  option_code: string;
  option_name: string;
};

type TagTypeSchema = {
  type_code: string;
  type_name: string;
  multi_select: boolean;
  required: boolean;
  options: TagOptionSchema[];
};

type TagLabels = {
  types: Record<string, TagTypeSchema>;
};

type DisplayDocument = IDocumentInfo & {
  can_view?: boolean;
  visibility_level?: number;
  visibility_name?: string;

  meta_fields?: Record<string, unknown> | string;
  meta_fields_display?: Record<string, unknown> | string;
  tag_metadata?: Record<
    string,
    {
      type_code?: string;
      type_name?: string;
      options?: Array<{
        option_code?: string;
        option_name?: string;
      }>;
    }
  >;
  author?: unknown;
  school?: unknown;
  publish_time?: unknown;
};

type EditableTagCellProps = {
  record: IDocumentInfo;
  typeCode: string;
  typeName: string;
  valueText: string;
  displayValue?: unknown;
  schema?: TagTypeSchema;
  authHeaders: Record<string, string>;
  disabled?: boolean;
};

const EditableTagCell: React.FC<EditableTagCellProps> = ({
  record,
  typeCode,
  typeName,
  valueText,
  displayValue,
  schema,
  authHeaders,
  disabled = false,
}) => {
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [displayExpanded, setDisplayExpanded] = useState(false);

  const parseObject = (value: unknown): Record<string, any> => {
    if (!value) {
      return {};
    }

    if (typeof value === 'object' && !Array.isArray(value)) {
      return value as Record<string, any>;
    }

    if (typeof value === 'string') {
      try {
        const parsed = JSON.parse(value);

        if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
          return parsed as Record<string, any>;
        }
      } catch {
        return {};
      }
    }

    return {};
  };

  const metaFields = parseObject((record as any).meta_fields);
  const rawValue = metaFields[typeCode];

  const initialValue = Array.isArray(rawValue)
    ? rawValue.map(String)
    : rawValue
      ? [String(rawValue)]
      : [];

  const [selectedValues, setSelectedValues] = useState<string[]>(initialValue);

  const reset = () => {
    setSelectedValues(initialValue);
    setEditing(false);
  };

  const toggleOption = (optionCode: string) => {
    if (!schema) {
      return;
    }

    if (schema.multi_select) {
      setSelectedValues((values) => {
        if (values.includes(optionCode)) {
          return values.filter((item) => item !== optionCode);
        }

        return [...values, optionCode];
      });

      return;
    }

    setSelectedValues((values) => {
      if (!schema.required && values.length === 1 && values[0] === optionCode) {
        return [];
      }

      return [optionCode];
    });
  };

  const handleSave = async () => {
    if (!schema) {
      message.warning(`未找到标签类型配置：${typeCode}`);
      return;
    }

    if (schema.required && selectedValues.length === 0) {
      message.error(`${schema.type_name || typeName}为必填项`);
      return;
    }

    setSaving(true);

    try {
      const res = await fetch('/v1/document/knowledge/tags/update-one', {
        method: 'POST',
        credentials: 'include',
        headers: authHeaders,
        body: JSON.stringify({
          doc_id: record.id,
          type_code: typeCode,
          option_codes: selectedValues,
        }),
      });

      const result = await res.json();

      if (
        !res.ok ||
        (result.code !== undefined && result.code !== 0 && result.code !== '0')
      ) {
        throw new Error(result.message || '保存标签失败');
      }

      message.success('保存成功');
      setEditing(false);
      window.location.reload();
    } catch (error: any) {
      message.error(error?.message || '保存失败');
    } finally {
      setSaving(false);
    }
  };

  if (!schema || !schema.options?.length) {
    return (
      <span
        className="block whitespace-normal break-words text-xs text-text-secondary"
        title={valueText}
      >
        {valueText || '-'}
      </span>
    );
  }
  const displayValues = Array.isArray(displayValue)
    ? displayValue.map(String).filter(Boolean)
    : valueText && valueText !== '-'
      ? [valueText]
      : [];
  if (!editing) {
    const values = Array.isArray(displayValue)
      ? displayValue.map(String).filter(Boolean)
      : displayValue && String(displayValue).trim()
        ? [String(displayValue)]
        : [];

    const visibleValues = displayExpanded ? values : values.slice(0, 1);
    const hasMore = values.length > 1;

    return (
      <div
        role="button"
        tabIndex={0}
        className="relative flex max-w-[220px] flex-col items-start gap-1 pr-5"
        title={
          disabled
            ? '当前用户没有操作该文档的权限'
            : valueText || `点击修改${typeName}`
        }
        onClick={(event) => {
          event.stopPropagation();

          if (disabled) {
            message.warning('当前用户没有操作该文档的权限');
            return;
          }

          setEditing(true);
        }}
        onKeyDown={(event) => {
          if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            event.stopPropagation();

            if (disabled) {
              message.warning('当前用户没有操作该文档的权限');
              return;
            }

            setEditing(true);
          }
        }}
        style={{
          cursor: disabled ? 'not-allowed' : 'pointer',
          // opacity: disabled ? 0.55 : 1,
        }}
      >
        {visibleValues.length > 0 ? (
          visibleValues.map((item, index) => (
            <Tag
              key={`${item}_${index}`}
              title={item}
              style={{
                display: 'inline-flex',
                width: 'fit-content',
                maxWidth: '100%',
                marginInlineEnd: 0,
                borderRadius: 4,
                fontSize: 12,
                lineHeight: '20px',
                padding: '0 8px',
                color: '#ffffff',
                backgroundColor: '#16a36f',
                borderColor: '#16a36f',
                verticalAlign: 'top',
                whiteSpace: 'normal',
                wordBreak: 'break-all',
              }}
            >
              {item}
            </Tag>
          ))
        ) : (
          <Tag
            style={{
              display: 'inline-flex',
              width: 'fit-content',
              marginInlineEnd: 0,
              borderRadius: 4,
              fontSize: 12,
              lineHeight: '20px',
              padding: '0 8px',
              color: '#6b7280',
              backgroundColor: '#f3f4f6',
              borderColor: '#d1d5db',
            }}
          >
            -
          </Tag>
        )}

        {hasMore ? (
          <button
            type="button"
            title={displayExpanded ? '收起' : '展开'}
            onClick={(event) => {
              event.preventDefault();
              event.stopPropagation();
              setDisplayExpanded((value) => !value);
            }}
            onKeyDown={(event) => {
              if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                event.stopPropagation();
                setDisplayExpanded((value) => !value);
              }
            }}
            className="absolute right-0 top-0 flex h-[20px] w-[16px] items-center justify-center text-[#0f766e]"
            style={{
              cursor: 'pointer',
              background: 'transparent',
              border: 'none',
              padding: 0,
            }}
          >
            <DownOutlined
              className={[
                'text-[10px]',
                'transition-transform',
                'duration-200',
                'ease-out',
                displayExpanded ? 'rotate-180' : 'rotate-0',
              ].join(' ')}
              style={{
                color: displayExpanded ? '#0f766e' : '#9ca3af',
              }}
            />
          </button>
        ) : null}
      </div>
    );
  }

  return (
    <div
      className="w-full min-w-[220px] max-w-[360px]"
      onClick={(event) => event.stopPropagation()}
    >
      <div className="mb-2 flex max-h-[180px] flex-col items-start gap-1 overflow-y-auto">
        {schema.options.map((option) => {
          const selected = selectedValues.includes(option.option_code);

          return (
            <Tag
              key={option.option_code}
              role="button"
              tabIndex={0}
              onClick={() => toggleOption(option.option_code)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' || event.key === ' ') {
                  event.preventDefault();
                  toggleOption(option.option_code);
                }
              }}
              style={{
                display: 'inline-flex',
                width: 'fit-content',
                marginInlineEnd: 0,
                cursor: saving ? 'not-allowed' : 'pointer',
                borderRadius: 4,
                fontSize: 12,
                lineHeight: '20px',
                padding: '0 8px',
                color: selected ? '#ffffff' : '#0f766e',
                backgroundColor: selected ? '#16a36f' : '#f0fdfa',
                borderColor: selected ? '#16a36f' : '#99f6e4',
                opacity: saving ? 0.6 : 1,
                whiteSpace: 'normal',
                wordBreak: 'break-all',
                maxWidth: '100%',
              }}
            >
              {option.option_name}
            </Tag>
          );
        })}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          className="text-xs text-[#00A870]"
          disabled={saving}
          onClick={handleSave}
          title="保存"
        >
          <CheckOutlined /> 保存
        </button>

        <button
          type="button"
          className="text-xs text-gray-400"
          disabled={saving}
          onClick={reset}
          title="取消"
        >
          <CloseOutlined /> 取消
        </button>
      </div>
    </div>
  );
};

export function useDatasetTableColumns({
  showChangeParserModal,
  showRenameModal,
  showSetMetaModal,
  showLog,
  readonly = false,
  documents = [],
  currentUserRole,
}: UseDatasetTableColumnsType) {
  const hasViewPermission = (record: IDocumentInfo) => {
    const displayRecord = record as DisplayDocument;

    /**
     * 严格判断：
     * 只有后端明确返回 can_view === true，才认为有权限。
     *
     * 如果你想兼容老接口，没返回 can_view 时也允许访问，
     * 可以改成：
     * return displayRecord.can_view !== false;
     */
    return displayRecord.can_view === true;
  };

  // 全局权限判断
  type OperationPermissionKey =
    | 'view'
    | 'upload'
    | 'download'
    | 'delete'
    | 'edit';

  const hasOperationPermission = (key: OperationPermissionKey) => {
    if (currentUserRole?.is_admin) {
      return true;
    }

    return !!currentUserRole?.operation_permissions?.[key];
  };

  const canEdit = hasOperationPermission('edit');
  const canDelete = hasOperationPermission('delete');
  const canDownload = hasOperationPermission('download');
  const canUpload = hasOperationPermission('upload');

  const PermissionLock = ({
    title = '当前用户没有查看该文档的权限',
  }: {
    title?: string;
  }) => {
    return (
      <Tooltip>
        <TooltipTrigger asChild>
          <div className="flex h-6 w-6 items-center justify-center rounded-full bg-blue-50 text-blue-600">
            <LockKeyhole size={15} strokeWidth={2.2} />
          </div>
        </TooltipTrigger>
        <TooltipContent>
          <p>{title}</p>
        </TooltipContent>
      </Tooltip>
    );
  };

  const parseObject = (value: unknown): Record<string, any> => {
    if (!value) {
      return {};
    }

    if (typeof value === 'object' && !Array.isArray(value)) {
      return value as Record<string, any>;
    }

    if (typeof value === 'string') {
      try {
        const parsed = JSON.parse(value);

        if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
          return parsed as Record<string, any>;
        }
      } catch {
        return {};
      }
    }

    return {};
  };

  const toDisplayText = (value: unknown): string => {
    if (Array.isArray(value)) {
      return value.length ? value.map(String).join('、') : '-';
    }

    if (value === null || value === undefined || value === '') {
      return '-';
    }

    return String(value);
  };

  // 1. authHeaders 和标签 schema 状态
  const authHeaders = useMemo(
    () => ({
      Authorization: getAuthorization() || '',
      'Content-Type': 'application/json',
    }),
    [],
  );

  const [tagLabels, setTagLabels] = useState<TagLabels>({
    types: {},
  });
  // 2. 加载全部标签定义
  useEffect(() => {
    let cancelled = false;

    async function loadTagLabels() {
      try {
        const res = await fetch('/v1/document/knowledge/tags/options', {
          method: 'GET',
          credentials: 'include',
          headers: authHeaders,
        });

        const result = await res.json();
        console.log('knowledge tag options result:', result);

        if (!res.ok || (result.code !== undefined && result.code !== 0)) {
          throw new Error(result.message || '获取标签字典失败');
        }

        if (!cancelled) {
          setTagLabels({
            types: result.data?.types || {},
          });
        }
      } catch (error) {
        console.error('Failed to load knowledge tag labels:', error);
      }
    }

    loadTagLabels();

    return () => {
      cancelled = true;
    };
  }, [authHeaders]);

  const tagColumns = useMemo<ColumnDef<IDocumentInfo>[]>(() => {
    const tagTypeMap = new Map<
      string,
      {
        typeCode: string;
        typeName: string;
      }
    >();

    documents.forEach((doc) => {
      const displayDoc = doc as DisplayDocument;

      const displayFields = parseObject(displayDoc.meta_fields_display);
      const tagMetadata = parseObject(displayDoc.tag_metadata);

      Object.keys(displayFields).forEach((typeCode) => {
        const typeName =
          tagLabels?.types?.[typeCode]?.type_name ||
          tagMetadata?.[typeCode]?.type_name ||
          typeCode;

        if (!tagTypeMap.has(typeCode)) {
          tagTypeMap.set(typeCode, {
            typeCode,
            typeName,
          });
        }
      });
    });

    return Array.from(tagTypeMap.values()).map(({ typeCode, typeName }) => ({
      id: `tag_${typeCode}`,
      header: typeName,
      meta: {
        cellClassName: 'min-w-[120px] max-w-[220px] align-top',
      },
      cell: ({ row }) => {
        const displayDoc = row.original as DisplayDocument;
        const displayFields = parseObject(displayDoc.meta_fields_display);
        // const valueText = toDisplayText(displayFields[typeCode]);

        const schema = tagLabels?.types?.[typeCode];

        const displayValue = displayFields[typeCode];
        const valueText = toDisplayText(displayValue);

        const canView = hasViewPermission(row.original);

        return (
          <EditableTagCell
            record={row.original}
            typeCode={typeCode}
            typeName={typeName}
            valueText={valueText}
            displayValue={displayValue}
            schema={schema}
            authHeaders={authHeaders}
            disabled={!canView || readonly || !canEdit}
          />
        );
      },
    }));
  }, [documents, tagLabels, authHeaders]);

  const updateOneKnowledgeTag = async ({
    docId,
    typeCode,
    optionCodes,
  }: {
    docId: string;
    typeCode: string;
    optionCodes: string[];
  }) => {
    const res = await fetch('/v1/document/knowledge/tags/update-one', {
      method: 'POST',
      credentials: 'include',
      headers: authHeaders,
      body: JSON.stringify({
        doc_id: docId,
        type_code: typeCode,
        option_codes: optionCodes,
      }),
    });

    const result = await res.json();

    if (!res.ok || (result.code !== undefined && result.code !== 0)) {
      throw new Error(result.message || '保存标签失败');
    }

    return result.data;
  };

  const openTagEditor = (
    record: IDocumentInfo,
    typeCode: string,
    typeName: string,
  ) => {
    const displayDoc = record as DisplayDocument;

    const schema = tagLabels?.types?.[typeCode];

    console.log('open tag editor:', {
      typeCode,
      typeName,
      schema,
      tagLabels,
    });

    if (!schema) {
      message.warning(`未找到标签类型配置：${typeCode}`);
      return;
    }

    if (!schema.options || schema.options.length === 0) {
      message.warning(`标签类型「${schema.type_name || typeName}」没有可选项`);
      return;
    }

    const metaFields = parseObject(displayDoc.meta_fields);

    const currentRawValue = metaFields[typeCode];

    const currentOptionCodes = Array.isArray(currentRawValue)
      ? currentRawValue.map(String)
      : currentRawValue
        ? [String(currentRawValue)]
        : [];

    let selectedOptionCodes = [...currentOptionCodes];

    Modal.confirm({
      title: `修改${schema.type_name || typeName}`,
      width: 520,
      okText: '保存',
      cancelText: '取消',
      content: (
        <div style={{ paddingTop: 12 }}>
          <Select
            style={{ width: '100%' }}
            mode={schema.multi_select ? 'multiple' : undefined}
            allowClear={!schema.required}
            defaultValue={
              schema.multi_select ? selectedOptionCodes : selectedOptionCodes[0]
            }
            placeholder={`请选择${schema.type_name || typeName}`}
            options={schema.options.map((option) => ({
              label: option.option_name,
              value: option.option_code,
            }))}
            onChange={(value) => {
              if (Array.isArray(value)) {
                selectedOptionCodes = value.map(String);
              } else if (value) {
                selectedOptionCodes = [String(value)];
              } else {
                selectedOptionCodes = [];
              }
            }}
          />
        </div>
      ),
      async onOk() {
        if (schema.required && selectedOptionCodes.length === 0) {
          message.error(`${schema.type_name || typeName}为必填项`);
          return Promise.reject();
        }

        try {
          await updateOneKnowledgeTag({
            docId: record.id,
            typeCode,
            optionCodes: selectedOptionCodes,
          });

          message.success('标签保存成功');

          // 最简单先刷新页面
          window.location.reload();
        } catch (error: any) {
          message.error(error?.message || '保存标签失败');
          return Promise.reject();
        }
      },
    });
  };

  const toText = (v: unknown) => {
    if (v === null || v === undefined) return '';
    if (typeof v === 'string') return v;
    if (typeof v === 'number' || typeof v === 'boolean') return String(v);
    try {
      return JSON.stringify(v);
    } catch {
      return String(v);
    }
  };
  const { t } = useTranslation('translation', {
    keyPrefix: 'knowledgeDetails',
  });
  const { dataSourceInfo } = useDataSourceInfo();
  const { navigateToChunkParsedResult } = useNavigatePage();
  const { setDocumentStatus } = useSetDocumentStatus();

  const formatDate = (dateStr: string) => {
    if (!dateStr) return '-';
    const date = new Date(dateStr);

    const year = date.getFullYear(); // 获取本地年份
    const month = String(date.getMonth() + 1).padStart(2, '0'); // 月份从0开始
    const day = String(date.getDate()).padStart(2, '0'); // 获取本地日期
    const hours = String(date.getHours()).padStart(2, '0'); // 获取本地小时
    const minutes = String(date.getMinutes()).padStart(2, '0');
    const seconds = String(date.getSeconds()).padStart(2, '0');

    return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
  };
  const toMetaText = (typeCode: string, value: unknown) => {
    const optionMap = tagLabels.options[typeCode] || {};

    if (Array.isArray(value)) {
      if (!value.length) {
        return '-';
      }

      return value
        .map((optionCode) => {
          const code = String(optionCode);
          return optionMap[code] || code;
        })
        .join('、');
    }

    if (value === null || value === undefined || value === '') {
      return '-';
    }

    const code = String(value);
    return optionMap[code] || code;
  };
  const getMetaTypeName = (typeCode: string) => {
    return tagLabels.types[typeCode] || typeCode;
  };
  const parseMetaFields = (value: unknown): Record<string, unknown> => {
    if (!value) {
      return {};
    }

    if (typeof value === 'object' && !Array.isArray(value)) {
      return value as Record<string, unknown>;
    }

    if (typeof value === 'string') {
      try {
        const parsed = JSON.parse(value);

        if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
          return parsed as Record<string, unknown>;
        }
      } catch {
        return {};
      }
    }

    return {};
  };

  const columns: ColumnDef<IDocumentInfo>[] = [
    {
      id: 'select',
      header: ({ table }) => {
        const selectableRows = table
          .getRowModel()
          .rows.filter((row) => row.original.can_view === true);

        const selectedRows = selectableRows.filter((row) =>
          row.getIsSelected(),
        );

        const allSelected =
          selectableRows.length > 0 &&
          selectedRows.length === selectableRows.length;

        const someSelected =
          selectedRows.length > 0 &&
          selectedRows.length < selectableRows.length;

        return (
          <Checkbox
            checked={allSelected || (someSelected ? 'indeterminate' : false)}
            onCheckedChange={(value) => {
              const checked = value === true;

              selectableRows.forEach((row) => {
                row.toggleSelected(checked);
              });
            }}
            aria-label="Select all visible documents"
          />
        );
      },
      cell: ({ row }) => {
        const canView = hasViewPermission(row.original);

        if (!canView) {
          return <PermissionLock title="当前用户没有操作该文档的权限" />;
        }

        return (
          <Checkbox
            checked={row.getIsSelected()}
            onCheckedChange={(value) => row.toggleSelected(!!value)}
            aria-label="Select row"
          />
        );
      },
      enableSorting: false,
      enableHiding: false,
    },
    {
      accessorKey: 'name',
      header: ({ column }) => {
        return (
          <Button
            variant="transparent"
            className="border-none"
            onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
          >
            {t('name')}
            <ArrowUpDown />
          </Button>
        );
      },
      meta: { cellClassName: 'max-w-[20vw]' },
      cell: ({ row }) => {
        const name = toText(row.getValue('name'));
        const record = row.original as DisplayDocument;
        const canView = hasViewPermission(record);

        const handleOpenDocument = (
          event: React.MouseEvent<HTMLDivElement>,
        ) => {
          event.preventDefault();
          event.stopPropagation();

          if (!canView) {
            message.warning('当前用户没有查看该文档的权限');
            return;
          }

          const handler = navigateToChunkParsedResult(record.id, record.kb_id);

          if (typeof handler === 'function') {
            handler(event as any);
          }
        };

        return (
          <Tooltip>
            <TooltipTrigger asChild>
              <div
                className={cn(
                  'flex min-w-0 items-center gap-2',
                  canView ? 'cursor-pointer' : 'cursor-not-allowed ',
                )}
                onClick={handleOpenDocument}
                title={
                  canView
                    ? name
                    : '当前用户没有查看该文档的权限，请申请该库的内部权限'
                }
              >
                <FileIcon name={name} />

                {/* <span className={cn('truncate', !canView && 'text-gray-400')}>
                  {name}
                </span> */}
                <span className="truncate">{name}</span>

                {/* {!canView && (
                  <LockKeyhole
                    size={14}
                    strokeWidth={2}
                    className="shrink-0 text-gray-400"
                  />
                )} */}
              </div>
            </TooltipTrigger>

            <TooltipContent>
              <p>{canView ? name : `${name}`}</p>
            </TooltipContent>
          </Tooltip>
        );
      },
    },
    {
      accessorKey: 'create_time',
      header: ({ column }) => {
        return (
          <Button
            variant="transparent"
            className="border-none"
            onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
          >
            {t('uploadDate')}
            <ArrowUpDown />
          </Button>
        );
      },
      cell: ({ row }) => (
        <div className="lowercase whitespace-nowrap">
          {formatDate(row.getValue('create_time'))}
        </div>
      ),
    },
    ...tagColumns,

    {
      id: 'metadata',
      header: '来源信息',
      cell: ({ row }) => {
        const canView = hasViewPermission(row.original);
        const author = toText(row.original.author);

        const schoolRaw = row.original.school;
        let school = '';

        if (typeof schoolRaw === 'string') {
          const trimmed = schoolRaw.trim();

          if (trimmed && trimmed[0] !== '{' && trimmed[0] !== '[') {
            school = schoolRaw;
          }
        }

        const publishTime = toText(row.original.publish_time);

        return (
          <div className="group relative flex min-h-[20px] min-w-0 flex-col gap-1 text-xs text-text-secondary">
            <div className="flex min-w-0 items-center gap-1">
              <span className="shrink-0 whitespace-nowrap font-medium">
                作者:
              </span>

              <span className="min-w-0 max-w-[120px] truncate" title={author}>
                {author || '-'}
              </span>
            </div>

            <div className="flex min-w-0 items-center gap-1">
              <span className="shrink-0 whitespace-nowrap font-medium">
                学校:
              </span>

              <span className="min-w-0 max-w-[120px] truncate" title={school}>
                {school || '-'}
              </span>
            </div>

            <div className="flex min-w-0 items-center gap-1">
              <span className="shrink-0 whitespace-nowrap font-medium">
                发布日期:
              </span>

              <span
                className="min-w-0 max-w-[120px] truncate"
                title={publishTime}
              >
                {publishTime || '-'}
              </span>
            </div>

            {!readonly && canView && (
              <div className="absolute right-0 top-0 hidden group-hover:block">
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-6 w-6"
                  title={canEdit ? '手动输入' : '当前用户没有编辑权限'}
                  disabled={!canEdit}
                  onClick={() => {
                    if (!canEdit) {
                      message.warning('当前用户没有编辑权限');
                      return;
                    }

                    showSetMetaModal(row.original);
                  }}
                >
                  <Edit className="h-4 w-4" />
                </Button>
              </div>
            )}
          </div>
        );
      },
    },
    {
      id: 'source_type',
      accessorKey: 'source_type',
      header: t('source'),
      size: 30,
      minSize: 30,
      maxSize: 30,
      cell: ({ row }) => {
        const sourceType = row.original.source_type;

        return (
          <div className="flex w-[30px] items-center justify-center text-text-primary">
            {sourceType === 'local' || sourceType === '' ? (
              <div className="flex h-6 w-6 items-center justify-center rounded-full bg-accent-primary-5">
                <MonitorUp
                  className="text-accent-primary"
                  size={16}
                  strokeWidth={1.8}
                />
              </div>
            ) : (
              <div className="flex h-6 w-6 items-center justify-center">
                {dataSourceInfo[sourceType as keyof typeof dataSourceInfo]
                  ?.icon || null}
              </div>
            )}
          </div>
        );
      },
    },
    {
      accessorKey: 'status',
      header: t('enabled'),
      cell: ({ row }) => {
        const record = row.original as DisplayDocument;
        const id = record.id;
        const canView = hasViewPermission(record);

        if (!canView) {
          return <PermissionLock title="当前用户没有操作该文档的权限" />;
        }

        return (
          <Switch
            checked={String(row.getValue('status') ?? '') === '1'}
            disabled={readonly || !canEdit}
            onCheckedChange={(e) => {
              if (!canEdit) {
                message.warning('当前用户没有编辑权限');
                return;
              }

              setDocumentStatus({ status: e, documentId: id });
            }}
          />
        );
      },
    },
    {
      id: 'chunk_num',
      accessorKey: 'chunk_num',
      header: t('chunkNumber'),
      size: 60,
      minSize: 60,
      maxSize: 60,
      cell: ({ row }) => (
        <div className="w-[60px] whitespace-nowrap text-center">
          {String(row.original.chunk_num ?? '-')}
        </div>
      ),
    },
    {
      id: 'parsingStatus',
      header: t('parsingStatus'),
      cell: ({ row }) => {
        const record = row.original;
        const run = record.run;
        const chunkNum = record.chunk_num || 0; // 👈 获取解析出的 chunk 数量
        const processScene = record.process_scene;

        // ==========================================
        // 【核心逻辑】：根据 run 和 chunk_num 联合判断真实状态
        // ==========================================
        let statusText = '';
        let statusColor = '';

        if (processScene === 'author_only') {
          if (run === RunningStatus.DONE) {
            statusText = t(
              'statusAuthorSuccessNoParse',
              '提取成功<br />未解析',
            );
            statusColor = 'text-orange-500';
          } else if (run === RunningStatus.FAIL) {
            statusText = t('statusAuthorFailNoParse', '提取失败<br />未解析');
            statusColor = 'text-yellow-600';
          }
        } else if (processScene === 'author_with_parse') {
          if (run === RunningStatus.DONE) {
            statusText = t('statusAuthorSuccessParseSuccess', '解析成功');
            statusColor = 'text-green-600';
          } else if (run === RunningStatus.FAIL) {
            statusText = t('statusAuthorSuccessParseFail', '解析失败');
            statusColor = 'text-red-600';
          }
        } else if (processScene === 'parse_only') {
          if (run === RunningStatus.DONE) {
            statusText = t('statusParseSuccess', '解析成功');
            statusColor = 'text-green-600';
          } else if (run === RunningStatus.FAIL) {
            statusText = t('statusParseFail', '解析失败');
            statusColor = 'text-red-600';
          }
        }

        if (statusText) {
          const statusStyles = {
            'text-orange-500': {
              wrapper:
                'bg-orange-50 text-orange-700 border-orange-200 shadow-orange-100',
              dot: 'bg-orange-400',
            },
            'text-yellow-600': {
              wrapper:
                'bg-yellow-50 text-yellow-700 border-yellow-200 shadow-yellow-100',
              dot: 'bg-yellow-400',
            },
            'text-green-600': {
              wrapper:
                'bg-emerald-50 text-emerald-700 border-emerald-200 shadow-emerald-100',
              dot: 'bg-emerald-500',
            },
            'text-red-600': {
              wrapper: 'bg-red-50 text-red-700 border-red-200 shadow-red-100',
              dot: 'bg-red-500',
            },
          } as const;

          const currentStyle = statusStyles[
            statusColor as keyof typeof statusStyles
          ] ?? {
            wrapper:
              'bg-slate-50 text-slate-600 border-slate-200 shadow-slate-100',
            dot: 'bg-slate-400',
          };

          return (
            <div
              className={[
                'inline-flex items-center gap-1.5 rounded-xl border px-2.5 py-1',
                'text-xs font-medium leading-tight shadow-sm',
                'transition-colors duration-200',
                currentStyle.wrapper,
              ].join(' ')}
            >
              <span
                className={`h-1.5 w-1.5 shrink-0 rounded-full ${currentStyle.dot}`}
              />
              <span
                className="whitespace-nowrap text-center"
                dangerouslySetInnerHTML={{ __html: statusText }}
              />
            </div>
          );
        }

        const raw = typeof record.progress === 'number' ? record.progress : 0;
        const percent = Math.max(
          0,
          Math.min(100, Number((raw * 100).toFixed(2))),
        );
        const isRunning =
          run === RunningStatus.RUNNING || run === RunningStatus.SCHEDULE;
        const label = t(`runningStatus${run}`);

        if (!isRunning) {
          return <div className="text-xs text-text-secondary">{label}</div>;
        }

        return (
          <div
            className="flex items-center gap-2 cursor-pointer min-w-28"
            onClick={() => showLog(record)}
          >
            <Progress value={percent} className="h-1 flex-1" />
            <span className="text-xs text-text-secondary tabular-nums">
              {percent}%
            </span>
          </div>
        );
      },
    },
    {
      id: 'actions',
      header: t('action'),
      enableHiding: false,
      cell: ({ row }) => {
        const record = row.original as DisplayDocument;
        const canView = hasViewPermission(record);

        if (!canView) {
          return <PermissionLock title="当前用户没有操作该文档的权限" />;
        }

        return (
          <DatasetActionCell
            record={record}
            showRenameModal={showRenameModal}
            readonly={readonly}
            canEdit={canEdit}
            canUpload={canUpload}
            canDownload={canDownload}
            canDelete={canDelete}
          />
        );
      },
    },
  ];

  return columns;
}
