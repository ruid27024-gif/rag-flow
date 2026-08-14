import { getAuthorization } from '@/utils/authorization-util';
import { DownOutlined, UpOutlined } from '@ant-design/icons';
import {
  Button,
  Checkbox,
  Form,
  Input,
  Modal,
  Radio,
  Select,
  Space,
  Switch,
  Table,
  Tag,
  Tooltip,
  TreeSelect,
  message,
  theme,
} from 'antd';
import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'umi';
import './index.less';

const { Option } = Select;

const FILE_PERMISSION_LEVEL = {
  PUBLIC: 1,
  INTERNAL: 2,
};

const operationOptions = [
  { label: '查看', value: 'view' },
  { label: '上传', value: 'upload' },
  { label: '下载', value: 'download' },
  { label: '删除', value: 'delete' },
  { label: '编辑', value: 'edit' },
];

const FILE_PERMISSION_TEXT: Record<number, string> = {
  1: '公开',
  2: '内部',
};

const OPERATION_PERMISSION_MAP: Record<string, number> = {
  查看: 1,
  上传: 2,
  下载: 4,
  删除: 8,
  编辑: 16,
};

const OPERATION_PERMISSION_VALUE_MAP: Record<string, number> = {
  view: 1,
  upload: 2,
  download: 4,
  delete: 8,
  edit: 16,
};

interface RoleItem {
  id: number;
  role_name: string;
  file_permission_level: number;
  operation_permission_mask: number;
  operation_permissions?: string[];
  need_approval: boolean;
  approval_order: number;
  department_id?: string | null;
  department_ids?: string[];
  is_admin: boolean;
  cover_child_dept: boolean;
  enabled: boolean;
  created_by?: string | null;
  created_by_name?: string | null;
  created_time?: string | number | null;
  updated_time?: string | number | null;
}

interface RoleFormValues {
  role_name: string;
  file_permission_level: number;
  operation_permissions: string[];
  need_approval: boolean;
  approval_order: number;

  /**
   * 前端表单使用数组
   */
  department_ids?: string[];

  is_admin: boolean;
  cover_child_dept: boolean;
  enabled: boolean;
}

interface PersonTreeItem {
  id: string;
  key: string;
  value: string;
  title: string;
  type?: 'company' | 'dept' | 'person' | 'group';
  selectable?: boolean;
  disabled?: boolean;
  children?: PersonTreeItem[];

  phone?: string;
  email?: string;
  user_id?: string;
  bindable?: boolean;

  companyCode?: string | null;
  parentId?: string | null;
  organizationCode?: string | null;
  mdmCode?: string | null;
  mdmName?: string | null;
  organize?: string | null;
  part?: string | null;
}

interface DeptTreeItem {
  id: string;
  key: string;
  value: string;
  title: string;
  parentId?: string | null;
  departmentName?: string | null;
  departmentCode?: string | null;
  longName?: string | null;
  longCode?: string | null;
  companyCode?: string | null;
  corporateName?: string | null;
  children?: DeptTreeItem[];
}

const parseOperationPermissions = (mask: number) => {
  const result: string[] = [];

  Object.entries(OPERATION_PERMISSION_MAP).forEach(([label, bit]) => {
    if (mask & bit) {
      result.push(label);
    }
  });

  return result;
};

const parseOperationMaskToValues = (mask: number): string[] => {
  const result: string[] = [];

  Object.entries(OPERATION_PERMISSION_VALUE_MAP).forEach(([value, bit]) => {
    if (mask & bit) {
      result.push(value);
    }
  });

  return result;
};

/**
 * 解析 department_id
 * 兼容：
 * 1. null
 * 2. "dept001"
 * 3. '["dept001","dept002"]'
 * 4. ["dept001","dept002"]
 */
const normalizeDepartmentIds = (value: any): string[] => {
  if (!value) {
    return [];
  }

  if (Array.isArray(value)) {
    return value.filter(Boolean);
  }

  if (typeof value === 'string') {
    try {
      const parsed = JSON.parse(value);

      if (Array.isArray(parsed)) {
        return parsed.filter(Boolean);
      }

      if (parsed) {
        return [String(parsed)];
      }
    } catch (e) {
      return [value];
    }

    return [value];
  }

  return [];
};

const RoleListPage: React.FC = () => {
  const navigate = useNavigate();
  const { token } = theme.useToken();
  const [expandedDeptRoleIds, setExpandedDeptRoleIds] = useState<number[]>([]);
  const toggleDeptExpanded = (roleId: number) => {
    setExpandedDeptRoleIds((ids) =>
      ids.includes(roleId)
        ? ids.filter((id) => id !== roleId)
        : [...ids, roleId],
    );
  };

  const [searchForm] = Form.useForm();
  const [roleForm] = Form.useForm<RoleFormValues>();
  const needApproval = Form.useWatch('need_approval', roleForm);
  const coverChildDept = Form.useWatch('cover_child_dept', roleForm);
  useEffect(() => {
    if (needApproval === false) {
      roleForm.setFieldsValue({
        approval_order: undefined,
      });
    }
  }, [needApproval, roleForm]);

  const [allList, setAllList] = useState<RoleItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchVersion, setSearchVersion] = useState(0);

  const [modalOpen, setModalOpen] = useState(false);
  const [modalType, setModalType] = useState<'create' | 'edit'>('create');
  const [currentRoleId, setCurrentRoleId] = useState<number | null>(null);
  const [modalLoading, setModalLoading] = useState(false);
  const [submitLoading, setSubmitLoading] = useState(false);

  const [statusUpdatingIds, setStatusUpdatingIds] = useState<number[]>([]);

  const [deptTreeData, setDeptTreeData] = useState<DeptTreeItem[]>([]);
  const [deptLoading, setDeptLoading] = useState(false);

  const [bindPersonOpen, setBindPersonOpen] = useState(false);
  const [bindRole, setBindRole] = useState<RoleItem | null>(null);

  const [personTreeData, setPersonTreeData] = useState<PersonTreeItem[]>([]);
  const [deptTreeExpandedKeys, setDeptTreeExpandedKeys] = useState<React.Key[]>(
    [],
  );
  const personTreeMeta = useMemo(() => {
    const valueAncestorKeyMap = new Map<string, React.Key[]>();

    const nodeMap = new Map<string, PersonTreeItem>();

    const walk = (
      list: PersonTreeItem[] = [],
      ancestorKeys: React.Key[] = [],
    ) => {
      list.forEach((item) => {
        const key = String(item.key || item.value || item.id);

        nodeMap.set(key, item);

        if (item.type === 'person' && item.value) {
          valueAncestorKeyMap.set(String(item.value), ancestorKeys);
        }

        if (item.children?.length) {
          walk(item.children, [...ancestorKeys, key]);
        }
      });
    };

    walk(personTreeData);

    return {
      valueAncestorKeyMap,
      nodeMap,
    };
  }, [personTreeData]);

  const [personTreeLoading, setPersonTreeLoading] = useState(false);

  const [bindPersonLoading, setBindPersonLoading] = useState(false);
  const [selectedPhones, setSelectedPhones] = useState<string[]>([]);

  const selectedPersonAncestorKeys = useMemo(() => {
    const keys = new Set<React.Key>();

    selectedPhones.forEach((phone) => {
      const ancestorKeys =
        personTreeMeta.valueAncestorKeyMap.get(String(phone)) || [];

      ancestorKeys.forEach((key) => {
        keys.add(key);
      });
    });

    return Array.from(keys);
  }, [selectedPhones, personTreeMeta]);

  useEffect(() => {
    if (bindPersonOpen && selectedPersonAncestorKeys.length) {
      setPersonTreeExpandedKeys(selectedPersonAncestorKeys);
    }
  }, [bindPersonOpen, selectedPersonAncestorKeys]);

  const [personKeyword, setPersonKeyword] = useState('');

  const [personTreeExpandedKeys, setPersonTreeExpandedKeys] = useState<
    React.Key[]
  >([]);

  const formatDateTime = (value?: string | number | null) => {
    if (!value) {
      return '-';
    }

    const timestamp = Number(value);

    if (Number.isNaN(timestamp)) {
      return String(value);
    }

    const date = new Date(timestamp);

    const pad = (num: number) => String(num).padStart(2, '0');

    const year = date.getFullYear();
    const month = pad(date.getMonth() + 1);
    const day = pad(date.getDate());
    const hour = pad(date.getHours());
    const minute = pad(date.getMinutes());
    const second = pad(date.getSeconds());

    return `${year}-${month}-${day} ${hour}:${minute}:${second}`;
  };

  const cardStyle: React.CSSProperties = {
    height: 'calc(100vh - 88px)',
    padding: 20,
    borderRadius: 12,
    background: token.colorBgContainer,
    boxSizing: 'border-box',
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
  };

  const authHeaders = {
    Authorization: getAuthorization() || '',
    'Content-Type': 'application/json',
  };

  const fetchList = async () => {
    try {
      setLoading(true);

      const res = await fetch('/v1/role/list', {
        method: 'GET',
        headers: authHeaders,
        credentials: 'include',
      });

      const result = await res.json();

      if (result.code === 0 || result.code === 200) {
        setAllList(result.data || []);
      } else {
        message.error(result.message || '获取角色列表失败');
      }
    } catch (e) {
      console.error(e);
      message.error('请求失败');
    } finally {
      setLoading(false);
    }
  };

  const fetchDeptTree = async () => {
    try {
      setDeptLoading(true);

      const res = await fetch('/v1/dept/tree', {
        method: 'POST',
        headers: authHeaders,
        credentials: 'include',
        body: JSON.stringify({
          keyword: '',
        }),
      });

      const result = await res.json();

      if (result.code === 0 || result.code === 200) {
        setDeptTreeData(result.data || []);
      } else {
        message.error(result.message || '获取部门列表失败');
      }
    } catch (e) {
      console.error(e);
      message.error('获取部门列表请求失败');
    } finally {
      setDeptLoading(false);
    }
  };

  const fetchPersonTree = async (keyword = '') => {
    try {
      setPersonTreeLoading(true);

      const res = await fetch('/v1/deptperson/person-tree', {
        method: 'POST',
        headers: authHeaders,
        credentials: 'include',
        body: JSON.stringify({
          keyword,
        }),
      });

      const result = await res.json();

      if (result.code === 0 || result.code === 200) {
        setPersonTreeData(result.data || []);
      } else {
        message.error(result.message || '获取人员树失败');
      }
    } catch (e) {
      console.error(e);
      message.error('获取人员树请求失败');
    } finally {
      setPersonTreeLoading(false);
    }
  };

  const fetchRoleBoundPersons = async (roleId: number) => {
    try {
      const res = await fetch(`/v1/role/persons/${roleId}`, {
        method: 'GET',
        headers: authHeaders,
        credentials: 'include',
      });

      const result = await res.json();

      if (result.code === 0 || result.code === 200) {
        setSelectedPhones((result.data || []).map(String));
      } else {
        message.error(result.message || '获取已绑定人员失败');
      }
    } catch (e) {
      console.error(e);
      message.error('获取已绑定人员请求失败');
    }
  };

  const openBindPersonModal = async (record: RoleItem) => {
    setBindRole(record);
    setBindPersonOpen(true);
    setSelectedPhones([]);
    setPersonKeyword('');

    await Promise.all([fetchPersonTree(''), fetchRoleBoundPersons(record.id)]);
  };

  const handleSubmitBindPersons = async () => {
    if (!bindRole) {
      return;
    }

    try {
      setBindPersonLoading(true);

      const res = await fetch('/v1/role/bind-persons', {
        method: 'POST',
        headers: authHeaders,
        credentials: 'include',
        body: JSON.stringify({
          role_id: bindRole.id,
          phones: selectedPhones,
        }),
      });

      const result = await res.json();

      if (result.code === 0 || result.code === 200 || result.data === true) {
        message.success('绑定成功');
        setBindPersonOpen(false);
        setBindRole(null);
        setSelectedPhones([]);
      } else {
        message.error(result.message || '绑定失败');
      }
    } catch (e) {
      console.error(e);
      message.error('绑定请求失败');
    } finally {
      setBindPersonLoading(false);
    }
  };

  const handleBindPersonCancel = () => {
    setBindPersonOpen(false);
    setBindRole(null);
    setSelectedPhones([]);
    setPersonKeyword('');
  };

  useEffect(() => {
    fetchList();
    fetchDeptTree();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const displayList = useMemo(() => {
    const values = searchForm.getFieldsValue();

    return allList.filter((item) => {
      if (values.role_name) {
        if (!item.role_name?.includes(values.role_name)) {
          return false;
        }
      }

      if (values.enabled !== undefined && values.enabled !== '') {
        const enabledValue = values.enabled === '1';

        if (item.enabled !== enabledValue) {
          return false;
        }
      }

      return true;
    });
  }, [allList, searchVersion, searchForm]);

  /**
   * TreeSelect 使用 deptTreeData 树形数据。
   * deptMap 只是给表格根据部门 ID 快速显示部门名称用。
   */
  const deptMap = useMemo(() => {
    const map = new Map<string, DeptTreeItem>();

    const walk = (list: DeptTreeItem[]) => {
      list.forEach((item) => {
        if (item.value) {
          map.set(item.value, item);
        }

        if (item.children?.length) {
          walk(item.children);
        }
      });
    };

    walk(deptTreeData);

    return map;
  }, [deptTreeData]);

  const deptTreeMeta = useMemo(() => {
    const valueAncestorKeyMap = new Map<string, React.Key[]>();
    const valueKeyMap = new Map<string, React.Key>();

    const walk = (
      list: DeptTreeItem[] = [],
      ancestorKeys: React.Key[] = [],
    ) => {
      list.forEach((item) => {
        const key = String(item.key || item.value || item.id);
        const value = String(item.value || item.id);

        if (value) {
          valueAncestorKeyMap.set(value, ancestorKeys);
          valueKeyMap.set(value, key);
        }

        if (item.children?.length) {
          walk(item.children, [...ancestorKeys, key]);
        }
      });
    };

    walk(deptTreeData);

    return {
      valueAncestorKeyMap,
      valueKeyMap,
    };
  }, [deptTreeData]);

  const watchedDepartmentIds = Form.useWatch('department_ids', roleForm);

  const normalizeDeptTreeSelectValue = (value: any): string[] => {
    if (!value) {
      return [];
    }

    if (Array.isArray(value)) {
      return value
        .map((item) => {
          if (!item) {
            return '';
          }

          if (typeof item === 'object') {
            return item.value;
          }

          return item;
        })
        .filter(Boolean)
        .map(String);
    }

    if (typeof value === 'object') {
      return value.value ? [String(value.value)] : [];
    }

    return [String(value)];
  };

  const selectedDeptExpandedKeys = useMemo(() => {
    const ids = normalizeDeptTreeSelectValue(watchedDepartmentIds);
    const keys = new Set<React.Key>();

    ids.forEach((id) => {
      const ancestorKeys =
        deptTreeMeta.valueAncestorKeyMap.get(String(id)) || [];

      ancestorKeys.forEach((key) => {
        keys.add(key);
      });

      /**
       * 如果你希望选中的节点本身也展开，把这一段保留。
       * 如果 cover_child_dept = true 后部门很多，觉得展开太多，可以删掉这一段。
       */
      const selfKey = deptTreeMeta.valueKeyMap.get(String(id));
      if (selfKey) {
        keys.add(selfKey);
      }
    });

    return Array.from(keys);
  }, [watchedDepartmentIds, deptTreeMeta]);

  useEffect(() => {
    if (modalOpen && selectedDeptExpandedKeys.length) {
      setDeptTreeExpandedKeys(selectedDeptExpandedKeys);
    }
  }, [modalOpen, selectedDeptExpandedKeys]);

  const getDeptChildrenValues = (
    targetValue: string,
    list: DeptTreeItem[],
  ): string[] => {
    const result: string[] = [];

    const findNode = (nodes: DeptTreeItem[]): DeptTreeItem | null => {
      for (const node of nodes) {
        if (String(node.value) === String(targetValue)) {
          return node;
        }

        if (node.children?.length) {
          const found = findNode(node.children);

          if (found) {
            return found;
          }
        }
      }

      return null;
    };

    const collect = (node?: DeptTreeItem) => {
      if (!node?.children?.length) {
        return;
      }

      node.children.forEach((child) => {
        if (child.value) {
          result.push(String(child.value));
        }

        collect(child);
      });
    };

    const targetNode = findNode(list);

    collect(targetNode || undefined);

    return result;
  };

  const expandDeptIdsWithChildren = (ids: string[]) => {
    const set = new Set<string>();

    ids.forEach((id) => {
      set.add(String(id));

      const childrenValues = getDeptChildrenValues(String(id), deptTreeData);

      childrenValues.forEach((childId) => {
        set.add(String(childId));
      });
    });

    return Array.from(set);
  };

  const openCreateModal = () => {
    setModalType('create');
    setCurrentRoleId(null);

    roleForm.resetFields();
    roleForm.setFieldsValue({
      role_name: '',
      file_permission_level: FILE_PERMISSION_LEVEL.PUBLIC,
      operation_permissions: ['view'],
      need_approval: true,
      approval_order: undefined,
      department_ids: [],
      is_admin: false,
      cover_child_dept: false,
      enabled: true,
    });

    setModalOpen(true);
  };

  const openEditModal = async (record: RoleItem) => {
    setModalType('edit');
    setCurrentRoleId(record.id);
    setModalOpen(true);

    try {
      setModalLoading(true);

      const res = await fetch(`/v1/role/get/${record.id}`, {
        method: 'GET',
        headers: authHeaders,
        credentials: 'include',
      });

      const result = await res.json();

      if (result.code === 0 || result.code === 200) {
        const data = result.data;

        if (!data) {
          message.error('角色不存在');
          setModalOpen(false);
          return;
        }

        const operationPermissions =
          data.operation_permissions ||
          parseOperationMaskToValues(data.operation_permission_mask || 0);

        roleForm.setFieldsValue({
          role_name: data.role_name,
          file_permission_level: data.file_permission_level,
          operation_permissions: operationPermissions,
          need_approval: data.need_approval,
          approval_order: data.approval_order || undefined,
          department_ids: normalizeDepartmentIds(
            data.department_ids || data.department_id,
          ),
          is_admin: data.is_admin,
          cover_child_dept: data.cover_child_dept,
          enabled: data.enabled,
        });
      } else {
        message.error(result.message || '获取角色信息失败');
        setModalOpen(false);
      }
    } catch (e) {
      console.error(e);
      message.error('请求失败');
      setModalOpen(false);
    } finally {
      setModalLoading(false);
    }
  };

  const handleModalCancel = () => {
    setModalOpen(false);
    setCurrentRoleId(null);
    roleForm.resetFields();
  };

  const handleSubmitRole = async () => {
    try {
      const values = await roleForm.validateFields();

      let departmentIds = normalizeDeptTreeSelectValue(values.department_ids);

      if (values.cover_child_dept) {
        departmentIds = expandDeptIdsWithChildren(departmentIds);
      }

      const payload: any = {
        role_name: values.role_name,
        file_permission_level: values.file_permission_level,
        operation_permissions: values.operation_permissions || [],
        need_approval: values.need_approval,
        approval_order: values.need_approval ? values.approval_order : 0,

        department_id: JSON.stringify(departmentIds),

        is_admin: values.is_admin,
        cover_child_dept: values.cover_child_dept,
        enabled: values.enabled,
      };

      let url = '/v1/role/add';

      if (modalType === 'edit') {
        url = '/v1/role/update';
        payload.id = currentRoleId;
      }

      const res = await fetch(url, {
        method: 'POST',
        headers: authHeaders,
        credentials: 'include',
        body: JSON.stringify(payload),
      });

      const result = await res.json();

      if (result.code === 0 || result.code === 200 || result.data === true) {
        message.success(modalType === 'create' ? '新增成功' : '保存成功');
        setModalOpen(false);
        setCurrentRoleId(null);
        roleForm.resetFields();
        fetchList();
      } else {
        message.error(result.message || '操作失败');
      }
    } catch (e: any) {
      if (e?.errorFields) {
        return;
      }

      console.error(e);
      message.error('请求失败');
    } finally {
      setSubmitLoading(false);
    }
  };

  const handleToggleEnabled = async (record: RoleItem, checked: boolean) => {
    try {
      setStatusUpdatingIds((ids) => [...ids, record.id]);

      const departmentIds = normalizeDepartmentIds(
        record.department_ids || record.department_id,
      );

      const payload = {
        id: record.id,
        role_name: record.role_name,
        file_permission_level: record.file_permission_level,
        operation_permissions:
          record.operation_permissions ||
          parseOperationMaskToValues(record.operation_permission_mask || 0),
        need_approval: record.need_approval,
        approval_order: record.approval_order || 0,
        department_id: JSON.stringify(departmentIds),
        is_admin: record.is_admin,
        cover_child_dept: record.cover_child_dept,
        enabled: checked,
      };

      const res = await fetch('/v1/role/update', {
        method: 'POST',
        headers: authHeaders,
        credentials: 'include',
        body: JSON.stringify(payload),
      });

      const result = await res.json();

      if (result.code === 0 || result.code === 200 || result.data === true) {
        message.success(checked ? '已启用' : '已禁用');

        setAllList((list) =>
          list.map((item) =>
            item.id === record.id
              ? {
                  ...item,
                  enabled: checked,
                  department_id: JSON.stringify(departmentIds),
                }
              : item,
          ),
        );
      } else {
        message.error(result.message || '状态更新失败');
      }
    } catch (e) {
      console.error(e);
      message.error('请求失败');
    } finally {
      setStatusUpdatingIds((ids) => ids.filter((id) => id !== record.id));
    }
  };

  const successTagStyle: React.CSSProperties = {
    border: 'none',
    borderRadius: 999,
    background: 'rgba(0, 168, 112, 0.14)',
    color: '#00A870',
    fontWeight: 500,
    padding: '0 10px',
  };

  const defaultTagStyle: React.CSSProperties = {
    border: '1px solid rgba(140, 140, 140, 0.4)',
    borderRadius: 999,
    background: 'rgba(245, 245, 245, 0.14)',
    color: token.colorTextSecondary,
    fontWeight: 500,
    padding: '0 10px',
  };
  const greenButtonStyle: React.CSSProperties = {
    backgroundColor: '#00A870',
    borderColor: '#00A870',
    color: '#fff',
    borderRadius: 6,
  };

  const orderBadgeStyle: React.CSSProperties = {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    minWidth: 24,
    height: 24,
    padding: '0 8px',
    borderRadius: 999,
    background: '#E6F9EF',
    color: '#00A870',
    fontWeight: 600,
    fontSize: 13,
  };

  const greenBoxTagStyle: React.CSSProperties = {
    border: 'none',
    borderRadius: 999,
    background: 'rgba(0, 168, 112, 0.12)',
    color: '#00A870',
    fontWeight: 500,
    padding: '0 10px',
  };

  const deptTagStyle: React.CSSProperties = {
    display: 'inline-flex',
    alignItems: 'center',
    color: token.colorText,
    fontWeight: 400,
    padding: 0,
    maxWidth: 160,
    overflow: 'hidden',
    whiteSpace: 'nowrap',
    background: 'transparent',
    border: 'none',
  };

  const moreTagStyle: React.CSSProperties = {
    border: '1px solid #D9D9D9',
    borderRadius: 4,
    background: '#F5F5F5',
    color: '#595959',
    fontWeight: 400,
    padding: '0 6px',
    height: 22,
    lineHeight: '20px',
  };

  const internalTagStyle: React.CSSProperties = {
    border: '1px solid rgba(0, 168, 160, 0.28)',
    borderRadius: 999,
    background: 'rgba(0, 168, 160, 0.14)',
    color: '#00A8A0',
    fontWeight: 500,
    padding: '0 10px',
  };

  const personNodeMap = useMemo(() => {
    const map = new Map<string, PersonTreeItem>();

    const walk = (list: PersonTreeItem[] = []) => {
      list.forEach((item) => {
        if (item.type === 'person' && item.value) {
          map.set(String(item.value), item);
        }

        if (item.children?.length) {
          walk(item.children);
        }
      });
    };

    walk(personTreeData);

    return map;
  }, [personTreeData]);

  const timeCellStyle: React.CSSProperties = {
    fontSize: 12,
    lineHeight: '20px',
    color: token.colorTextSecondary,
    fontVariantNumeric: 'tabular-nums',
  };
  const columns = [
    {
      title: '序号',
      // width: 60,
      align: 'center' as const,
      render: (_: any, __: RoleItem, index: number) => index + 1,
    },
    {
      title: '角色名称',
      dataIndex: 'role_name',
      // width: 120,
      ellipsis: true,
      align: 'center' as const,
      render: (value: string) => (
        <Tooltip title={value}>
          <span
            style={{
              color: token.colorText,
              fontWeight: 600,
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
              display: 'inline-block',
              maxWidth: '100%',
            }}
          >
            {value || '-'}
          </span>
        </Tooltip>
      ),
    },
    {
      title: '文件权限',
      dataIndex: 'file_permission_level',
      // width: 100,
      align: 'center' as const,
      render: (value: number) => {
        const isPublic = value === FILE_PERMISSION_LEVEL.PUBLIC;

        return isPublic ? (
          <Tag style={greenBoxTagStyle}>
            {FILE_PERMISSION_TEXT[value] || '-'}
          </Tag>
        ) : (
          <Tag style={internalTagStyle}>
            {FILE_PERMISSION_TEXT[value] || '-'}
          </Tag>
        );
      },
    },

    {
      title: '操作权限',
      dataIndex: 'operation_permission_mask',
      // width: 260,
      align: 'center' as const,
      render: (mask: number) => {
        const permissions = parseOperationPermissions(mask || 0);

        if (!permissions.length) {
          return <span style={{ color: token.colorTextTertiary }}>-</span>;
        }

        return (
          <Tooltip title={permissions.join('、')}>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 4,
                overflow: 'hidden',
                whiteSpace: 'nowrap',
                maxWidth: '100%',
              }}
            >
              {permissions.map((item) => (
                <Tag
                  key={item}
                  style={{
                    ...successTagStyle,
                    marginInlineEnd: 0,
                    flexShrink: 0,
                  }}
                >
                  {item}
                </Tag>
              ))}
            </div>
          </Tooltip>
        );
      },
    },
    {
      title: '审批序号',
      dataIndex: 'approval_order',
      // width: 120,
      align: 'center' as const,
      render: (value: number) =>
        value ? (
          <Tag
            style={{
              border: '1px solid rgba(0, 122, 85, 0.28)',
              borderRadius: 4,
              background: 'rgba(0, 122, 85, 0.12)',
              color: '#00A870',
              fontWeight: 500,
              padding: '0 8px',
              height: 22,
              lineHeight: '20px',
            }}
          >
            第 {value} 级
          </Tag>
        ) : (
          <span style={{ color: token.colorTextTertiary }}>-</span>
        ),
    },
    {
      title: '所属部门',
      dataIndex: 'department_id',
      // width: 210,
      render: (_: any, record: RoleItem) => {
        const ids = normalizeDepartmentIds(
          record.department_ids || record.department_id,
        );

        if (!ids.length) {
          return <span style={{ color: token.colorTextTertiary }}>-</span>;
        }

        const deptNames = ids.map((id) => {
          const dept = deptMap.get(id);
          return dept?.title || id;
        });

        const expanded = expandedDeptRoleIds.includes(record.id);

        const defaultShowCount = 2;

        const visibleDeptNames = expanded
          ? deptNames
          : deptNames.slice(0, defaultShowCount);

        const canToggle = deptNames.length > defaultShowCount;

        return (
          <div
            style={{
              position: 'relative',
              maxHeight: expanded ? 120 : 56,
              overflowY: expanded ? 'auto' : 'hidden',
              overflowX: 'hidden',
              paddingRight: canToggle ? 24 : 0,
            }}
          >
            <Tooltip title={deptNames.join('、')}>
              <Space size={[4, 6]} wrap>
                {visibleDeptNames.map((name, index) => (
                  <Tag key={`${name}-${index}`} style={deptTagStyle}>
                    <span
                      style={{
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {name}
                    </span>
                  </Tag>
                ))}
              </Space>
            </Tooltip>

            {canToggle && (
              <span
                onClick={(e) => {
                  e.stopPropagation();
                  toggleDeptExpanded(record.id);
                }}
                style={{
                  position: 'absolute',
                  right: 0,
                  top: '50%',
                  transform: 'translateY(-50%)',
                  width: 22,
                  height: 22,
                  color: token.colorTextSecondary,
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  cursor: 'pointer',
                  zIndex: 2,
                }}
              >
                {expanded ? (
                  <UpOutlined style={{ fontSize: 11 }} />
                ) : (
                  <DownOutlined style={{ fontSize: 11 }} />
                )}
              </span>
            )}
          </div>
        );
      },
    },
    {
      title: '管理员权限',
      dataIndex: 'is_admin',
      // width: 120,
      align: 'center' as const,
      render: (value: boolean) =>
        value ? (
          <Tag style={successTagStyle}>是</Tag>
        ) : (
          <Tag style={defaultTagStyle}>否</Tag>
        ),
    },
    {
      title: '覆盖下级部门',
      dataIndex: 'cover_child_dept',
      // width: 120,
      align: 'center' as const,
      render: (value: boolean) =>
        value ? (
          <Tag style={successTagStyle}>是</Tag>
        ) : (
          <Tag style={defaultTagStyle}>否</Tag>
        ),
    },
    {
      title: '状态',
      dataIndex: 'enabled',
      // width: 110,
      align: 'center' as const,
      render: (enabled: boolean, record: RoleItem) => (
        <Switch
          checked={enabled}
          checkedChildren="启用"
          unCheckedChildren="禁用"
          loading={statusUpdatingIds.includes(record.id)}
          onChange={(checked) => handleToggleEnabled(record, checked)}
          style={
            enabled
              ? {
                  backgroundColor: '#00A870',
                }
              : undefined
          }
        />
      ),
    },
    {
      title: '创建人',
      dataIndex: 'created_by_name',
      // width: 130,
      align: 'center' as const,
      render: (_: string, record: RoleItem) => {
        const name = record.created_by_name || record.created_by || '-';
        const firstChar = name !== '-' ? name.slice(0, 1) : '-';

        return (
          <Tooltip title={name}>
            <div
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 8,
                maxWidth: '100%',
              }}
            >
              <span
                style={{
                  width: 24,
                  height: 24,
                  borderRadius: '50%',
                  background: 'rgba(0, 168, 112, 0.14)',
                  color: '#00A870',
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: 12,
                  fontWeight: 600,
                  flexShrink: 0,
                }}
              >
                {firstChar}
              </span>

              <span
                style={{
                  color: token.colorText,
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}
              >
                {name}
              </span>
            </div>
          </Tooltip>
        );
      },
    },

    {
      title: '创建时间',
      dataIndex: 'created_time',
      // width: 100,
      render: (value: string | number) => (
        <span style={timeCellStyle}>{formatDateTime(value)}</span>
      ),
    },

    {
      title: '更新时间',
      dataIndex: 'updated_time',
      // width: 100,
      render: (value: string | number) => (
        <span style={timeCellStyle}>{formatDateTime(value)}</span>
      ),
    },
    {
      title: '操作',
      // width: 160,
      fixed: 'right' as const,
      align: 'center' as const,
      render: (_: any, record: RoleItem) => (
        <Space size={8}>
          <Button
            size="small"
            onClick={() => openEditModal(record)}
            style={{
              borderColor: '#00A870',
              color: '#00A870',
              borderRadius: 4,
              fontWeight: 500,
            }}
          >
            编辑
          </Button>

          <Button
            size="small"
            onClick={() => openBindPersonModal(record)}
            style={{
              borderColor: '#00A8A0',
              color: '#00A8A0',
              borderRadius: 4,
              fontWeight: 500,
            }}
          >
            绑定
          </Button>
        </Space>
      ),
    },
  ];

  useEffect(() => {
    const currentValue = roleForm.getFieldValue('department_ids');
    const ids = normalizeDeptTreeSelectValue(currentValue);

    if (!ids.length) {
      return;
    }

    if (coverChildDept) {
      roleForm.setFieldsValue({
        department_ids: expandDeptIdsWithChildren(ids),
      });
    } else {
      roleForm.setFieldsValue({
        department_ids: ids,
      });
    }
  }, [coverChildDept, deptTreeData]);

  return (
    <div
      style={{
        height: '100%',
        minHeight: 0,
        overflowY: 'auto',
        overflowX: 'hidden',
        background: token.colorBgContainer,
      }}
    >
      {/* 顶部层级 */}
      {/* <div style={{ marginBottom: 20 }}>
  <div
    className="text-2xl font-semibold flex items-center gap-2.5"
    style={{
      lineHeight: '32px',
    }}
  >
    <span
      onClick={() => navigate('/admin-files')}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 10,
        cursor: 'pointer',
        color: token.colorText,
      }}
    >
      <HomeIcon name="set" width="32" />
      <span>系统设置</span>
    </span>

    <span
      style={{
        color: token.colorTextTertiary,
        fontWeight: 400,
      }}
    >
      /
    </span>

    <span
      style={{
        color: token.colorTextSecondary,
        fontWeight: 500,
      }}
    >
      角色管理
    </span>
  </div>
</div> */}

      <div style={cardStyle}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: 16,
            gap: 16,
            flexShrink: 0,
          }}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              fontSize: 16,
              fontWeight: 700,
              color: token.colorText,
              flexShrink: 0,
            }}
          >
            <span
              style={{
                width: 4,
                height: 16,
                borderRadius: 999,
                background: '#00A870',
                display: 'inline-block',
              }}
            />
            角色管理
          </div>

          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 12,
              marginLeft: 'auto',
            }}
          >
            <Form
              form={searchForm}
              layout="inline"
              style={{
                marginBottom: 0,
              }}
            >
              <Form.Item name="role_name" style={{ marginBottom: 0 }}>
                <Input
                  placeholder="请输入角色名称"
                  allowClear
                  style={{ width: 180 }}
                  onChange={() => setSearchVersion((v) => v + 1)}
                  onPressEnter={() => setSearchVersion((v) => v + 1)}
                />
              </Form.Item>

              <Form.Item name="enabled" style={{ marginBottom: 0 }}>
                <Select
                  style={{ width: 120 }}
                  allowClear
                  placeholder="全部状态"
                  onChange={() => setSearchVersion((v) => v + 1)}
                >
                  <Option value="1">启用</Option>
                  <Option value="0">禁用</Option>
                </Select>
              </Form.Item>
            </Form>

            <Button
              type="primary"
              onClick={openCreateModal}
              style={greenButtonStyle}
            >
              新增角色
            </Button>
          </div>
        </div>

        <div
          style={{
            flex: 1,
            minHeight: 0,
            overflow: 'hidden',
          }}
        >
          <Table
            className="role-table"
            rowKey="id"
            loading={loading}
            columns={columns}
            dataSource={displayList}
            bordered={false}
            scroll={{ x: 'max-content' }}
            pagination={{
              pageSize: 10,
              showSizeChanger: true,
              showTotal: (total) => `共 ${total} 条`,
            }}
          />
        </div>
      </div>

      <Modal
        title={modalType === 'create' ? '新增角色' : '编辑角色'}
        open={modalOpen}
        onCancel={handleModalCancel}
        onOk={handleSubmitRole}
        confirmLoading={submitLoading}
        okText={modalType === 'create' ? '确认新增' : '保存修改'}
        cancelText="取消"
        width={760}
        destroyOnClose
      >
        <Form<RoleFormValues>
          form={roleForm}
          layout="vertical"
          disabled={modalLoading}
          initialValues={{
            file_permission_level: FILE_PERMISSION_LEVEL.PUBLIC,
            operation_permissions: ['view'],
            need_approval: true,
            approval_order: 0,
            department_ids: [],
            is_admin: false,
            cover_child_dept: false,
            enabled: true,
          }}
        >
          <Form.Item
            label="角色名称"
            name="role_name"
            rules={[{ required: true, message: '请输入角色名称' }]}
          >
            <Input placeholder="请输入角色名称" />
          </Form.Item>

          <Form.Item
            label="文件权限"
            name="file_permission_level"
            rules={[{ required: true, message: '请选择文件权限' }]}
          >
            <Radio.Group>
              <Radio value={FILE_PERMISSION_LEVEL.PUBLIC}>公开</Radio>
              <Radio value={FILE_PERMISSION_LEVEL.INTERNAL}>内部</Radio>
            </Radio.Group>
          </Form.Item>

          <Form.Item
            label="操作权限"
            name="operation_permissions"
            rules={[{ required: true, message: '请选择至少一个操作权限' }]}
          >
            <Checkbox.Group options={operationOptions} />
          </Form.Item>

          <Form.Item
            label="是否审批"
            name="need_approval"
            valuePropName="checked"
          >
            <Switch checkedChildren="是" unCheckedChildren="否" />
          </Form.Item>

          <Form.Item
            label="审批序号"
            name="approval_order"
            dependencies={['need_approval']}
            rules={[
              ({ getFieldValue }) => ({
                validator(_, value) {
                  const approval = getFieldValue('need_approval');

                  if (approval && !value) {
                    return Promise.reject(new Error('审批时请选择审批序号'));
                  }

                  return Promise.resolve();
                },
              }),
            ]}
          >
            <Select
              allowClear
              disabled={!needApproval}
              placeholder={needApproval ? '请选择审批序号' : '不审批时无需选择'}
              style={{ width: '100%' }}
            >
              <Option value={1}>1</Option>
              <Option value={2}>2</Option>
            </Select>
          </Form.Item>

          <Form.Item label="管理员权限" name="is_admin" valuePropName="checked">
            <Switch checkedChildren="是" unCheckedChildren="否" />
          </Form.Item>

          <Form.Item
            label="覆盖下级部门"
            name="cover_child_dept"
            valuePropName="checked"
          >
            <Switch checkedChildren="是" unCheckedChildren="否" />
          </Form.Item>
          <Form.Item name="department_ids" hidden>
            <Input />
          </Form.Item>

          <Form.Item shouldUpdate noStyle>
            {() => {
              const rawDepartmentIds = roleForm.getFieldValue('department_ids');
              const departmentIds =
                normalizeDeptTreeSelectValue(rawDepartmentIds);

              const treeValue = coverChildDept
                ? departmentIds
                : departmentIds.map((id) => ({
                    value: id,
                    label: deptMap.get(id)?.title || id,
                  }));

              return (
                <Form.Item label="所属部门">
                  <TreeSelect
                    treeCheckable
                    allowClear
                    showSearch
                    loading={deptLoading}
                    placeholder={
                      coverChildDept
                        ? '请选择部门，选择父级会包含下级部门'
                        : '请选择部门，只选择当前部门'
                    }
                    treeData={deptTreeData}
                    treeNodeFilterProp="title"
                    treeDefaultExpandAll={false}
                    treeCheckStrictly={!coverChildDept}
                    showCheckedStrategy={TreeSelect.SHOW_ALL}
                    maxTagCount="responsive"
                    listHeight={360}
                    style={{ width: '100%' }}
                    value={treeValue}
                    treeExpandedKeys={deptTreeExpandedKeys}
                    onTreeExpand={(keys) => {
                      setDeptTreeExpandedKeys(keys as React.Key[]);
                    }}
                    onDropdownVisibleChange={(open) => {
                      if (open) {
                        setDeptTreeExpandedKeys(selectedDeptExpandedKeys);
                      }
                    }}
                    onChange={(value) => {
                      let ids = normalizeDeptTreeSelectValue(value);

                      if (coverChildDept) {
                        ids = expandDeptIdsWithChildren(ids);
                      }

                      roleForm.setFieldsValue({
                        department_ids: ids,
                      });
                    }}
                  />
                </Form.Item>
              );
            }}
          </Form.Item>

          <Form.Item label="是否启用" name="enabled" valuePropName="checked">
            <Switch checkedChildren="启用" unCheckedChildren="禁用" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={bindRole ? `绑定人员 - ${bindRole.role_name}` : '绑定人员'}
        open={bindPersonOpen}
        onCancel={handleBindPersonCancel}
        onOk={handleSubmitBindPersons}
        confirmLoading={bindPersonLoading}
        okText="保存绑定"
        cancelText="取消"
        width={900}
        destroyOnClose
        okButtonProps={{
          style: {
            backgroundColor: '#00A870',
            borderColor: '#00A870',
            color: '#fff',
          },
        }}
      >
        <div style={{ marginBottom: 16 }}>
          <Input.Search
            allowClear
            placeholder="请输入姓名、手机号、邮箱、部门搜索"
            value={personKeyword}
            onChange={(e) => setPersonKeyword(e.target.value)}
            onSearch={(value) => fetchPersonTree(value)}
            enterButton="搜索"
            loading={personTreeLoading}
          />
        </div>

        <div
          style={{
            marginBottom: 12,
          }}
        >
          <div
            style={{
              marginBottom: 8,
              color: token.colorTextSecondary,
              fontSize: 13,
            }}
          >
            已绑定/已选择 {selectedPhones.length} 个人员
          </div>

          <div
            style={{
              minHeight: 40,
              maxHeight: 120,
              overflowY: 'auto',
              padding: 10,
              borderRadius: 8,
              border: `1px solid ${token.colorBorderSecondary}`,
              background: token.colorFillQuaternary,
            }}
          >
            {selectedPhones.length ? (
              <Space size={[0, 8]} wrap>
                {selectedPhones.map((phone) => {
                  const person = personNodeMap.get(String(phone));
                  const label = person?.title || phone;

                  return (
                    <Tag
                      key={phone}
                      closable
                      onClose={(e) => {
                        e.preventDefault();

                        setSelectedPhones((list) =>
                          list.filter((item) => item !== phone),
                        );
                      }}
                      style={{
                        border: 'none',
                        borderRadius: 999,
                        background: '#E6F9EF',
                        color: '#00A870',
                        fontWeight: 500,
                        padding: '2px 8px',
                      }}
                    >
                      {label}
                    </Tag>
                  );
                })}
              </Space>
            ) : (
              <span
                style={{
                  color: token.colorTextTertiary,
                  fontSize: 13,
                }}
              >
                暂未选择人员
              </span>
            )}
          </div>
        </div>

        <TreeSelect
          className="bind-person-tree-select"
          treeCheckable
          showSearch={false}
          allowClear={false}
          loading={personTreeLoading}
          placeholder="请选择绑定人员"
          treeData={personTreeData}
          showCheckedStrategy={TreeSelect.SHOW_CHILD}
          maxTagCount={0}
          maxTagPlaceholder={() => null}
          value={selectedPhones}
          treeExpandedKeys={personTreeExpandedKeys}
          onTreeExpand={(keys) => {
            setPersonTreeExpandedKeys(keys as React.Key[]);
          }}
          onDropdownVisibleChange={(open) => {
            if (open) {
              setPersonTreeExpandedKeys(selectedPersonAncestorKeys);
            }
          }}
          onInputKeyDown={(e) => {
            if (e.key === 'Backspace' || e.key === 'Delete') {
              e.preventDefault();
              e.stopPropagation();
            }
          }}
          onChange={(values) => {
            setSelectedPhones((values || []).map(String));
          }}
          style={{ width: '100%' }}
          listHeight={500}
        />
      </Modal>
    </div>
  );
};

export default RoleListPage;
