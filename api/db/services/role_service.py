from api.db.db_models import DB, Role, RoleUser, SyncPerson
from api.db.services.common_service import CommonService
from common.misc_utils import get_uuid
from common.time_utils import current_timestamp
from api.db.db_models import User
import json



class FilePermissionLevel:
    PUBLIC = 1
    INTERNAL = 2


class OperationPermissionBits:
    VIEW = 1 << 0
    UPLOAD = 1 << 1
    DOWNLOAD = 1 << 2
    DELETE = 1 << 3
    EDIT = 1 << 4


OPERATION_PERMISSION_MAP = {
    "view": OperationPermissionBits.VIEW,
    "upload": OperationPermissionBits.UPLOAD,
    "download": OperationPermissionBits.DOWNLOAD,
    "delete": OperationPermissionBits.DELETE,
    "edit": OperationPermissionBits.EDIT,
}


def validate_file_permission_level(value):
    return value in (
        FilePermissionLevel.PUBLIC,
        FilePermissionLevel.INTERNAL,
    )


def validate_operation_permissions(operation_permissions):
    if not isinstance(operation_permissions, list):
        return False

    for permission in operation_permissions:
        if permission not in OPERATION_PERMISSION_MAP:
            return False

    return True


def build_operation_permission_mask(operation_permissions):
    mask = 0

    for permission in operation_permissions:
        mask |= OPERATION_PERMISSION_MAP[permission]

    return mask


class RoleService(CommonService):
    model = Role

    @classmethod
    @DB.connection_context()
    def save(cls, **kwargs):
        if "created_time" not in kwargs:
            kwargs["created_time"] = current_timestamp()

        if "updated_time" not in kwargs:
            kwargs["updated_time"] = current_timestamp()

        if "enabled" not in kwargs:
            kwargs["enabled"] = True

        obj = cls.model(**kwargs)
        obj.save(force_insert=True)
        return obj

    @classmethod
    @DB.connection_context()
    def get_by_name(cls, role_name):
        return cls.model.select().where(
            cls.model.role_name == role_name
        ).first()

    @classmethod
    @DB.connection_context()
    def get_by_id(cls, role_id):
        return cls.model.select().where(
            cls.model.id == role_id
        ).first()

    @classmethod
    @DB.connection_context()
    def update_by_id(cls, role_id, **kwargs):
        kwargs["updated_time"] = current_timestamp()

        return cls.model.update(**kwargs).where(
            cls.model.id == role_id
        ).execute()

    @classmethod
    @DB.connection_context()
    def list_all(cls):
        return list(
            cls.model
            .select()
            .order_by(cls.model.created_time.desc())
        )

    @classmethod
    def parse_role_department_ids(cls, value):
        """
        兼容 Role.department_id 的多种存储格式：
        1. "dept001"
        2. "dept001,dept002"
        3. '["dept001", "dept002"]'
        """

        if not value:
            return []

        if isinstance(value, list):
            return [str(x) for x in value]

        value = str(value).strip()

        if not value:
            return []

        if value.startswith("[") and value.endswith("]"):
            try:
                arr = json.loads(value)
                if isinstance(arr, list):
                    return [str(x) for x in arr]
            except Exception:
                pass

        if "," in value:
            return [
                item.strip()
                for item in value.split(",")
                if item.strip()
            ]

        return [value]

    @classmethod
    def role_contains_department(cls, role, department_id):
        """
        判断角色是否包含某个部门。
        """

        if not department_id:
            return False

        dept_ids = cls.parse_role_department_ids(role.department_id)

        return str(department_id) in [str(x) for x in dept_ids]

    @classmethod
    def get_approval_roles_by_department(cls, department_id):
        """
        根据部门 ID 获取审批角色。

        条件：
        - enabled = True
        - need_approval = True
        - approval_order in [1, 2]
        - Role.department_id 精确包含 department_id
        """

        if not department_id:
            return []

        roles = list(
            cls.model
            .select()
            .where(
                cls.model.enabled == True,
                cls.model.need_approval == True,
                cls.model.approval_order.in_([1, 2]),
            )
            .order_by(cls.model.approval_order.asc())
        )

        matched_roles = []

        for role in roles:
            if cls.role_contains_department(role, department_id):
                matched_roles.append(role)

        return matched_roles

    @classmethod
    def get_role_users_by_role_ids(cls, role_ids):
        """
        根据角色 ID 查询绑定用户。
        """

        role_ids = list(set([rid for rid in role_ids if rid]))

        if not role_ids:
            return []

        rows = (
            RoleUser
            .select(
                RoleUser.role_id,
                RoleUser.user_id,
            )
            .where(RoleUser.role_id.in_(role_ids))
        )

        return list(rows)

    # 获取所有审批人
    # @classmethod
    # def get_approval_users_by_department(cls, department_id):

        """
        根据部门 ID 获取审批人员，并按审批顺序分组。

        审批角色筛选条件由 get_approval_roles_by_department 处理：
        - Role.department_id 包含当前 department_id
        - Role.need_approval = True
        - Role.enabled = True
        - Role.approval_order in [1, 2]

        人员关联关系：
        RoleUser.user_id -> User.id
        User.email -> SyncPerson.phone

        返回：
        {
            "level_1": [
                {
                    "user_id": "...",
                    "user_name": "...",
                    "email": "...",
                    "avatar": null,
                    "mdm_code": "...",
                    "mdm_name": "...",
                    "department_id": "...",
                    "department_name": "...",
                    "role_id": 1,
                    "role_name": "...",
                    "approval_order": 1
                }
            ],
            "level_2": []
        }
        """

        if not department_id:
            return {
                "level_1": [],
                "level_2": [],
            }

        # 1. 查询当前部门可用的一级、二级审批角色。
        roles = cls.get_approval_roles_by_department(department_id)

        if not roles:
            return {
                "level_1": [],
                "level_2": [],
            }

        role_ids = [role.id for role in roles]

        # 2. 查询角色绑定的用户。
        role_user_rows = list(
            RoleUser
            .select(
                RoleUser.role_id,
                RoleUser.user_id,
            )
            .where(RoleUser.role_id.in_(role_ids))
        )

        if not role_user_rows:
            return {
                "level_1": [],
                "level_2": [],
            }

        role_map = {
            role.id: role
            for role in roles
        }

        user_ids = list({
            row.user_id
            for row in role_user_rows
            if row.user_id
        })

        if not user_ids:
            return {
                "level_1": [],
                "level_2": [],
            }

        # 3. 批量查询系统用户。
        users = (
            User
            .select(
                User.id,
                User.nickname,
                User.email,
                User.avatar,
            )
            .where(User.id.in_(user_ids))
        )

        user_map = {}

        for user in users:
            user_map[user.id] = {
                "id": user.id,
                "nickname": user.nickname,
                "email": user.email,
                "avatar": user.avatar,
            }

        # 4. 用 User.email 对应 SyncPerson.phone，批量查询人员主数据。
        emails = list({
            user["email"]
            for user in user_map.values()
            if user.get("email")
        })

        sync_person_map = {}

        if emails:
            sync_person_rows = (
                SyncPerson
                .select(
                    SyncPerson.phone,
                    SyncPerson.mdmCode,
                    SyncPerson.mdmName,
                    SyncPerson.organizationCode,
                    SyncPerson.organize,
                )
                .where(SyncPerson.phone.in_(emails))
            )

            for person in sync_person_rows:
                # phone 应唯一；若同步数据重复，这里以最后读到的一条为准。
                sync_person_map[person.phone] = {
                    "mdm_code": person.mdmCode,
                    "mdm_name": person.mdmName,
                    "department_id": person.organizationCode,
                    "department_name": person.organize,
                }

        result = {
            "level_1": [],
            "level_2": [],
        }

        added_user_ids = {
            "level_1": set(),
            "level_2": set(),
        }

        # 5. 按角色审批顺序组织返回数据。
        for row in role_user_rows:
            role = role_map.get(row.role_id)

            if not role:
                continue

            if role.approval_order not in [1, 2]:
                continue

            user = user_map.get(row.user_id)
            user_email = user["email"] if user else None
            sync_person = sync_person_map.get(user_email, {})

            item = {
                "user_id": row.user_id,
                "user_name": user["nickname"] if user else row.user_id,
                "email": user_email,
                "avatar": user["avatar"] if user else None,

                # SyncPerson 数据，关联条件为 User.email == SyncPerson.phone。
                "mdm_code": sync_person.get("mdm_code"),
                "mdm_name": sync_person.get("mdm_name"),
                "department_id": sync_person.get("department_id"),
                "department_name": sync_person.get("department_name"),

                "role_id": role.id,
                "role_name": role.role_name,
                "approval_order": role.approval_order,
            }

            if role.approval_order == 1:
                level_key = "level_1"
            else:
                level_key = "level_2"

            if row.user_id in added_user_ids[level_key]:
                continue

            result[level_key].append(item)
            added_user_ids[level_key].add(row.user_id)

        return result

    # 获取所有审批人
    @classmethod
    def get_approval_users_by_department(cls, department_id):
        """
        根据部门 ID 获取审批人员。

        新规则：
        - 不再区分一级、二级审批。
        - 只要角色具备审批权限，就是审批人。

        审批角色筛选条件由 get_approval_roles_by_department 处理：
        - Role.department_id 包含当前 department_id
        - Role.need_approval = True
        - Role.enabled = True

        人员关联关系：
        RoleUser.user_id -> User.id
        User.email -> SyncPerson.phone

        返回：
        {
            "approvers": [
                {
                    "user_id": "...",
                    "user_name": "...",
                    "email": "...",
                    "avatar": null,
                    "mdm_code": "...",
                    "mdm_name": "...",
                    "department_id": "...",
                    "department_name": "...",
                    "role_id": 1,
                    "role_name": "..."
                }
            ]
        }
        """

        if not department_id:
            return {
                "approvers": [],
            }

        # 1. 查询当前部门可用的审批角色。
        roles = cls.get_approval_roles_by_department(department_id)

        if not roles:
            return {
                "approvers": [],
            }

        role_ids = [role.id for role in roles]

        # 2. 查询角色绑定的用户。
        role_user_rows = list(
            RoleUser
            .select(
                RoleUser.role_id,
                RoleUser.user_id,
            )
            .where(RoleUser.role_id.in_(role_ids))
        )

        if not role_user_rows:
            return {
                "approvers": [],
            }

        role_map = {
            role.id: role
            for role in roles
        }

        user_ids = list({
            row.user_id
            for row in role_user_rows
            if row.user_id
        })

        if not user_ids:
            return {
                "approvers": [],
            }

        # 3. 批量查询系统用户。
        users = (
            User
            .select(
                User.id,
                User.nickname,
                User.email,
                User.avatar,
            )
            .where(User.id.in_(user_ids))
        )

        user_map = {}

        for user in users:
            user_map[user.id] = {
                "id": user.id,
                "nickname": user.nickname,
                "email": user.email,
                "avatar": user.avatar,
            }

        # 4. 用 User.email 对应 SyncPerson.phone，批量查询人员主数据。
        emails = list({
            user["email"]
            for user in user_map.values()
            if user.get("email")
        })

        sync_person_map = {}

        if emails:
            sync_person_rows = (
                SyncPerson
                .select(
                    SyncPerson.phone,
                    SyncPerson.mdmCode,
                    SyncPerson.mdmName,
                    SyncPerson.organizationCode,
                    SyncPerson.organize,
                )
                .where(SyncPerson.phone.in_(emails))
            )

            for person in sync_person_rows:
                sync_person_map[person.phone] = {
                    "mdm_code": person.mdmCode,
                    "mdm_name": person.mdmName,
                    "department_id": person.organizationCode,
                    "department_name": person.organize,
                }

        result = {
            "approvers": [],
        }

        added_user_ids = set()

        # 5. 组织审批人列表，不再按 approval_order 分组。
        for row in role_user_rows:
            role = role_map.get(row.role_id)

            if not role:
                continue

            user = user_map.get(row.user_id)
            user_email = user["email"] if user else None
            sync_person = sync_person_map.get(user_email, {})

            # 同一个用户可能绑定多个审批角色，这里只保留一次。
            if row.user_id in added_user_ids:
                continue

            item = {
                "user_id": row.user_id,
                "user_name": user["nickname"] if user else row.user_id,
                "email": user_email,
                "avatar": user["avatar"] if user else None,

                # SyncPerson 数据，关联条件为 User.email == SyncPerson.phone。
                "mdm_code": sync_person.get("mdm_code"),
                "mdm_name": sync_person.get("mdm_name"),
                "department_id": sync_person.get("department_id"),
                "department_name": sync_person.get("department_name"),

                "role_id": role.id,
                "role_name": role.role_name,
            }

            result["approvers"].append(item)
            added_user_ids.add(row.user_id)

        return result