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
import groupService from '@/services/group-service';
import { Plus, Trash2, Users } from 'lucide-react';
import { useEffect, useState } from 'react';

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
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [groups, setGroups] = useState<Group[]>([]);
  const [loading, setLoading] = useState(false);
  const [newGroupName, setNewGroupName] = useState('');
  const [creating, setCreating] = useState(false);

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
    if (!newMemberUserId.trim() || !selectedGroup?.id) return;
    setAddingMember(true);
    try {
      const res = await groupService.addUserToGroup(
        newMemberUserId,
        selectedGroup.id,
      );
      if (res.data?.code === 0) {
        message.success('添加成功');
        setNewMemberUserId('');
        setIsAddMemberModalOpen(false);
        fetchMembers(selectedGroup.id);
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
    if (!selectedGroup?.id) return;
    try {
      const res = await groupService.removeUserFromGroup(
        userId,
        selectedGroup.id,
      );
      if (res.data?.code === 0) {
        message.success('移除成功');
        fetchMembers(selectedGroup.id);
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
    </div>
  );
};

export default AdminFiles;
