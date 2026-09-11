export type SearchTagFieldValue = string | string[];

export interface SearchTag {
  suffix: string[];
  run_status: string[];
  version: string;
  document_status: string[];
  applicable_lines: string[];
  knowledge_category: string[];
  knowledge_level: string[];
  knowledge_type: string[];
  author: string;
  school: string;
  publish_date: string[];

  /**
   * 兼容后端动态返回的 type_code
   */
  [key: string]: SearchTagFieldValue;
}

export const createEmptySearchTag = (): SearchTag => ({
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
});

export const normalizeSearchTag = (tag?: Partial<SearchTag>): SearchTag => {
  const source = tag || {};

  return {
    ...createEmptySearchTag(),
    ...source,

    suffix: Array.isArray(source.suffix) ? source.suffix : [],

    run_status: Array.isArray(source.run_status) ? source.run_status : [],

    version: typeof source.version === 'string' ? source.version : '',

    document_status: Array.isArray(source.document_status)
      ? source.document_status
      : [],

    applicable_lines: Array.isArray(source.applicable_lines)
      ? source.applicable_lines
      : [],

    knowledge_category: Array.isArray(source.knowledge_category)
      ? source.knowledge_category
      : [],

    knowledge_level: Array.isArray(source.knowledge_level)
      ? source.knowledge_level
      : [],

    knowledge_type: Array.isArray(source.knowledge_type)
      ? source.knowledge_type
      : [],

    author: typeof source.author === 'string' ? source.author : '',

    school: typeof source.school === 'string' ? source.school : '',

    publish_date: Array.isArray(source.publish_date) ? source.publish_date : [],
  };
};
