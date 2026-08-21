from api.db.db_models import AdminUser
from api.apps import login_required, current_user
from api.utils.api_utils import get_json_result, server_error_response, validate_request, get_request_json
from common.constants import RetCode
from api.db.services.role_service import RoleService, validate_file_permission_level, validate_operation_permissions, build_operation_permission_mask
from api.db.db_models import User,SyncPerson,OaApplication
import json

import logging

from api.apps import login_required, current_user
from api.db.db_models import User, Role, SyncDept,PermissionApplication,RoleUser
from api.db.services.role_service import RoleService
from api.db.services.roleuser_service import RoleUserService
from api.utils.api_utils import (
    get_json_result,
    server_error_response,
    validate_request,
    get_request_json,
)
import time

def normalize_department_id(req: dict):
    """
    统一把部门字段转成 JSON 字符串存入 department_id
    """

    # 推荐前端以后传 department_ids: []
    department_ids = req.get("department_ids", None)

    if department_ids is not None:
        if isinstance(department_ids, list):
            department_ids = [str(item) for item in department_ids if item]
            return json.dumps(department_ids, ensure_ascii=False)

        if isinstance(department_ids, str):
            # 如果已经是字符串，尝试判断是不是 JSON 数组
            try:
                parsed = json.loads(department_ids)
                if isinstance(parsed, list):
                    parsed = [str(item) for item in parsed if item]
                    return json.dumps(parsed, ensure_ascii=False)
            except Exception:
                pass

            return json.dumps([department_ids], ensure_ascii=False)

    # 兼容旧字段 department_id
    department_id = req.get("department_id", None)

    if department_id is None or department_id == "":
        return None

    if isinstance(department_id, list):
        department_id = [str(item) for item in department_id if item]
        return json.dumps(department_id, ensure_ascii=False)

    if isinstance(department_id, str):
        # 前端传的就是 JSON 字符串：["dept001","dept002"]
        try:
            parsed = json.loads(department_id)
            if isinstance(parsed, list):
                parsed = [str(item) for item in parsed if item]
                return json.dumps(parsed, ensure_ascii=False)
        except Exception:
            pass

        # 兼容以前单部门字符串
        return json.dumps([department_id], ensure_ascii=False)

    return None
def check_admin(user):
    admin_user = AdminUser.query(user_id=user.id, role_level=1)
    if not admin_user:
        return get_json_result(
            data=False, message='Only admin users can perform this action.', code=RetCode.OPERATING_ERROR
        )
    return None

# 新增角色
@manager.route('/add', methods=['POST'])
@login_required
async def add_role():
    try:
        # 1. 判断是否超级管理员
        error_response = check_admin(current_user)
        if error_response:
            return error_response

        # 2. 获取请求参数
        req = await get_request_json()

        role_name = req.get("role_name")
        file_permission_level = req.get("file_permission_level")
        operation_permissions = req.get("operation_permissions", [])

        need_approval = req.get("need_approval", True)
        approval_order = req.get("approval_order", 0)
        department_id = normalize_department_id(req)
        is_admin = req.get("is_admin", False)
        cover_child_dept = req.get("cover_child_dept", False)
        enabled = req.get("enabled", True)

        # 3. 校验角色名称
        if not role_name:
            return get_json_result(
                data=False,
                message="角色名称不能为空",
                code=RetCode.ARGUMENT_ERROR
            )

        # 4. 校验角色名称是否重复
        exists_role = RoleService.get_by_name(role_name)
        if exists_role:
            return get_json_result(
                data=False,
                message="角色名称已存在",
                code=RetCode.OPERATING_ERROR
            )

        # 5. 校验文件权限，必须是 1 或 2
        if file_permission_level is None:
            return get_json_result(
                data=False,
                message="文件权限不能为空",
                code=RetCode.ARGUMENT_ERROR
            )

        if not validate_file_permission_level(file_permission_level):
            return get_json_result(
                data=False,
                message="文件权限只能选择公开或内部",
                code=RetCode.ARGUMENT_ERROR
            )

        # 6. 校验操作权限
        if not validate_operation_permissions(operation_permissions):
            return get_json_result(
                data=False,
                message="操作权限参数错误",
                code=RetCode.ARGUMENT_ERROR
            )

        # 7. 转换操作权限为 bitmask
        operation_permission_mask = build_operation_permission_mask(
            operation_permissions
        )

        # 8. 入库
        role = RoleService.save(
            role_name=role_name,
            file_permission_level=file_permission_level,
            operation_permission_mask=operation_permission_mask,
            need_approval=need_approval,
            approval_order=approval_order,
            department_id=department_id,
            is_admin=is_admin,
            cover_child_dept=cover_child_dept,
            enabled=enabled,
            created_by=current_user.id,
        )

        # 9. 返回结果
        return get_json_result(data={
            "id": role.id,
            "role_name": role.role_name,
            "file_permission_level": role.file_permission_level,
            "operation_permission_mask": role.operation_permission_mask,
            "operation_permissions": operation_permissions,
            "need_approval": role.need_approval,
            "approval_order": role.approval_order,
            "department_id": role.department_id,
            "is_admin": role.is_admin,
            "cover_child_dept": role.cover_child_dept,
            "enabled": role.enabled,
            "created_by": role.created_by,
            "created_time": role.created_time,
        })

    except Exception as e:
        return server_error_response(e)  

@manager.route('/list', methods=['GET'])
@login_required
async def role_list():
    try:
        # 判断是否超级管理员
        # error_response = check_admin(current_user)
        # if error_response:
        #     return error_response

        roles = RoleService.list_all()

        # 收集 created_by 用户ID
        created_by_ids = [
            role.created_by
            for role in roles
            if role.created_by
        ]

        # 批量查询用户，避免循环查数据库
        user_map = {}

        if created_by_ids:
            users = User.select().where(User.id.in_(created_by_ids))

            for user in users:
                user_map[user.id] = (
                    user.nickname
                    or user.email
                    or user.id
                )

        data = []
        for role in roles:
            data.append({
                "id": role.id,
                "role_name": role.role_name,

                # 文件权限：1 公开，2 内部
                "file_permission_level": role.file_permission_level,

                # 操作权限 bitmask
                "operation_permission_mask": role.operation_permission_mask,

                "need_approval": role.need_approval,
                "approval_order": role.approval_order,
                "department_id": role.department_id,
                "is_admin": role.is_admin,
                "cover_child_dept": role.cover_child_dept,
                "enabled": role.enabled,

                # 创建人 ID
                "created_by": role.created_by,

                # 创建人名称
                "created_by_name": user_map.get(
                    role.created_by,
                    role.created_by or "-"
                ),

                "created_time": role.created_time,
                "updated_time": role.updated_time,
            })

        return get_json_result(data=data)

    except Exception as e:
        return server_error_response(e)

@manager.route('/personrole_list', methods=['GET'])
@login_required
async def person_role_list():
    try:
        # 判断是否超级管理员
        # error_response = check_admin(current_user)
        # if error_response:
        #     return error_response

        roles = RoleService.list_all()

        # =========================
        # 批量查询创建人
        # =========================
        created_by_ids = [
            role.created_by
            for role in roles
            if role.created_by
        ]

        user_map = {}

        if created_by_ids:
            users = User.select().where(User.id.in_(created_by_ids))

            for user in users:
                user_map[user.id] = (
                    user.nickname
                    or user.email
                    or user.id
                )

        # =========================
        # 收集所有角色部门 ID
        # =========================
        all_dept_ids = set()

        for role in roles:
            dept_ids = parse_department_ids(role.department_id)
            all_dept_ids.update(dept_ids)

        # =========================
        # 批量查询部门
        # =========================
        dept_map = {}

        if all_dept_ids:
            dept_rows = SyncDept.select().where(
                SyncDept.mdmCode.in_(all_dept_ids)
            )

            for dept in dept_rows:
                dept_code = str(dept.mdmCode).strip() if dept.mdmCode else ""

                if not dept_code:
                    continue

                dept_map[dept_code] = {
                    "id": dept_code,
                    "name": get_dept_display_name(dept),
                    "mdmCode": dept.mdmCode,
                    "mdmName": dept.mdmName,
                    "departmentName": dept.departmentName,
                    "departmentCode": dept.departmentCode,
                    "longName": dept.longName,
                    "companyCode": dept.companyCode,
                    "corporateName": dept.corporateName,
                }

        # =========================
        # 组装返回数据
        # =========================
        data = []

        for role in roles:
            dept_ids = parse_department_ids(role.department_id)

            role_depts = [
                dept_map.get(dept_id, {
                    "id": dept_id,
                    "name": dept_id,
                })
                for dept_id in dept_ids
            ]

            dept_names = [
                dept.get("name")
                for dept in role_depts
                if dept.get("name")
            ]

            data.append({
                "id": role.id,
                "role_name": role.role_name,

                # 文件权限：1 公开，2 内部
                "file_permission_level": role.file_permission_level,

                # 操作权限 bitmask
                "operation_permission_mask": role.operation_permission_mask,

                "need_approval": role.need_approval,
                "approval_order": role.approval_order,

                # 原始部门 ID，保留给编辑/保存/绑定使用
                "department_id": role.department_id,

                # 规范化后的部门 ID 列表
                "department_ids": dept_ids,

                # 部门名称字符串，方便简单展示
                "department_name": "、".join(dept_names) if dept_names else "",

                # 部门名称列表，方便前端 Tag 展示
                "department_names": dept_names,

                # 部门详情列表，方便前端 tooltip 或弹窗展示
                "departments": role_depts,

                "is_admin": role.is_admin,
                "cover_child_dept": role.cover_child_dept,
                "enabled": role.enabled,

                # 创建人 ID
                "created_by": role.created_by,

                # 创建人名称
                "created_by_name": user_map.get(
                    role.created_by,
                    role.created_by or "-"
                ),

                "created_time": role.created_time,
                "updated_time": role.updated_time,
            })

        return get_json_result(data=data)

    except Exception as e:
        logging.exception(e)
        return server_error_response(e)

class FilePermissionLevel:
    PUBLIC = 1      # 公开
    INTERNAL = 2    # 内部


class OperationPermissionBits:
    VIEW = 1 << 0       # 1 查看
    UPLOAD = 1 << 1     # 2 上传
    DOWNLOAD = 1 << 2   # 4 下载
    DELETE = 1 << 3     # 8 删除
    EDIT = 1 << 4       # 16 编辑



OPERATION_PERMISSION_MAP = {
    "view": OperationPermissionBits.VIEW,
    "upload": OperationPermissionBits.UPLOAD,
    "download": OperationPermissionBits.DOWNLOAD,
    "delete": OperationPermissionBits.DELETE,
    "edit": OperationPermissionBits.EDIT,
}


def build_operation_permission_mask(operation_permissions):
    mask = 0

    for permission in operation_permissions:
        mask |= OPERATION_PERMISSION_MAP[permission]

    return mask

def parse_operation_permission_mask(mask):
    result = []

    for key, bit in OPERATION_PERMISSION_MAP.items():
        if mask & bit:
            result.append(key)

    return result

@manager.route('/get/<role_id>', methods=['GET'])
@login_required
async def get_role(role_id):
    try:
        error_response = check_admin(current_user)
        if error_response:
            return error_response

        if not role_id:
            return get_json_result(
                data=False,
                message="角色ID不能为空",
                code=RetCode.ARGUMENT_ERROR
            )

        role = RoleService.get_by_id(role_id)
        if not role:
            return get_json_result(
                data=False,
                message="角色不存在",
                code=RetCode.OPERATING_ERROR
            )

        created_by_name = role.created_by or "-"

        if role.created_by:
            user = User.get_or_none(User.id == role.created_by)

            if user:
                created_by_name = (
                    user.nickname
                    or user.email
                    or user.id
                )

        data = {
            "id": role.id,
            "role_name": role.role_name,
            "file_permission_level": role.file_permission_level,
            "operation_permission_mask": role.operation_permission_mask,
            "operation_permissions": parse_operation_permission_mask(
                role.operation_permission_mask
            ),
            "need_approval": role.need_approval,
            "approval_order": role.approval_order,
            "department_id": role.department_id,
            "is_admin": role.is_admin,
            "cover_child_dept": role.cover_child_dept,
            "enabled": role.enabled,

            # 创建人 ID
            "created_by": role.created_by,

            # 创建人名称
            "created_by_name": created_by_name,

            "created_time": role.created_time,
            "updated_time": role.updated_time,
        }

        return get_json_result(data=data)

    except Exception as e:
        return server_error_response(e)

@manager.route('/update', methods=['POST'])
@login_required
async def update_role():
    try:
        # 1. 判断是否超级管理员
        error_response = check_admin(current_user)
        if error_response:
            return error_response

        # 2. 获取请求参数
        req = await get_request_json()

        role_id = req.get("id")
        if not role_id:
            return get_json_result(
                data=False,
                message="角色ID不能为空",
                code=RetCode.ARGUMENT_ERROR
            )

        # 3. 判断角色是否存在
        role = RoleService.get_by_id(role_id)
        if not role:
            return get_json_result(
                data=False,
                message="角色不存在",
                code=RetCode.OPERATING_ERROR
            )

        # 4. 校验角色名称
        role_name = req.get("role_name")
        if not role_name:
            return get_json_result(
                data=False,
                message="角色名称不能为空",
                code=RetCode.ARGUMENT_ERROR
            )

        # 5. 校验角色名称是否重复
        exists_role = RoleService.get_by_name(role_name)
        if exists_role and exists_role.id != int(role_id):
            return get_json_result(
                data=False,
                message="角色名称已存在",
                code=RetCode.OPERATING_ERROR
            )

        # 6. 校验文件权限
        file_permission_level = req.get("file_permission_level")
        if not validate_file_permission_level(file_permission_level):
            return get_json_result(
                data=False,
                message="文件权限只能选择公开或内部",
                code=RetCode.ARGUMENT_ERROR
            )

        # 7. 校验操作权限
        operation_permissions = req.get("operation_permissions", [])
        if not validate_operation_permissions(operation_permissions):
            return get_json_result(
                data=False,
                message="操作权限参数错误",
                code=RetCode.ARGUMENT_ERROR
            )

        # 8. 操作权限转 bitmask
        operation_permission_mask = build_operation_permission_mask(
            operation_permissions
        )
        department_id = normalize_department_id(req)
        # 9. 更新入库
        RoleService.update_by_id(
            role_id,
            role_name=role_name,
            file_permission_level=file_permission_level,
            operation_permission_mask=operation_permission_mask,
            need_approval=req.get("need_approval", True),
            approval_order=req.get("approval_order", 0),
            department_id=department_id,
            is_admin=req.get("is_admin", False),
            cover_child_dept=req.get("cover_child_dept", False),
            enabled=req.get("enabled", True),
        )

        return get_json_result(data=True)

    except Exception as e:
        return server_error_response(e)


@manager.route('/bind-persons', methods=['POST'])
@login_required
@validate_request("role_id", "phones")
async def bind_role_persons():
    req = await get_request_json()

    role_id = req["role_id"]
    phones = req["phones"]

    try:
        if not isinstance(phones, list):
            return get_json_result(
                data=False,
                message="phones 必须是数组"
            )

        role = RoleService.model.select().where(
            RoleService.model.id == role_id
        ).first()

        if not role:
            return get_json_result(
                data=False,
                message="角色不存在"
            )

        RoleUserService.bind_persons(
            role_id=role_id,
            phones=phones,
            created_by=current_user.id
        )

        return get_json_result(
            data=True,
            message="绑定成功"
        )

    except Exception as e:
        logging.exception(e)
        return server_error_response(e)

@manager.route('/persons/<int:role_id>', methods=['GET'])
@login_required
async def get_role_bound_persons(role_id):
    try:
        role = RoleService.model.select().where(
            RoleService.model.id == role_id
        ).first()

        if not role:
            return get_json_result(
                data=[],
                message="角色不存在"
            )

        phones = RoleUserService.get_bound_phones_by_role_id(role_id)

        return get_json_result(data=phones)

    except Exception as e:
        logging.exception(e)
        return server_error_response(e)

import json


def parse_department_ids(department_id):
    if not department_id:
        return []

    if isinstance(department_id, list):
        return [
            str(item).strip()
            for item in department_id
            if item and str(item).strip()
        ]

    department_id = str(department_id).strip()

    if not department_id:
        return []

    if department_id.startswith("[") and department_id.endswith("]"):
        try:
            arr = json.loads(department_id)
            if isinstance(arr, list):
                return [
                    str(item).strip()
                    for item in arr
                    if item and str(item).strip()
                ]
        except Exception:
            pass

    if "," in department_id:
        return [
            item.strip()
            for item in department_id.split(",")
            if item.strip()
        ]

    return [department_id]


def get_dept_display_name(dept):
    return (
        getattr(dept, "departmentName", None)
        or getattr(dept, "mdmName", None)
        or getattr(dept, "nameOfAdminOrg", None)
        or getattr(dept, "longName", None)
        or getattr(dept, "mdmCode", None)
    )


@manager.route('/person-detail', methods=['POST'])
@login_required
@validate_request("phone")
async def get_person_detail():
    req = await get_request_json()
    phone = str(req["phone"]).strip()

    try:
        if not phone:
            return get_json_result(
                data=None,
                message="phone 不能为空"
            )

        person = SyncPerson.select().where(
            SyncPerson.phone == phone
        ).first()

        user = User.select().where(
            User.email == phone
        ).first()

        roles = []

        if user:
            role_user_model = RoleUserService.model
            role_model = RoleService.model

            role_user_rows = role_user_model.select().where(
                role_user_model.user_id == user.id
            )

            role_ids = [
                row.role_id
                for row in role_user_rows
                if row.role_id
            ]

            if role_ids:
                role_rows = list(
                    role_model.select().where(
                        role_model.id.in_(role_ids)
                    )
                )

                # 收集部门 ID
                all_dept_ids = set()

                for role in role_rows:
                    dept_ids = parse_department_ids(role.department_id)
                    all_dept_ids.update(dept_ids)

                # 查询部门
                dept_map = {}

                if all_dept_ids:
                    dept_rows = SyncDept.select().where(
                        SyncDept.mdmCode.in_(all_dept_ids)
                    )

                    for dept in dept_rows:
                        dept_code = str(dept.mdmCode).strip() if dept.mdmCode else ""

                        if not dept_code:
                            continue

                        dept_map[dept_code] = {
                            "id": dept_code,
                            "name": get_dept_display_name(dept),
                            "mdmCode": dept.mdmCode,
                            "mdmName": dept.mdmName,
                            "departmentName": dept.departmentName,
                            "departmentCode": dept.departmentCode,
                            "longName": dept.longName,
                            "companyCode": dept.companyCode,
                            "corporateName": dept.corporateName,
                        }

                # 组装角色
                for role in role_rows:
                    dept_ids = parse_department_ids(role.department_id)

                    role_depts = [
                        dept_map.get(dept_id, {
                            "id": dept_id,
                            "name": dept_id,
                        })
                        for dept_id in dept_ids
                    ]

                    dept_names = [
                        dept.get("name")
                        for dept in role_depts
                        if dept.get("name")
                    ]

                    roles.append({
                        "id": role.id,

                        "name": role.role_name,
                        "role_name": role.role_name,

                        "file_permission_level": role.file_permission_level,
                        "operation_permission_mask": role.operation_permission_mask,

                        "need_approval": role.need_approval,
                        "approval_order": role.approval_order,

                        # 原始部门字段
                        "department_id": role.department_id,

                        # 展示字段
                        "department_ids": dept_ids,
                        "department_name": "、".join(dept_names) if dept_names else "",
                        "department_names": dept_names,
                        "departments": role_depts,

                        "is_admin": role.is_admin,
                        "cover_child_dept": role.cover_child_dept,
                        "enabled": role.enabled,

                        "created_by": role.created_by,
                        "created_time": role.created_time,
                        "updated_time": role.updated_time,
                    })

        data = {
            "phone": phone,
            "bindable": bool(user),
            "person": None,
            "user": None,
            "roles": roles,
        }

        if person:
            data["person"] = {
                "id": person.id,
                "mdmName": person.mdmName,
                "mdmCode": person.mdmCode,
                "phone": person.phone,
                "email": person.email,
                "erpid": person.erpid,
                "organize": person.organize,
                "organizationCode": person.organizationCode,
                "part": person.part,
                "gender": person.gender,
                "onDutyOrNot": person.onDutyOrNot,
                "personnelCategory": person.personnelCategory,
            }

        if user:
            data["user"] = {
                "id": user.id,
                "email": user.email,
                "nickname": getattr(user, "nickname", None),
                "username": getattr(user, "username", None),
                "status": getattr(user, "is_active", None),
            }

        return get_json_result(data=data)

    except Exception as e:
        logging.exception(e)
        return server_error_response(e)

import json
from typing import Set

# 1. 部门集合解析函数（支持多种存储格式）
def get_department_set(role) -> Set[str]:
    """
    解析角色的 department_id 字段，返回部门集合（set）
    支持：
    - None / 空字符串 / "null" / "[]" -> 空集合
    - JSON 数组字符串: '["dept1","dept2"]' -> {"dept1","dept2"}
    - 逗号分隔字符串: "dept1,dept2" -> {"dept1","dept2"}
    - 单个字符串: "dept1" -> {"dept1"}
    - 已经是 list 类型 -> 转 set
    """
    dept_value = role.department_id
    if not dept_value:
        return set()
    
    if isinstance(dept_value, list):
        return {d for d in dept_value if d}
    
    if isinstance(dept_value, str):
        # 尝试 JSON 解析
        try:
            parsed = json.loads(dept_value)
            if isinstance(parsed, list):
                return {d for d in parsed if d}
            elif isinstance(parsed, str) and parsed:
                return {parsed}
            else:
                return set()
        except (json.JSONDecodeError, TypeError):
            # 不是 JSON，按逗号分隔
            parts = [d.strip() for d in dept_value.split(',') if d.strip()]
            return set(parts)
    
    return set()

# 2. 根据申请角色查找审批人（匹配相同部门集合）
def find_approver_for_role(role) -> tuple:
    """
    根据申请角色查找对应的审批人
    规则：审批角色为 need_approval=True 且部门集合与申请角色完全相同（集合相等）
    返回: (approver_user_id, approver_user_name, approver_role_id)
    如果找不到，返回 (None, None, None)
    """
    target_dept_set = get_department_set(role)
    
    # 查找所有启用且 need_approval=True 的审批角色
    approver_roles = Role.select().where(
        (Role.need_approval == True) &
        (Role.enabled == True)
    )
    
    for approver_role in approver_roles:
        # 比较部门集合是否完全相同
        if get_department_set(approver_role) == target_dept_set:
            # 找到第一个匹配的审批角色
            approver_user = RoleUser.select().where(
                RoleUser.role_id == approver_role.id
            ).first()
            if approver_user:
                # 获取用户姓名（假设有 User 模型）
                user_obj = User.select().where(User.id == approver_user.user_id).first()
                user_name = user_obj.nickname if user_obj else approver_user.user_id
                return (approver_user.user_id, user_name, approver_role.id)
    
    # 没找到匹配的审批角色
    return (None, None, None)

@manager.route('/apply', methods=['POST'])
@login_required
@validate_request("role_id")
async def apply_role_permission():
    req = await get_request_json()
    role_id = req.get("role_id")
    reason = req.get("reason", "")
    applicant = current_user

    try:
        # 1. 校验角色
        role = Role.select().where(Role.id == role_id).first()
        if not role:
            return get_json_result(data=False, message="角色不存在")

        # 2. 防重复提交
        pending_exists = PermissionApplication.select().where(
            (PermissionApplication.applicant_user_id == applicant.id) &
            (PermissionApplication.role_id == role_id) &
            (PermissionApplication.status == PermissionApplication.Status.PENDING)
        ).exists()
        if pending_exists:
            return get_json_result(data=False, message="您已提交过该角色的申请，请等待审批完成")

        # ========== 3. 查找审批人 ==========
        approver_id, approver_name, approver_role_id = find_approver_for_role(role)
        if not approver_id:
            # 可提示具体部门集合，方便排查
            dept_str = str(get_department_set(role))
            return get_json_result(
                data=False,
                message=f"未找到与部门集合 {dept_str} 匹配的审批角色，请联系管理员配置"
            )

        # ========== 4. 构造 OA 请求 ==========

        oa_payload = {
            "business_type": "role_permission",
            "business_id": f"role_apply_{role_id}_{applicant.id}_{int(time.time())}",
            "applicant": {
                "user_id": applicant.id,
                "user_name": applicant.nickname
            },
            "approver": {
                "user_id": approver_id,
                "user_name": approver_name
            },
            "data": {
                "role_id": role.id,
                "role_name": role.role_name,
                "dept_set": list(get_department_set(role))  # 传给OA展示
            },
            "reason": reason or f"申请角色【{role.role_name}】权限",

            "timestamp": int(time.time())
        }

        # ========== 5. 调用 OA 接口 ==========
        oa_resp = await call_oa_apply_api(oa_payload)
        if not oa_resp.get("success"):
            logging.error(f"OA申请失败: {oa_resp}")
            return get_json_result(
                data=False,
                message=f"OA审批发起失败: {oa_resp.get('message', '未知错误')}"
            )

        oa_business_id = oa_resp.get("business_id") or oa_resp.get("process_instance_id")
        if not oa_business_id:
            logging.error(f"OA返回数据缺少business_id: {oa_resp}")
            return get_json_result(data=False, message="OA接口返回异常，缺少业务ID")

        # ========== 6. 插入本地申请表 ==========
        application = PermissionApplication.create(
            applicant_user_id=applicant.id,
            role_id=role_id,
            oa_business_id=oa_business_id,
            reason=reason or f"申请角色【{role.role_name}】权限",
            status=PermissionApplication.Status.PENDING,
            created_by=applicant.nickname,
            created_time=int(time.time()),
            processed_time=None,
            oa_callback_payload=None
        )

        return get_json_result(
            data={
                "application_id": application.id,
                "oa_business_id": oa_business_id,
                "status": "pending",
                "approver": {"id": approver_id, "name": approver_name}
            },
            message="申请提交成功"
        )

    except Exception as e:
        logging.exception(e)
        return server_error_response(e)


# ========== 辅助函数：实际调用OA接口（需要你实现） ==========
async def call_oa_apply_api(payload: dict) -> dict:
    """
    调用 OA 申请接口，返回标准化字典
    """
    url = "http://localhost:9222/v1/role/oa/apply"  # 根据实际情况调整
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, timeout=30) as resp:
            result = await resp.json()
            
            # 判断成功条件：模拟 OA 返回 code=0 且 data.success=True
            # 真实 OA 可能返回 code=200 或 code=0，请按实际字段调整
            if result.get("code") == 0 and result.get("data", {}).get("success") is True:
                return {
                    "success": True,
                    "business_id": result["data"].get("business_id"),
                    "message": result.get("message", "成功"),
                    "raw": result
                }
            else:
                return {
                    "success": False,
                    "message": result.get("message", "OA 申请失败"),
                    "raw": result
                }

import json
import time
import uuid
from flask import request

@manager.route('/oa/apply', methods=['POST'])
async def mock_oa_apply():
    """
    模拟 OA 的 apply_for_permission 接口
    接收与真实 OA 相同格式的 JSON，存储到本地表，返回 business_id
    """
    req = await get_request_json()
    if not req:
        return get_json_result(data=False, message="无效请求")

    # 生成 OA 内部唯一 ID（例如时间戳+UUID）
    business_id = f"OA_{int(time.time())}_{uuid.uuid4().hex[:8]}"

    # 提取一些关键字段用于后续查询
    business_type = req.get("business_type", "unknown")
    applicant = req.get("applicant", {})
    approver = req.get("approver", {})

    # 存入模拟 OA 申请表
    try:
        OaApplication.create(
            business_id=business_id,
            business_type=business_type,
            payload=json.dumps(req, ensure_ascii=False),
            status=0,  # 审批中
            approver_id=approver.get("user_id"),
            applicant_id=applicant.get("user_id"),
            created_time=int(time.time()),
            updated_time=None
        )
    except Exception as e:
        logging.exception(e)
        return get_json_result(data=False, message=f"存储失败: {str(e)}")

    # 模拟 OA 返回格式（与真实 OA 一致）
    return get_json_result(
        data={
            "success": True,
            "business_id": business_id,
            "message": "申请已提交到OA"
        },
        message="OK"
    )

import aiohttp
import asyncio

# 模拟OA侧审批通过
@manager.route('/oa/approve', methods=['POST'])
@login_required  # 仅管理员可操作（测试时可去掉）
async def mock_oa_approve():
    """
    模拟 OA 审批动作：管理员传入 business_id 和 action (agree/reject)
    然后主动调用业务系统的回调接口 /manager/oa-callback
    """
    req = await get_request_json()
    business_id = req.get("business_id")
    action = req.get("action")  # "agree" 或 "reject"
    comment = req.get("comment", "")

    if not business_id or action not in ("agree", "reject"):
        return get_json_result(data=False, message="参数错误：需要 business_id 和 action (agree/reject)")

    # 1. 从模拟 OA 表中获取申请记录
    try:
        oa_app = OaApplication.get(OaApplication.business_id == business_id)
    except OaApplication.DoesNotExist:
        return get_json_result(data=False, message="未找到该业务ID")

    if oa_app.status != 0:
        return get_json_result(data=False, message="该申请已处理过，请勿重复操作")

    # 2. 更新 OA 表状态
    new_status = 1 if action == "agree" else 2
    oa_app.status = new_status
    oa_app.updated_time = int(time.time())
    oa_app.save()

    # 3. 构造模拟 OA 回调的报文（模仿真实 OA 回调格式）
    callback_payload = {
        "business_id": business_id,
        "business_type": oa_app.business_type,
        "approval_result": "agree" if action == "agree" else "reject",
        "comment": comment,
        "approver": {"user_id": oa_app.approver_id},  # 可以从 payload 中解析，这里简化
        "timestamp": int(time.time())
    }

    # 4. 调用真实的业务回调接口（本地）
    #    注意：这里需要获取当前服务的主机和端口，测试时可硬编码为 http://localhost:5000
    callback_url = "http://localhost:9222/v1/role/oa-callback"  # 请按实际部署地址修改

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(callback_url, json=callback_payload, timeout=10) as resp:
                result = await resp.json()
                # 记录结果（日志）
                logging.info(f"模拟OA回调结果: {result}")
                if resp.status != 200:
                    return get_json_result(data=False, message=f"回调业务接口失败: {result}")
    except Exception as e:
        logging.exception(e)
        return get_json_result(data=False, message=f"回调异常: {str(e)}")

    return get_json_result(
        data={"status": "success", "new_status": "approved" if action == "agree" else "rejected"},
        message="审批完成，已触发回调"
    )


import json
import logging
import time
from peewee import DoesNotExist

@manager.route('/oa-callback', methods=['POST'])
async def oa_callback():
    """
    OA 审批回调接口
    接收 OA 的 POST 请求，更新本地申请状态，通过时直接绑定角色
    """
    try:
        req = await get_request_json()
        if not req:
            logging.warning("OA回调: 请求体为空")
            return get_json_result(data=False, message="请求体为空"), 200

        # 提取参数（根据实际 OA 字段调整）
        business_id = req.get("business_id") or req.get("process_instance_id")
        approval_result = req.get("approval_result") or req.get("result")
        if not business_id:
            logging.error(f"OA回调缺少 business_id: {req}")
            return get_json_result(data=False, message="缺少 business_id"), 200

        # 归一化审批结果
        is_approved = approval_result in ("agree", "approved", "pass")

        # 查询本地申请表
        try:
            application = PermissionApplication.get(
                PermissionApplication.oa_business_id == business_id
            )
        except DoesNotExist:
            logging.error(f"未找到 business_id={business_id} 的申请记录")
            return get_json_result(data=False, message="未找到对应申请"), 200

        # 幂等性：已处理则直接返回成功
        if application.status != PermissionApplication.Status.PENDING:
            logging.info(f"申请 {business_id} 已处理过，状态={application.status}，忽略重复回调")
            return get_json_result(data=True, message="已处理过"), 200

        # 审批通过 → 绑定角色
        if is_approved:
            try:
                # 检查是否已存在绑定关系（防止重复绑定）
                existing = RoleUser.select().where(
                    (RoleUser.role_id == application.role_id) &
                    (RoleUser.user_id == application.applicant_user_id)
                ).first()

                if not existing:
                    RoleUser.create(
                        role_id=application.role_id,
                        user_id=application.applicant_user_id,
                        created_by="system_oa_callback",
                        created_time=int(time.time())
                    )
                    logging.info(f"绑定成功: user_id={application.applicant_user_id}, role_id={application.role_id}")
                else:
                    logging.info(f"用户已拥有该角色，跳过绑定")

                application.status = PermissionApplication.Status.APPROVED

            except Exception as e:
                logging.exception(f"绑定角色失败: {e}")
                # 绑定失败，状态保持 PENDING，返回 200 防止 OA 重试，但需人工介入
                # 可在此触发告警（邮件/钉钉）
                return get_json_result(data=False, message="角色绑定失败，请人工处理"), 200

        else:
            # 审批拒绝
            application.status = PermissionApplication.Status.REJECTED

        # 更新公共字段
        application.processed_time = int(time.time())
        application.oa_callback_payload = json.dumps(req, ensure_ascii=False)
        application.save()

        logging.info(f"申请 {business_id} 处理完成，状态更新为 {application.status}")
        return get_json_result(data=True, message="回调处理成功"), 200

    except Exception as e:
        logging.exception(f"OA回调处理异常: {e}")
        # 返回 200 让 OA 不重试，但记录错误
        return get_json_result(data=False, message="内部错误"), 200

@manager.route('/oa/list', methods=['GET'])
# @login_required
async def get_oa_apply_list():
    """
    获取 OA 系统的申请列表（用于审批管理页面）
    查询 OaApplication 表
    """
    try:
        # 使用 await 异步获取请求参数
        req = await get_request_json()
        if not req:
            req = {}  # 防止 GET 请求没有参数时报错
            
        status = req.get('status')
        business_type = req.get('business_type')

        query = OaApplication.select().order_by(OaApplication.created_time.desc())

        if status is not None:
            query = query.where(OaApplication.status == int(status))
        if business_type:
            query = query.where(OaApplication.business_type == business_type)

        results = []
        for app in query:
            # 解析 payload 中的关键信息
            payload = json.loads(app.payload) if app.payload else {}
            applicant = payload.get('applicant', {})
            approver = payload.get('approver', {})
            data = payload.get('data', {})

            results.append({
                "id": app.id,
                "business_id": app.business_id,
                "business_type": app.business_type,
                "applicant_user_id": app.applicant_id or applicant.get('user_id'),
                "applicant_name": applicant.get('user_name'),
                "approver_user_id": app.approver_id or approver.get('user_id'),
                "approver_name": approver.get('user_name'),
                "role_id": data.get('role_id'),
                "role_name": data.get('role_name'),
                "dept_codes": data.get('dept_codes') or data.get('dept_set'),
                "reason": payload.get('reason'),
                "status": app.status,
                "created_time": app.created_time,
                "updated_time": app.updated_time,
                "payload": app.payload,
            })
        return get_json_result(data=results, message="OK")
    except Exception as e:
        logging.exception(e)
        return server_error_response(e)
