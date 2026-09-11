// export type FilterType = {
//   id: string;
//   label: string | JSX.Element;
//   count?: number;
// };

// export type FilterCollection = {
//   field: string;
//   label: string;
//   list: FilterType[];
// };

// export type FilterValue = Record<string, Array<string>>;

// export type FilterChange = (value: FilterValue) => void;

export type FilterType = {
  id: string;
  label: string | JSX.Element;
  count?: number;
};

export type CheckboxFilterCollection = {
  type?: 'checkbox';
  field: string;
  label: string | JSX.Element;
  list: FilterType[];
};

export type TextFilterCollection = {
  type: 'text';
  field: string;
  label: string | JSX.Element;
  placeholder?: string;
};

export type DateRangeFilterCollection = {
  type: 'date-range';
  field: string;
  label: string | JSX.Element;
};

export type FilterCollection =
  | CheckboxFilterCollection
  | TextFilterCollection
  | DateRangeFilterCollection;

export type DateRangeValue = {
  start?: string;
  end?: string;
};

export type FilterValue = Record<
  string,
  string[] | string | DateRangeValue | undefined
>;

export type FilterChange = (value: FilterValue) => void;
