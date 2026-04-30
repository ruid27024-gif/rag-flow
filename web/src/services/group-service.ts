import api from '@/utils/api';
import request from '@/utils/request';

class GroupService {
  listGroup() {
    return request.get(api.list_group);
  }

  listGroupMembers(groupId: string) {
    return request.get(api.list_group_members(groupId));
  }

  deleteGroup(groupId: string) {
    console.log('准备删除:', groupId);
    return request.post(api.delete_group, { data: { group_id: groupId } });
  }

  newGroup(groupName: string) {
    return request.post(api.new_group, { data: { group_name: groupName } });
  }

  addUserToGroup(userId: string, groupId: string) {
    return request.post(api.add_user_to_group, {
      data: { user_id: userId, group_id: groupId },
    });
  }

  removeUserFromGroup(userId: string, groupId: string) {
    return request.post(api.remove_user_from_group, {
      data: { user_id: userId, group_id: groupId },
    });
  }

  listCandidateUsers() {
    return request.get(api.list_candidate_users);
  }

  getMyGroup() {
    return request.get(api.my_group);
  }

  createMyGroup(groupName: string) {
    return request.post(api.create_my_group, {
      data: { group_name: groupName },
    });
  }

  listMyGroupMembers() {
    return request.get(api.my_group_members);
  }

  addMemberToMyGroup(userId: string) {
    return request.post(api.add_member_to_my_group, {
      data: { user_id: userId },
    });
  }

  removeMemberFromMyGroup(userId: string) {
    return request.post(api.remove_member_from_my_group, {
      data: { user_id: userId },
    });
  }
}

export default new GroupService();
