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
from api.db.db_models import File, Knowledgebase, AdminUser, UserTenant, UserGroup
from api.db.services.file_service import FileService
from api.db.services.knowledgebase_service import KnowledgebaseService
from api.db.services.user_group_service import UserGroupService


def check_kb_team_permission(kb: dict | Knowledgebase, other: str) -> bool:
    if AdminUser.query(user_id=other, role_level=1):
        return True
    
    kb = kb.to_dict() if isinstance(kb, Knowledgebase) else kb
    kb_tenant_id = kb["tenant_id"]

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

    if kb["permission"] == TenantPermission.EVERYONE:
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
