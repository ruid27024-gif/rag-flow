import { HomeIcon } from '@/components/svg-icon';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import message from '@/components/ui/message';
import { Modal } from '@/components/ui/modal/modal';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { useFetchUserInfo } from '@/hooks/use-user-setting-request';
import groupService from '@/services/group-service';
import RefKbService from '@/services/refkb-service';
import {
  addGroupAdmin,
  addGroupAdminall,
  delGroupAdminall,
  listGroupAdminCandidates,
  listGroupAdmins,
  removeGroupAdmin,
} from '@/services/user-service';
import { Spin, Transfer } from 'antd';
import {
  Plus,
  RefreshCw,
  Settings,
  ShieldCheck,
  Trash2,
  Users,
} from 'lucide-react'; // 确保引入了 RefreshCw 图标
import {
  useCallback,
  useDeferredValue,
  useEffect,
  useMemo,
  useState,
} from 'react';
import { useTranslation } from 'react-i18next';
import { DialogConfigModal } from './DialogConfigModal';

interface Group {
  id: string;
  group_name: string;
  created_by: string;
  created_by_nickname?: string;
  create_time: number;
  member_count?: number;
}

interface Knowledgebase {
  id: string;
  create_date: string;
  avatar?: string; // null=True，设为可选
  tenant_id: string;
  name: string;
  language?: string; // 有默认值且可为空，设为可选
  description?: string; // null=True，设为可选
  embd_id: string;
  permission: string; // 对应 me|team|everyone
  created_by: string;
  doc_num: number; // 有默认值，但通常前端展示需要，保留为必选
  token_num: number;
  chunk_num: number;
  similarity_threshold: number;
  vector_similarity_weight: number;
  parser_id: string;
  pipeline_id?: string; // null=True，设为可选
  parser_config: {
    pages: number[][];
    table_context_size: number;
    image_context_size: number;
  };
  pagerank: number;
  graphrag_task_id?: string; // null=True，设为可选
  graphrag_task_finish_at?: number; // DateTimeField 通常转为时间戳
  raptor_task_id?: string; // null=True，设为可选
  raptor_task_finish_at?: number;
  mindmap_task_id?: string; // null=True，设为可选
  mindmap_task_finish_at?: number;
  nickname: string;
  email: string;
}

// interface GroupMember {
//   user_id: string;
//   nickname?: string;
//   created_by: string;
//   created_by_nickname?: string;
//   created_time: number;
// }

interface GroupMember {
  // --- 原有基础字段 ---
  user_id: string;
  nickname?: string; // 来自 User 表，LEFT JOIN 可能导致为空

  created_by: string;
  created_by_nickname?: string;
  created_time: number;

  // --- 新增：人员信息 (来自 SyncPerson 表) ---
  phone?: string | null;
  gender?: string | null; // 可能是 '男'/'女' 或者 0/1

  // --- 新增：部门信息 (来自 SyncDept 表) ---
  mdmCode?: string | null; // 部门代码
  nameOfAdminOrg?: string | null; // 部门名称
  corporateName?: string | null; // 公司/企业名称
  is_admin?: boolean; // 是否是管理员
}

export interface CandidateUser {
  user_id: string;
  nickname: string;
  phone: string | null;
  gender: string | null; // 通常是 '男'/'女' 或 0/1
  mdmCode: string | null; // 部门代码
  nameOfAdminOrg: string | null; // 部门名称
  corporateName: string | null; // 公司/企业名称
}

const AdminFiles = () => {
  const { t } = useTranslation();
  const { data: userInfo } = useFetchUserInfo();
  const isGroupAdmin = userInfo?.role_level === 2;
  // const isSuperAdmin = userInfo?.role_level === 1 || userInfo?.is_admin_user;
  const canOperateAdmin = userInfo?.role_level === 1;

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isConfigModalOpen, setIsConfigModalOpen] = useState(false);
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);

  const [isGroupAdminKbOpen, setIsGroupAdminKbOpen] = useState(false);

  const [groups, setGroups] = useState<Group[]>([]);
  const [kbs, setKbs] = useState<Knowledgebase[]>([]);

  const [allMembers, setallMembers] = useState<GroupMember[]>([]);
  const [kbwriteableMembers, setkbwriteableMembers] = useState<GroupMember[]>(
    [],
  );

  const [loading, setLoading] = useState(false);
  const [newGroupName, setNewGroupName] = useState('');
  const [creating, setCreating] = useState(false);

  const [isCreateMyGroupModalOpen, setIsCreateMyGroupModalOpen] =
    useState(false);

  const [isMemberModalOpen, setIsMemberModalOpen] = useState(false);
  const [isKbMemberModalOpen, setIsKbMemberModalOpen] = useState(false);
  const [selectedGroup, setSelectedGroup] = useState<Group | null>(null);
  const [selectedkb, setSelectedkb] = useState<Knowledgebase | null>(null);
  const [members, setMembers] = useState<GroupMember[]>([]);
  const [memberLoading, setMemberLoading] = useState(false);

  // 添加成员相关
  const [isAddMemberModalOpen, setIsAddMemberModalOpen] = useState(false);
  const [newMemberUserId, setNewMemberUserId] = useState('');
  const [addingMember, setAddingMember] = useState(false);
  const [candidates, setCandidates] = useState<CandidateUser[]>([]);
  const [candidateLoading, setCandidateLoading] = useState(false);

  // Group Admin State
  const [isGroupAdminModalOpen, setIsGroupAdminModalOpen] = useState(false);
  const [groupAdmins, setGroupAdmins] = useState<
    {
      user_id: string;
      nickname: string;
      phone: string;
      nameOfAdminOrg: string;
      mdmCode: string;
    }[]
  >([]);
  const [groupAdminLoading, setGroupAdminLoading] = useState(false);
  const [isAddGroupAdminModalOpen, setIsAddGroupAdminModalOpen] =
    useState(false);
  const [newGroupAdminId, setNewGroupAdminId] = useState('');
  const [addingGroupAdmin, setAddingGroupAdmin] = useState(false);
  const [adminCandidates, setAdminCandidates] = useState<CandidateUser[]>([]);
  const [adminCandidateLoading, setAdminCandidateLoading] = useState(false);

  // 分页状态
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 10;

  const [memberCurrentPage, setMemberCurrentPage] = useState(1);

  const memberPageSize = 10;

  const [searchKeyword, setSearchKeyword] = useState('');
  const [searchPhone, setSearchPhone] = useState('');
  const [selectedDept, setSelectedDept] = useState('');

  // 获取组
  const fetchGroups = async () => {
    setLoading(true);
    try {
      const { data } = await groupService.listGroup();
      if (Array.isArray(data?.data)) {
        setGroups(data.data);
      } else {
        setGroups([]);
      }
    } catch (error) {
      console.error('Failed to fetch groups:', error);
      setGroups([]);
    } finally {
      setLoading(false);
    }
  };

  // 获取组 --> 更新kbs
  const fetchRefKb = async (userId: string) => {
    setLoading(true);
    try {
      // 获取到参考库数据
      const { data } = await groupService.listRefKb(userId);
      console.log(data);
      if (Array.isArray(data?.data)) {
        setKbs(data.data);
      } else {
        setKbs([]);
      }
    } catch (error) {
      console.error('Failed to fetch groups:', error);
      setKbs([]);
    } finally {
      setLoading(false);
    }
  };

  // 通过user_id 获取 组内所有成员
  const fetchKbMembersall = async (kbId: string) => {
    setMemberLoading(true);
    try {
      const { data } = await groupService.listAllKbMembers(kbId);
      if (Array.isArray(data?.data)) {
        setallMembers(data.data);
      } else {
        setallMembers([]);
      }
    } catch (error) {
      console.error('Failed to fetch group members:', error);
      setallMembers([]);
    } finally {
      setMemberLoading(false);
    }
  };

  const [writeableIds, setWriteableIds] = useState<Set<string>>(new Set());
  // 通过kb_id 获取所有的可写组员
  const fetchKbMemberswrite = async (kbId: string) => {
    setMemberLoading(true);
    try {
      const { data } = await groupService.listwritableMembers(kbId);
      if (Array.isArray(data?.data)) {
        setkbwriteableMembers(data.data);
        const ids = new Set(data.data.map((m: GroupMember) => m.user_id));
        setWriteableIds(ids);
      } else {
        setkbwriteableMembers([]);
      }
    } catch (error) {
      console.error('Failed to fetch group members:', error);
      setkbwriteableMembers([]);
    } finally {
      setMemberLoading(false);
    }
  };

  // 删除群组的
  const handleDeleteGroup = async (groupId: string) => {
    // 1. 二次确认，防止误操作
    if (!window.confirm('确定要删除这个群组吗？此操作不可恢复。')) {
      return;
    }

    try {
      // 2. 调用删除群组的 API
      // 假设你的 API 函数叫 deleteGroupApi，参数是 groupId
      const res = await groupService.deleteGroup(groupId);

      // 3. 检查响应结果
      if (res.data?.code === 0) {
        message.success('删除成功');

        // 4. 关键步骤：重新获取列表，更新页面状态
        // 这里就是你提到的 fetchGroups (或者叫 fetchGroupList 等)
        fetchGroups();
      } else {
        message.error(res.data?.message || '删除失败');
      }
    } catch (error) {
      console.error('Failed to delete group:', error);
      message.error('删除失败，请检查网络或联系管理员');
    }
  };

  // 删除群组的
  const addmems = async (selectedkb: string, mems: string[]) => {
    try {
      const res = await RefKbService.addmems(selectedkb, mems);

      // 3. 检查响应结果
      if (res.data?.code === 0) {
        message.success('添加权限成功');
      } else {
        message.error(res.data?.message || '添加权限');
      }
    } catch (error) {
      console.error('Failed to add pro:', error);
      message.error('添加权限失败，请检查网络或联系管理员');
    }
  };

  // 删除群组的
  const delmems = async (selectedkb: string, mems: string[]) => {
    try {
      const res = await RefKbService.delmems(selectedkb, mems);

      // 3. 检查响应结果
      if (res.data?.code === 0) {
        message.success('移除权限成功');
      } else {
        message.error(res.data?.message || '移除权限');
      }
    } catch (error) {
      console.error('Failed to delete pro:', error);
      message.error('删除权限失败，请检查网络或联系管理员');
    }
  };

  const handleTransferChange = async (nextTargetKeys: string[]) => {
    // 1. 提取出当前（移动前）右侧拥有权限的 keys
    const currentTargetKeys = transferDataSource
      .filter((item) => item.hasWritePermission)
      .map((item) => item.key);

    // 2. 对比差异，找出被“新增”和“移除”的 ID
    const addedKeys = nextTargetKeys.filter(
      (key) => !currentTargetKeys.includes(key),
    );
    const removedKeys = currentTargetKeys.filter(
      (key) => !nextTargetKeys.includes(key),
    );

    try {
      // 3. 调用后端接口
      const requests: Promise<any>[] = []; // 加上泛型更规范
      if (addedKeys.length > 0) {
        // ✅ 把返回的 Promise 对象推进数组
        console.log(selectedkb.id);
        requests.push(addmems(selectedkb.id, addedKeys));
      }
      if (removedKeys.length > 0) {
        // ✅ 把返回的 Promise 对象推进数组
        requests.push(delmems(selectedkb.id, removedKeys));
      }

      // 等待所有接口请求完成
      await Promise.all(requests);

      // 4. 接口成功后，更新本地数据源，触发界面重新渲染
      const newData = transferDataSource.map((item) => ({
        ...item,
        hasWritePermission: nextTargetKeys.includes(item.key),
      }));
      setTransferDataSource(newData);
    } catch (error) {
      console.error('权限更新失败:', error);
      // 接口失败不更新本地数据，界面自动保持原样（回滚效果）
      // 因为你的 addmems/delmems 里已经有 message.error 提示了，这里可以不再重复弹 alert
    }
  };

  // 获取组员
  const fetchMembers = async (groupId: string) => {
    setMemberLoading(true);
    try {
      const { data } = await groupService.listGroupMembers(groupId);
      if (Array.isArray(data?.data)) {
        setMembers(data.data);
      } else {
        setMembers([]);
      }
    } catch (error) {
      console.error('Failed to fetch group members:', error);
      setMembers([]);
    } finally {
      setMemberLoading(false);
    }
  };

  const fetchCandidates = async () => {
    setCandidateLoading(true);
    try {
      const { data } = await groupService.listCandidateUsers();
      if (Array.isArray(data?.data)) {
        setCandidates(data.data);
      } else {
        setCandidates([]);
      }
    } catch (error) {
      console.error('Failed to fetch candidates:', error);
      setCandidates([]);
    } finally {
      setCandidateLoading(false);
    }
  };

  // 获取组管理员
  const fetchGroupAdmins = async () => {
    setGroupAdminLoading(true);
    try {
      const { data } = await listGroupAdmins();
      if (data?.code === 0 && Array.isArray(data?.data)) {
        setGroupAdmins(data.data);
        console.log(data.data);
      } else {
        setGroupAdmins([]);
      }
    } catch (error) {
      console.error('Failed to fetch group admins:', error);
      setGroupAdmins([]);
    } finally {
      setGroupAdminLoading(false);
    }
  };

  // 获取未在管理员列表中的数据
  const fetchAdminCandidates = async () => {
    setAdminCandidateLoading(true);
    try {
      const { data } = await listGroupAdminCandidates();
      if (data?.code === 0 && Array.isArray(data?.data)) {
        setAdminCandidates(data.data);
      } else {
        setAdminCandidates([]);
      }
    } catch (error) {
      console.error('Failed to fetch admin candidates:', error);
      setAdminCandidates([]);
    } finally {
      setAdminCandidateLoading(false);
    }
  };

  const DEPARTMENT_OPTIONS = [
    { label: '工艺研究一室', value: '工艺研究一室' },
    { label: '工艺研究二室', value: '工艺研究二室' },
    { label: '工艺研究三室', value: '工艺研究三室' },
    { label: '新品事业部研发部', value: '新品事业部研发部' },
  ];

  const filteredCandidates = useMemo(() => {
    // 如果所有筛选条件都为空，直接返回所有候选人
    if (!searchKeyword && !searchPhone && !selectedDept) return candidates;
    // if (!searchKeyword.trim() && !searchPhone.trim() && !selectedDept) return [];

    return candidates.filter((user) => {
      // 1. 匹配昵称或用户ID
      const keyword = searchKeyword.toLowerCase();
      const matchKeyword =
        !searchKeyword ||
        user.nickname?.toLowerCase().includes(keyword) ||
        user.user_id?.toString().includes(keyword);

      // 2. 匹配手机号
      const matchPhone = !searchPhone || user.phone?.includes(searchPhone);

      // 3. 新增：匹配部门（如果没选部门则默认通过，否则必须等于用户的部门）
      const matchDept = !selectedDept || user.nameOfAdminOrg === selectedDept;

      // 三个条件必须同时满足
      return matchKeyword && matchPhone && matchDept;
    });
  }, [candidates, searchKeyword, searchPhone, selectedDept]); // 记得把 selectedDept 加入依赖数组

  // const filteredadminCandidates = useMemo(() => {
  //   // 如果所有筛选条件都为空，直接返回所有候选人
  //   if (!searchKeyword && !searchPhone && !selectedDept) return adminCandidates;

  //   return adminCandidates.filter((user) => {
  //     // 1. 匹配昵称或用户ID
  //     const keyword = searchKeyword.toLowerCase();
  //     const matchKeyword =
  //       !searchKeyword ||
  //       user.nickname?.toLowerCase().includes(keyword) ||
  //       user.user_id?.toString().includes(keyword);

  //     // 2. 匹配手机号
  //     const matchPhone = !searchPhone || user.phone?.includes(searchPhone);

  //     // 3. 新增：匹配部门（如果没选部门则默认通过，否则必须等于用户的部门）
  //     const matchDept = !selectedDept || user.nameOfAdminOrg === selectedDept;

  //     // 三个条件必须同时满足
  //     return matchKeyword && matchPhone && matchDept;
  //   });
  // }, [adminCandidates, searchKeyword, searchPhone, selectedDept]);

  // 2. 核心优化：创建一个延迟更新的值
  // deferredKeyword 会在你停止打字后，或者浏览器空闲时才去更新
  const deferredKeyword = useDeferredValue(searchKeyword);
  const deferredPhone = useDeferredValue(searchPhone);

  // 繁重的过滤计算
  const filteredadminCandidates = useMemo(() => {
    // 这里全部使用延迟的 deferred 值
    if (!deferredKeyword && !deferredPhone && !selectedDept)
      return adminCandidates;

    return adminCandidates.filter((user) => {
      const keyword = deferredKeyword.toLowerCase();
      const matchKeyword =
        !deferredKeyword ||
        user.nickname?.toLowerCase().includes(keyword) ||
        user.user_id?.toString().includes(keyword);

      // 修改点1：这里把 searchPhone 换成 deferredPhone
      const matchPhone = !deferredPhone || user.phone?.includes(deferredPhone);

      const matchDept = !selectedDept || user.nameOfAdminOrg === selectedDept;

      return matchKeyword && matchPhone && matchDept;
    });
    // 修改点2：依赖项数组里也要换成 deferredPhone
  }, [adminCandidates, deferredKeyword, deferredPhone, selectedDept]);

  // 添加组员的
  const handleAddGroupAdmin = async () => {
    if (!newGroupAdminId.trim()) return;
    setAddingGroupAdmin(true);
    try {
      const res = await addGroupAdmin(newGroupAdminId);
      if (res.data?.code === 0) {
        message.success('添加成功');
        setNewGroupAdminId('');
        setIsAddGroupAdminModalOpen(false);
        fetchGroupAdmins();
      } else {
        message.error(res.data?.message || '添加失败');
      }
    } catch (error) {
      console.error('Failed to add group admin:', error);
      message.error('添加失败，请检查权限或网络');
    } finally {
      setAddingGroupAdmin(false);
    }
  };

  const resetAddGroupAdminForm = () => {
    setSearchKeyword('');
    setSearchPhone('');
    setSelectedDept('');
    setNewGroupAdminId('');
  };

  const handleAddGroupAdminOk = async () => {
    await handleAddGroupAdmin();
    resetAddGroupAdminForm();
  };

  const handleAddGroupAdminCancel = () => {
    resetAddGroupAdminForm();
    setIsAddGroupAdminModalOpen(false);
  };

  // 删除组管理员的
  const handleRemoveGroupAdmin = async (userId: string) => {
    try {
      const res = await removeGroupAdmin(userId);
      if (res.data?.code === 0) {
        message.success('移除成功');
        fetchGroupAdmins();
      } else {
        message.error(res.data?.message || '移除失败');
      }
    } catch (error) {
      console.error('Failed to remove group admin:', error);
      message.error('移除失败，请检查权限或网络');
    }
  };

  // 获取组群信息
  const handleMyGroupClick = async () => {
    try {
      const { data } = await groupService.getMyGroup();
      if (data?.data) {
        setSelectedGroup(data.data);
        setIsMemberModalOpen(true);
      } else {
        setIsCreateMyGroupModalOpen(true);
      }
    } catch (error) {
      console.error('Failed to fetch my group:', error);
      message.error('获取组群信息失败');
    }
  };

  // 创建组
  const handleCreateMyGroup = async () => {
    if (!newGroupName.trim()) return;
    setCreating(true);
    try {
      const res = await groupService.createMyGroup(newGroupName);
      if (res.data?.code === 0) {
        message.success('创建成功');
        setNewGroupName('');
        setIsCreateMyGroupModalOpen(false);
        handleMyGroupClick();
      } else {
        message.error(res.data?.message || '创建失败');
      }
    } catch (error) {
      console.error('Failed to create group:', error);
      message.error('创建失败，请检查网络');
    } finally {
      setCreating(false);
    }
  };

  useEffect(() => {
    if (isModalOpen) {
      setCurrentPage(1);
      fetchGroups();
    }
  }, [isModalOpen]);

  // 拉取参考库数据
  useEffect(() => {
    if (isGroupAdminKbOpen) {
      // 获取当前组管理员 的组参考库

      setCurrentPage(1);
      fetchRefKb(userInfo?.id);
    }
  }, [isGroupAdminKbOpen]);

  useEffect(() => {
    if (isMemberModalOpen && selectedGroup?.id) {
      setMemberCurrentPage(1);
      // 获取组内所有人员
      fetchMembers(selectedGroup.id);
    }
  }, [isMemberModalOpen, selectedGroup?.id]);

  // 穿梭框专用的数据类型（必须包含 key 和 hasWritePermission）
  interface TransferMember extends GroupMember {
    key: string;
    hasWritePermission: boolean;
  }

  const [transferDataSource, setTransferDataSource] = useState<
    TransferMember[]
  >([]);

  // 1. 定义获取数据的函数
  const loadData = useCallback(() => {
    if (!selectedkb?.id) return;

    setMemberCurrentPage(1);
    // 注意：这里需要确保你的 fetch 函数能正确更新状态
    fetchKbMembersall(selectedkb.id);
    fetchKbMemberswrite(selectedkb.id);
  }, [selectedkb?.id]); // 依赖项只包含 id，保证 id 变了函数就更新

  // 2. 监听 id 变化（切换知识库时触发）
  useEffect(() => {
    loadData();
  }, [loadData]);

  // // 3. 监听 Modal 打开（每次打开都触发，确保数据最新）
  // useEffect(() => {
  //   if (isKbMemberModalOpen) {
  //     loadData();
  //   }
  // }, [isKbMemberModalOpen, loadData]);

  // 2. 负责“分离与合并数据”的 useEffect
  // 当 allMembers 或 writeableIds 更新后，自动执行合并逻辑
  useEffect(() => {
    if (allMembers.length > 0) {
      const formattedData = allMembers.map((member) => ({
        ...member,
        key: member.user_id, // Transfer 组件强制要求的 key
        hasWritePermission: writeableIds.has(member.user_id), // 判断当前成员是否在“可写名单”里
      }));
      setTransferDataSource(formattedData);
    }
  }, [allMembers, writeableIds]);

  useEffect(() => {
    if (isAddMemberModalOpen) {
      setNewMemberUserId('');
      fetchCandidates();
    }
  }, [isAddMemberModalOpen]);

  useEffect(() => {
    if (isGroupAdminModalOpen) {
      fetchGroupAdmins();
    }
  }, [isGroupAdminModalOpen]);

  useEffect(() => {
    if (isAddGroupAdminModalOpen) {
      setNewGroupAdminId('');
      fetchAdminCandidates();
    }
  }, [isAddGroupAdminModalOpen]);

  const handleAddGroup = async () => {
    if (!newGroupName.trim()) return;
    setCreating(true);
    try {
      await groupService.newGroup(newGroupName);
      setNewGroupName('');
      setIsAddModalOpen(false);
      fetchGroups();
    } catch (error) {
      console.error('Failed to create group:', error);
    } finally {
      setCreating(false);
    }
  };

  const handleAddMember = async () => {
    if (!newMemberUserId.trim() || (!selectedGroup?.id && !isGroupAdmin))
      return;
    setAddingMember(true);
    try {
      let res;
      if (isGroupAdmin) {
        // 添加所有成员
        res = await groupService.addMemberToMyGroup(newMemberUserId);
      } else {
        // 添加所有成员
        res = await groupService.addUserToGroup(
          newMemberUserId,
          selectedGroup!.id,
        );
      }

      if (res.data?.code === 0) {
        message.success('添加成功');
        if (selectedGroup?.id) {
          fetchMembers(selectedGroup.id);
        }
      } else {
        message.error(res.data?.message || '添加失败');
      }
    } catch (error) {
      console.error('Failed to add member:', error);
      message.error('添加失败，请检查权限或网络');
    } finally {
      setAddingMember(false);
    }
  };

  const handleAddallMember = async () => {
    if (!selectedGroup?.id && !isGroupAdmin) return;
    setAddingMember(true);
    try {
      let res;
      if (isGroupAdmin) {
        res = await groupService.addallMemberToMyGroup(selectedGroup!.id);
      } else {
        res = await groupService.addallUserToGroup(selectedGroup!.id);
      }

      if (res.data?.code === 0) {
        message.success('添加成功');
        setNewMemberUserId('');
        setIsAddMemberModalOpen(false);
        if (selectedGroup?.id) {
          fetchMembers(selectedGroup.id);
        }
      } else {
        message.error(res.data?.message || '添加失败');
      }
    } catch (error) {
      console.error('Failed to add member:', error);
      message.error('添加失败，请检查权限或网络');
    } finally {
      setAddingMember(false);
    }
  };

  const handleRemoveMember = async (userId: string) => {
    if (!selectedGroup?.id && !isGroupAdmin) return;
    try {
      let res;
      if (isGroupAdmin) {
        res = await groupService.removeMemberFromMyGroup(userId);
      } else {
        res = await groupService.removeUserFromGroup(userId, selectedGroup!.id);
      }

      if (res.data?.code === 0) {
        message.success('移除成功');
        if (selectedGroup?.id) {
          fetchMembers(selectedGroup.id);
        }
      } else {
        message.error(res.data?.message || '移除失败');
      }
    } catch (error) {
      console.error('Failed to remove member:', error);
      message.error('移除失败，请检查权限或网络');
    }
  };

  // 任命为管理员
  const handleSetAdmin = async (userId: string) => {
    if (!selectedGroup?.id && !isGroupAdmin) return;
    try {
      let res;

      res = await addGroupAdminall(userId, selectedGroup!.id);

      if (res.data?.code === 0) {
        message.success('任命成功');
        if (selectedGroup?.id) {
          fetchMembers(selectedGroup.id);
        }
      } else {
        message.error(res.data?.message || '任命失败');
      }
    } catch (error) {
      console.error('Failed to remove member:', error);
      message.error('移除失败，请检查权限或网络');
    }
  };

  // 取消任命
  const handleCancelAdmin = async (userId: string) => {
    if (!selectedGroup?.id && !isGroupAdmin) return;
    try {
      let res;
      res = await delGroupAdminall(userId, selectedGroup!.id);

      if (res.data?.code === 0) {
        message.success('移除成功');
        if (selectedGroup?.id) {
          fetchMembers(selectedGroup.id);
        }
      } else {
        message.error(res.data?.message || '移除失败');
      }
    } catch (error) {
      console.error('Failed to remove member:', error);
      message.error('移除失败，请检查权限或网络');
    }
  };

  // 计算当前页的数据
  const indexOfLastItem = currentPage * pageSize;
  const indexOfFirstItem = indexOfLastItem - pageSize;
  const currentItems = groups.slice(indexOfFirstItem, indexOfLastItem);

  // 当前的kbs参考库
  const currentItems2 = kbs.slice(indexOfFirstItem, indexOfLastItem);
  const totalPages2 = Math.ceil(kbs.length / pageSize);

  const totalPages = Math.ceil(groups.length / pageSize);

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
  };

  const handleMemberPageChange = (page: number) => {
    setMemberCurrentPage(page);
  };

  const memberIndexOfLastItem = memberCurrentPage * memberPageSize;
  const memberIndexOfFirstItem = memberIndexOfLastItem - memberPageSize;
  const memberCurrentItems = members.slice(
    memberIndexOfFirstItem,
    memberIndexOfLastItem,
  );
  const memberTotalPages = Math.ceil(members.length / memberPageSize);

  function convertTimeFormat(timeStr: string): string {
    const date = new Date(timeStr);

    // 使用 UTC 系列的方法，强制提取原字符串中的时间，不进行本地时区转换
    const year = date.getUTCFullYear();
    const month = String(date.getUTCMonth() + 1).padStart(2, '0');
    const day = String(date.getUTCDate()).padStart(2, '0');
    const hours = String(date.getUTCHours()).padStart(2, '0');
    const minutes = String(date.getUTCMinutes()).padStart(2, '0');
    const seconds = String(date.getUTCSeconds()).padStart(2, '0');

    return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
  }

  return (
    <div className="p-8">
      <div>
        {/* 图标和标题的简单组合 */}
        <div className="text-2xl font-semibold flex items-center gap-2.5">
          {/* 1. 图标 */}
          <HomeIcon name="set" width={'32'} />
          {/* 2. 名称 */}
          <span>{'系统设置'}</span>
        </div>
      </div>

      <div className="flex gap-4 mb-8 mt-5">
        {isGroupAdmin ? (
          <>
            <Card
              className="w-[264px] cursor-pointer hover:shadow-lg transition-shadow"
              onClick={handleMyGroupClick}
            >
              <CardContent className="p-4 flex items-center gap-4">
                <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                  <Users className="w-6 h-6 text-blue-600" />
                </div>
                <div>
                  <h3 className="font-medium text-lg">成员管理</h3>
                  <p className="text-sm text-gray-500">管理我的组群成员</p>
                </div>
              </CardContent>
            </Card>

            <Card
              className="w-[264px] cursor-pointer hover:shadow-lg transition-shadow"
              onClick={() => setIsGroupAdminKbOpen(true)}
            >
              <CardContent className="p-4 flex items-center gap-4">
                <div className="w-12 h-12 bg-pink-100 rounded-lg flex items-center justify-center">
                  <Users className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h3 className="font-medium text-lg">参考库权限管理</h3>
                  <p className="text-sm text-gray-500">查看组内参考库</p>
                </div>
              </CardContent>
            </Card>
          </>
        ) : (
          <>
            {/* 按钮卡片 第一张 */}
            <Card
              className="w-[264px] cursor-pointer hover:shadow-lg transition-shadow"
              onClick={() => setIsModalOpen(true)}
            >
              <CardContent className="p-4 flex items-center gap-4">
                <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                  <Users className="w-6 h-6 text-blue-600" />
                </div>
                <div>
                  <h3 className="font-medium text-lg">群组管理</h3>
                  <p className="text-sm text-gray-500">查看所有群组</p>
                </div>
              </CardContent>
            </Card>

            {/* 统一配置管理卡片 */}
            <Card
              className="w-[264px] cursor-pointer hover:shadow-lg transition-shadow"
              onClick={() => setIsConfigModalOpen(true)}
            >
              <CardContent className="p-4 flex items-center gap-4">
                <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
                  <Settings className="w-6 h-6 text-purple-600" />
                </div>
                <div>
                  <h3 className="font-medium text-lg">统一配置管理</h3>
                  <p className="text-sm text-gray-500">管理对话默认配置</p>
                </div>
              </CardContent>
            </Card>

            {/* 组群管理员卡片 */}
            <Card
              className="w-[264px] cursor-pointer hover:shadow-lg transition-shadow"
              onClick={() => setIsGroupAdminModalOpen(true)}
            >
              <CardContent className="p-4 flex items-center gap-4">
                <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                  <Users className="w-6 h-6 text-green-600" />
                </div>
                <div>
                  <h3 className="font-medium text-lg">组群管理员</h3>
                  <p className="text-sm text-gray-500">查看组群管理员</p>
                </div>
              </CardContent>
            </Card>

            {/* 组内参考库权限管理 */}
            <Card
              className="w-[264px] cursor-pointer hover:shadow-lg transition-shadow"
              onClick={() => setIsGroupAdminKbOpen(true)}
            >
              <CardContent className="p-4 flex items-center gap-4">
                <div className="w-12 h-12 bg-teal-100 rounded-lg flex items-center justify-center">
                  <Users className="w-6 h-6 text-teal-600" />
                </div>
                <div>
                  <h3 className="font-medium text-lg">参考库权限管理</h3>
                  <p className="text-sm text-gray-500">查看组内参考库</p>
                </div>
              </CardContent>
            </Card>
          </>
        )}
      </div>

      {/* 点击第一张后触发 isGroupAdminKbOpen*/}
      <Modal
        title={
          <div className="flex justify-between items-center pr-8">
            <span>参考库列表</span>
          </div>
        }
        open={isGroupAdminKbOpen}
        onOk={() => setIsGroupAdminKbOpen(false)}
        onCancel={() => setIsGroupAdminKbOpen(false)}
        size="large"
        className="w-[1100px] max-w-[calc(100vw-2rem)]"
        showfooter={false}
      >
        <div className="p-4">
          {loading ? (
            <div className="text-center py-4">加载中...</div>
          ) : (
            <>
              <div className="rounded-md border mb-4 overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="min-w-[240px]">
                        知识库名称
                      </TableHead>
                      {/* <TableHead className="min-w-[120px]">群组人数</TableHead> */}
                      <TableHead className="min-w-[160px]">创建人</TableHead>
                      <TableHead className="min-w-[200px]">创建时间</TableHead>
                      {/* <TableHead className="w-[80px]">操作</TableHead> */}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {currentItems2.length > 0 ? (
                      currentItems2.map((kb) => (
                        <TableRow
                          key={kb.id}
                          onClick={() => {
                            // 获取数据
                            setSelectedkb(kb);
                            // 进行展示
                            setIsKbMemberModalOpen(true);
                          }}
                          className="cursor-pointer"
                        >
                          <TableCell
                            className="whitespace-nowrap"
                            title="单击查看"
                          >
                            {kb.name}
                          </TableCell>

                          <TableCell
                            className="whitespace-nowrap"
                            title="单击查看"
                          >
                            {kb.nickname}
                          </TableCell>

                          <TableCell
                            className="whitespace-nowrap"
                            title="单击查看"
                          >
                            {convertTimeFormat(kb.create_date)}
                            {/* {kb.create_date} */}
                          </TableCell>
                        </TableRow>
                      ))
                    ) : (
                      <TableRow>
                        <TableCell colSpan={5} className="text-center h-24">
                          暂无数据
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </div>

              {totalPages2 > 1 && (
                <div className="flex justify-center gap-2 mt-4">
                  <button
                    className="px-3 py-1 border rounded disabled:opacity-50"
                    onClick={() => handlePageChange(currentPage - 1)}
                    disabled={currentPage === 1}
                    type="button"
                  >
                    上一页
                  </button>
                  <span className="px-3 py-1 flex items-center">
                    {currentPage} / {totalPages2}
                  </span>
                  <button
                    className="px-3 py-1 border rounded disabled:opacity-50"
                    onClick={() => handlePageChange(currentPage + 1)}
                    disabled={currentPage === totalPages2}
                    type="button"
                  >
                    下一页
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </Modal>
      <Modal
        title="权限管理"
        open={isKbMemberModalOpen}
        onCancel={() => setIsKbMemberModalOpen(false)}
        footer={null}
        showfooter={false}
        size="large"
        style={{ width: '2000px' }}
      >
        <Transfer
          // 1. 数据源：刚才处理好的包含所有成员的数组
          dataSource={transferDataSource}
          // 2. 控制右边显示谁：只有 hasWritePermission 为 true 的才在右边
          // 这里我们过滤出所有有权限的人的 key (也就是 user_id)
          targetKeys={transferDataSource
            .filter((item) => item.hasWritePermission)
            .map((item) => item.key)}
          operations={['添加权限', '移除权限']}
          // 3. 每一行展示的内容：显示你想要的 nickname, phone 等
          render={(item) => (
            <div className="flex justify-between w-full pr-4">
              <span>{item.nickname}</span>
              <span className="text-gray-400 text-sm">
                {item.phone} | {item.gender === '男' ? '♂ 男' : '♀ 女'} |{' '}
                {item.nameOfAdminOrg}
              </span>
            </div>
          )}
          // 4. 列表标题：左边是无权限，右边是有权限
          titles={['无写权限', '有写权限']}
          // 5. 关键：开关变化的逻辑
          onChange={(nextTargetKeys, direction, moveKeys) => {
            handleTransferChange(nextTargetKeys);
          }}
          // 6. 样式优化：让列表高一点，好看一点
          listStyle={{
            width: '48%', // 👈 改为百分比，让左右列表自动平分空间
            height: 500,
          }}
        />
      </Modal>

      {/* 点击第一张后触发 isModalOpen*/}
      <Modal
        title={
          <div className="flex justify-between items-center pr-8">
            <span>群组列表</span>
            <Button
              size="icon"
              variant="ghost"
              onClick={() => setIsAddModalOpen(true)}
              className="h-8 w-8"
            >
              <Plus className="h-4 w-4" />
            </Button>
          </div>
        }
        open={isModalOpen}
        onOk={() => setIsModalOpen(false)}
        onCancel={() => setIsModalOpen(false)}
        size="large"
        className="w-[1100px] max-w-[calc(100vw-2rem)]"
        showfooter={false} // 不需要底部按钮
      >
        <div className="p-4">
          {loading ? (
            <div className="text-center py-4">加载中...</div>
          ) : (
            <>
              <div className="rounded-md border mb-4 overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="min-w-[240px]">群组名称</TableHead>
                      <TableHead className="min-w-[120px]">群组人数</TableHead>
                      <TableHead className="min-w-[160px]">创建人</TableHead>
                      <TableHead className="min-w-[200px]">创建时间</TableHead>
                      <TableHead className="w-[80px]">操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {currentItems.length > 0 ? (
                      currentItems.map((group) => (
                        <TableRow
                          key={group.id}
                          onClick={() => {
                            setSelectedGroup(group);
                            setIsMemberModalOpen(true);
                          }}
                          className="cursor-pointer"
                        >
                          <TableCell
                            className="whitespace-nowrap"
                            title="单击查看"
                          >
                            {group.group_name}
                          </TableCell>
                          <TableCell className="whitespace-nowrap">
                            {group.member_count ?? 0}
                          </TableCell>
                          <TableCell
                            className="whitespace-nowrap"
                            title="单击查看"
                          >
                            {group.created_by_nickname || group.created_by}
                          </TableCell>
                          <TableCell>
                            {group.create_time
                              ? new Date(group.create_time).toLocaleString()
                              : '-'}
                          </TableCell>
                          {/* 新增操作列 */}
                          <TableCell>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8 text-red-500 hover:text-red-700 hover:bg-red-50"
                              onClick={(e) => {
                                // 1. 阻止事件冒泡
                                e.stopPropagation();

                                // 2. 增加二次确认
                                if (
                                  window.confirm(
                                    `确定要删除该组吗？此操作不可撤销！`,
                                  )
                                ) {
                                  handleDeleteGroup(group.id);
                                }
                              }}
                              title="删除组"
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))
                    ) : (
                      <TableRow>
                        <TableCell colSpan={5} className="text-center h-24">
                          暂无数据
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </div>

              {/* 分页控件 */}
              {totalPages > 1 && (
                <div className="flex justify-center gap-2 mt-4">
                  <button
                    className="px-3 py-1 border rounded disabled:opacity-50"
                    onClick={() => handlePageChange(currentPage - 1)}
                    disabled={currentPage === 1}
                    type="button"
                  >
                    上一页
                  </button>
                  <span className="px-3 py-1 flex items-center">
                    {currentPage} / {totalPages}
                  </span>
                  <button
                    className="px-3 py-1 border rounded disabled:opacity-50"
                    onClick={() => handlePageChange(currentPage + 1)}
                    disabled={currentPage === totalPages}
                    type="button"
                  >
                    下一页
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </Modal>

      <Modal
        title={
          <div className="flex justify-between items-center w-full !w-full">
            {/* 左侧标题 */}
            <span className="font-medium mr-6">
              {selectedGroup?.group_name ?? ''} - 成员管理
            </span>
            {/* <div className="flex-grow"></div> */}
            {/* 右侧按钮组（移到 pr-8 外面，紧贴关闭按钮） */}
            <div className="flex items-center gap-2">
              {/* 单个添加成员按钮 */}
              <Button
                size="icon"
                variant="outline"
                onClick={() => setIsAddMemberModalOpen(true)}
                className="h-8 w-8 border-gray-300 hover:bg-blue-50 hover:text-blue-600 hover:border-blue-400"
                title="添加单个成员"
              >
                <Plus className="h-4 w-4" />
              </Button>

              {/* 一键拉取成员按钮 */}
              <Button
                size="icon"
                variant="outline"
                onClick={() => {
                  if (
                    window.confirm(
                      '确定要一键拉取更新所有成员吗？此操作可能需要一些时间。',
                    )
                  ) {
                    handleAddallMember();
                  }
                }}
                disabled={addingMember} // 拉取中禁用
                className="h-8 w-8 border-gray-300 hover:bg-green-50 hover:text-green-600 hover:border-green-400"
                title="一键拉取成员"
              >
                {addingMember ? (
                  <RefreshCw className="h-4 w-4 animate-spin" /> // 加载中旋转
                ) : (
                  <RefreshCw className="h-4 w-4" /> // 正常同步图标
                )}
              </Button>
            </div>
          </div>
        }
        open={isMemberModalOpen}
        onOk={() => setIsMemberModalOpen(false)}
        onCancel={() => setIsMemberModalOpen(false)}
        size="large"
        className="w-[1100px] max-w-[calc(100vw-2rem)]"
        showfooter={false} // 不需要底部按钮
      >
        <div className="p-4">
          {memberLoading ? (
            <div className="text-center py-4">加载中...</div>
          ) : (
            <>
              <div className="rounded-md border mb-4 overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      {/* 1. 表头：新增了一列展示详细用户信息 */}
                      <TableHead className="min-w-[180px]">用户</TableHead>
                      <TableHead className="min-w-[200px]">用户信息</TableHead>
                      <TableHead className="min-w-[100px]">添加人</TableHead>
                      <TableHead className="min-w-[200px]">添加时间</TableHead>
                      <TableHead className="w-[100px]">删除</TableHead>
                      <TableHead className="w-[100px]">管理员</TableHead>
                      {/* <TableHead className="w-[150px]">撤销任命</TableHead> */}
                      {/* <TableHead className="w-[180px]">当前权限</TableHead> */}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {memberCurrentItems.length > 0 ? (
                      memberCurrentItems.map((m) => (
                        <TableRow key={`${m.user_id}-${m.created_time}`}>
                          {/* 2. 用户名列：展示昵称或ID */}
                          <TableCell className="whitespace-nowrap font-medium">
                            {m.nickname || m.user_id}
                          </TableCell>

                          {/* 3. 新增列：展示电话、性别、部门 */}
                          <TableCell className="space-y-1 py-2">
                            {/* 电话 */}
                            <div className="text-sm text-muted-foreground flex items-center gap-1">
                              📞 {m.phone || '-'}
                            </div>

                            {/* 部门与公司 */}
                            <div className="text-sm text-muted-foreground flex items-center gap-1 truncate max-w-[250px]">
                              🏢
                              <span className="truncate">
                                {m.nameOfAdminOrg ||
                                  m.corporateName ||
                                  '未知部门'}
                              </span>
                            </div>

                            {/* 性别 (可选，如果空间不够可以隐藏) */}
                            {m.gender && (
                              <div className="text-xs text-muted-foreground">
                                {m.gender === '1' || m.gender === '男'
                                  ? '♂ 男'
                                  : '♀ 女'}
                              </div>
                            )}
                          </TableCell>

                          {/* 4. 添加人列 */}
                          <TableCell className="whitespace-nowrap">
                            {m.created_by_nickname || m.created_by}
                          </TableCell>

                          {/* 5. 时间列 */}
                          <TableCell>
                            {m.created_time
                              ? new Date(m.created_time).toLocaleString()
                              : '-'}
                          </TableCell>

                          {/* 6. 操作列 */}
                          <TableCell>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8 text-red-500 hover:text-red-700 hover:bg-red-50"
                              onClick={() => {
                                if (
                                  window.confirm(
                                    `确定要移除 ${m.nickname} 吗？`,
                                  )
                                ) {
                                  handleRemoveMember(m.user_id);
                                }
                              }}
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </TableCell>

                          {/* 6. 操作列：合并后的管理员状态按钮 */}
                          <TableCell>
                            {m.is_admin ? (
                              <Button
                                variant="ghost"
                                size="icon"
                                className={`
                                  h-8 w-8 text-green-600 bg-green-50
                                  ${
                                    canOperateAdmin
                                      ? 'hover:bg-green-100 hover:text-green-700 cursor-pointer'
                                      : 'cursor-default hover:bg-green-50 hover:text-green-600'
                                  }
                                `}
                                onClick={() => {
                                  if (!canOperateAdmin) return;

                                  if (
                                    window.confirm(
                                      `确定要撤销 ${m.nickname} 的管理员权限吗？`,
                                    )
                                  ) {
                                    handleCancelAdmin(m.user_id);
                                  }
                                }}
                                title={
                                  canOperateAdmin
                                    ? '点击撤销管理员权限'
                                    : '该用户是管理员'
                                }
                              >
                                <ShieldCheck className="h-4 w-4" />
                              </Button>
                            ) : (
                              <Button
                                variant="ghost"
                                size="icon"
                                className={`
                                  h-8 w-8
                                  ${
                                    canOperateAdmin
                                      ? 'text-gray-400 hover:text-green-600 hover:bg-green-50 cursor-pointer'
                                      : 'text-gray-300 cursor-default hover:bg-transparent'
                                  }
                                `}
                                onClick={() => {
                                  if (!canOperateAdmin) return;

                                  if (
                                    window.confirm(
                                      `确定要将 ${m.nickname} 设置为管理员吗？`,
                                    )
                                  ) {
                                    handleSetAdmin(m.user_id);
                                  }
                                }}
                                title={
                                  canOperateAdmin
                                    ? '点击任命为管理员'
                                    : '只有一级管理员可以操作'
                                }
                              >
                                <ShieldCheck className="h-4 w-4" />
                              </Button>
                            )}
                          </TableCell>
                        </TableRow>
                      ))
                    ) : (
                      <TableRow>
                        <TableCell colSpan={5} className="text-center h-24">
                          暂无数据
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </div>

              {memberTotalPages > 1 && (
                <div className="flex justify-center gap-2 mt-4">
                  <button
                    className="px-3 py-1 border rounded disabled:opacity-50"
                    onClick={() =>
                      handleMemberPageChange(memberCurrentPage - 1)
                    }
                    disabled={memberCurrentPage === 1}
                    type="button"
                  >
                    上一页
                  </button>
                  <span className="px-3 py-1 flex items-center">
                    {memberCurrentPage} / {memberTotalPages}
                  </span>
                  <button
                    className="px-3 py-1 border rounded disabled:opacity-50"
                    onClick={() =>
                      handleMemberPageChange(memberCurrentPage + 1)
                    }
                    disabled={memberCurrentPage === memberTotalPages}
                    type="button"
                  >
                    下一页
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </Modal>

      {/* 新增群组弹窗 */}
      <Modal
        title="新增群组"
        open={isAddModalOpen}
        onOk={handleAddGroup}
        onCancel={() => setIsAddModalOpen(false)}
        confirmLoading={creating}
      >
        <div className="p-4">
          <Input
            placeholder="请输入群组名称"
            value={newGroupName}
            onChange={(e) => setNewGroupName(e.target.value)}
          />
        </div>
      </Modal>

      {/* 添加成员弹窗
      <Modal
        title="添加成员"
        open={isAddMemberModalOpen}
        onOk={handleAddMember}
        onCancel={() => {
        setIsAddMemberModalOpen(false);
        setSearchKeyword(""); // 关闭弹窗时清空搜索词
        }}
        confirmLoading={addingMember}
      >
        <div className="p-4">
          {candidateLoading ? (
            <div className="text-center py-2 text-sm text-gray-500">
              加载候选用户...
            </div>
          ) : (
            
            <Select value={newMemberUserId} onValueChange={setNewMemberUserId}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="请选择用户（未加入任何群组）" />
              </SelectTrigger>
              <SelectContent>
                {candidates.length > 0 ? (
                  candidates.map((user) => (
                    <SelectItem key={user.user_id} value={user.user_id}>
                      {user.nickname}
                    </SelectItem>
                  ))
                ) : (
                  <div className="p-2 text-sm text-center text-gray-500">
                    无可选用户
                  </div>
                )}
              </SelectContent>
            </Select>
          )}
        </div>
      </Modal> */}

      <Modal
        title="添加成员"
        open={isAddMemberModalOpen}
        onOk={handleAddMember}
        onCancel={() => {
          setIsAddMemberModalOpen(false);
          setSearchKeyword(''); // 关闭弹窗时清空搜索词
        }}
        confirmLoading={addingMember}
      >
        <div className="p-4">
          {candidateLoading ? (
            <div className="text-center py-2 text-sm text-gray-500">
              {/* 加载候选用户... */}
              <Spin tip="加载候选用户中..." />
            </div>
          ) : (
            <div className="space-y-4">
              {/* 1. 姓名搜索框 */}
              <div className="flex items-center gap-3">
                {/* 固定宽度的文字标签，保证上下两个输入框左对齐 */}
                <span className="text-sm font-medium text-gray-700 w-16 shrink-0">
                  姓名：
                </span>
                <div className="relative flex-1">
                  <Input
                    type="text"
                    placeholder="搜索昵称或用户ID..."
                    value={searchKeyword}
                    onChange={(e) => setSearchKeyword(e.target.value)}
                    className="w-full"
                  />
                </div>
              </div>
              {/* 2. 手机号搜索框 */}
              <div className="flex items-center gap-3">
                {/* 固定宽度的文字标签，与上面的“姓名：”对齐 */}
                <span className="text-sm font-medium text-gray-700 w-16 shrink-0">
                  手机号：
                </span>
                <div className="relative flex-1">
                  <Input
                    type="tel"
                    inputMode="numeric"
                    placeholder="输入手机号后几位过滤..."
                    value={searchPhone}
                    onChange={(e) => setSearchPhone(e.target.value)}
                    maxLength={11}
                    className="w-full"
                  />
                  {/* 可选：当有输入内容时，显示一个清除按钮 */}
                  {searchPhone && (
                    <span
                      className="absolute right-3 top-2.5 text-gray-400 text-sm cursor-pointer hover:text-gray-600"
                      onClick={() => setSearchPhone('')}
                    >
                      ✕
                    </span>
                  )}
                </div>
              </div>{' '}
              {/* ⬅️ 这里补上了手机号输入框的闭合标签 */}
              <div className="flex items-center gap-3">
                <span className="text-sm font-medium text-gray-700 w-16 shrink-0">
                  部门：
                </span>
                <div className="relative flex-1">
                  <Select value={selectedDept} onValueChange={setSelectedDept}>
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="请选择部门" />
                    </SelectTrigger>
                    <SelectContent>
                      {DEPARTMENT_OPTIONS.map((dept) => (
                        <SelectItem key={dept.value} value={dept.value}>
                          {dept.label}
                        </SelectItem>
                      ))}

                      {/* 下拉框底部的自定义清空按钮 */}
                      <div
                        className="relative flex cursor-pointer select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none hover:bg-accent hover:text-accent-foreground text-red-500 hover:bg-red-50"
                        onClick={() => setSelectedDept('')}
                      >
                        清空选择
                      </div>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              {/* 4. 修改：下拉选择框，数据源改为 filteredCandidates */}
              <Select
                value={newMemberUserId}
                onValueChange={setNewMemberUserId}
              >
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="请选择搜索到的用户" />
                </SelectTrigger>
                <SelectContent>
                  {filteredCandidates.length > 0 ? (
                    filteredCandidates.map((user) => (
                      <SelectItem key={user.user_id} value={user.user_id}>
                        {/* 可以在这里展示更多信息，比如 ID */}
                        <div className="flex justify-between items-center">
                          <span>{user.nickname}</span>
                          <span className="text-xs text-gray-400 ml-2">
                            手机号: {user.phone}
                          </span>
                          <span className="text-xs text-gray-400 ml-2">
                            部门名称: {user.nameOfAdminOrg}
                          </span>
                          <span className="text-xs text-gray-400 ml-2">
                            mdmCode: {user.mdmCode}
                          </span>
                        </div>
                      </SelectItem>
                    ))
                  ) : (
                    <div className="p-2 text-sm text-center text-gray-500">
                      没有找到匹配的用户
                    </div>
                  )}
                </SelectContent>
              </Select>
            </div>
          )}
        </div>
      </Modal>

      {/* 组群管理员弹窗 */}
      <Modal
        title={
          <div className="flex justify-between items-center pr-8">
            <span>组群管理员列表</span>
            <Button
              size="icon"
              variant="ghost"
              onClick={() => setIsAddGroupAdminModalOpen(true)}
              className="h-8 w-8"
            >
              <Plus className="h-4 w-4" />
            </Button>
          </div>
        }
        open={isGroupAdminModalOpen}
        onOk={() => setIsGroupAdminModalOpen(false)}
        onCancel={() => setIsGroupAdminModalOpen(false)}
        footer={null}
        showfooter={false}
      >
        <div className="p-4">
          {groupAdminLoading ? (
            <div className="text-center py-4">加载中...</div>
          ) : (
            <div className="rounded-md border mb-4 overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>昵称</TableHead>
                    <TableHead>手机号</TableHead>
                    <TableHead>组名</TableHead>
                    <TableHead>部门编码</TableHead>
                    <TableHead className="w-[80px]">操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {groupAdmins.length > 0 ? (
                    groupAdmins.map((admin) => (
                      <TableRow key={admin.user_id}>
                        <TableCell>{admin.nickname}</TableCell>
                        <TableCell>{admin.phone}</TableCell>
                        <TableCell>{admin.nameOfAdminOrg}</TableCell>
                        <TableCell>{admin.mdmCode}</TableCell>
                        <TableCell>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8 text-red-500 hover:text-red-700 hover:bg-red-50"
                            onClick={(e) => {
                              // 1. 阻止事件冒泡
                              e.stopPropagation();

                              // 2. 增加二次确认
                              if (window.confirm(`确定要撤销该组管理员吗！`)) {
                                handleRemoveGroupAdmin(admin.user_id);
                              }
                            }}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))
                  ) : (
                    <TableRow>
                      <TableCell colSpan={3} className="text-center h-24">
                        暂无数据
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </div>
          )}
        </div>
      </Modal>

      <Modal
        title="添加组群管理员"
        open={isAddGroupAdminModalOpen}
        onOk={handleAddGroupAdminOk}
        onCancel={handleAddGroupAdminCancel}
        confirmLoading={addingGroupAdmin}
      >
        <div className="p-4">
          {adminCandidateLoading ? (
            <div className="text-center py-2 text-sm text-gray-500">
              <Spin tip="加载候选用户中..." />
            </div>
          ) : (
            <div className="space-y-4">
              {/* 1. 姓名搜索框 */}
              <div className="flex items-center gap-3">
                <span className="text-sm font-medium text-gray-700 w-16 shrink-0">
                  姓名：
                </span>
                <div className="relative flex-1">
                  <Input
                    type="text"
                    placeholder="搜索昵称或用户ID..."
                    value={searchKeyword}
                    onChange={(e) => setSearchKeyword(e.target.value)}
                    className="w-full"
                  />
                </div>
              </div>
              {/* 2. 手机号搜索框 */}
              <div className="flex items-center gap-3">
                <span className="text-sm font-medium text-gray-700 w-16 shrink-0">
                  手机号：
                </span>
                <div className="relative flex-1">
                  <Input
                    type="tel"
                    inputMode="numeric"
                    placeholder="输入手机号后几位过滤..."
                    value={searchPhone}
                    onChange={(e) => setSearchPhone(e.target.value)}
                    maxLength={11}
                    className="w-full"
                  />
                  {searchPhone && (
                    <span
                      className="absolute right-3 top-2.5 text-gray-400 text-sm cursor-pointer hover:text-gray-600"
                      onClick={() => setSearchPhone('')}
                    >
                      ✕
                    </span>
                  )}
                </div>
              </div>{' '}
              {/* ⬅️ 这里修正了手机号区域的闭合 */}
              {/* 3. 部门搜索框 */}
              <div className="flex items-center gap-3">
                <span className="text-sm font-medium text-gray-700 w-16 shrink-0">
                  部门：
                </span>
                <div className="relative flex-1">
                  <Select value={selectedDept} onValueChange={setSelectedDept}>
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="请选择部门" />
                    </SelectTrigger>
                    <SelectContent>
                      {DEPARTMENT_OPTIONS.map((dept) => (
                        <SelectItem key={dept.value} value={dept.value}>
                          {dept.label}
                        </SelectItem>
                      ))}

                      {/* 下拉框底部的自定义清空按钮 */}
                      <div
                        className="relative flex cursor-pointer select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none hover:bg-accent hover:text-accent-foreground text-red-500 hover:bg-red-50"
                        onClick={() => setSelectedDept('')}
                      >
                        清空选择
                      </div>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              {/* 4. 用户选择器（被修正并移出部门框） */}
              <div className="flex flex-col gap-2">
                <span className="text-sm font-medium text-gray-700">
                  选择管理员：
                </span>

                <Select
                  value={newGroupAdminId}
                  onValueChange={setNewGroupAdminId}
                >
                  <SelectTrigger className="w-full h-10">
                    <SelectValue placeholder="请选择用户" />
                  </SelectTrigger>

                  <SelectContent className="max-h-72">
                    {filteredadminCandidates.length > 0 ? (
                      filteredadminCandidates.map((user) => (
                        <SelectItem
                          key={user.user_id}
                          value={user.user_id}
                          className="py-2 cursor-pointer"
                        >
                          <div className="flex items-center gap-3 w-full">
                            <div className="w-9 h-9 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center text-sm font-semibold shrink-0">
                              {user.nickname?.slice(0, 1) || '用'}
                            </div>

                            <div className="flex flex-col min-w-0 flex-1">
                              <div className="flex items-center gap-2">
                                <span className="text-sm font-medium text-gray-800 truncate">
                                  {user.nickname || '未命名用户'}
                                </span>

                                <span className="text-xs text-gray-400">
                                  ID: {user.user_id}
                                </span>
                              </div>

                              <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
                                <span className="truncate">
                                  手机号：{user.phone || '-'}
                                </span>

                                <span className="truncate">
                                  部门：{user.nameOfAdminOrg || '-'}
                                </span>
                              </div>
                            </div>
                          </div>
                        </SelectItem>
                      ))
                    ) : (
                      <div className="p-2 text-sm text-center text-gray-500">
                        没有找到匹配的用户
                      </div>
                    )}
                  </SelectContent>
                </Select>
              </div>{' '}
              {/* ⬅️ 这里补上了 Select 的闭合标签 */}
            </div>
          )}
        </div>
      </Modal>

      <Modal
        title="创建组群"
        open={isCreateMyGroupModalOpen}
        onOk={handleCreateMyGroup}
        onCancel={() => setIsCreateMyGroupModalOpen(false)}
        confirmLoading={creating}
      >
        <div className="p-4">
          <p className="mb-4 text-gray-500">
            您当前未加入任何组群，请创建一个组群以开始管理成员。
          </p>
          <Input
            placeholder="请输入群组名称"
            value={newGroupName}
            onChange={(e) => setNewGroupName(e.target.value)}
          />
        </div>
      </Modal>

      <DialogConfigModal
        open={isConfigModalOpen}
        onCancel={() => setIsConfigModalOpen(false)}
      />
    </div>
  );
};

export default AdminFiles;
