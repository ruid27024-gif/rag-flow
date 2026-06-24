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
from api.db.db_models import DB, KnowledgePermissionApply, OaApproval
from api.utils.api_utils import get_error_data_result, server_error_response, get_data_error_result, validate_request, not_allowed_parameters, \
    get_request_json
from common import settings
from peewee import JOIN
from common.misc_utils import get_uuid, hash_str2int
import json, requests
import datetime

#  OA侧接收申请的接口
@manager.route("/oa/workflow/create", methods=["POST"])
async def oa_create_workflow():
    req = await get_request_json()

    business_id = req["business_id"]
    business_type = req.get("business_type", "knowledge_permission_apply")

    exists = OaApproval.get_or_none(
        (OaApproval.business_id == business_id)
        & (OaApproval.business_type == business_type)
    )

    if exists:
        return get_json_result(data={
            "success": True,
            "process_id": exists.id,
            "task_id": exists.id,
            "message": "Workflow already exists.",
        })

    approval_id = get_uuid()

    OaApproval.create(
        id=approval_id,
        business_id=business_id,
        business_type=business_type,
        title=req.get("title"),
        applicant_id=req.get("applicant_id"),
        applicant_name=req.get("applicant_name"),
        payload=json.dumps(req, ensure_ascii=False),
        callback_url=req.get("callback_url"),
        status="pending",
        created_by=req.get("applicant_id"),
    )

    return get_json_result(data={
        "success": True,
        "process_id": approval_id,
        "task_id": approval_id,
    })

# 查询待审批列表
@manager.route("/oa/workflow/pending", methods=["GET"])
@login_required
async def oa_pending_list():
    approvals = OaApproval.select().where(
        OaApproval.status == "pending"
    ).order_by(OaApproval.create_time.desc())

    data = []

    for item in approvals:
        payload = json.loads(item.payload or "{}")

        data.append({
            "id": item.id,
            "business_id": item.business_id,
            "business_type": item.business_type,
            "title": item.title,
            "applicant_id": item.applicant_id,
            "applicant_name": item.applicant_name,
            "kb_id": payload.get("kb_id"),
            "kb_name": payload.get("kb_name"),
            "permissions": payload.get("permissions", []),
            "reason": payload.get("reason", ""),
            "status": item.status,
        })

    return get_json_result(data=data)

# OA：回调 RAGFlow
def callback_ragflow_permission_apply(
    approval,
    status,
    approver_id,
    approver_name,
    comment="",
):
    if not approval.callback_url:
        return {
            "success": False,
            "message": "Callback URL is empty.",
        }

    payload = {
        "business_id": approval.business_id,
        "process_id": approval.id,
        "task_id": approval.id,
        "status": status,
        "approver_id": approver_id,
        "approver_name": approver_name,
        "comment": comment,
    }

    resp = requests.post(
        approval.callback_url,
        json=payload,
        timeout=10,
    )

    if resp.status_code != 200:
        return {
            "success": False,
            "message": resp.text,
        }

    return {
        "success": True,
        "response": resp.json(),
    }

# OA：审批通过 / 驳回
@manager.route("/oa/workflow/approve", methods=["POST"])
@login_required
@validate_request("approval_id", "status")
async def oa_approve_workflow():
    req = await get_request_json()

    approval_id = req["approval_id"]
    status = req["status"]
    comment = req.get("comment", "")

    if status not in ["approved", "rejected"]:
        return get_json_result(
            code=RetCode.DATA_ERROR,
            message="Invalid status.",
        )

    approval = OaApproval.get_or_none(OaApproval.id == approval_id)

    if not approval:
        return get_json_result(
            code=RetCode.DATA_ERROR,
            message="Approval does not exist.",
        )

    if approval.status != "pending":
        return get_json_result(
            code=RetCode.DATA_ERROR,
            message="Approval already handled.",
        )

    OaApproval.update({
        OaApproval.status: status,
        OaApproval.approver_id: current_user.id,
        OaApproval.approver_name: current_user.nickname,
        OaApproval.approve_comment: comment,
        OaApproval.approve_time: datetime.now(),
    }).where(
        OaApproval.id == approval_id
    ).execute()

    callback_result = callback_ragflow_permission_apply(
        approval=approval,
        status=status,
        approver_id=current_user.id,
        approver_name=current_user.nickname,
        comment=comment,
    )

    return get_json_result(data={
        "approval_id": approval_id,
        "status": status,
        "callback_result": callback_result,
    })