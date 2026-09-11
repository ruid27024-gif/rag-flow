import { useGetPaginationWithRouter } from '@/hooks/logic-hooks';
import { useCallback, useState } from 'react';
import { FilterChange, FilterValue } from './interface';

// export function useHandleFilterSubmit() {
//   // const [filterValue, setFilterValue] = useState<FilterValue>({});
//   const [filterValue, setFilterValue] = useState<FilterValue>({
//     type: [],
//     run: [],
//     version: [],
//     document_status: [],
//     applicable_lines: [],
//     knowledge_category: [],
//     knowledge_level: [],
//     knowledge_type: [],
//   });
//   const { setPagination } = useGetPaginationWithRouter();
//   const handleFilterSubmit: FilterChange = useCallback(
//     (value) => {
//       setFilterValue(value);
//       setPagination({ page: 1 });
//     },
//     [setPagination],
//   );

//   return { filterValue, setFilterValue, handleFilterSubmit };
// }

export function useHandleFilterSubmit() {
  const [filterValue, setFilterValue] = useState<FilterValue>({
    type: [],
    run: [],
    version: [],
    document_status: [],
    applicable_lines: [],
    knowledge_category: [],
    knowledge_level: [],
    knowledge_type: [],

    author: '',
    school: '',
    publish_date: {
      start: '',
      end: '',
    },
  });

  const { setPagination } = useGetPaginationWithRouter();

  const handleFilterSubmit: FilterChange = useCallback(
    (value) => {
      console.log('提交筛选条件:', value);

      setFilterValue(value);
      setPagination({ page: 1 });
    },
    [setPagination],
  );

  return {
    filterValue,
    setFilterValue,
    handleFilterSubmit,
  };
}
