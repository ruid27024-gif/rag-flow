import { FilterCollection } from '@/components/list-filter-bar/interface';
import { useTranslate } from '@/hooks/common-hooks';
import { useGetDocumentFilter } from '@/hooks/use-document-request';
import { useMemo } from 'react';

// 辅助函数：处理值为数字的对象（如 author: { "张三": 5, "李四": 3 }）
const extractCounts = (obj: Record<string, number> | undefined) => {
  if (!obj) return [];
  return Object.entries(obj).map(([id, count]) => ({
    id,
    label: id, // 可直接显示 id，也可以做映射
    count,
  }));
};

// 辅助函数：处理值为 { count, name } 的对象（如 applicable_lines）
const extractNamedCounts = (
  obj: Record<string, { count: number; name: string }> | undefined,
) => {
  if (!obj) return [];
  return Object.entries(obj).map(([id, { count, name }]) => ({
    id,
    label: name || id,
    count,
  }));
};

export function useSelectDatasetFilters() {
  const { t } = useTranslate('knowledgeDetails');
  const { filter, onOpenChange } = useGetDocumentFilter();

  const fileTypes = useMemo(() => {
    if (filter.suffix) {
      return Object.keys(filter.suffix).map((x) => ({
        id: x,
        label: x.toUpperCase(),
        count: filter.suffix[x],
      }));
    }

    return [];
  }, [filter.suffix]);

  const fileStatus = useMemo(() => {
    if (filter.run_status) {
      return Object.keys(filter.run_status).map((x) => ({
        id: x,
        label: t(`runningStatus${x}`),
        count: filter.run_status[x as unknown as number],
      }));
    }

    return [];
  }, [filter.run_status, t]);

  const docStatus = useMemo(() => {
    const statusMap: Record<string, string> = {
      '0': '禁用',
      '1': '启用',
      '2': '回收站',
    };

    if (filter.document_status) {
      return Object.entries(filter.document_status).map(([id, count]) => ({
        id,
        label: statusMap[id] || id,
        count,
      }));
    }

    return [];
  }, [filter.document_status]);

  const applicableLines = useMemo(() => {
    return extractNamedCounts(filter.applicable_lines);
  }, [filter.applicable_lines]);

  const knowledgeCategory = useMemo(() => {
    return extractNamedCounts(filter.knowledge_category);
  }, [filter.knowledge_category]);

  const knowledgeLevel = useMemo(() => {
    return extractNamedCounts(filter.knowledge_level);
  }, [filter.knowledge_level]);

  const knowledgeType = useMemo(() => {
    return extractNamedCounts(filter.knowledge_type);
  }, [filter.knowledge_type]);

  const versions = useMemo(() => {
    return extractCounts(filter.version);
  }, [filter.version]);

  const filters: FilterCollection[] = useMemo(() => {
    return [
      {
        type: 'checkbox',
        field: 'type',
        label: '文件类型',
        list: fileTypes,
      },
      {
        type: 'checkbox',
        field: 'run',
        label: '状态',
        list: fileStatus,
      },
      {
        type: 'checkbox',
        field: 'version',
        label: '版本',
        list: versions,
      },
      {
        type: 'checkbox',
        field: 'document_status',
        label: '文档状态',
        list: docStatus,
      },
      {
        type: 'checkbox',
        field: 'applicable_lines',
        label: '适用产线',
        list: applicableLines,
      },
      {
        type: 'checkbox',
        field: 'knowledge_category',
        label: '知识分类',
        list: knowledgeCategory,
      },
      {
        type: 'checkbox',
        field: 'knowledge_level',
        label: '知识等级',
        list: knowledgeLevel,
      },
      {
        type: 'checkbox',
        field: 'knowledge_type',
        label: '知识类型',
        list: knowledgeType,
      },

      // 作者：输入框
      {
        type: 'text',
        field: 'author',
        label: '作者',
        placeholder: '请输入作者姓名',
      },

      // 学校：输入框
      {
        type: 'text',
        field: 'school',
        label: '学校',
        placeholder: '请输入学校名称',
      },

      // 时间：日期范围
      {
        type: 'date-range',
        field: 'publish_date',
        label: '发布时间',
      },
    ];
  }, [
    fileStatus,
    fileTypes,
    versions,
    docStatus,
    applicableLines,
    knowledgeCategory,
    knowledgeLevel,
    knowledgeType,
  ]);

  return {
    filters,
    onOpenChange,
  };
}

// export function useSelectDatasetFilters() {
//   const { t } = useTranslate('knowledgeDetails');
//   const { filter, onOpenChange } = useGetDocumentFilter();

//   // 文件类型（suffix）
//   const fileTypes = useMemo(() => {
//     if (filter.suffix) {
//       return Object.keys(filter.suffix).map((x) => ({
//         id: x,
//         label: x.toUpperCase(),
//         count: filter.suffix[x],
//       }));
//     }
//     return [];
//   }, [filter.suffix]);

//   // 运行状态（run_status）
//   const fileStatus = useMemo(() => {
//     if (filter.run_status) {
//       return Object.keys(filter.run_status).map((x) => ({
//         id: x,
//         label: t(`runningStatus${x}`), // 使用国际化
//         count: filter.run_status[x as unknown as number],
//       }));
//     }
//     return [];
//   }, [filter.run_status, t]);

//   // 新增：作者（author）
//   const authors = useMemo(() => {
//     return extractCounts(filter.author);
//   }, [filter.author]);

//   // 新增：文档状态（document_status）
//   const docStatus = useMemo(() => {
//     // 需要将数字键映射为可读标签，可借助国际化或硬编码映射
//     const statusMap: Record<string, string> = {
//       '0': '禁用',
//       '1': '启用',
//       '2': '回收站',
//     };
//     if (filter.document_status) {
//       return Object.entries(filter.document_status).map(([id, count]) => ({
//         id,
//         label: statusMap[id] || id,
//         count,
//       }));
//     }
//     return [];
//   }, [filter.document_status]);

//   // 新增：适用产线（applicable_lines）
//   const applicableLines = useMemo(() => {
//     return extractNamedCounts(filter.applicable_lines);
//   }, [filter.applicable_lines]);

//   // 新增：知识分类（knowledge_category）
//   const knowledgeCategory = useMemo(() => {
//     return extractNamedCounts(filter.knowledge_category);
//   }, [filter.knowledge_category]);

//   // 新增：知识等级（knowledge_level）
//   const knowledgeLevel = useMemo(() => {
//     return extractNamedCounts(filter.knowledge_level);
//   }, [filter.knowledge_level]);

//   // 新增：知识类型（knowledge_type）
//   const knowledgeType = useMemo(() => {
//     return extractNamedCounts(filter.knowledge_type);
//   }, [filter.knowledge_type]);

//   // 新增：学校（school）
//   const schools = useMemo(() => {
//     return extractCounts(filter.school);
//   }, [filter.school]);

//   // 版本（StagedFile.version）
//   const versions = useMemo(() => {
//     return extractCounts(filter.version);
//   }, [filter.version]);

//   // 组装 filters 数组
//   const filters: FilterCollection[] = useMemo(() => {
//     return [
//       // 已有的
//       { field: 'type', label: '文件类型', list: fileTypes },
//       { field: 'run', label: '状态', list: fileStatus },
//       { field: 'version', label: '版本', list: versions },

//       // { field: 'author', label: '作者', list: authors },
//       { field: 'document_status', label: '文档状态', list: docStatus },
//       { field: 'applicable_lines', label: '适用产线', list: applicableLines },
//       {
//         field: 'knowledge_category',
//         label: '知识分类',
//         list: knowledgeCategory,
//       },
//       { field: 'knowledge_level', label: '知识等级', list: knowledgeLevel },
//       { field: 'knowledge_type', label: '知识类型', list: knowledgeType },
//       // { field: 'school', label: '学校', list: schools },
//     ] as FilterCollection[];
//   }, [
//     fileStatus,
//     fileTypes,
//     applicableLines,
//     authors,
//     docStatus,
//     knowledgeCategory,
//     knowledgeLevel,
//     knowledgeType,
//     schools,
//   ]);

//   return { filters, onOpenChange };
// }

// export function useSelectDatasetFilters() {
//   const { t } = useTranslate('knowledgeDetails');
//   const { filter, onOpenChange } = useGetDocumentFilter();

//   const fileTypes = useMemo(() => {
//     if (filter.suffix) {
//       return Object.keys(filter.suffix).map((x) => ({
//         id: x,
//         label: x.toUpperCase(),
//         count: filter.suffix[x],
//       }));
//     }
//   }, [filter.suffix]);
//   const fileStatus = useMemo(() => {
//     if (filter.run_status) {
//       return Object.keys(filter.run_status).map((x) => ({
//         id: x,
//         label: t(`runningStatus${x}`),
//         count: filter.run_status[x as unknown as number],
//       }));
//     }
//   }, [filter.run_status, t]);
//   const filters: FilterCollection[] = useMemo(() => {
//     return [
//       // { field: 'type', label: 'File Type', list: fileTypes },
//       // { field: 'run', label: 'Status', list: fileStatus },
//       { field: 'type', label: '文件类型', list: fileTypes },
//       { field: 'run', label: '状态', list: fileStatus },
//     ] as FilterCollection[];
//   }, [fileStatus, fileTypes]);

//   return { filters, onOpenChange };
// }
