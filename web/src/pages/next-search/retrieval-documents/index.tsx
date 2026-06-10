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
import { useEffect, useMemo, useState } from 'react';

interface IProps {
  onTesting(documentIds: string[]): void;
  setSelectedDocumentIds(documentIds: string[]): void;
  selectedDocumentIds: string[];
  setLoading?: (loading: boolean) => void;
}

const RetrievalDocuments = ({
  onTesting,
  selectedDocumentIds,
  setSelectedDocumentIds,
  setLoading,
}: IProps) => {
  const { documents: documentsAll } = useAllTestingResult();
  const { documents } = useSelectTestingResult();
  const isTesting = useChunkIsTesting();
  const [isPopoverOpen, setIsPopoverOpen] = useState(false);

  useEffect(() => {
    if (isTesting) {
      setLoading?.(true);
    } else {
      setLoading?.(false);
    }
  }, [isTesting, setLoading]);

  const { documents: useDocuments } = {
    documents:
      documentsAll?.length > documents?.length ? documentsAll : documents,
  };

  const [selectedValues, setSelectedValues] =
    useState<string[]>(selectedDocumentIds);

  useEffect(() => {
    setSelectedValues(selectedDocumentIds);
  }, [selectedDocumentIds]);

  const multiOptions = useMemo(() => {
    if (!useDocuments || !useDocuments.length) {
      return [];
    }
    return useDocuments?.map((item) => {
      return {
        label: item.doc_name,
        value: item.doc_id,
        disabled: item.doc_name === 'Disabled User',
        // suffix: (
        //   <div className="flex justify-between gap-3 ">
        //     <div>{item.count}</div>
        //     <div>
        //       <Eye />
        //     </div>
        //   </div>
        // ),
      };
    });
  }, [useDocuments]);

  const handleTogglePopover = () => {
    setIsPopoverOpen((prev) => !prev);
  };

  const onValueChange = (value: string[]) => {
    console.log(value);
    onTesting(value);
    setSelectedDocumentIds(value);
    // handleDatasetSelectChange(value, field.onChange);
  };
  const handleClear = () => {
    setSelectedValues([]);
    onValueChange([]);
  };

  // const handleInputKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
  //   if (event.key === 'Enter') {
  //     setIsPopoverOpen(true);
  //   } else if (event.key === 'Backspace' && !event.currentTarget.value) {
  //     const newSelectedValues = [...selectedValues];
  //     newSelectedValues.pop();
  //     setSelectedValues(newSelectedValues);
  //     onValueChange(newSelectedValues);
  //   }
  // };
  const handleInputKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter') {
      setIsPopoverOpen(true);
    } else if (event.key === 'Backspace' && !event.currentTarget.value) {
      const newSelectedValues = [...selectedValues];
      newSelectedValues.pop();
      setSelectedValues(newSelectedValues);
    }
  };

  const toggleOption = (option: string) => {
    const newSelectedValues = selectedValues.includes(option)
      ? selectedValues.filter((value) => value !== option)
      : [...selectedValues, option];
    setSelectedValues(newSelectedValues);
    // onValueChange(newSelectedValues);
  };
  // 新增确认函数
  const handleConfirm = () => {
    onValueChange(selectedValues);
    setIsPopoverOpen(false);
  };
  return (
    <Popover open={isPopoverOpen} onOpenChange={setIsPopoverOpen}>
      {useDocuments?.length > 0 && (
        <PopoverTrigger asChild>
          {useDocuments?.length && (
            <Button
              onClick={handleTogglePopover}
              className={cn(
                'flex w-full p-1 rounded-md text-base text-text-primary border min-h-10 h-auto items-center justify-between bg-inherit hover:bg-inherit [&_svg]:pointer-events-auto',
              )}
            >
              <div className="flex justify-between items-center w-full">
                <div className="flex flex-wrap items-center gap-2">
                  <Files />
                  {/* <span>
                  {selectedDocumentIds?.length ?? 0}/{useDocuments?.length ?? 0}
                </span>
                文件 */}
                  <span>
                    {selectedDocumentIds?.length
                      ? `已选 ${selectedDocumentIds.length}/${useDocuments?.length ?? 0}`
                      : `全部 ${useDocuments?.length ?? 0}`}
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
          )}
        </PopoverTrigger>
      )}
      {/* <PopoverContent
        className="w-auto p-0"
        align="start"
        onEscapeKeyDown={() => setIsPopoverOpen(false)}
      > */}
      <PopoverContent
        side="bottom"
        align="start"
        sideOffset={6}
        className="z-50 w-[320px] p-0"
        onOpenAutoFocus={(event) => {
          event.preventDefault();
        }}
        onEscapeKeyDown={() => setIsPopoverOpen(false)}
      >
        <Command>
          <CommandInput placeholder="搜索..." onKeyDown={handleInputKeyDown} />
          <CommandList>
            <CommandEmpty>未找到结果.</CommandEmpty>
            <CommandGroup>
              {!multiOptions.some((x) => 'options' in x) &&
                (multiOptions as unknown as MultiSelectOptionType[]).map(
                  (option) => {
                    const isSelected = selectedValues.includes(option.value);
                    return (
                      <CommandItem
                        key={option.value}
                        onSelect={() => {
                          if (option.disabled) return false;
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
                              ? 'bg-primary '
                              : 'opacity-50 [&_svg]:invisible',

                            { 'text-primary-foreground': !option.disabled },
                            { 'text-text-disabled': option.disabled },
                          )}
                        >
                          <CheckIcon className="h-4 w-4" />
                        </div>
                        {option.icon && (
                          <option.icon
                            className={cn('mr-2 h-4 w-4 ', {
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
            {/* <CommandGroup>
              <div className="flex items-center justify-between">
                {selectedValues.length > 0 && (
                  <>
                    <CommandItem
                      onSelect={handleClear}
                      className="flex-1 justify-center cursor-pointer"
                    >
                      清空
                    </CommandItem>
                    <Separator
                      orientation="vertical"
                      className="flex min-h-6 h-full"
                    />
                  </>
                )}
                <CommandItem
                  onSelect={() => setIsPopoverOpen(false)}
                  className="flex-1 justify-center cursor-pointer max-w-full"
                >
                  关闭
                </CommandItem>
              </div>
            </CommandGroup> */}
            <CommandGroup>
              <div className="flex items-center justify-between">
                <CommandItem
                  onSelect={handleClear}
                  className="flex-1 justify-center cursor-pointer"
                >
                  清空
                </CommandItem>

                <Separator
                  orientation="vertical"
                  className="flex min-h-6 h-full"
                />

                <CommandItem
                  onSelect={() => {
                    handleConfirm();
                    return false; // 👈 关键：阻止 cmdk 默认的关闭行为，防止闪烁
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
                  onSelect={() => {
                    setSelectedValues(selectedDocumentIds);
                    setIsPopoverOpen(false);
                  }}
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
