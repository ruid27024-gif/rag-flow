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
from api.db.db_models import File, Group, Knowledgebase, AdminUser, UserTenant, UserGroup,Role,RoleUser
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

def get_current_super_admin(user_id):
        if not user_id:
            return False

        admin = AdminUser.query(user_id=user_id, role_level=1)
        return bool(admin)

# 获取当前人员的角色
def get_current_user_role(user_id):
        """
        当前业务：一个用户只绑定一个角色。
        根据 role_user.user_id 查询 Role。
        """
        if not user_id:
            return None

        return (
            Role.select(
                Role.id,
                Role.role_name,
                Role.file_permission_level,
                Role.operation_permission_mask,
                Role.need_approval,
                Role.approval_order,
                Role.department_id,
                Role.is_admin,
                Role.cover_child_dept,
                Role.enabled,
            )
            .join(
                RoleUser,
                on=(RoleUser.role_id == Role.id),
            )
            .where(
                (RoleUser.user_id == str(user_id))
                & (Role.enabled == True)
            )
            .first()
        )

OPERATION_PERMISSION_MAP = {
    "view": 1,
    "upload": 2,
    "download": 4,
    "delete": 8,
    "edit": 16,
}

# 判断用户是否存在操作权限
def user_has_operation_permission(user_id: str, action: str) -> bool:
    """
    判断用户是否拥有某个操作权限。

    action 支持：
      - view
      - upload
      - download
      - delete
      - edit
    """

    if not user_id:
        return False

    if action not in OPERATION_PERMISSION_MAP:
        return False

    # 一级管理员直接拥有全部权限
    if get_current_super_admin(user_id):
        return True

    role = get_current_user_role(user_id)

    if role is None:
        return False

    # 角色管理员拥有全部权限
    if bool(role.is_admin):
        return True

    try:
        operation_permission_mask = int(role.operation_permission_mask or 0)
    except Exception:
        operation_permission_mask = 0

    permission_value = OPERATION_PERMISSION_MAP[action]

    return bool(operation_permission_mask & permission_value)

# 当前用户 user_id
#     -> 获取用户角色
#     -> 获取角色可见部门 ID
#     -> 获取这些部门下的用户 ID
#     -> 判断 kb.tenant_id 是否在这些用户 ID 中
import json
from api.db.db_models import SyncPerson, User
def _parse_department_ids(department_id) -> list[str]:
    """
    将角色中的 department_id 转换为部门 ID 列表。

    支持：
    - "dept-001"
    - "dept-001,dept-002"
    - '["dept-001", "dept-002"]'
    - ["dept-001", "dept-002"]
    """

    if not department_id:
        return []

    if isinstance(department_id, (list, tuple, set)):
        return [str(item) for item in department_id if item]

    value = str(department_id).strip()

    if not value:
        return []

    try:
        parsed = json.loads(value)

        if isinstance(parsed, list):
            return [str(item) for item in parsed if item]

        if parsed:
            return [str(parsed)]
    except (TypeError, ValueError, json.JSONDecodeError):
        pass

    return [
        item.strip()
        for item in value.split(",")
        if item.strip()
    ]


def _get_user_role(user_id: str):
    """
    获取用户当前启用的角色。
    """

    role_user = RoleUser.get_or_none(
        RoleUser.user_id == str(user_id)
    )

    if not role_user:
        return None

    return Role.get_or_none(
        (Role.id == role_user.role_id)
        & (Role.enabled == True)
    )


def _get_role_department_ids(role) -> list[str]:
    """
    获取角色对应的部门 ID。

    当前包含角色直接配置的部门。
    如果需要覆盖子部门，需要在这里补充子部门查询逻辑。
    """

    if not role or not role.enabled:
        return []

    return _parse_department_ids(role.department_id)


def _get_department_user_ids(
    department_ids: list[str],
    current_user_id: str | None = None,
) -> set[str]:
    """
    获取部门下所有系统用户 ID。

    SyncPersonCode
        -> SyncPerson.phone
        -> User.email
        -> User.id
    """

    user_ids = set()

    if current_user_id:
        user_ids.add(str(current_user_id))

    if not department_ids:
        return user_ids

    persons = (
        SyncPerson
        .select(SyncPerson.phone)
        .where(
            (SyncPerson.organizationCode.in_(department_ids))
            & (SyncPerson.phone.is_null(False))
            & (SyncPerson.phone != "")
        )
    )

    phones = {
        str(person.phone).strip()
        for person in persons
        if person.phone
    }

    if not phones:
        return user_ids

    users = (
        User
        .select(User.id)
        .where(
            (User.email.in_(phones))
            & (User.status == "1")
        )
    )

    user_ids.update(str(user.id) for user in users)

    return user_ids

def can_user_access_kb(
    user_id: str,
    kb: dict | Knowledgebase,
) -> bool:
    """
    判断用户是否可以访问指定知识库。

    这里只判断知识库可见范围，不判断：
    - upload
    - download
    - delete
    - edit
    """

    if not user_id or not kb:
        return False

    user_id = str(user_id)

    if isinstance(kb, Knowledgebase):
        kb_tenant_id = getattr(kb, "tenant_id", None)
    else:
        kb_tenant_id = kb.get("tenant_id")

    if not kb_tenant_id:
        return False

    kb_tenant_id = str(kb_tenant_id)

    # 一级管理员可以访问所有知识库
    if AdminUser.query(
        user_id=user_id,
        role_level=1,
    ):
        return True

    # 用户自己的知识库
    if kb_tenant_id == user_id:
        return True

    # 全局参考库
    reference_tenant_id = getattr(
        settings,
        "REFERENCE_TENANT_ID",
        None,
    )

    if (
        reference_tenant_id
        and kb_tenant_id == str(reference_tenant_id)
    ):
        return True

    # 获取用户角色
    role = _get_user_role(user_id)

    # 没有角色或角色未启用时，只能访问自己的库
    if not role:
        return False

    # 获取角色所属部门
    department_ids = _get_role_department_ids(role)

    if not department_ids:
        return False

    # 当前角色部门对应的部门参考库
    department_reference_map = getattr(
        settings,
        "DEPARTMENT_REFERENCE_TENANT_MAP",
        None,
    )

    if department_reference_map is None:
        department_reference_map = getattr(
            settings,
            "GROUP_REFERENCE_TENANT_MAP",
            {},
        ) or {}

    department_reference_tenant_ids = {
        str(tenant_id)
        for department_id, tenant_id in department_reference_map.items()
        if str(department_id) in {str(item) for item in department_ids}
    }

    if kb_tenant_id in department_reference_tenant_ids:
        return True

    # 当前部门下的所有用户
    visible_user_ids = _get_department_user_ids(
        department_ids,
        current_user_id=user_id,
    )

    # 知识库 tenant_id 是知识库所有者的用户 ID
    return kb_tenant_id in visible_user_ids