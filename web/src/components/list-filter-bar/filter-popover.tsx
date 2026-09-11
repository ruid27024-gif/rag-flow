// import {
//   Popover,
//   PopoverContent,
//   PopoverTrigger,
// } from '@/components/ui/popover';
// import { zodResolver } from '@hookform/resolvers/zod';
// import { PropsWithChildren, useCallback, useEffect, useState } from 'react';
// import { useForm } from 'react-hook-form';
// import { ZodArray, ZodString, z } from 'zod';

// import { Button } from '@/components/ui/button';
// import { Checkbox } from '@/components/ui/checkbox';
// import {
//   Collapsible,
//   CollapsibleContent,
//   CollapsibleTrigger,
// } from '@/components/ui/collapsible';
// import {
//   Form,
//   FormControl,
//   FormField,
//   FormItem,
//   FormLabel,
//   FormMessage,
// } from '@/components/ui/form';
// import { t } from 'i18next';
// import { ChevronDown } from 'lucide-react';
// import { FilterChange, FilterCollection, FilterValue } from './interface';

// export type CheckboxFormMultipleProps = {
//   filters?: FilterCollection[];
//   value?: FilterValue;
//   onChange?: FilterChange;
//   onOpenChange?: (open: boolean) => void;
//   setOpen(open: boolean): void;
// };

// function CheckboxFormMultiple({
//   filters = [],
//   value,
//   onChange,
//   setOpen,
// }: CheckboxFormMultipleProps) {
//   const fieldsDict = filters?.reduce<Record<string, Array<any>>>((pre, cur) => {
//     pre[cur.field] = [];
//     return pre;
//   }, {});

//   const FormSchema = z.object(
//     filters.reduce<Record<string, ZodArray<ZodString, 'many'>>>((pre, cur) => {
//       pre[cur.field] = z.array(z.string());

//       return pre;
//     }, {}),
//   );

//   const form = useForm<z.infer<typeof FormSchema>>({
//     resolver: zodResolver(FormSchema),
//     defaultValues: fieldsDict,
//   });

//   function onSubmit(data: z.infer<typeof FormSchema>) {
//     onChange?.(data);
//     setOpen(false);
//   }

//   const onReset = useCallback(() => {
//     onChange?.(fieldsDict);
//     setOpen(false);
//   }, [fieldsDict, onChange, setOpen]);

//   useEffect(() => {
//     form.reset(value);
//   }, [form, value]);

//   return (
//     <Form {...form}>
//       <form
//         onSubmit={form.handleSubmit(onSubmit)}
//         className="space-y-8 px-5 py-2.5"
//         onReset={() => form.reset()}
//       >

//         {filters.map((filter) => (
//           <Collapsible key={filter.field} className="group">
//             <FormField
//               control={form.control}
//               name={filter.field}
//               render={() => (
//                 <FormItem className="space-y-0">
//                   <CollapsibleTrigger asChild>
//                     <button
//                       type="button"
//                       className="flex w-full items-center justify-between py-1 text-left"
//                     >
//                       <FormLabel className="cursor-pointer text-sm leading-5 text-text-sub-title-invert">
//                         {filter.label}
//                       </FormLabel>

//                       <ChevronDown
//                         aria-hidden="true"
//                         className="size-3.5 shrink-0 transition-transform duration-200 group-data-[state=open]:rotate-180"
//                       />
//                     </button>
//                   </CollapsibleTrigger>

//                   <CollapsibleContent>
//                     <div className="space-y-1 pb-1 pl-1">
//                       {filter.list.map((item) => (
//                         <FormField
//                           key={item.id}
//                           control={form.control}
//                           name={filter.field}
//                           render={({ field }) => {
//                             const selectedValues = field.value ?? [];

//                             return (
//                               <div className="flex min-h-6 items-center justify-between text-xs text-text-primary">
//                                 <FormItem className="flex flex-row items-center space-x-2 space-y-0">
//                                   <FormControl>
//                                     <Checkbox
//                                       checked={selectedValues.includes(item.id)}
//                                       onCheckedChange={(checked) => {
//                                         field.onChange(
//                                           checked === true
//                                             ? [...selectedValues, item.id]
//                                             : selectedValues.filter(
//                                                 (value) => value !== item.id,
//                                               ),
//                                         );
//                                       }}
//                                     />
//                                   </FormControl>

//                                   <FormLabel className="cursor-pointer text-xs leading-4">
//                                     {item.label}
//                                   </FormLabel>
//                                 </FormItem>

//                                 <span className="text-xs leading-4">
//                                   {item.count}
//                                 </span>
//                               </div>
//                             );
//                           }}
//                         />
//                       ))}

//                       <FormMessage />
//                     </div>
//                   </CollapsibleContent>
//                 </FormItem>
//               )}
//             />
//           </Collapsible>
//         ))}
//         <div className="flex justify-end gap-5">
//           <Button
//             type="button"
//             variant={'outline'}
//             size={'sm'}
//             onClick={onReset}
//           >
//             {t('common.clear')}
//           </Button>
//           <Button type="submit" size={'sm'}>
//             {t('common.submit')}
//           </Button>
//         </div>
//       </form>
//     </Form>
//   );
// }

// export function FilterPopover({
//   children,
//   value,
//   onChange,
//   onOpenChange,
//   filters,
// }: PropsWithChildren & Omit<CheckboxFormMultipleProps, 'setOpen'>) {
//   const [open, setOpen] = useState(false);
//   const onOpenChangeFun = useCallback(
//     (e: boolean) => {
//       onOpenChange?.(e);
//       setOpen(e);
//     },
//     [onOpenChange],
//   );
//   return (
//     <Popover open={open} onOpenChange={onOpenChangeFun}>
//       <PopoverTrigger asChild>{children}</PopoverTrigger>
//       <PopoverContent className="p-4 max-h-[60vh] overflow-y-auto">
//         <CheckboxFormMultiple
//           onChange={onChange}
//           value={value}
//           filters={filters}
//           setOpen={setOpen}
//         />
//       </PopoverContent>
//     </Popover>
//   );
// }

import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { zodResolver } from '@hookform/resolvers/zod';
import {
  PropsWithChildren,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';

import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';

import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';

import { t } from 'i18next';
import { ChevronDown } from 'lucide-react';
import { FilterChange, FilterCollection, FilterValue } from './interface';

function CheckboxFormMultiple({
  filters = [],
  value,
  onChange,
  setOpen,
}: {
  filters?: FilterCollection[];
  value?: FilterValue;
  onChange?: FilterChange;
  setOpen(open: boolean): void;
}) {
  const { formSchema, defaultValues } = useMemo(() => {
    const schemaShape: Record<string, z.ZodTypeAny> = {};
    const defaults: Record<string, any> = {};

    filters.forEach((filter) => {
      const type = filter.type ?? 'checkbox';

      if (type === 'checkbox') {
        schemaShape[filter.field] = z.array(z.string());
        defaults[filter.field] = [];
      }

      if (type === 'text') {
        schemaShape[filter.field] = z.string();
        defaults[filter.field] = '';
      }

      if (type === 'date-range') {
        schemaShape[`${filter.field}_start`] = z.string();
        schemaShape[`${filter.field}_end`] = z.string();

        defaults[`${filter.field}_start`] = '';
        defaults[`${filter.field}_end`] = '';
      }
    });

    return {
      formSchema: z.object(schemaShape),
      defaultValues: defaults,
    };
  }, [filters]);

  const form = useForm({
    resolver: zodResolver(formSchema),
    defaultValues,
  });

  useEffect(() => {
    form.reset({
      ...defaultValues,
      ...value,
    });
  }, [form, value, defaultValues]);

  const onSubmit = (data: Record<string, any>) => {
    const result: FilterValue = {
      ...data,

      // 将开始日期、结束日期组装成一个时间对象
      publish_date: {
        start: data.publish_date_start || undefined,
        end: data.publish_date_end || undefined,
      },
    };

    // 删除中间字段，避免同时传三种时间字段
    delete result.publish_date_start;
    delete result.publish_date_end;

    // 如果没有选择时间，则删除 publish_date
    const publishDate = result.publish_date as
      | { start?: string; end?: string }
      | undefined;

    if (!publishDate?.start && !publishDate?.end) {
      delete result.publish_date;
    }

    onChange?.(result);
    setOpen(false);
  };

  const onReset = useCallback(() => {
    const emptyFilterValue: FilterValue = {
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
    };

    form.reset(emptyFilterValue);
    onChange?.(emptyFilterValue);
    setOpen(false);
  }, [form, onChange, setOpen]);
  return (
    <Form {...form}>
      <form
        onSubmit={form.handleSubmit(onSubmit)}
        className="space-y-5 px-1 py-2"
      >
        {filters.map((filter) => {
          const type = filter.type ?? 'checkbox';

          return (
            <Collapsible key={filter.field} className="group">
              <FormItem className="space-y-0">
                <CollapsibleTrigger asChild>
                  <button
                    type="button"
                    className="flex w-full items-center justify-between py-1 text-left"
                  >
                    <FormLabel className="cursor-pointer text-sm leading-5 text-text-sub-title-invert">
                      {filter.label}
                    </FormLabel>

                    <ChevronDown
                      aria-hidden="true"
                      className="size-3.5 shrink-0 transition-transform duration-200 group-data-[state=open]:rotate-180"
                    />
                  </button>
                </CollapsibleTrigger>

                <CollapsibleContent>
                  <div className="space-y-2 pb-2 pl-1">
                    {type === 'checkbox' && (
                      <CheckboxContent filter={filter} form={form} />
                    )}

                    {type === 'text' && (
                      <FormField
                        control={form.control}
                        name={filter.field}
                        render={({ field }) => (
                          <FormItem>
                            <FormControl>
                              <Input
                                {...field}
                                value={field.value ?? ''}
                                placeholder={filter.placeholder}
                                className="h-8"
                              />
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                    )}

                    {type === 'date-range' && (
                      <div className="flex items-end gap-2">
                        <FormField
                          control={form.control}
                          name={`${filter.field}_start`}
                          render={({ field }) => (
                            <FormItem className="flex-1">
                              <FormLabel className="text-xs">
                                开始日期
                              </FormLabel>
                              <FormControl>
                                <Input
                                  {...field}
                                  type="date"
                                  value={field.value ?? ''}
                                  className="h-8"
                                />
                              </FormControl>
                            </FormItem>
                          )}
                        />

                        <span className="pb-2 text-xs">至</span>

                        <FormField
                          control={form.control}
                          name={`${filter.field}_end`}
                          render={({ field }) => (
                            <FormItem className="flex-1">
                              <FormLabel className="text-xs">
                                结束日期
                              </FormLabel>
                              <FormControl>
                                <Input
                                  {...field}
                                  type="date"
                                  value={field.value ?? ''}
                                  className="h-8"
                                />
                              </FormControl>
                            </FormItem>
                          )}
                        />
                      </div>
                    )}
                  </div>
                </CollapsibleContent>
              </FormItem>
            </Collapsible>
          );
        })}

        <div className="flex justify-end gap-3">
          <Button type="button" variant="outline" size="sm" onClick={onReset}>
            {t('common.clear')}
          </Button>

          <Button type="submit" size="sm">
            {t('common.submit')}
          </Button>
        </div>
      </form>
    </Form>
  );
}

function CheckboxContent({
  filter,
  form,
}: {
  filter: Extract<FilterCollection, { type?: 'checkbox' }>;
  form: any;
}) {
  return (
    <div className="space-y-1">
      {filter.list.map((item) => (
        <FormField
          key={item.id}
          control={form.control}
          name={filter.field}
          render={({ field }) => {
            const selectedValues: string[] = field.value ?? [];

            return (
              <div className="flex min-h-6 items-center justify-between text-xs text-text-primary">
                <FormItem className="flex flex-row items-center space-x-2 space-y-0">
                  <FormControl>
                    <Checkbox
                      checked={selectedValues.includes(item.id)}
                      onCheckedChange={(checked) => {
                        field.onChange(
                          checked === true
                            ? [...selectedValues, item.id]
                            : selectedValues.filter(
                                (itemId) => itemId !== item.id,
                              ),
                        );
                      }}
                    />
                  </FormControl>

                  <FormLabel className="cursor-pointer text-xs leading-4">
                    {item.label}
                  </FormLabel>
                </FormItem>

                <span className="text-xs leading-4">{item.count ?? ''}</span>
              </div>
            );
          }}
        />
      ))}

      <FormMessage />
    </div>
  );
}

export function FilterPopover({
  children,
  value,
  onChange,
  onOpenChange,
  filters,
}: PropsWithChildren &
  Omit<
    {
      filters?: FilterCollection[];
      value?: FilterValue;
      onChange?: FilterChange;
      onOpenChange?: (open: boolean) => void;
    },
    'setOpen'
  >) {
  const [open, setOpen] = useState(false);

  const onOpenChangeFun = useCallback(
    (openValue: boolean) => {
      onOpenChange?.(openValue);
      setOpen(openValue);
    },
    [onOpenChange],
  );

  return (
    <Popover open={open} onOpenChange={onOpenChangeFun}>
      <PopoverTrigger asChild>{children}</PopoverTrigger>

      <PopoverContent className="w-80 max-h-[60vh] overflow-y-auto p-4">
        <CheckboxFormMultiple
          value={value}
          onChange={onChange}
          filters={filters}
          setOpen={setOpen}
        />
      </PopoverContent>
    </Popover>
  );
}
