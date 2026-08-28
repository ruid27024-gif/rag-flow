import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { zodResolver } from '@hookform/resolvers/zod';
import { PropsWithChildren, useCallback, useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { ZodArray, ZodString, z } from 'zod';

import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
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

export type CheckboxFormMultipleProps = {
  filters?: FilterCollection[];
  value?: FilterValue;
  onChange?: FilterChange;
  onOpenChange?: (open: boolean) => void;
  setOpen(open: boolean): void;
};

function CheckboxFormMultiple({
  filters = [],
  value,
  onChange,
  setOpen,
}: CheckboxFormMultipleProps) {
  const fieldsDict = filters?.reduce<Record<string, Array<any>>>((pre, cur) => {
    pre[cur.field] = [];
    return pre;
  }, {});

  const FormSchema = z.object(
    filters.reduce<Record<string, ZodArray<ZodString, 'many'>>>((pre, cur) => {
      pre[cur.field] = z.array(z.string());

      // .refine((value) => value.some((item) => item), {
      //   message: 'You have to select at least one item.',
      // });
      return pre;
    }, {}),
  );

  const form = useForm<z.infer<typeof FormSchema>>({
    resolver: zodResolver(FormSchema),
    defaultValues: fieldsDict,
  });

  function onSubmit(data: z.infer<typeof FormSchema>) {
    onChange?.(data);
    setOpen(false);
  }

  const onReset = useCallback(() => {
    onChange?.(fieldsDict);
    setOpen(false);
  }, [fieldsDict, onChange, setOpen]);

  useEffect(() => {
    form.reset(value);
  }, [form, value]);

  return (
    <Form {...form}>
      <form
        onSubmit={form.handleSubmit(onSubmit)}
        className="space-y-8 px-5 py-2.5"
        onReset={() => form.reset()}
      >
        {/* {filters.map((x) => (
          <FormField
            key={x.field}
            control={form.control}
            name={x.field}
            render={() => (
              <FormItem className="space-y-4">
                <div>
                  <FormLabel className="text-base text-text-sub-title-invert">
                    {x.label}
                  </FormLabel>
                </div>
                {x.list.map((item) => (
                  <FormField
                    key={item.id}
                    control={form.control}
                    name={x.field}
                    render={({ field }) => {
                      return (
                        <div className="flex items-center justify-between text-text-primary text-xs">
                          <FormItem
                            key={item.id}
                            className="flex flex-row  space-x-3 space-y-0 items-center "
                          >
                            <FormControl>
                              <Checkbox
                                checked={field.value?.includes(item.id)}
                                onCheckedChange={(checked) => {
                                  return checked
                                    ? field.onChange([...field.value, item.id])
                                    : field.onChange(
                                        field.value?.filter(
                                          (value) => value !== item.id,
                                        ),
                                      );
                                }}
                              />
                            </FormControl>
                            <FormLabel>{item.label}</FormLabel>
                          </FormItem>
                          <span className=" text-sm">{item.count}</span>
                        </div>
                      );
                    }}
                  />
                ))}
                <FormMessage />
              </FormItem>
            )}
          />
        ))} */}
        {filters.map((filter) => (
          <Collapsible key={filter.field} className="group">
            <FormField
              control={form.control}
              name={filter.field}
              render={() => (
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
                    <div className="space-y-1 pb-1 pl-1">
                      {filter.list.map((item) => (
                        <FormField
                          key={item.id}
                          control={form.control}
                          name={filter.field}
                          render={({ field }) => {
                            const selectedValues = field.value ?? [];

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
                                                (value) => value !== item.id,
                                              ),
                                        );
                                      }}
                                    />
                                  </FormControl>

                                  <FormLabel className="cursor-pointer text-xs leading-4">
                                    {item.label}
                                  </FormLabel>
                                </FormItem>

                                <span className="text-xs leading-4">
                                  {item.count}
                                </span>
                              </div>
                            );
                          }}
                        />
                      ))}

                      <FormMessage />
                    </div>
                  </CollapsibleContent>
                </FormItem>
              )}
            />
          </Collapsible>
        ))}
        <div className="flex justify-end gap-5">
          <Button
            type="button"
            variant={'outline'}
            size={'sm'}
            onClick={onReset}
          >
            {t('common.clear')}
          </Button>
          <Button type="submit" size={'sm'}>
            {t('common.submit')}
          </Button>
        </div>
      </form>
    </Form>
  );
}

// import {
//   Accordion,
//   AccordionContent,
//   AccordionItem,
//   AccordionTrigger,
// } from '@/components/ui/accordion';

// import { useMemo } from 'react';

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
//   const fieldsDict = useMemo(
//     () =>
//       filters.reduce<Record<string, string[]>>((result, current) => {
//         result[current.field] = [];
//         return result;
//       }, {}),
//     [filters],
//   );

//   const formSchema = useMemo(
//     () =>
//       z.object(
//         filters.reduce<Record<string, z.ZodArray<z.ZodString>>>(
//           (result, current) => {
//             result[current.field] = z.array(z.string());
//             return result;
//           },
//           {},
//         ),
//       ),
//     [filters],
//   );

//   type FormValues = z.infer<typeof formSchema>;

//   const form = useForm<FormValues>({
//     resolver: zodResolver(formSchema),
//     defaultValues: fieldsDict as FormValues,
//   });

//   useEffect(() => {
//     form.reset((value ?? fieldsDict) as FormValues);
//   }, [form, value, fieldsDict]);

//   function onSubmit(data: FormValues) {
//     onChange?.(data);
//     setOpen(false);
//   }

//   const onReset = useCallback(() => {
//     form.reset(fieldsDict as FormValues);
//     onChange?.(fieldsDict);
//     setOpen(false);
//   }, [fieldsDict, form, onChange, setOpen]);

//   return (
//     <Form {...form}>
//       <form
//         onSubmit={form.handleSubmit(onSubmit)}
//         className="px-5 py-2.5"
//       >
//         <Accordion
//           type="multiple"
//           defaultValue={[]}
//           className="w-full"
//         >
//           {filters.map((filter) => (
//             <AccordionItem
//               key={filter.field}
//               value={filter.field}
//             >
//               <FormField
//                 control={form.control}
//                 name={filter.field}
//                 render={() => (
//                   <FormItem className="border-0">
//                     <AccordionTrigger className="py-3 text-base text-text-sub-title-invert hover:no-underline">
//                       {filter.label}
//                     </AccordionTrigger>

//                     <AccordionContent className="pb-3">
//                       <div className="space-y-3">
//                         {filter.list.map((item) => (
//                           <FormField
//                             key={item.id}
//                             control={form.control}
//                             name={filter.field}
//                             render={({ field }) => (
//                               <div className="flex items-center justify-between text-xs text-text-primary">
//                                 <FormItem className="flex flex-row items-center space-x-3 space-y-0">
//                                   <FormControl>
//                                     <Checkbox
//                                       checked={field.value?.includes(item.id)}
//                                       onCheckedChange={(checked) => {
//                                         const currentValue =
//                                           field.value ?? [];

//                                         field.onChange(
//                                           checked
//                                             ? [
//                                                 ...currentValue,
//                                                 item.id,
//                                               ]
//                                             : currentValue.filter(
//                                                 (selectedValue) =>
//                                                   selectedValue !== item.id,
//                                               ),
//                                         );
//                                       }}
//                                     />
//                                   </FormControl>

//                                   <FormLabel className="cursor-pointer">
//                                     {item.label}
//                                   </FormLabel>
//                                 </FormItem>

//                                 <span className="text-sm text-muted-foreground">
//                                   {item.count}
//                                 </span>
//                               </div>
//                             )}
//                           />
//                         ))}

//                         <FormMessage />
//                       </div>
//                     </AccordionContent>
//                   </FormItem>
//                 )}
//               />
//             </AccordionItem>
//           ))}
//         </Accordion>

//         <div className="flex justify-end gap-5 pt-4">
//           <Button
//             type="button"
//             variant="outline"
//             size="sm"
//             onClick={onReset}
//           >
//             {t('common.clear')}
//           </Button>

//           <Button type="submit" size="sm">
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
//       <PopoverContent className="p-0">
//         <CheckboxFormMultiple
//           onChange={onChange}
//           value={value}
//           filters={filters}
//           setOpen={setOpen}
//         ></CheckboxFormMultiple>
//       </PopoverContent>
//     </Popover>
//   );
// }

export function FilterPopover({
  children,
  value,
  onChange,
  onOpenChange,
  filters,
}: PropsWithChildren & Omit<CheckboxFormMultipleProps, 'setOpen'>) {
  const [open, setOpen] = useState(false);
  const onOpenChangeFun = useCallback(
    (e: boolean) => {
      onOpenChange?.(e);
      setOpen(e);
    },
    [onOpenChange],
  );
  return (
    <Popover open={open} onOpenChange={onOpenChangeFun}>
      <PopoverTrigger asChild>{children}</PopoverTrigger>
      <PopoverContent className="p-4 max-h-[60vh] overflow-y-auto">
        <CheckboxFormMultiple
          onChange={onChange}
          value={value}
          filters={filters}
          setOpen={setOpen}
        />
      </PopoverContent>
    </Popover>
  );
}
