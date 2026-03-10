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
import {
  addGroupAdmin,
  listGroupAdminCandidates,
  listGroupAdmins,
  removeGroupAdmin,
} from '@/services/user-service';
import { Plus, Settings, Trash2, Users } from 'lucide-react';
import { useEffect, useState } from 'react';
import { DialogConfigModal } from './DialogConfigModal';

interface Group {
  id: string;
  group_name: string;
  created_by: string;
  created_by_nickname?: string;
  create_time: number;
  member_count?: number;
}

interface GroupMember {
  user_id: string;
  nickname?: string;
  created_by: string;
  created_by_nickname?: string;
  created_time: number;
}

interface CandidateUser {
  user_id: string;
  nickname: string;
}

const AdminFiles = () => {
  const { data: userInfo } = useFetchUserInfo();
  const isGroupAdmin = userInfo?.role_level === 2;
  // const isSuperAdmin = userInfo?.role_level === 1 || userInfo?.is_admin_user;

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isConfigModalOpen, setIsConfigModalOpen] = useState(false);
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [groups, setGroups] = useState<Group[]>([]);
  const [loading, setLoading] = useState(false);
  const [newGroupName, setNewGroupName] = useState('');
  const [creating, setCreating] = useState(false);

  const [isCreateMyGroupModalOpen, setIsCreateMyGroupModalOpen] =
    useState(false);

  const [isMemberModalOpen, setIsMemberModalOpen] = useState(false);
  const [selectedGroup, setSelectedGroup] = useState<Group | null>(null);
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
    { user_id: string; nickname: string }[]
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

  const fetchGroupAdmins = async () => {
    setGroupAdminLoading(true);
    try {
      const { data } = await listGroupAdmins();
      if (data?.code === 0 && Array.isArray(data?.data)) {
        setGroupAdmins(data.data);
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

  useEffect(() => {
    if (isMemberModalOpen && selectedGroup?.id) {
      setMemberCurrentPage(1);
      fetchMembers(selectedGroup.id);
    }
  }, [isMemberModalOpen, selectedGroup?.id]);

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
        res = await groupService.addMemberToMyGroup(newMemberUserId);
      } else {
        res = await groupService.addUserToGroup(
          newMemberUserId,
          selectedGroup!.id,
        );
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

  // 计算当前页的数据
  const indexOfLastItem = currentPage * pageSize;
  const indexOfFirstItem = indexOfLastItem - pageSize;
  const currentItems = groups.slice(indexOfFirstItem, indexOfLastItem);
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

  return (
    <div className="p-8">
      <div className="flex gap-4 mb-8">
        {isGroupAdmin ? (
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
        ) : (
          <>
            {/* 按钮卡片 */}
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
          </>
        )}
      </div>

      {/* 弹窗 */}
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
        footer={null} // 不需要底部按钮
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
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {currentItems.length > 0 ? (
                      currentItems.map((group) => (
                        <TableRow
                          key={group.id}
                          onDoubleClick={() => {
                            setSelectedGroup(group);
                            setIsMemberModalOpen(true);
                          }}
                          className="cursor-pointer"
                        >
                          <TableCell className="whitespace-nowrap">
                            {group.group_name}
                          </TableCell>
                          <TableCell className="whitespace-nowrap">
                            {group.member_count ?? 0}
                          </TableCell>
                          <TableCell className="whitespace-nowrap">
                            {group.created_by_nickname || group.created_by}
                          </TableCell>
                          <TableCell>
                            {group.create_time
                              ? new Date(group.create_time).toLocaleString()
                              : '-'}
                          </TableCell>
                        </TableRow>
                      ))
                    ) : (
                      <TableRow>
                        <TableCell colSpan={4} className="text-center h-24">
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
          <div className="flex justify-between items-center pr-8">
            <span>{selectedGroup?.group_name ?? ''} - 成员管理</span>
            <Button
              size="icon"
              variant="ghost"
              onClick={() => setIsAddMemberModalOpen(true)}
              className="h-8 w-8"
            >
              <Plus className="h-4 w-4" />
            </Button>
          </div>
        }
        open={isMemberModalOpen}
        onOk={() => setIsMemberModalOpen(false)}
        onCancel={() => setIsMemberModalOpen(false)}
        size="large"
        className="w-[1100px] max-w-[calc(100vw-2rem)]"
        footer={null}
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
                      <TableHead className="min-w-[180px]">用户</TableHead>
                      <TableHead className="min-w-[180px]">添加人</TableHead>
                      <TableHead className="min-w-[200px]">添加时间</TableHead>
                      <TableHead className="w-[80px]">操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {memberCurrentItems.length > 0 ? (
                      memberCurrentItems.map((m) => (
                        <TableRow key={`${m.user_id}-${m.created_time}`}>
                          <TableCell className="whitespace-nowrap">
                            {m.nickname || m.user_id}
                          </TableCell>
                          <TableCell className="whitespace-nowrap">
                            {m.created_by_nickname || m.created_by}
                          </TableCell>
                          <TableCell>
                            {m.created_time
                              ? new Date(m.created_time).toLocaleString()
                              : '-'}
                          </TableCell>
                          <TableCell>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8 text-red-500 hover:text-red-700 hover:bg-red-50"
                              onClick={() => handleRemoveMember(m.user_id)}
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))
                    ) : (
                      <TableRow>
                        <TableCell colSpan={4} className="text-center h-24">
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

      {/* 添加成员弹窗 */}
      <Modal
        title="添加成员"
        open={isAddMemberModalOpen}
        onOk={handleAddMember}
        onCancel={() => setIsAddMemberModalOpen(false)}
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
                    <TableHead>用户ID</TableHead>
                    <TableHead className="w-[80px]">操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {groupAdmins.length > 0 ? (
                    groupAdmins.map((admin) => (
                      <TableRow key={admin.user_id}>
                        <TableCell>{admin.nickname}</TableCell>
                        <TableCell>{admin.user_id}</TableCell>
                        <TableCell>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8 text-red-500 hover:text-red-700 hover:bg-red-50"
                            onClick={() =>
                              handleRemoveGroupAdmin(admin.user_id)
                            }
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

      {/* 添加组群管理员弹窗 */}
      <Modal
        title="添加组群管理员"
        open={isAddGroupAdminModalOpen}
        onOk={handleAddGroupAdmin}
        onCancel={() => setIsAddGroupAdminModalOpen(false)}
        confirmLoading={addingGroupAdmin}
      >
        <div className="p-4">
          {adminCandidateLoading ? (
            <div className="text-center py-2 text-sm text-gray-500">
              加载候选用户...
            </div>
          ) : (
            <Select value={newGroupAdminId} onValueChange={setNewGroupAdminId}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="请选择用户" />
              </SelectTrigger>
              <SelectContent>
                {adminCandidates.length > 0 ? (
                  adminCandidates.map((user) => (
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
