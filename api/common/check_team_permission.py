#
#  Copyright 2025 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#


from api.db import TenantPermission, UserTenantRole
from api.db.db_models import File, Group, Knowledgebase, AdminUser, UserTenant, UserGroup
from api.db.services.file_service import FileService
from api.db.services.knowledgebase_service import KnowledgebaseService
from api.db.services.kb_access_service import KnowledgebaseAccessService
from api.db.services.user_group_service import UserGroupService
from common import settings

# 可见的权限
def check_kb_team_permission(kb: dict | Knowledgebase, other: str) -> bool:
    if AdminUser.query(user_id=other, role_level=1):
        return True
    
    kb = kb.to_dict() if isinstance(kb, Knowledgebase) else kb
    kb_tenant_id = kb["tenant_id"]

    if settings.REFERENCE_TENANT_ID and kb_tenant_id == settings.REFERENCE_TENANT_ID:
        return True
    is_group_reference = (
        kb_tenant_id in KnowledgebaseService.get_all_group_reference_tenant_ids()
    )
    if is_group_reference:
        if kb_tenant_id == other:
            return True
        group_ids = KnowledgebaseService.get_group_ids_by_reference_tenant_id(kb_tenant_id)
        if not group_ids:
            return False
        return (
            UserGroup.select()
            .where((UserGroup.user_id == other) & (UserGroup.group_id.in_(group_ids)))
            .exists()
            or Group.select()
            .where((Group.created_by == other) & (Group.group_id.in_(group_ids)))
            .exists()
        )

    # Check for level 2 admin
    if AdminUser.query(user_id=other, role_level=2):
        # 1. Find the owner of this tenant
        owner_record = UserTenant.select().where(
            (UserTenant.tenant_id == kb_tenant_id) & 
            (UserTenant.role == UserTenantRole.OWNER)
        ).first()
        
        if owner_record:
            owner_user_id = owner_record.user_id
            
            # 2. Check if current user (other) and owner are in the same group
            my_group = UserGroup.select().where(UserGroup.user_id == other).first()
            owner_group = UserGroup.select().where(UserGroup.user_id == owner_user_id).first()
            
            if my_group and owner_group and my_group.group_id == owner_group.group_id:
                return True

    if kb_tenant_id == other:
        return True

    if kb["permission"] in (TenantPermission.EVERYONE, TenantPermission.EVERYONE_VISIBLE):
        return True

    if kb["permission"] not in (TenantPermission.TEAM, TenantPermission.TEAM_VISIBLE):
        return False

    team_tenant_ids = UserGroupService.get_team_tenant_ids(other)
    return kb_tenant_id in team_tenant_ids


def check_file_team_permission(file: dict | File, other: str) -> bool:
    if AdminUser.query(user_id=other, role_level=1):
        return True
    file = file.to_dict() if isinstance(file, File) else file

    file_tenant_id = file["tenant_id"]
    if file_tenant_id == other:
        return True

    file_id = file["id"]

    kb_ids = [kb_info["kb_id"] for kb_info in FileService.get_kb_id_by_file_id(file_id)]

    for kb_id in kb_ids:
        ok, kb = KnowledgebaseService.get_by_id(kb_id)
        if not ok:
            continue

        if check_kb_team_permission(kb, other):
            return True

    return False


def check_file_team_write_permission(file: dict | File, other: str) -> bool:
    if AdminUser.query(user_id=other, role_level=1):
        return True
    if AdminUser.query(user_id=other, role_level=2):
        return True

    file = file.to_dict() if isinstance(file, File) else file

    file_tenant_id = file["tenant_id"]
    if file_tenant_id == other:
        return True

    file_id = file["id"]

    kb_ids = [kb_info["kb_id"] for kb_info in FileService.get_kb_id_by_file_id(file_id)]
    for kb_id in kb_ids:
        ok, kb = KnowledgebaseService.get_by_id(kb_id)
        if not ok:
            continue
        if check_kb_team_write_permission(kb, other):
            return True

    return False

# 知识库写入权限
def check_kb_team_write_permission(kb: dict | Knowledgebase, other: str) -> bool:


    # 一级管理员
    if AdminUser.query(user_id=other, role_level=1):
        return True
    
    kb = kb.to_dict() if isinstance(kb, Knowledgebase) else kb
    kb_tenant_id = kb["tenant_id"]


    # 全局参考库
    if settings.REFERENCE_TENANT_ID and kb_tenant_id == settings.REFERENCE_TENANT_ID:
        # 先查询一下是否存在

        allow = KnowledgebaseAccessService.has_write_permission(kb['id'], other)

        return allow or (kb_tenant_id == other)
    
    is_group_reference = (
        kb_tenant_id in KnowledgebaseService.get_all_group_reference_tenant_ids()
    )

    # 组参考库
    if is_group_reference:
        # 如果是参考库本身
        if kb_tenant_id == other:
            return True
        
        allow = KnowledgebaseAccessService.has_write_permission(kb['id'], other)
        if allow:
            return True

        # 获取参考库所属的组
        group_ids = KnowledgebaseService.get_group_ids_by_reference_tenant_id(kb_tenant_id)

        if not group_ids:
            return False
        # 如果操作者是该引用群组的创建者，允许写入。
        if Group.select().where((Group.created_by == other) & (Group.group_id.in_(group_ids))).exists():
            return True
        
        # 不是二级管理员不允许
        if not AdminUser.query(user_id=other, role_level=2):
            return False
        
        return (
            UserGroup.select()
            .where((UserGroup.user_id == other) & (UserGroup.group_id.in_(group_ids)))
            .exists()
        )

    # 如果当前用户为二级管理员（允许写入组员的库）
    if AdminUser.query(user_id=other, role_level=2):
        # 获取当前知识库所属的用户信息
        owner_record = UserTenant.select().where(
            (UserTenant.tenant_id == kb_tenant_id)
            & (UserTenant.role == UserTenantRole.OWNER)
        ).first()

        if owner_record:
            # 获取当前用户的id
            owner_user_id = owner_record.user_id
            # 获取二级管理员所在的组
            my_group = UserGroup.select().where(UserGroup.user_id == other).first()
            # 获取知识库所有者所在的组
            owner_group = UserGroup.select().where(UserGroup.user_id == owner_user_id).first()
            # 是同一个组的
            if my_group and owner_group and my_group.group_id == owner_group.group_id:
                return True

    # 如果是自己的库直接返回可以
    if kb_tenant_id == other:
        return True

    # 如果所有人不可见
    if kb["permission"] == TenantPermission.EVERYONE_VISIBLE:
        return False
    # 如果所有人可见
    if kb["permission"] == TenantPermission.EVERYONE:
        return True
    # 如果权限不是全队相关
    if kb["permission"] not in (TenantPermission.TEAM, TenantPermission.TEAM_VISIBLE):
        return False


    team_tenant_ids = UserGroupService.get_team_tenant_ids(other)
    return kb_tenant_id in team_tenant_ids
