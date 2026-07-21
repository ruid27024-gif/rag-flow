// import { Button } from '@/components/ui/button';
// import {
//   Command,
//   CommandEmpty,
//   CommandGroup,
//   CommandInput,
//   CommandItem,
//   CommandList,
//   CommandSeparator,
// } from '@/components/ui/command';
// import { MultiSelectOptionType } from '@/components/ui/multi-select';
// import {
//   Popover,
//   PopoverContent,
//   PopoverTrigger,
// } from '@/components/ui/popover';
// import { Separator } from '@/components/ui/separator';
// import {
//   useAllTestingResult,
//   useChunkIsTesting,
//   useSelectTestingResult,
// } from '@/hooks/use-knowledge-request';
// import { cn } from '@/lib/utils';
// import { CheckIcon, ChevronDown, Files, XIcon } from 'lucide-react';
// import { useEffect, useMemo, useState } from 'react';

// interface IProps {
//   onTesting(documentIds: string[]): void;
//   setSelectedDocumentIds(documentIds: string[]): void;
//   selectedDocumentIds: string[];
//   setLoading?: (loading: boolean) => void;
// }

// const RetrievalDocuments = ({
//   onTesting,
//   selectedDocumentIds,
//   setSelectedDocumentIds,
//   setLoading,
// }: IProps) => {
//   const { documents: documentsAll } = useAllTestingResult();
//   const { documents } = useSelectTestingResult();
//   const isTesting = useChunkIsTesting();
//   const [isPopoverOpen, setIsPopoverOpen] = useState(false);

//   useEffect(() => {
//     if (isTesting) {
//       setLoading?.(true);
//     } else {
//       setLoading?.(false);
//     }
//   }, [isTesting, setLoading]);

//   const { documents: useDocuments } = {
//     documents:
//       documentsAll?.length > documents?.length ? documentsAll : documents,
//   };

//   const [selectedValues, setSelectedValues] =
//     useState<string[]>(selectedDocumentIds);

//   useEffect(() => {
//     setSelectedValues(selectedDocumentIds);
//   }, [selectedDocumentIds]);

//   const multiOptions = useMemo(() => {
//     if (!useDocuments || !useDocuments.length) {
//       return [];
//     }
//     return useDocuments?.map((item) => {
//       return {
//         label: item.doc_name,
//         value: item.doc_id,
//         disabled: item.doc_name === 'Disabled User',
//         // suffix: (
//         //   <div className="flex justify-between gap-3 ">
//         //     <div>{item.count}</div>
//         //     <div>
//         //       <Eye />
//         //     </div>
//         //   </div>
//         // ),
//       };
//     });
//   }, [useDocuments]);

//   const handleTogglePopover = () => {
//     setIsPopoverOpen((prev) => !prev);
//   };

//   const onValueChange = (value: string[]) => {
//     console.log(value);
//     onTesting(value);
//     setSelectedDocumentIds(value);
//     // handleDatasetSelectChange(value, field.onChange);
//   };
//   const handleClear = () => {
//     setSelectedValues([]);
//     onValueChange([]);
//   };

//   // const handleInputKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
//   //   if (event.key === 'Enter') {
//   //     setIsPopoverOpen(true);
//   //   } else if (event.key === 'Backspace' && !event.currentTarget.value) {
//   //     const newSelectedValues = [...selectedValues];
//   //     newSelectedValues.pop();
//   //     setSelectedValues(newSelectedValues);
//   //     onValueChange(newSelectedValues);
//   //   }
//   // };
//   const handleInputKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
//     if (event.key === 'Enter') {
//       setIsPopoverOpen(true);
//     } else if (event.key === 'Backspace' && !event.currentTarget.value) {
//       const newSelectedValues = [...selectedValues];
//       newSelectedValues.pop();
//       setSelectedValues(newSelectedValues);
//     }
//   };

//   const toggleOption = (option: string) => {
//     const newSelectedValues = selectedValues.includes(option)
//       ? selectedValues.filter((value) => value !== option)
//       : [...selectedValues, option];
//     setSelectedValues(newSelectedValues);
//     // onValueChange(newSelectedValues);
//   };
//   // 新增确认函数
//   const handleConfirm = () => {
//     onValueChange(selectedValues);
//     setIsPopoverOpen(false);
//   };
//   return (
//     <Popover open={isPopoverOpen} onOpenChange={setIsPopoverOpen}>
//       {useDocuments?.length > 0 && (
//         <PopoverTrigger asChild>
//           {useDocuments?.length && (
//             <Button
//               onClick={handleTogglePopover}
//               className={cn(
//                 'flex w-full p-1 rounded-md text-base text-text-primary border min-h-10 h-auto items-center justify-between bg-inherit hover:bg-inherit [&_svg]:pointer-events-auto',
//               )}
//             >
//               <div className="flex justify-between items-center w-full">
//                 <div className="flex flex-wrap items-center gap-2">
//                   <Files />
//                   {/* <span>
//                   {selectedDocumentIds?.length ?? 0}/{useDocuments?.length ?? 0}
//                 </span>
//                 文件 */}
//                   <span>
//                     {selectedDocumentIds?.length
//                       ? `已选 ${selectedDocumentIds.length}/${useDocuments?.length ?? 0}`
//                       : `全部 ${useDocuments?.length ?? 0}`}
//                   </span>
//                   文件
//                 </div>
//                 <div className="flex items-center justify-between">
//                   <XIcon
//                     className="h-4 mx-2 cursor-pointer text-muted-foreground"
//                     onClick={(event) => {
//                       event.stopPropagation();
//                       handleClear();
//                     }}
//                   />
//                   <Separator
//                     orientation="vertical"
//                     className="flex min-h-6 h-full"
//                   />
//                   <ChevronDown className="h-4 mx-2 cursor-pointer text-muted-foreground" />
//                 </div>
//               </div>
//             </Button>
//           )}
//         </PopoverTrigger>
//       )}
//       {/* <PopoverContent
//         className="w-auto p-0"
//         align="start"
//         onEscapeKeyDown={() => setIsPopoverOpen(false)}
//       > */}
//       <PopoverContent
//         side="bottom"
//         align="start"
//         sideOffset={6}
//         className="z-50 w-[320px] p-0"
//         onOpenAutoFocus={(event) => {
//           event.preventDefault();
//         }}
//         onEscapeKeyDown={() => setIsPopoverOpen(false)}
//       >
//         <Command>
//           <CommandInput placeholder="搜索..." onKeyDown={handleInputKeyDown} />
//           <CommandList>
//             <CommandEmpty>未找到结果.</CommandEmpty>
//             <CommandGroup>
//               {!multiOptions.some((x) => 'options' in x) &&
//                 (multiOptions as unknown as MultiSelectOptionType[]).map(
//                   (option) => {
//                     const isSelected = selectedValues.includes(option.value);
//                     return (
//                       <CommandItem
//                         key={option.value}
//                         onSelect={() => {
//                           if (option.disabled) return false;
//                           toggleOption(option.value);
//                         }}
//                         className={cn('cursor-pointer', {
//                           'cursor-not-allowed text-text-disabled':
//                             option.disabled,
//                         })}
//                       >
//                         <div
//                           className={cn(
//                             'mr-2 flex h-4 w-4 items-center justify-center rounded-sm border border-primary',
//                             isSelected
//                               ? 'bg-primary '
//                               : 'opacity-50 [&_svg]:invisible',

//                             { 'text-primary-foreground': !option.disabled },
//                             { 'text-text-disabled': option.disabled },
//                           )}
//                         >
//                           <CheckIcon className="h-4 w-4" />
//                         </div>
//                         {option.icon && (
//                           <option.icon
//                             className={cn('mr-2 h-4 w-4 ', {
//                               'text-text-disabled': option.disabled,
//                               'text-muted-foreground': !option.disabled,
//                             })}
//                           />
//                         )}
//                         <span
//                           className={cn({
//                             'text-text-disabled': option.disabled,
//                           })}
//                         >
//                           {option.label}
//                         </span>
//                         {option.suffix && (
//                           <span
//                             className={cn({
//                               'text-text-disabled': option.disabled,
//                             })}
//                           >
//                             {option.suffix}
//                           </span>
//                         )}
//                       </CommandItem>
//                     );
//                   },
//                 )}
//             </CommandGroup>
//             <CommandSeparator />
//             {/* <CommandGroup>
//               <div className="flex items-center justify-between">
//                 {selectedValues.length > 0 && (
//                   <>
//                     <CommandItem
//                       onSelect={handleClear}
//                       className="flex-1 justify-center cursor-pointer"
//                     >
//                       清空
//                     </CommandItem>
//                     <Separator
//                       orientation="vertical"
//                       className="flex min-h-6 h-full"
//                     />
//                   </>
//                 )}
//                 <CommandItem
//                   onSelect={() => setIsPopoverOpen(false)}
//                   className="flex-1 justify-center cursor-pointer max-w-full"
//                 >
//                   关闭
//                 </CommandItem>
//               </div>
//             </CommandGroup> */}
//             <CommandGroup>
//               <div className="flex items-center justify-between">
//                 <CommandItem
//                   onSelect={handleClear}
//                   className="flex-1 justify-center cursor-pointer"
//                 >
//                   清空
//                 </CommandItem>

//                 <Separator
//                   orientation="vertical"
//                   className="flex min-h-6 h-full"
//                 />

//                 <CommandItem
//                   onSelect={() => {
//                     handleConfirm();
//                     return false; // 👈 关键：阻止 cmdk 默认的关闭行为，防止闪烁
//                   }}
//                   className="flex-1 justify-center cursor-pointer text-primary"
//                 >
//                   确认
//                 </CommandItem>

//                 <Separator
//                   orientation="vertical"
//                   className="flex min-h-6 h-full"
//                 />

//                 <CommandItem
//                   onSelect={() => {
//                     setSelectedValues(selectedDocumentIds);
//                     setIsPopoverOpen(false);
//                   }}
//                   className="flex-1 justify-center cursor-pointer max-w-full"
//                 >
//                   关闭
//                 </CommandItem>
//               </div>
//             </CommandGroup>
//           </CommandList>
//         </Command>
//       </PopoverContent>
//     </Popover>
//   );
// };

// export default RetrievalDocuments;

import { Button } from '@/components/ui/button';
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from '@/components/ui/command';
import { MultiSelectOptionType } from '@/components/ui/multi-select';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { Separator } from '@/components/ui/separator';
import {
  useChunkIsTesting,
  useSelectTestingResult,
} from '@/hooks/use-knowledge-request';
import { cn } from '@/lib/utils';
import { CheckIcon, ChevronDown, Files, XIcon } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';

interface IProps {
  onTesting(documentIds: string[]): void;
  setSelectedDocumentIds(documentIds: string[]): void;
  selectedDocumentIds: string[];
  setLoading?: (loading: boolean) => void;

  /**
   * 每次新问题时改变这个值，用来重置组件内部状态
   */
  resetKey?: string | number;
}

type TestingDocument = {
  doc_id: string;
  doc_name: string;
  [key: string]: any;
};

const RetrievalDocuments = ({
  onTesting,
  selectedDocumentIds,
  setSelectedDocumentIds,
  setLoading,
  resetKey,
}: IProps) => {
  /**
   * documents 是当前检索返回的文档。
   *
   * 注意：
   * 当用户选择部分文件后，这个 documents 很可能会变成筛选后的文件列表。
   * 比如原来 43 个，少选一个后接口返回 42 个。
   *
   * 所以不能直接拿 documents.length 当分母。
   */
  const { documents } = useSelectTestingResult();
  const isTesting = useChunkIsTesting();

  const [isPopoverOpen, setIsPopoverOpen] = useState(false);

  /**
   * selectedValues 是弹窗内部临时选择值。
   * 点击确认后才同步给外部 selectedDocumentIds。
   */
  const [selectedValues, setSelectedValues] =
    useState<string[]>(selectedDocumentIds);

  /**
   * baseDocuments 表示当前问题的原始可选文档列表。
   *
   * 例如：
   * 问题「淀粉」第一次返回 43 个文件，这里就保存 43 个。
   * 后续用户少选一个，接口返回 42 个，也不会覆盖 baseDocuments。
   *
   * 这样按钮才能显示：
   * 已选 42/43
   */
  const [baseDocuments, setBaseDocuments] = useState<TestingDocument[]>([]);

  /**
   * 新问题开始时，父组件改变 resetKey。
   * 这里清空内部选择状态和基础文档列表。
   */
  useEffect(() => {
    if (resetKey === undefined) return;

    setSelectedValues([]);
    setBaseDocuments([]);
    setSelectedDocumentIds([]);
    setIsPopoverOpen(false);
  }, [resetKey, setSelectedDocumentIds]);

  /**
   * 检索 loading 同步给父组件
   */
  useEffect(() => {
    setLoading?.(!!isTesting);
  }, [isTesting, setLoading]);

  /**
   * 外部 selectedDocumentIds 改变时，同步到内部 selectedValues。
   */
  useEffect(() => {
    setSelectedValues(selectedDocumentIds);
  }, [selectedDocumentIds]);

  /**
   * 只在「全部文件」状态下，更新当前问题的原始文档列表。
   *
   * selectedDocumentIds.length === 0 表示全部文件。
   *
   * 用户已经选择部分文件后：
   * selectedDocumentIds.length > 0
   *
   * 这时接口返回的 documents 可能是筛选后的 42 个，
   * 不能再覆盖 baseDocuments，否则分母会变成 42。
   */
  useEffect(() => {
    if (!documents?.length) return;

    if (selectedDocumentIds.length === 0) {
      setBaseDocuments(documents as TestingDocument[]);
    }
  }, [documents, selectedDocumentIds.length]);

  /**
   * 页面中真正用于展示下拉选项、计算分母的文档列表。
   */
  const useDocuments = baseDocuments;

  /**
   * 下拉选项
   */
  const multiOptions = useMemo(() => {
    if (!useDocuments?.length) {
      return [];
    }

    return useDocuments.map((item) => {
      return {
        label: item.doc_name,
        value: item.doc_id,
        disabled: item.doc_name === 'Disabled User',
      };
    });
  }, [useDocuments]);

  /**
   * 所有可选文档 ID
   */
  const allDocumentIds = useMemo(() => {
    return multiOptions
      .filter((item) => !item.disabled)
      .map((item) => item.value);
  }, [multiOptions]);

  /**
   * 约定：
   * selectedValues = [] 表示全部文件
   */
  const isAllSelected = selectedValues.length === 0;

  /**
   * 真正通知父组件选择变化
   */
  const onValueChange = (value: string[]) => {
    onTesting(value);
    setSelectedDocumentIds(value);
  };

  /**
   * 恢复全部文件。
   *
   * 注意：
   * 这里不是清空为 0 个文件。
   * 因为我们约定 [] 表示全部。
   */
  const handleClear = () => {
    setSelectedValues([]);
    onValueChange([]);
  };

  const handleInputKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter') {
      setIsPopoverOpen(true);
      return;
    }

    if (event.key === 'Backspace' && !event.currentTarget.value) {
      /**
       * 当前是全部状态，Backspace 不处理。
       */
      if (selectedValues.length === 0) return;

      const newSelectedValues = [...selectedValues];
      newSelectedValues.pop();

      /**
       * 如果删完后等于空数组，也就是恢复全部。
       */
      setSelectedValues(newSelectedValues);
    }
  };

  /**
   * 切换某个文档的选择状态
   */
  const toggleOption = (option: string) => {
    let newSelectedValues: string[];

    /**
     * 当前是「全部文件」状态。
     *
     * 此时点击某一个文件，含义是：
     * 从全部文件中取消这个文件。
     *
     * 例如总共 43 个，点掉 1 个，就变成 42 个。
     */
    if (selectedValues.length === 0) {
      newSelectedValues = allDocumentIds.filter((value) => value !== option);
    } else {
      newSelectedValues = selectedValues.includes(option)
        ? selectedValues.filter((value) => value !== option)
        : [...selectedValues, option];
    }

    /**
     * 如果用户重新选满全部文件，则归一化为 []。
     *
     * [] 表示全部文件。
     */
    if (newSelectedValues.length === allDocumentIds.length) {
      newSelectedValues = [];
    }

    setSelectedValues(newSelectedValues);
  };

  /**
   * 点击确认后，才真正触发外部检索
   */
  const handleConfirm = () => {
    /**
     * 防御性处理：
     * 如果选中了全部 ID，统一转成 []，表示全部。
     */
    const normalizedValues =
      selectedValues.length === allDocumentIds.length ? [] : selectedValues;

    onValueChange(normalizedValues);
    setIsPopoverOpen(false);
  };

  /**
   * 点击关闭或者外部关闭时，不保存临时选择，恢复到上一次确认的值。
   */
  const handleClose = () => {
    setSelectedValues(selectedDocumentIds);
    setIsPopoverOpen(false);
  };

  /**
   * Popover 外部点击关闭时，也恢复未确认的临时选择。
   */
  const handleOpenChange = (open: boolean) => {
    if (!open) {
      setSelectedValues(selectedDocumentIds);
    }

    setIsPopoverOpen(open);
  };

  /**
   * 当前问题还没有文档时，不展示
   */
  if (!useDocuments?.length) {
    return null;
  }

  return (
    <Popover open={isPopoverOpen} onOpenChange={handleOpenChange}>
      <PopoverTrigger asChild>
        <Button
          className={cn(
            'flex w-full p-1 rounded-md text-base text-text-primary border min-h-10 h-auto items-center justify-between bg-inherit hover:bg-inherit [&_svg]:pointer-events-auto',
          )}
        >
          <div className="flex justify-between items-center w-full">
            <div className="flex flex-wrap items-center gap-2">
              <Files />
              <span>
                {selectedDocumentIds?.length
                  ? `已选 ${selectedDocumentIds.length}/${useDocuments.length}`
                  : `全部 ${useDocuments.length}`}
              </span>
              文件
            </div>

            <div className="flex items-center justify-between">
              <XIcon
                className="h-4 mx-2 cursor-pointer text-muted-foreground"
                onClick={(event) => {
                  event.stopPropagation();
                  handleClear();
                }}
              />

              <Separator
                orientation="vertical"
                className="flex min-h-6 h-full"
              />

              <ChevronDown className="h-4 mx-2 cursor-pointer text-muted-foreground" />
            </div>
          </div>
        </Button>
      </PopoverTrigger>

      <PopoverContent
        side="bottom"
        align="start"
        sideOffset={6}
        className="z-50 w-[320px] p-0"
        onOpenAutoFocus={(event) => {
          event.preventDefault();
        }}
        onEscapeKeyDown={handleClose}
      >
        <Command>
          <CommandInput placeholder="搜索..." onKeyDown={handleInputKeyDown} />

          <CommandList>
            <CommandEmpty>未找到结果.</CommandEmpty>

            <CommandGroup>
              {!multiOptions.some((x) => 'options' in x) &&
                (multiOptions as unknown as MultiSelectOptionType[]).map(
                  (option) => {
                    /**
                     * selectedValues = [] 表示全部文件。
                     * 所以默认状态下，所有非 disabled 选项都显示勾选。
                     */
                    const isSelected =
                      !option.disabled &&
                      (isAllSelected || selectedValues.includes(option.value));

                    return (
                      <CommandItem
                        key={option.value}
                        onSelect={() => {
                          if (option.disabled) return;
                          toggleOption(option.value);
                        }}
                        className={cn('cursor-pointer', {
                          'cursor-not-allowed text-text-disabled':
                            option.disabled,
                        })}
                      >
                        <div
                          className={cn(
                            'mr-2 flex h-4 w-4 items-center justify-center rounded-sm border border-primary',
                            isSelected
                              ? 'bg-primary'
                              : 'opacity-50 [&_svg]:invisible',
                            {
                              'text-primary-foreground': !option.disabled,
                            },
                            {
                              'text-text-disabled': option.disabled,
                            },
                          )}
                        >
                          <CheckIcon className="h-4 w-4" />
                        </div>

                        {option.icon && (
                          <option.icon
                            className={cn('mr-2 h-4 w-4', {
                              'text-text-disabled': option.disabled,
                              'text-muted-foreground': !option.disabled,
                            })}
                          />
                        )}

                        <span
                          className={cn({
                            'text-text-disabled': option.disabled,
                          })}
                        >
                          {option.label}
                        </span>

                        {option.suffix && (
                          <span
                            className={cn({
                              'text-text-disabled': option.disabled,
                            })}
                          >
                            {option.suffix}
                          </span>
                        )}
                      </CommandItem>
                    );
                  },
                )}
            </CommandGroup>

            <CommandSeparator />

            <CommandGroup>
              <div className="flex items-center justify-between">
                {/* <CommandItem
                  onSelect={handleClear}
                  className="flex-1 justify-center cursor-pointer"
                >
                  全部
                </CommandItem> */}

                <Separator
                  orientation="vertical"
                  className="flex min-h-6 h-full"
                />

                <CommandItem
                  onSelect={() => {
                    handleConfirm();
                  }}
                  className="flex-1 justify-center cursor-pointer text-primary"
                >
                  确认
                </CommandItem>

                <Separator
                  orientation="vertical"
                  className="flex min-h-6 h-full"
                />

                <CommandItem
                  onSelect={handleClose}
                  className="flex-1 justify-center cursor-pointer max-w-full"
                >
                  关闭
                </CommandItem>
              </div>
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
};

export default RetrievalDocuments;
