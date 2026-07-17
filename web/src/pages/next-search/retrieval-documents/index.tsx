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
  useAllTestingResult,
  useChunkIsTesting,
  useSelectTestingResult,
} from '@/hooks/use-knowledge-request';
import { cn } from '@/lib/utils';
import { CheckIcon, ChevronDown, Files, XIcon } from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';

interface IProps {
  onTesting(documentIds: string[]): void;
  setSelectedDocumentIds(documentIds: string[]): void;
  selectedDocumentIds: string[];
  setLoading?: (loading: boolean) => void;

  /**
   * 每次搜索变化时传入一个变化值，例如 searchVersion。
   * 用来重置为默认全选。
   */
  resetKey?: string | number;
}

/**
 * 约定：
 * [] = 清空，一个文件都不选
 * allDocumentIds = 全部
 * 部分 id = 部分选择
 */
const RetrievalDocuments = ({
  onTesting,
  selectedDocumentIds,
  setSelectedDocumentIds,
  setLoading,
  resetKey,
}: IProps) => {
  const { documents: documentsAll } = useAllTestingResult();
  const { documents } = useSelectTestingResult();
  const isTesting = useChunkIsTesting();

  const [isPopoverOpen, setIsPopoverOpen] = useState(false);

  /**
   * 弹窗内部临时选择值。
   * 点击确认后才真正生效。
   */
  const [selectedValues, setSelectedValues] =
    useState<string[]>(selectedDocumentIds);

  /**
   * 记录当前 resetKey。
   */
  const lastResetKeyRef = useRef<string | number | '__INITIAL__' | undefined>(
    undefined,
  );

  /**
   * 记录当前搜索下已经应用过默认全选的文档列表。
   */
  const lastAppliedDocumentIdsKeyRef = useRef<string | undefined>(undefined);

  /**
   * 当前搜索内用户是否手动操作过。
   * 用户清空后，不能又被自动恢复成全选。
   */
  const hasUserChangedRef = useRef(false);

  useEffect(() => {
    setLoading?.(!!isTesting);
  }, [isTesting, setLoading]);

  /**
   * 当前文档列表。
   *
   * 注意：
   * 不要再用 documentsAll.length > documents.length 的方式。
   * 否则搜索切换时容易拿到旧数据，出现 62/41。
   */
  const useDocuments = useMemo(() => {
    return documents?.length ? documents : documentsAll;
  }, [documents, documentsAll]);

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
   * 当前文档列表中所有可选文档 id。
   */
  const allDocumentIds = useMemo(() => {
    return multiOptions
      .filter((item) => !item.disabled)
      .map((item) => item.value);
  }, [multiOptions]);

  const allDocumentIdsKey = useMemo(() => {
    return allDocumentIds.join('|');
  }, [allDocumentIds]);

  const currentDocumentIdSet = useMemo(() => {
    return new Set(allDocumentIds);
  }, [allDocumentIds]);

  /**
   * 过滤掉旧搜索遗留的 id。
   * 防止显示 62/41。
   */
  const validSelectedDocumentIds = useMemo(() => {
    return selectedDocumentIds.filter((id) => currentDocumentIdSet.has(id));
  }, [selectedDocumentIds, currentDocumentIdSet]);

  /**
   * resetKey 变化，说明是一次新搜索。
   * 新搜索时要允许重新默认全选。
   */
  useEffect(() => {
    const currentResetKey = resetKey ?? '__INITIAL__';

    if (lastResetKeyRef.current === currentResetKey) {
      return;
    }

    lastResetKeyRef.current = currentResetKey;
    lastAppliedDocumentIdsKeyRef.current = undefined;
    hasUserChangedRef.current = false;
  }, [resetKey]);

  /**
   * 默认全选 / 新搜索后重置为全选。
   *
   * 注意：
   * 这里是把 selectedDocumentIds 设置为所有文档 id，
   * 而不是设置成 []。
   */
  useEffect(() => {
    if (!allDocumentIds.length) {
      return;
    }

    /**
     * 当前搜索内用户已经手动清空/选择过，就不要自动恢复全选。
     */
    if (hasUserChangedRef.current) {
      return;
    }

    /**
     * 当前文档列表已经默认全选过，就不重复执行。
     */
    if (lastAppliedDocumentIdsKeyRef.current === allDocumentIdsKey) {
      return;
    }

    lastAppliedDocumentIdsKeyRef.current = allDocumentIdsKey;

    setSelectedValues(allDocumentIds);
    setSelectedDocumentIds(allDocumentIds);

    /**
     * 一般不要在这里调用 onTesting(allDocumentIds)，
     * 因为外部 handleSearch 通常已经请求了默认结果。
     *
     * 如果你确认默认全选后必须重新请求，可以打开：
     */
    // onTesting(allDocumentIds);
  }, [allDocumentIds, allDocumentIdsKey, setSelectedDocumentIds]);

  /**
   * 外部 selectedDocumentIds 变化时，同步弹窗内部状态。
   */
  useEffect(() => {
    setSelectedValues(validSelectedDocumentIds);
  }, [validSelectedDocumentIds]);

  /**
   * 最终提交选择。
   */
  const onValueChange = (value: string[]) => {
    hasUserChangedRef.current = true;

    const nextValue = value.filter((id) => currentDocumentIdSet.has(id));

    setSelectedDocumentIds(nextValue);
    onTesting(nextValue);
  };

  /**
   * 顶部 X：立即清空并生效。
   */
  const handleClearImmediately = () => {
    setSelectedValues([]);
    onValueChange([]);
  };

  /**
   * 弹窗底部清空：只改临时值，点击确认后才生效。
   */
  const handleClearInPopover = () => {
    setSelectedValues([]);
  };

  /**
   * 弹窗底部全部：只改临时值，点击确认后才生效。
   */
  const handleSelectAllInPopover = () => {
    setSelectedValues(allDocumentIds);
  };

  const handleInputKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter') {
      setIsPopoverOpen(true);
      return;
    }

    if (event.key === 'Backspace' && !event.currentTarget.value) {
      const newSelectedValues = [...selectedValues];
      newSelectedValues.pop();

      setSelectedValues(
        newSelectedValues.filter((id) => currentDocumentIdSet.has(id)),
      );
    }
  };

  const toggleOption = (optionValue: string) => {
    const baseSelectedValues = selectedValues.filter((id) =>
      currentDocumentIdSet.has(id),
    );

    const newSelectedValues = baseSelectedValues.includes(optionValue)
      ? baseSelectedValues.filter((id) => id !== optionValue)
      : [...baseSelectedValues, optionValue];

    setSelectedValues(newSelectedValues);
  };

  const handleConfirm = () => {
    onValueChange(selectedValues);
    setIsPopoverOpen(false);
  };

  const handleClose = () => {
    setSelectedValues(validSelectedDocumentIds);
    setIsPopoverOpen(false);
  };

  const handlePopoverOpenChange = (open: boolean) => {
    setSelectedValues(validSelectedDocumentIds);
    setIsPopoverOpen(open);
  };

  if (!useDocuments?.length) {
    return null;
  }

  const totalCount = allDocumentIds.length;
  const selectedCount = validSelectedDocumentIds.length;

  const isAllSelected = totalCount > 0 && selectedCount === totalCount;

  const triggerText = isAllSelected
    ? `全部 ${totalCount}`
    : `已选 ${selectedCount}/${totalCount}`;

  return (
    <Popover open={isPopoverOpen} onOpenChange={handlePopoverOpenChange}>
      <PopoverTrigger asChild>
        <Button
          className={cn(
            'flex w-full p-1 rounded-md text-base text-text-primary border min-h-10 h-auto items-center justify-between bg-inherit hover:bg-inherit [&_svg]:pointer-events-auto',
          )}
        >
          <div className="flex justify-between items-center w-full">
            <div className="flex flex-wrap items-center gap-2">
              <Files />
              <span>{triggerText}</span>
              文件
            </div>

            <div className="flex items-center justify-between">
              <XIcon
                className="h-4 mx-2 cursor-pointer text-muted-foreground"
                onClick={(event) => {
                  event.stopPropagation();
                  event.preventDefault();
                  handleClearImmediately();
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
              {(multiOptions as unknown as MultiSelectOptionType[]).map(
                (option) => {
                  const isSelected = selectedValues.includes(option.value);

                  return (
                    <CommandItem
                      key={option.value}
                      onSelect={() => {
                        if (option.disabled) {
                          return;
                        }

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
                <CommandItem
                  onSelect={handleClearInPopover}
                  className="flex-1 justify-center cursor-pointer"
                >
                  清空
                </CommandItem>

                <Separator
                  orientation="vertical"
                  className="flex min-h-6 h-full"
                />

                <CommandItem
                  onSelect={handleSelectAllInPopover}
                  className="flex-1 justify-center cursor-pointer"
                >
                  全部
                </CommandItem>

                <Separator
                  orientation="vertical"
                  className="flex min-h-6 h-full"
                />

                <CommandItem
                  onSelect={handleConfirm}
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
