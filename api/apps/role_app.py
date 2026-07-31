from api.db.db_models import AdminUser
from api.apps import login_required, current_user
from api.utils.api_utils import get_json_result, server_error_response, validate_request, get_request_json
from common.constants import RetCode
from api.db.services.role_service import RoleService, validate_file_permission_level, validate_operation_permissions, build_operation_permission_mask
from api.db.db_models import User,SyncPerson
import json

import logging

from api.apps import login_required, current_user
from api.db.db_models import User, Role, SyncDept
from api.db.services.role_service import RoleService
from api.db.services.roleuser_service import RoleUserService
from api.utils.api_utils import (
    get_json_result,
    server_error_response,
    validate_request,
    get_request_json,
)

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
        error_response = check_admin(current_user)
        if error_response:
            return error_response

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
        error_response = check_admin(current_user)
        if error_response:
            return error_response

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