from quart import request
from api.db.db_models import AdminUser, User, UserGroup
from api.db.services.group_service import GroupService
from api.utils.api_utils import get_json_result, server_error_response, validate_request, get_request_json
from api.apps import login_required, current_user
from common.constants import RetCode
from peewee import fn
from api.db.services.knowledgebase_service import KnowledgebaseService
from api.db.services.user_group_service import UserGroupService
from api.db.services.file_service import FileService
from api.db.services.file_admin_service import FileAdminService
from api.db.services.file_group_service import FileGroupService
from api.db import FileType
from api.db.services import UserService
from peewee import IntegrityError
from api.db.db_models import DB, KnowledgePermissionApply, KnowledgePermission
from api.utils.api_utils import get_error_data_result, server_error_response, get_data_error_result, validate_request, not_allowed_parameters, \
    get_request_json
from common import settings
from peewee import JOIN
from common.misc_utils import get_uuid, hash_str2int
import json, requests


def push_apply_to_oa(apply):
    payload = {
        "business_id": apply.id,
        "business_type": "knowledge_permission_apply",
        "title": f"知识库权限申请：{apply.kb_name}",
        "applicant_id": apply.user_id,
        "applicant_name": apply.user_name,
        "kb_id": apply.kb_id,
        "kb_name": apply.kb_name,
        "permissions": json.loads(apply.permissions),
        "reason": apply.reason,
        "callback_url": settings.OA_KB_PERMISSION_CALLBACK_URL,
    }

    # TODO：推送到OA的真实接口
    """
    OA_CREATE_PROCESS_URL = "http://127.0.0.1:9380/api/oa/workflow/create"
    OA_KB_PERMISSION_CALLBACK_URL = "http://127.0.0.1:9380/api/knowledge/permission/oa_callback"
    """
    resp = requests.post(
        settings.OA_CREATE_PROCESS_URL,
        json=payload,
        timeout=10,
    )

    if resp.status_code != 200:
        raise Exception(resp.text)

    data = resp.json()

    result = data.get("data") or data

    if not result.get("success", True):
        raise Exception(result.get("message", "OA create workflow failed."))

    return {
        "process_id": result.get("process_id"),
        "task_id": result.get("task_id"),
    }

# 用户申请的接口
@manager.route("/knowledge/permission/apply", methods=["POST"])
@login_required
@validate_request("kb_id", "permissions")
async def apply_knowledge_permission():
    req = await get_request_json()

    kb_id = req["kb_id"]
    permissions = req["permissions"]
    reason = req.get("reason", "")

    e, kb = KnowledgebaseService.get_by_id(req["kb_id"])
    if not e:
        return get_data_error_result(
            message="Can't find this dataset!")

    exists = KnowledgePermissionApply.select().where(
        (KnowledgePermissionApply.user_id == current_user.id)
        & (KnowledgePermissionApply.kb_id == kb_id)
        & (KnowledgePermissionApply.status == "pending")
    ).first()

    if exists:
        return get_json_result(
            code=RetCode.DATA_ERROR,
            message="Permission application already pending.",
            data={"id": exists.id},
        )

    apply_id = get_uuid()

    apply = KnowledgePermissionApply.create(
        id=apply_id,
        user_id=current_user.id,
        user_name=current_user.nickname,
        kb_id=kb_id,
        kb_name=kb.name,
        permissions=json.dumps(permissions, ensure_ascii=False),
        reason=reason,
        status="pending",
        oa_push_status="pending",
        created_by=current_user.id,
    )

    try:
        # 推送消息到OA的接口
        oa_result = push_apply_to_oa(apply)

        # 返回的消息写入申请表
        KnowledgePermissionApply.update({
            KnowledgePermissionApply.oa_process_id: oa_result.get("process_id"),
            KnowledgePermissionApply.oa_task_id: oa_result.get("task_id"),
            KnowledgePermissionApply.oa_push_status: "success",
            KnowledgePermissionApply.oa_push_error: None,
        }).where(
            KnowledgePermissionApply.id == apply_id
        ).execute()

    except Exception as e:
        KnowledgePermissionApply.update({
            KnowledgePermissionApply.oa_push_status: "failed",
            KnowledgePermissionApply.oa_push_error: str(e),
        }).where(
            KnowledgePermissionApply.id == apply_id
        ).execute()

        return get_json_result(
            code=RetCode.OPERATING_ERROR,
            message=f"OA push failed: {str(e)}",
        )

    return get_json_result(data={
        "id": apply_id,
        "status": "pending",
    })

def write_knowledge_permission(apply):
    permissions = json.loads(apply.permissions or "[]")

    can_preview = "preview" in permissions
    can_upload = "upload" in permissions
    can_delete = "delete" in permissions
    can_edit = "edit" in permissions

    exists = KnowledgePermission.get_or_none(
        (KnowledgePermission.user_id == apply.user_id)
        & (KnowledgePermission.kb_id == apply.kb_id)
    )

    if exists:
        KnowledgePermission.update({
            KnowledgePermission.can_preview: exists.can_preview or can_preview,
            KnowledgePermission.can_upload: exists.can_upload or can_upload,
            KnowledgePermission.can_delete: exists.can_delete or can_delete,
            KnowledgePermission.can_edit: exists.can_edit or can_edit,
            KnowledgePermission.apply_id: apply.id,
        }).where(
            KnowledgePermission.id == exists.id
        ).execute()
    else:
        KnowledgePermission.create(
            id=get_uuid(),
            user_id=apply.user_id,
            kb_id=apply.kb_id,
            can_preview=can_preview,
            can_upload=can_upload,
            can_delete=can_delete,
            can_edit=can_edit,
            apply_id=apply.id,
            source="oa",
            created_by=apply.user_id,
        )


# 10. RAGFlow：接收 OA 回调 更新申请表 、写入权限表
@manager.route("/knowledge/permission/oa_callback", methods=["POST"])
async def oa_permission_callback():
    req = await get_request_json()

    apply_id = req.get("business_id")
    process_id = req.get("process_id")
    status = req.get("status")
    approver_id = req.get("approver_id")
    approver_name = req.get("approver_name")
    comment = req.get("comment", "")

    if status not in ["approved", "rejected"]:
        return get_json_result(
            code=RetCode.DATA_ERROR,
            message="Invalid OA status.",
        )

    apply = KnowledgePermissionApply.get_or_none(
        KnowledgePermissionApply.id == apply_id
    )

    if not apply:
        return get_json_result(
            code=RetCode.DATA_ERROR,
            message="Application does not exist.",
        )

    if apply.oa_process_id and process_id != apply.oa_process_id:
        return get_json_result(
            code=RetCode.DATA_ERROR,
            message="OA process id does not match.",
        )

    if apply.status != "pending":
        return get_json_result(data={
            "message": "Application already handled.",
        })

    KnowledgePermissionApply.update({
        KnowledgePermissionApply.status: status,
        KnowledgePermissionApply.approver_id: approver_id,
        KnowledgePermissionApply.approver_name: approver_name,
        KnowledgePermissionApply.approve_comment: comment,
        KnowledgePermissionApply.approve_time: datetime.now(),
    }).where(
        KnowledgePermissionApply.id == apply_id
    ).execute()

    if status == "approved":
        write_knowledge_permission(apply)

    return get_json_result(data=True)

# 1. 我的申请列表接口
@manager.route("/knowledge/permission/apply/list", methods=["GET"])
@login_required
async def list_my_permission_apply():
    applies = (
        KnowledgePermissionApply
        .select()
        .where(KnowledgePermissionApply.user_id == current_user.id)
        .order_by(KnowledgePermissionApply.created_time.desc())
    )

    data = []

    for item in applies:
        data.append({
            "id": item.id,
            "kb_id": item.kb_id,
            "kb_name": item.kb_name,
            "permissions": json.loads(item.permissions or "[]"),
            "reason": item.reason,
            "status": item.status,
            "oa_push_status": item.oa_push_status,
            "oa_push_error": item.oa_push_error,
            "approver_id": item.approver_id,
            "approver_name": item.approver_name,
            "approve_comment": item.approve_comment,
            "approve_time": item.approve_time,
            "created_time": item.created_time,
            "updated_time": item.updated_time,
        })

    return get_json_result(data=data)

# 2. 查看单个申请详情
@manager.route("/knowledge/permission/apply/<apply_id>", methods=["GET"])
@login_required
async def get_my_permission_apply(apply_id):
    apply = KnowledgePermissionApply.get_or_none(
        (KnowledgePermissionApply.id == apply_id)
        & (KnowledgePermissionApply.user_id == current_user.id)
    )

    if not apply:
        return get_json_result(
            code=RetCode.DATA_ERROR,
            message="Application does not exist.",
        )

    return get_json_result(data={
        "id": apply.id,
        "kb_id": apply.kb_id,
        "kb_name": apply.kb_name,
        "permissions": json.loads(apply.permissions or "[]"),
        "reason": apply.reason,
        "status": apply.status,
        "oa_push_status": apply.oa_push_status,
        "oa_push_error": apply.oa_push_error,
        "approver_id": apply.approver_id,
        "approver_name": apply.approver_name,
        "approve_comment": apply.approve_comment,
        "approve_time": apply.approve_time,
        "created_time": apply.created_time,
        "updated_time": apply.updated_time,
    })

# 权限校验方法

def check_knowledge_permission(user_id, kb_id, action):
    perm = KnowledgePermission.get_or_none(
        (KnowledgePermission.user_id == user_id)
        & (KnowledgePermission.kb_id == kb_id)
    )

    if not perm:
        return False

    if action == "preview":
        return perm.can_preview

    if action == "upload":
        return perm.can_upload

    if action == "delete":
        return perm.can_delete

    if action == "edit":
        return perm.can_edit

    return False


# if not check_knowledge_permission(current_user.id, kb_id, "upload"):
#     return get_json_result(
#         code=RetCode.AUTHENTICATION_ERROR,
#         message="No upload permission.",
#     )