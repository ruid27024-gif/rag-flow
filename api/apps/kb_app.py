#
#  Copyright 2024 The InfiniFlow Authors. All Rights Reserved.
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
import json
import logging
import random
import re
import asyncio

from quart import request
import numpy as np

from api.db.services.connector_service import Connector2KbService
from api.db.services.llm_service import LLMBundle
from api.db.services.document_service import DocumentService, queue_raptor_o_graphrag_tasks
from api.db.services.file2document_service import File2DocumentService
from api.db.services.file_service import FileService
from api.db.services.pipeline_operation_log_service import PipelineOperationLogService
from api.db.services.task_service import TaskService, GRAPH_RAPTOR_FAKE_DOC_ID
from api.db.services.user_service import TenantService, UserTenantService
from api.utils.api_utils import get_error_data_result, server_error_response, get_data_error_result, validate_request, not_allowed_parameters, \
    get_request_json
from api.db import VALID_FILE_TYPES
from api.db.services.file_admin_service import FileAdminService
from api.db.services.file_group_service import FileGroupService
from api.db.services.knowledgebase_service import KnowledgebaseService
from api.db.db_models import File, AdminUser, File_Admin, File_Group, PipelineOperationLog
from api.utils.api_utils import get_json_result
from rag.nlp import search
from api.constants import DATASET_NAME_LIMIT
from rag.utils.redis_conn import REDIS_CONN
from rag.utils.doc_store_conn import OrderByExpr
from common.constants import RetCode, PipelineTaskType, StatusEnum, VALID_TASK_STATUS, FileSource, LLMType, PAGERANK_FLD
from common import settings
from api.apps import login_required, current_user
from api.db.db_models import DB, Group,OAApplicationkb as OAApplication,OAApprovalTaskkb as OAApprovalTask,KnowledgeBaseCreateApply

import time
import uuid

import json
import time
import uuid
import httpx

from quart import request

from api.db.db_models import (
    KnowledgeBaseCreateApply,
    Role,
    RoleUser,
    User,
    SyncPerson,
)


OA_CREATE_URL = "http://localhost:9222/v1/kb/oa/approval/create"
OA_APP_ID = "ragflow"


def generate_business_id():
    return f"kb_create_{uuid.uuid4().hex}"



@manager.route("/create", methods=["POST"])  # noqa: F821
@login_required
@validate_request("name")
async def create():
    """
    提交知识库创建申请。

    流程：

    1. 接收前端建库参数；
    2. 根据当前登录用户自动获取所属部门；
    3. 根据当前部门绑定的审批角色自动获取审批人；
    4. 保存知识库侧申请记录；
    5. 调用 OA 创建审批单；
    6. 保存 OA 返回的 oa_request_id；
    7. 返回 pending 状态。

    当前接口不会真正创建知识库。
    审批通过后，应在 OA 回调接口中真正创建知识库。
    """

    logger = logging.getLogger(__name__)

    business_id = None

    # ==============================================================
    # 内部辅助方法
    # ==============================================================

    def print_json(title, value):
        """
        调试打印 JSON。
        """
        print("\n" + "=" * 100)
        print(title)

        try:
            print(
                json.dumps(
                    value,
                    ensure_ascii=False,
                    indent=2,
                    default=str,
                )
            )
        except Exception:
            print(str(value))

        print("=" * 100 + "\n")

    
    def _parse_role_department_ids(value):
        """
        解析角色绑定的部门 ID。

        支持：

            "1001"
            "1001,1002"
            "1001，1002"
            ["1001", "1002"]
            '["1001", "1002"]'
        """

        if value is None:
            return set()

        if isinstance(value, (list, tuple, set)):
            return {
                str(item).strip()
                for item in value
                if item is not None and str(item).strip()
            }

        value = str(value).strip()

        if not value:
            return set()

        # JSON 数组
        if value.startswith("[") and value.endswith("]"):
            try:
                data = json.loads(value)

                if isinstance(data, list):
                    return {
                        str(item).strip()
                        for item in data
                        if item is not None and str(item).strip()
                    }
            except Exception:
                pass

        # 普通分隔字符串
        value = (
            value
            .replace("，", ",")
            .replace(";", ",")
            .replace("；", ",")
        )

        return {
            item.strip()
            for item in value.split(",")
            if item.strip()
        }


    def get_department_approver(
        department_code,
        current_user_id=None,
    ):
        """
        查询当前部门下 need_approval=1 角色绑定的审批人员。

        查询条件：

            Role.department_id 匹配 department_code
            Role.enabled = 1
            Role.need_approval = 1
            RoleUser.role_id = Role.id
            RoleUser.user_id = User.id
            User.status = "1"

        同时排除当前登录用户自己。

        返回：

            {
                "user_id": "审批人 ID",
                "user_name": "审批人名称",
                "role_id": "角色 ID",
                "role_name": "角色名称",
            }

        如果没有找到审批人，返回 None。
        """

        # ----------------------------------------
        # 1. 校验部门编码
        # ----------------------------------------

        if department_code is None:
            return None

        department_code = str(department_code).strip()

        if not department_code:
            return None

        # ----------------------------------------
        # 2. 当前登录用户 ID
        # ----------------------------------------

        current_user_id_str = None

        if current_user_id is not None:
            current_user_id_str = str(current_user_id).strip()

            if not current_user_id_str:
                current_user_id_str = None

        # ----------------------------------------
        # 3. 可选的角色名称配置
        # ----------------------------------------

        approval_role_names = getattr(
            settings,
            "KB_CREATE_APPROVAL_ROLE_NAMES",
            None,
        )

        if approval_role_names:
            if isinstance(approval_role_names, str):
                approval_role_names = [
                    approval_role_names,
                ]

            approval_role_names = {
                str(item).strip()
                for item in approval_role_names
                if item is not None and str(item).strip()
            }

        # ----------------------------------------
        # 4. 查询启用且 need_approval=1 的角色
        # ----------------------------------------

        roles_query = (
            Role
            .select(
                Role.id,
                Role.role_name,
                Role.department_id,
                Role.enabled,
                Role.need_approval,
            )
            .where(
                (Role.enabled == 1)
                & (Role.need_approval == 1)
            )
            .order_by(
                Role.id.asc()
            )
        )

        # 如果配置了角色名称，则继续按角色名称过滤
        if approval_role_names:
            roles_query = roles_query.where(
                Role.role_name.in_(
                    list(approval_role_names)
                )
            )

        # ----------------------------------------
        # 5. 按部门编码匹配角色
        # ----------------------------------------

        matched_roles = []

        for role in roles_query:
            role_department_ids = _parse_role_department_ids(
                role.department_id
            )

            if department_code not in role_department_ids:
                continue

            # 这里不要使用：
            #
            #     role.need_approval is not True
            #
            # 因为数据库返回值可能是整数 1。
            #
            # 使用 bool 判断即可。
            if not role.enabled:
                continue

            if not role.need_approval:
                continue

            matched_roles.append(role)

        if not matched_roles:
            print(
                "[APPROVER] 当前部门没有绑定 need_approval=1 的启用角色：",
                {
                    "department_code": department_code,
                    "approval_role_names": (
                        list(approval_role_names)
                        if approval_role_names
                        else None
                    ),
                },
            )

            return None

        print(
            "[APPROVER] 匹配到审批角色：",
            [
                {
                    "role_id": role.id,
                    "role_name": role.role_name,
                    "department_id": role.department_id,
                    "enabled": role.enabled,
                    "need_approval": role.need_approval,
                }
                for role in matched_roles
            ],
        )

        role_ids = [
            role.id
            for role in matched_roles
            if role.id is not None
        ]

        if not role_ids:
            return None

        # ----------------------------------------
        # 6. 查询审批角色绑定的有效用户
        # ----------------------------------------

        approver_query = (
            User
            .select(
                User.id,
                User.nickname,
                User.email,
                Role.id.alias("role_id"),
                Role.role_name.alias("role_name"),
            )
            .join(
                RoleUser,
                on=(RoleUser.user_id == User.id),
            )
            .join(
                Role,
                on=(Role.id == RoleUser.role_id),
            )
            .where(
                (Role.id.in_(role_ids))
                & (Role.enabled == 1)
                & (Role.need_approval == 1)
                & (User.status == "1")
            )
            .order_by(
                Role.id.asc(),
                User.id.asc(),
            )
        )

        # ----------------------------------------
        # 7. 组装审批人，并排除当前登录用户
        # ----------------------------------------

        for user in approver_query:
            if user.id is None:
                continue

            user_id = str(user.id).strip()

            if not user_id:
                continue

            # 排除当前登录用户自己
            if (
                current_user_id_str is not None
                and user_id == current_user_id_str
            ):
                print(
                    "[APPROVER] 跳过当前登录用户：",
                    {
                        "user_id": user_id,
                        "current_user_id": current_user_id_str,
                    },
                )

                continue

            user_name = (
                getattr(user, "nickname", None)
                or getattr(user, "email", None)
                or user_id
            )

            approver = {
                "user_id": user_id,
                "user_name": str(user_name),
                "role_id": getattr(user, "role_id", None),
                "role_name": getattr(user, "role_name", None),
            }

            print(
                "[APPROVER] 最终审批人：",
                approver,
            )

            return approver

        # ----------------------------------------
        # 8. 没有其他有效审批人
        # ----------------------------------------

        print(
            "[APPROVER] need_approval=1 的角色没有绑定其他有效用户：",
            {
                "department_code": department_code,
                "role_ids": role_ids,
                "current_user_id": current_user_id_str,
            },
        )

        return None

    def get_current_user_department(current_user_obj):
        """
        根据当前登录用户获取所属部门。

        关联关系：

            User.email == SyncPerson.phone

        返回：

            {
                "dept_code": "部门编码",
                "dept_name": "部门名称"
            }
        """

        if not current_user_obj:
            print(
                "[KB CREATE] 当前登录用户为空，无法获取部门"
            )
            return None

        current_user_email = str(
            getattr(
                current_user_obj,
                "email",
                None,
            )
            or ""
        ).strip()

        current_user_id = str(
            getattr(
                current_user_obj,
                "id",
                None,
            )
            or ""
        ).strip()

        if not current_user_email:
            print(
                "[KB CREATE] 当前登录用户 email 为空：",
                {
                    "user_id": current_user_id,
                    "email": current_user_email,
                },
            )
            return None

        print(
            "[KB CREATE] 开始查询当前用户所属部门：",
            {
                "user_id": current_user_id,
                "email": current_user_email,
            },
        )

        person = (
            SyncPerson
            .select(
                SyncPerson.organizationCode,
                SyncPerson.organize,
            )
            .where(
                (SyncPerson.phone == current_user_email)
                & SyncPerson.organizationCode.is_null(False)
                & (SyncPerson.organizationCode != "")
            )
            .first()
        )

        if not person:
            print(
                "[KB CREATE] 没有找到当前用户对应的部门：",
                {
                    "user_id": current_user_id,
                    "email": current_user_email,
                },
            )
            return None

        department_code = str(
            person.organizationCode or ""
        ).strip()

        department_name = str(
            person.organize or ""
        ).strip()

        if not department_code:
            print(
                "[KB CREATE] 当前用户部门编码为空：",
                {
                    "user_id": current_user_id,
                    "email": current_user_email,
                    "person": getattr(
                        person,
                        "__data__",
                        {},
                    ),
                },
            )
            return None

        result = {
            "dept_code": department_code,
            "dept_name": department_name,
        }

        print(
            "[KB CREATE] 当前用户所属部门：",
            result,
        )

        return result

    
    def save_oa_failed(error_message):
        """
        保存 OA 推送失败状态。
        """
        if not business_id:
            return

        try:
            affected_rows = (
                KnowledgeBaseCreateApply
                .update(
                    oa_push_status="failed",
                    oa_push_error=str(
                        error_message
                    ),
                    updated_time=int(
                        time.time()
                    ),
                )
                .where(
                    KnowledgeBaseCreateApply.business_id
                    == business_id
                )
                .execute()
            )

            print(
                "[KB CREATE] OA 失败状态已保存：",
                {
                    "business_id": business_id,
                    "affected_rows": affected_rows,
                    "error": str(error_message),
                },
            )

        except Exception as update_error:
            print(
                "[KB CREATE] 保存 OA 失败状态时发生异常："
            )
            print(
                {
                    "business_id": business_id,
                    "original_error": str(
                        error_message
                    ),
                    "update_error": str(
                        update_error
                    ),
                }
            )
            print(traceback.format_exc())

    # ==============================================================
    # 1. 读取请求参数
    # ==============================================================

    try:
        req = await request.get_json()

    except Exception as e:
        print(
            "[KB CREATE] 读取请求 JSON 失败："
        )
        print(str(e))
        print(traceback.format_exc())

        return get_json_result(
            data=False,
            message=(
                "Invalid request JSON: "
                f"{str(e)}"
            ),
            code=RetCode.ARGUMENT_ERROR,
        )

    if not req:
        return get_json_result(
            data=False,
            message="Empty request body.",
            code=RetCode.ARGUMENT_ERROR,
        )

    if not isinstance(req, dict):
        return get_json_result(
            data=False,
            message=(
                "Request body must be a JSON object."
            ),
            code=RetCode.ARGUMENT_ERROR,
        )

    req = dict(req)

    # ==============================================================
    # 2. 校验知识库名称
    # ==============================================================

    kb_name = req.get("name")

    if kb_name is None:
        return get_json_result(
            data=False,
            message=(
                "Knowledge base name is required."
            ),
            code=RetCode.ARGUMENT_ERROR,
        )

    kb_name = str(kb_name).strip()

    if not kb_name:
        return get_json_result(
            data=False,
            message=(
                "Knowledge base name is required."
            ),
            code=RetCode.ARGUMENT_ERROR,
        )

    # ==============================================================
    # 3. 获取当前用户信息
    # ==============================================================

    current_user_id = str(
        getattr(
            current_user,
            "id",
            None,
        )
        or ""
    ).strip()

    current_user_name = (
        getattr(
            current_user,
            "name",
            None,
        )
        or getattr(
            current_user,
            "nickname",
            None,
        )
        or getattr(
            current_user,
            "email",
            None,
        )
        or ""
    )

    if not current_user_id:
        return get_json_result(
            data=False,
            message="Current user id is required.",
            code=RetCode.AUTHENTICATION_ERROR,
        )

    # ==============================================================
    # 4. 后端获取当前用户所属部门
    # ==============================================================

    applicant_dept = get_current_user_department(
        current_user
    )

    if not applicant_dept:
        return get_json_result(
            data=False,
            message=(
                "The current user is not bound "
                "to any department."
            ),
            code=RetCode.ARGUMENT_ERROR,
        )

    # ==============================================================
    # 5. 后端获取部门审批人
    # ==============================================================

    approver = get_department_approver(
        department_code=applicant_dept.get(
            "dept_code"
        ),
        current_user_id=current_user_id,
    )

    if not approver:
        return get_json_result(
            data=False,
            message=(
                "No approver is configured for "
                f"department: "
                f"{applicant_dept.get('dept_code')}"
            ),
            code=RetCode.ARGUMENT_ERROR,
        )

    # ==============================================================
    # 6. 生成申请业务 ID
    # ==============================================================

    business_id = generate_business_id()
    now = int(time.time())

    public_kb = req.get("public_kb") or {}

    # 保存完整原始申请参数。
    #
    # 注意：
    # 不信任前端传来的 applicant_dept、approver，
    # 使用后端实际查询结果覆盖。
    original_request = dict(req)

    original_request["tenant_id"] = current_user_id

    original_request["applicant_dept"] = applicant_dept

    original_request["approver"] = {
        "user_id": approver.get("user_id"),
        "user_name": approver.get("user_name"),
    }

    print_json(
        "[KB CREATE] 当前申请人、部门、审批人",
        {
            "user_id": current_user_id,
            "user_name": current_user_name,
            "applicant_dept": applicant_dept,
            "approver": approver,
        },
    )

    # ==============================================================
    # 7. OA 回调地址
    # ==============================================================

    # 生产环境不要使用 localhost。
    #
    # 例如：
    #
    # settings.OA_CALLBACK_URL =
    # http://ragflow-api:9380/v1/kb/oa/approval/callback
    #
    oa_callback_url = getattr(
        settings,
        "OA_CALLBACK_URL",
        (
            "http://localhost:9380"
            "/v1/kb/oa/approval/callback"
        ),
    )

    # ==============================================================
    # 8. 保存知识库侧申请记录
    # ==============================================================

    apply_data = {
        "business_id": business_id,
        "business_type": "kb_create",
        "request_data": json.dumps(
            original_request,
            ensure_ascii=False,
            default=str,
        ),
        "user_id": current_user_id,
        "user_name": current_user_name,
        "kb_name": kb_name,
        "status": "pending",
        "create_status": "pending",
        "oa_push_status": "pending",
        "created_time": now,
        "updated_time": now,
    }

    # 如果 DataBaseModel 中定义了 create_time，
    # 且数据库表中已经存在 create_time 字段，
    # 可以显式赋值。
    #
    # 你之前的报错说明父类很可能存在该字段。
    # 如果数据库已经补充 create_time，保留下面这行。
    apply_data["create_time"] = now

    print_json(
        "[KB CREATE] 准备保存知识库申请记录",
        {
            "business_id": business_id,
            "apply_data": apply_data,
        },
    )

    try:
        created_apply = (
            KnowledgeBaseCreateApply.create(
                **apply_data
            )
        )

        print_json(
            "[KB CREATE] 知识库申请记录保存成功",
            {
                "business_id": business_id,
                "record": getattr(
                    created_apply,
                    "__data__",
                    {},
                ),
            },
        )

    except Exception as e:
        error_message = (
            "Save KnowledgeBaseCreateApply failed: "
            f"{type(e).__name__}: {str(e)}"
        )

        print(
            "[KB CREATE] 保存知识库申请记录失败："
        )
        print(error_message)
        print(traceback.format_exc())

        return server_error_response(e)

    # ==============================================================
    # 9. 构造 OA 请求数据
    # ==============================================================

    oa_data = {
        "applicant_dept": {
            "dept_code": applicant_dept.get(
                "dept_code"
            ),
            "dept_name": applicant_dept.get(
                "dept_name"
            ),
        },
        "kb_name": kb_name,
    }

    if public_kb:
        oa_data["public_kb"] = {
            "kb_id": public_kb.get("kb_id"),
            "kb_name": public_kb.get("kb_name"),
        }

    oa_payload = {
        "app_id": OA_APP_ID,
        "business_type": "kb_create",
        "business_id": business_id,
        "batch_id": business_id,
        "reason": req.get("reason", ""),
        "applicant": {
            "user_id": current_user_id,
            "user_name": current_user_name,
        },
        "approver": {
            "user_id": approver.get(
                "user_id"
            ),
            "user_name": approver.get(
                "user_name"
            ),
        },
        "data": oa_data,
        "callback_url": oa_callback_url,
        "timestamp": now,
    }

    print_json(
        (
            "[KB CREATE] 准备推送 OA，URL："
            + str(OA_CREATE_URL)
        ),
        oa_payload,
    )

    # ==============================================================
    # 10. 调用 OA 创建审批单
    # ==============================================================

    try:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        print(
            "[KB CREATE] 开始调用 OA：",
            {
                "url": OA_CREATE_URL,
                "business_id": business_id,
                "headers": headers,
            },
        )

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=5.0,
                read=20.0,
                write=10.0,
                pool=5.0,
            )
        ) as client:
            response = await client.post(
                OA_CREATE_URL,
                json=oa_payload,
                headers=headers,
            )

        # ----------------------------------------------------------
        # 10.1 HTTP 状态码判断
        #
        # HTTP 200 和业务 code=0 是两层含义：
        #
        # HTTP：
        #     200 <= status < 300
        #
        # 业务：
        #     code == 0 或 code == 200
        # ----------------------------------------------------------

        print(
            "[KB CREATE] OA HTTP 状态码：",
            response.status_code,
        )

        print(
            "[KB CREATE] OA 响应头：",
            dict(response.headers),
        )

        print(
            "[KB CREATE] OA 原始响应：",
            response.text,
        )

        if not (
            200 <= int(response.status_code) < 300
        ):
            error_message = (
                "OA HTTP request failed: "
                f"status_code={response.status_code}, "
                f"response={response.text}"
            )

            print(
                "[KB CREATE] "
                + error_message
            )

            raise RuntimeError(
                error_message
            )

        # ----------------------------------------------------------
        # 10.2 解析 OA JSON
        # ----------------------------------------------------------

        try:
            oa_result = response.json()

        except Exception as e:
            error_message = (
                "OA response is not valid JSON: "
                f"status_code={response.status_code}, "
                f"response={response.text}"
            )

            print(
                "[KB CREATE] "
                + error_message
            )
            print(traceback.format_exc())

            raise RuntimeError(
                error_message
            ) from e

        print_json(
            "[KB CREATE] OA JSON 响应",
            oa_result,
        )

        # ----------------------------------------------------------
        # 10.3 判断 OA 业务码
        # ----------------------------------------------------------

        oa_code = oa_result.get("code")
        oa_message = oa_result.get("message")

        print(
            "[KB CREATE] OA business code:",
            oa_code,
        )

        print(
            "[KB CREATE] OA business message:",
            oa_message,
        )

        # 你的 OA 返回 code=0，所以必须接受 0。
        if str(oa_code) not in {
            "0",
            "200",
        }:
            error_message = (
                "OA business request failed: "
                f"code={oa_code}, "
                f"message={oa_message}, "
                f"response={json.dumps(oa_result, ensure_ascii=False, default=str)}"
            )

            print(
                "[KB CREATE] "
                + error_message
            )

            raise RuntimeError(
                error_message
            )

        # ----------------------------------------------------------
        # 10.4 获取 OA 审批单 ID
        # ----------------------------------------------------------

        oa_result_data = (
            oa_result.get("data")
            or {}
        )

        oa_request_id = (
            oa_result_data.get(
                "oa_request_id"
            )
            or oa_result_data.get(
                "request_id"
            )
            or oa_result_data.get(
                "approval_id"
            )
            or oa_result_data.get(
                "instance_id"
            )
            or oa_result.get(
                "oa_request_id"
            )
            or oa_result.get(
                "request_id"
            )
            or oa_result.get(
                "approval_id"
            )
        )

        if not oa_request_id:
            error_message = (
                "OA returned success, "
                "but oa_request_id is missing: "
                f"{json.dumps(oa_result, ensure_ascii=False, default=str)}"
            )

            print(
                "[KB CREATE] "
                + error_message
            )

            raise RuntimeError(
                error_message
            )

        oa_request_id = str(
            oa_request_id
        ).strip()

        print(
            "[KB CREATE] OA 创建审批成功：",
            {
                "business_id": business_id,
                "oa_request_id": oa_request_id,
                "approver": approver,
            },
        )

        # ----------------------------------------------------------
        # 10.5 更新本地申请记录
        # ----------------------------------------------------------

        affected_rows = (
            KnowledgeBaseCreateApply
            .update(
                oa_request_id=oa_request_id,
                oa_push_status="success",
                oa_push_error=None,
                updated_time=int(
                    time.time()
                ),
            )
            .where(
                KnowledgeBaseCreateApply.business_id
                == business_id
            )
            .execute()
        )

        print(
            "[KB CREATE] 本地 OA 信息更新完成：",
            {
                "business_id": business_id,
                "oa_request_id": oa_request_id,
                "affected_rows": affected_rows,
            },
        )

        if not affected_rows:
            print(
                "[KB CREATE] 警告：OA 创建成功，"
                "但本地申请记录没有更新。"
            )

        # ----------------------------------------------------------
        # 10.6 返回申请成功
        # ----------------------------------------------------------
        #
        # 这里不能返回真实 kb_id。
        # 因为审批通过前，知识库还没有创建。
        # ----------------------------------------------------------

        return get_json_result(
            data={
                "business_id": business_id,
                "oa_request_id": oa_request_id,
                "status": "pending",
                "oa_push_status": "success",
                "created": False,
                "approved": False,
                "kb_id": None,
                "created_kb_id": None,
                "applicant_dept": applicant_dept,
                "approver": {
                    "user_id": approver.get(
                        "user_id"
                    ),
                    "user_name": approver.get(
                        "user_name"
                    ),
                },
            },
            message=(
                "Knowledge base creation request "
                "submitted and is waiting for approval."
            ),
            code=RetCode.SUCCESS,
        )

    # ==============================================================
    # 11. OA 请求超时
    # ==============================================================

    except httpx.TimeoutException as e:
        error_message = (
            "OA request timeout: "
            f"{type(e).__name__}: {str(e)}"
        )

        print(
            "[KB CREATE] "
            + error_message
        )
        print(traceback.format_exc())

        logger.exception(
            "OA request timeout, business_id=%s",
            business_id,
        )

        save_oa_failed(error_message)

        return get_json_result(
            data={
                "business_id": business_id,
                "status": "pending",
                "oa_push_status": "failed",
                "error_type": "timeout",
                "message": error_message,
            },
            message=(
                "Application saved, "
                "but OA request timed out."
            ),
            code=RetCode.SERVER_ERROR,
        )

    # ==============================================================
    # 12. OA 连接失败
    # ==============================================================

    except httpx.ConnectError as e:
        error_message = (
            "Cannot connect to OA: "
            f"{type(e).__name__}: {str(e)}"
        )

        print(
            "[KB CREATE] "
            + error_message
        )
        print(traceback.format_exc())

        logger.exception(
            "Cannot connect to OA, business_id=%s",
            business_id,
        )

        save_oa_failed(error_message)

        return get_json_result(
            data={
                "business_id": business_id,
                "status": "pending",
                "oa_push_status": "failed",
                "error_type": "connect_error",
                "message": error_message,
            },
            message=(
                "Application saved, "
                "but OA cannot be reached."
            ),
            code=RetCode.SERVER_ERROR,
        )

    # ==============================================================
    # 13. 其他 HTTP 网络异常
    # ==============================================================

    except httpx.RequestError as e:
        error_message = (
            "OA network request failed: "
            f"{type(e).__name__}: {str(e)}"
        )

        print(
            "[KB CREATE] "
            + error_message
        )
        print(traceback.format_exc())

        logger.exception(
            "OA network request failed, business_id=%s",
            business_id,
        )

        save_oa_failed(error_message)

        return get_json_result(
            data={
                "business_id": business_id,
                "status": "pending",
                "oa_push_status": "failed",
                "error_type": "request_error",
                "message": error_message,
            },
            message=(
                "Application saved, "
                "but OA request failed."
            ),
            code=RetCode.SERVER_ERROR,
        )

    # ==============================================================
    # 14. 其他异常
    # ==============================================================

    except Exception as e:
        error_message = (
            "OA processing failed: "
            f"{type(e).__name__}: {str(e)}"
        )

        print(
            "[KB CREATE] "
            + error_message
        )
        print(traceback.format_exc())

        logger.exception(
            "OA processing failed, business_id=%s",
            business_id,
        )

        save_oa_failed(error_message)

        return get_json_result(
            data={
                "business_id": business_id,
                "status": "pending",
                "oa_push_status": "failed",
                "error_type": type(e).__name__,
                "message": error_message,
            },
            message=(
                "Application saved, "
                "but OA request failed."
            ),
            code=RetCode.SERVER_ERROR,
        )

def generate_oa_request_id():
    return f"oa_req_{uuid.uuid4().hex[:16]}"

# 获取OA返回
@manager.route(
    "/oa/approval/create",
    methods=["POST"]
)
async def create_approval_request():
    """
    模拟 OA 创建审批单。

    当前逻辑：
    1. 校验 app_id
    2. 校验参数
    3. 根据业务 ID 做幂等
    4. 写入 OA 主表
    5. 写入一级审批任务
    6. 返回 oa_request_id
    """

    import os

    oa_secret = os.environ.get("OA_SECRET", "")
    expected_app_id = os.environ.get(
        "OA_APP_ID",
        "ragflow"
    )

    data = await request.get_json()

    if not data:
        return get_json_result(
            data=False,
            message="Empty request body.",
            code=RetCode.ARGUMENT_ERROR,
        )

    # app_id 校验
    if data.get("app_id") != expected_app_id:
        return get_json_result(
            data=False,
            message="Invalid app_id.",
            code=RetCode.AUTHENTICATION_ERROR,
        )

    # 签名校验
    recv_signature = request.headers.get(
        "X-OA-Signature",
        ""
    )

    # if oa_secret:
    #     expected_signature = make_oa_signature(
    #         data,
    #         oa_secret
    #     )

    #     if recv_signature != expected_signature:
    #         return get_json_result(
    #             data=False,
    #             message="Invalid signature.",
    #             code=RetCode.AUTHENTICATION_ERROR,
    #         )

    business_type = data.get("business_type")
    business_id = data.get("business_id")

    # 兼容当前接口，也可以使用 batch_id
    batch_id = data.get("batch_id") or business_id

    reason = data.get("reason", "")
    applicant = data.get("applicant") or {}
    approver = data.get("approver") or {}
    business_data = data.get("data") or {}
    callback_url = data.get("callback_url")

    if business_type != "kb_create":
        return get_json_result(
            data=False,
            message="Unsupported business_type.",
            code=RetCode.ARGUMENT_ERROR,
        )

    if not batch_id:
        return get_json_result(
            data=False,
            message="business_id is required.",
            code=RetCode.ARGUMENT_ERROR,
        )

    if not applicant.get("user_id"):
        return get_json_result(
            data=False,
            message="applicant.user_id is required.",
            code=RetCode.ARGUMENT_ERROR,
        )

    if not business_data.get("kb_name"):
        return get_json_result(
            data=False,
            message="data.kb_name is required.",
            code=RetCode.ARGUMENT_ERROR,
        )

    if not callback_url:
        return get_json_result(
            data=False,
            message="callback_url is required.",
            code=RetCode.ARGUMENT_ERROR,
        )

    # 幂等查询
    existed = (
        OAApplication
        .select()
        .where(
            (OAApplication.source_system == "knowledge")
            & (OAApplication.business_type == business_type)
            & (OAApplication.business_id == batch_id)
        )
        .first()
    )

    if existed:
        return get_json_result(
            data={
                "oa_request_id": existed.oa_request_id,
                "business_id": existed.business_id,
                "status": existed.status,
            }
        )

    oa_request_id = generate_oa_request_id()
    now = int(time.time())

    # try:
    with DB.atomic():
        OAApplication.create(
            oa_request_id=oa_request_id,
            app_id=data.get("app_id"),
            source_system="knowledge",
            business_type=business_type,
            business_id=batch_id,
            reason=reason,
            applicant_user_id=applicant.get("user_id"),
            applicant_user_name=applicant.get("user_name"),
            approver_user_id=approver.get("user_id"),
            approver_user_name=approver.get("user_name"),
            data=json.dumps(
                business_data,
                ensure_ascii=False
            ),
            status="pending",
            callback_url=callback_url,
            callback_status="pending",
            created_time=now,
            updated_time=now,
        )

        # 创建一级审批任务
        if approver.get("user_id"):
            OAApprovalTask.create(
                oa_request_id=oa_request_id,
                level=1,
                approver_user_id=approver.get("user_id"),
                approver_user_name=approver.get("user_name"),
                status="pending",
                created_time=now,
                updated_time=now,
            )

    return get_json_result(
        data={
            "oa_request_id": oa_request_id,
            "business_id": batch_id,
            "status": "pending",
        }
    )

    # except Exception as e:
    #     # 如果是并发请求导致唯一键冲突，可以再次查询并返回已有数据
    #     existed = (
    #         OAApplication
    #         .select()
    #         .where(
    #             (OAApplication.source_system == "knowledge")
    #             & (OAApplication.business_type == business_type)
    #             & (OAApplication.business_id == batch_id)
    #         )
    #         .first()
    #     )

    #     if existed:
    #         return get_json_result(
    #             data={
    #                 "oa_request_id": existed.oa_request_id,
    #                 "business_id": existed.business_id,
    #                 "status": existed.status,
    #             }
    #         )

    #     return server_error_response(e)

# 同意
@manager.route(
    "/oa/approval/<oa_request_id>/approve",
    methods=["POST"]
)
async def approve_approval_request(oa_request_id):
    """
    模拟 OA 审批通过。
    """
    data = await request.get_json() or {}

    comment = data.get(
        "comment",
        "同意"
    )

    approver = data.get("approver") or {}

    oa_application = (
        OAApplication
        .select()
        .where(
            OAApplication.oa_request_id == oa_request_id
        )
        .first()
    )

    if not oa_application:
        return get_json_result(
            data=False,
            message="OA request not found.",
            code=RetCode.NOT_FOUND,
        )

    approver_user_id = (
        approver.get("user_id")
        or oa_application.approver_user_id
    )

    approver_user_name = (
        approver.get("user_name")
        or oa_application.approver_user_name
    )

    now = int(time.time())

    # 只允许 pending 被处理
    updated_count = (
        OAApplication
        .update(
            status="approved",
            approve_comment=comment,
            approve_time=now,
            approver_user_id=approver_user_id,
            approver_user_name=approver_user_name,
            updated_time=now,
        )
        .where(
            (OAApplication.oa_request_id == oa_request_id)
            & (OAApplication.status == "pending")
        )
        .execute()
    )

    # 已经是 approved，视为幂等
    if updated_count == 0:
        current = (
            OAApplication
            .select()
            .where(
                OAApplication.oa_request_id == oa_request_id
            )
            .first()
        )

        if current and current.status == "approved":
            return get_json_result(
                data={
                    "oa_request_id": oa_request_id,
                    "status": "approved",
                    "message": "Already approved.",
                }
            )

        return get_json_result(
            data=False,
            message="Request has already been processed.",
            code=RetCode.ARGUMENT_ERROR,
        )

    # 更新审批任务
    (
        OAApprovalTask
        .update(
            status="approved",
            comment=comment,
            processed_time=now,
            updated_time=now,
        )
        .where(
            (OAApprovalTask.oa_request_id == oa_request_id)
            & (OAApprovalTask.status == "pending")
        )
        .execute()
    )

    # 从 OA 主表中取回调信息
    oa_application = (
        OAApplication
        .select()
        .where(
            OAApplication.oa_request_id == oa_request_id
        )
        .first()
    )

    callback_payload = {
        "oa_request_id": oa_application.oa_request_id,
        "business_type": oa_application.business_type,
        "business_id": oa_application.business_id,
        "result": "approved",
        "comment": comment,
        "approver": {
            "user_id": approver_user_id,
            "user_name": approver_user_name,
        },
        "timestamp": now,
    }

    # 回调知识库
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                oa_application.callback_url,
                json=callback_payload,
                headers={
                    "Content-Type": "application/json",
                },
            )

        if response.status_code != 200:
            raise RuntimeError(
                f"Knowledge callback http error: "
                f"{response.status_code}"
            )

        callback_result = response.json()

        if callback_result.get("code") != 200:
            raise RuntimeError(
                callback_result.get(
                    "message",
                    "Knowledge callback failed"
                )
            )

        OAApplication.update(
            callback_status="success",
            callback_error=None,
            callback_time=int(time.time()),
            updated_time=int(time.time()),
        ).where(
            OAApplication.oa_request_id == oa_request_id
        ).execute()

    except Exception as e:
        OAApplication.update(
            callback_status="failed",
            callback_error=str(e),
            callback_retry_count=(
                OAApplication.callback_retry_count + 1
            ),
            callback_time=int(time.time()),
            updated_time=int(time.time()),
        ).where(
            OAApplication.oa_request_id == oa_request_id
        ).execute()

        # 注意：OA 审批已经成功，不能因为回调失败而回滚审批状态
        return get_json_result(
            data={
                "oa_request_id": oa_request_id,
                "status": "approved",
                "callback_status": "failed",
            },
            message="Approved, but callback failed.",
            code=RetCode.SERVER_ERROR,
        )

    return get_json_result(
        data={
            "oa_request_id": oa_request_id,
            "status": "approved",
            "callback_status": "success",
        }
    )

# 拒绝
@manager.route(
    "/oa/approval/<oa_request_id>/reject",
    methods=["POST"]
)
async def reject_approval_request(oa_request_id):
    """
    模拟 OA 审批拒绝。
    """
    data = await request.get_json() or {}

    comment = data.get(
        "comment",
        "不同意"
    )

    approver = data.get("approver") or {}

    oa_application = (
        OAApplication
        .select()
        .where(
            OAApplication.oa_request_id == oa_request_id
        )
        .first()
    )

    if not oa_application:
        return get_json_result(
            data=False,
            message="OA request not found.",
            code=RetCode.NOT_FOUND,
        )

    approver_user_id = (
        approver.get("user_id")
        or oa_application.approver_user_id
    )

    approver_user_name = (
        approver.get("user_name")
        or oa_application.approver_user_name
    )

    now = int(time.time())

    updated_count = (
        OAApplication
        .update(
            status="rejected",
            approve_comment=comment,
            approve_time=now,
            approver_user_id=approver_user_id,
            approver_user_name=approver_user_name,
            updated_time=now,
        )
        .where(
            (OAApplication.oa_request_id == oa_request_id)
            & (OAApplication.status == "pending")
        )
        .execute()
    )

    if updated_count == 0:
        current = (
            OAApplication
            .select()
            .where(
                OAApplication.oa_request_id == oa_request_id
            )
            .first()
        )

        if current and current.status == "rejected":
            return get_json_result(
                data={
                    "oa_request_id": oa_request_id,
                    "status": "rejected",
                    "message": "Already rejected.",
                }
            )

        return get_json_result(
            data=False,
            message="Request has already been processed.",
            code=RetCode.ARGUMENT_ERROR,
        )

    (
        OAApprovalTask
        .update(
            status="rejected",
            comment=comment,
            processed_time=now,
            updated_time=now,
        )
        .where(
            (OAApprovalTask.oa_request_id == oa_request_id)
            & (OAApprovalTask.status == "pending")
        )
        .execute()
    )

    callback_payload = {
        "oa_request_id": oa_application.oa_request_id,
        "business_type": oa_application.business_type,
        "business_id": oa_application.business_id,
        "result": "rejected",
        "comment": comment,
        "approver": {
            "user_id": approver_user_id,
            "user_name": approver_user_name,
        },
        "timestamp": now,
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                oa_application.callback_url,
                json=callback_payload,
                headers={
                    "Content-Type": "application/json",
                },
            )

        if response.status_code != 200:
            raise RuntimeError(
                f"Knowledge callback http error: "
                f"{response.status_code}"
            )

        callback_result = response.json()

        if callback_result.get("code") != 200:
            raise RuntimeError(
                callback_result.get(
                    "message",
                    "Knowledge callback failed"
                )
            )

        OAApplication.update(
            callback_status="success",
            callback_error=None,
            callback_time=int(time.time()),
            updated_time=int(time.time()),
        ).where(
            OAApplication.oa_request_id == oa_request_id
        ).execute()

    except Exception as e:
        OAApplication.update(
            callback_status="failed",
            callback_error=str(e),
            callback_retry_count=(
                OAApplication.callback_retry_count + 1
            ),
            callback_time=int(time.time()),
            updated_time=int(time.time()),
        ).where(
            OAApplication.oa_request_id == oa_request_id
        ).execute()

        return get_json_result(
            data={
                "oa_request_id": oa_request_id,
                "status": "rejected",
                "callback_status": "failed",
            },
            message="Rejected, but callback failed.",
            code=RetCode.SERVER_ERROR,
        )

    return get_json_result(
        data={
            "oa_request_id": oa_request_id,
            "status": "rejected",
            "callback_status": "success",
        }
    )


def get_oa_application_kb_name(oa_application):
    """
    从 OAApplicationkb.data JSON 中获取知识库名称。

    OA 表中保存的数据结构类似：

    {
        "kb_name": "测试知识库",
        "applicant_dept": {
            "dept_code": "dept-001",
            "dept_name": "工艺研究一室"
        }
    }
    """

    raw_data = getattr(
        oa_application,
        "data",
        None,
    )

    if not raw_data:
        return ""

    # 如果 Peewee 已经返回 dict
    if isinstance(raw_data, dict):
        business_data = raw_data

    else:
        try:
            business_data = json.loads(
                str(raw_data)
            )

        except (
            TypeError,
            ValueError,
            json.JSONDecodeError,
        ):
            print(
                "[OA TODO] OA application.data "
                "不是合法 JSON：",
                {
                    "oa_request_id": getattr(
                        oa_application,
                        "oa_request_id",
                        None,
                    ),
                    "data": raw_data,
                },
            )
            return ""

    if not isinstance(business_data, dict):
        return ""

    kb_name = (
        business_data.get("kb_name")
        or business_data.get("name")
        or ""
    )

    return str(kb_name).strip()

# ragflow侧回调
@manager.route(
    "/oa/approval/callback",
    methods=["POST"]
)
async def oa_approval_callback():
    """
    OA 审批完成后回调知识库。

    approved：
        更新审批状态
        真正创建知识库

    rejected：
        更新审批状态
        不创建知识库
    """
    data = await request.get_json()

    if not data:
        return get_json_result(
            data=False,
            message="Empty request body.",
            code=RetCode.ARGUMENT_ERROR,
        )

    oa_request_id = data.get("oa_request_id")
    business_id = data.get("business_id")
    result = data.get("result")
    comment = data.get("comment")
    approver = data.get("approver") or {}
    timestamp = data.get("timestamp") or int(time.time())

    if not oa_request_id:
        return get_json_result(
            data=False,
            message="oa_request_id is required.",
            code=RetCode.ARGUMENT_ERROR,
        )

    if result not in ("approved", "rejected"):
        return get_json_result(
            data=False,
            message="Invalid result.",
            code=RetCode.ARGUMENT_ERROR,
        )

    # 可以同时使用 business_id 和 oa_request_id 查询
    apply_record = (
        KnowledgeBaseCreateApply
        .select()
        .where(
            KnowledgeBaseCreateApply.oa_request_id
            == oa_request_id
        )
        .first()
    )

    if not apply_record and business_id:
        apply_record = (
            KnowledgeBaseCreateApply
            .select()
            .where(
                KnowledgeBaseCreateApply.business_id
                == business_id
            )
            .first()
        )

    if not apply_record:
        return get_json_result(
            data=False,
            message="Application not found.",
            code=RetCode.NOT_FOUND,
        )

    # 校验 OA 回调中的 business_id
    if (
        business_id
        and apply_record.business_id != business_id
    ):
        return get_json_result(
            data=False,
            message="business_id does not match.",
            code=RetCode.ARGUMENT_ERROR,
        )

    now = int(time.time())

    # 已经处理过的相同结果，直接幂等返回成功
    if apply_record.status == result:
        return get_json_result(
            data={
                "business_id": apply_record.business_id,
                "oa_request_id": oa_request_id,
                "status": apply_record.status,
                "message": "Callback already processed.",
            }
        )

    # 防止 approved 和 rejected 相互覆盖
    if apply_record.status != "pending":
        return get_json_result(
            data=False,
            message=(
                f"Invalid status transition: "
                f"{apply_record.status} -> {result}"
            ),
            code=RetCode.ARGUMENT_ERROR,
        )

    # 审批拒绝：只更新申请状态，不创建知识库
    if result == "rejected":
        updated_count = (
            KnowledgeBaseCreateApply
            .update(
                status="rejected",
                approver_id=approver.get("user_id"),
                approver_name=approver.get("user_name"),
                approve_comment=comment,
                approve_time=timestamp,
                callback_time=now,
                updated_time=now,
            )
            .where(
                (KnowledgeBaseCreateApply.business_id
                 == apply_record.business_id)
                & (KnowledgeBaseCreateApply.status
                   == "pending")
            )
            .execute()
        )

        if updated_count == 0:
            return get_json_result(
                data=False,
                message="Application has already been processed.",
                code=RetCode.ARGUMENT_ERROR,
            )

        return get_json_result(
            data={
                "business_id": apply_record.business_id,
                "oa_request_id": oa_request_id,
                "status": "rejected",
            }
        )

    # 审批通过：
    # 先抢占创建权，避免 OA 重复回调导致重复建库
    updated_count = (
        KnowledgeBaseCreateApply
        .update(
            status="approved",
            create_status="processing",
            approver_id=approver.get("user_id"),
            approver_name=approver.get("user_name"),
            approve_comment=comment,
            approve_time=timestamp,
            callback_time=now,
            updated_time=now,
        )
        .where(
            (KnowledgeBaseCreateApply.business_id
             == apply_record.business_id)
            & (KnowledgeBaseCreateApply.status
               == "pending")
            & (KnowledgeBaseCreateApply.create_status
               == "pending")
        )
        .execute()
    )

    if updated_count == 0:
        # 可能是并发回调，检查当前状态
        current = (
            KnowledgeBaseCreateApply
            .select()
            .where(
                KnowledgeBaseCreateApply.business_id
                == apply_record.business_id
            )
            .first()
        )

        if current and current.create_status in (
            "processing",
            "success",
        ):
            return get_json_result(
                data={
                    "business_id": current.business_id,
                    "oa_request_id": current.oa_request_id,
                    "status": current.status,
                    "create_status": current.create_status,
                    "created_kb_id": current.created_kb_id,
                }
            )

        return get_json_result(
            data=False,
            message="Application has already been processed.",
            code=RetCode.ARGUMENT_ERROR,
        )

    # 查询最新申请记录，获取原始 request_data
    apply_record = (
        KnowledgeBaseCreateApply
        .select()
        .where(
            KnowledgeBaseCreateApply.business_id
            == apply_record.business_id
        )
        .first()
    )

    try:
        original_request = json.loads(
            apply_record.request_data
        )

        # 不能完全信任原始请求中的 tenant_id。
        # 如果 tenant_id 应该是当前申请用户，需要由服务端重新赋值。
        original_request["tenant_id"] = apply_record.user_id

        create_name = original_request.pop(
            "name",
            apply_record.kb_name
        )

        parser_id = original_request.pop(
            "parser_id",
            None
        )

        # 防止客户端提交不应该进入创建逻辑的字段
        original_request.pop("business_id", None)
        original_request.pop("oa_request_id", None)
        original_request.pop("reason", None)

        e, res = KnowledgebaseService.create_with_name(
            name=create_name,
            tenant_id=apply_record.user_id,
            parser_id=parser_id,
            **original_request
        )

        if not e:
            raise RuntimeError(
                "KnowledgebaseService.create_with_name failed"
            )

        if not KnowledgebaseService.save(**res):
            raise RuntimeError(
                "KnowledgebaseService.save failed"
            )

        created_kb_id = res["id"]

        KnowledgeBaseCreateApply.update(
            create_status="success",
            created_kb_id=created_kb_id,
            create_error=None,
            updated_time=int(time.time()),
        ).where(
            KnowledgeBaseCreateApply.business_id
            == apply_record.business_id
        ).execute()

        return get_json_result(
            data={
                "business_id": apply_record.business_id,
                "oa_request_id": oa_request_id,
                "status": "approved",
                "create_status": "success",
                "kb_id": created_kb_id,
            }
        )

    except Exception as e:
        KnowledgeBaseCreateApply.update(
            create_status="failed",
            create_error=str(e),
            updated_time=int(time.time()),
        ).where(
            KnowledgeBaseCreateApply.business_id
            == apply_record.business_id
        ).execute()

        # 返回失败后，OA 可以根据 callback_status 进行重试。
        # 但这里需要注意：如果审批已是 approved，重复回调不能再次创建。
        return get_json_result(
            data={
                "business_id": apply_record.business_id,
                "oa_request_id": oa_request_id,
                "status": "approved",
                "create_status": "failed",
                "message": str(e),
            },
            message="Approval succeeded, but knowledge base creation failed.",
            code=RetCode.SERVER_ERROR,
        )

@manager.route(
    "/oa/approval/tasks/todo",
    methods=["GET"],
)
@login_required
async def get_oa_todo_tasks():
    """
    获取当前用户的 OA 待办审批任务。
    """

    current_user_id = str(
        getattr(
            current_user,
            "id",
            None,
        )
        or ""
    ).strip()

    if not current_user_id:
        return get_json_result(
            data=False,
            message="Current user id is required.",
            code=RetCode.AUTHENTICATION_ERROR,
        )

    try:
        tasks = (
            OAApprovalTask
            .select(
                OAApprovalTask,
                OAApplication,
            )
            .join(
                OAApplication,
                on=(
                    OAApprovalTask.oa_request_id
                    == OAApplication.oa_request_id
                ),
            )
            .where(
                (
                    OAApprovalTask.approver_user_id
                    == current_user_id
                )
                & (
                    OAApprovalTask.status
                    == "pending"
                )
                & (
                    OAApplication.status
                    == "pending"
                )
            )
            .order_by(
                OAApprovalTask.created_time.desc()
            )
        )

        result = []

        for task in tasks:
            oa_application = task.oaapplicationkb

            # 从 data JSON 中读取 kb_name
            kb_name = get_oa_application_kb_name(
                oa_application
            )

            item = {
                "task_id": getattr(
                    task,
                    "id",
                    None,
                ),
                "oa_request_id": getattr(
                    oa_application,
                    "oa_request_id",
                    None,
                ),
                "business_id": getattr(
                    oa_application,
                    "business_id",
                    None,
                ),
                "business_type": getattr(
                    oa_application,
                    "business_type",
                    None,
                ),
                "kb_name": kb_name,
                "reason": getattr(
                    oa_application,
                    "reason",
                    "",
                ),
                "applicant_user_id": getattr(
                    oa_application,
                    "applicant_user_id",
                    None,
                ),
                "applicant_user_name": getattr(
                    oa_application,
                    "applicant_user_name",
                    None,
                ),
                "approver_user_id": getattr(
                    oa_application,
                    "approver_user_id",
                    None,
                ),
                "approver_user_name": getattr(
                    oa_application,
                    "approver_user_name",
                    None,
                ),
                "status": getattr(
                    oa_application,
                    "status",
                    None,
                ),
                "task_status": getattr(
                    task,
                    "status",
                    None,
                ),
                "created_time": getattr(
                    oa_application,
                    "created_time",
                    None,
                ),
                "updated_time": getattr(
                    oa_application,
                    "updated_time",
                    None,
                ),
            }

            # 读取申请部门
            raw_data = getattr(
                oa_application,
                "data",
                None,
            )

            try:
                if isinstance(raw_data, dict):
                    business_data = raw_data
                else:
                    business_data = json.loads(
                        str(raw_data or "{}")
                    )

            except (
                TypeError,
                ValueError,
                json.JSONDecodeError,
            ):
                business_data = {}

            applicant_dept = (
                business_data.get(
                    "applicant_dept"
                )
                or {}
            )

            item["applicant_dept"] = {
                "dept_code": applicant_dept.get(
                    "dept_code"
                ),
                "dept_name": applicant_dept.get(
                    "dept_name"
                ),
            }

            result.append(item)

        return get_json_result(
            data=result,
            message="success",
            code=RetCode.SUCCESS,
        )

    except Exception as e:
        print(
            "[OA TODO] 获取 OA 待办失败：",
            repr(e),
        )
        # print(traceback.format_exc())

        return get_json_result(
            data=False,
            message=(
                "Get OA todo tasks failed: "
                f"{str(e)}"
            ),
            code=RetCode.SERVER_ERROR,
        )
# @manager.route('/create', methods=['post'])  # noqa: F821
# @login_required
# @validate_request("name")
# async def create():
#     req = await get_request_json()
#     print('DEBUG: req content follows')
#     print(req)

#     # 组id --> 全局参考库用户
#     cfg_map = getattr(settings, "GROUP_REFERENCE_TENANT_MAP", {}) or {}
#     # 这个库 所属的组id
#     tids = {tid for gid, tid in cfg_map.items()}
#     public_id = settings.REFERENCE_TENANT_ID



#     # 如果是管理员或者参考库的用户(只有管理员和公共库可以创建)
#     # if AdminUser.query(user_id=current_user.id) or current_user.id in tids or current_user.id == public_id:
#     e, res = KnowledgebaseService.create_with_name(
#         name = req.pop("name", None),
#         tenant_id = current_user.id,
#         parser_id = req.pop("parser_id", None),
#         **req
#     )

#     if not e:
#         return res

#     try:
#         if not KnowledgebaseService.save(**res):
#             return get_data_error_result()
#         return get_json_result(data={"kb_id":res["id"]})
#     except Exception as e:
#         return server_error_response(e)
        
#     # ---------------- 新增的代码块 ----------------
#     # else:
#     #     print("暂无权限")
#     #     return get_data_error_result(message="抱歉！当前用户暂无权限创建知识库")


@manager.route('/update', methods=['post'])  # noqa: F821
@login_required
@validate_request("kb_id", "name", "description", "parser_id")
@not_allowed_parameters("id", "tenant_id", "created_by", "create_time", "update_time", "create_date", "update_date", "created_by")
async def update():
    req = await get_request_json()

    if "group_id" in req:
        del req["group_id"]

    if "group_name" in req:
        del req["group_name"]

    if "color" in req:
        del req["color"]

    if not isinstance(req["name"], str):
        return get_data_error_result(message="Dataset name must be string.")
    if req["name"].strip() == "":
        return get_data_error_result(message="Dataset name can't be empty.")
    if len(req["name"].encode("utf-8")) > DATASET_NAME_LIMIT:
        return get_data_error_result(
            message=f"Dataset name length is {len(req['name'])} which is large than {DATASET_NAME_LIMIT}")
    req["name"] = req["name"].strip()

    try:
        # 检查是否有写入权限
        if not KnowledgebaseService.writable(req["kb_id"], current_user.id):
            return get_json_result(
                data=False,
                message='Only owner of dataset authorized for this operation.',
                code=RetCode.OPERATING_ERROR,
            )

        e, kb = KnowledgebaseService.get_by_id(req["kb_id"])
        if not e:
            return get_data_error_result(
                message="Can't find this dataset!")

        if req["name"].lower() != kb.name.lower() \
                and len(
            KnowledgebaseService.query(name=req["name"], tenant_id=kb.tenant_id, status=StatusEnum.VALID.value)) >= 1:
            return get_data_error_result(
                message="Duplicated dataset name.")

        
        del req["kb_id"]
        connectors = []
        if "connectors" in req:
            connectors = req["connectors"]
            del req["connectors"]
        
        org_name = kb.name
        if not KnowledgebaseService.update_by_id(kb.id, req):
            return get_data_error_result()
        
        from peewee import DoesNotExist
        # 获取到知识库的原始相关信息
        if org_name != req['name']:
            print(kb.tenant_id)
            # 通过这三个字段精准定位一行数据
            print(org_name)
            try:
                file_record = File.get(
                    File.name == org_name,
                    File.tenant_id == kb.tenant_id,
                    # File.source_type == FileSource.KNOWLEDGEBASE
                )
                file_record.name = req['name']
                file_record.save()
            except DoesNotExist:
                # 找不到记录说明没权限或不存在，直接跳过即可
                pass
            try:        
                file_record2 = File_Admin.get(
                    File_Admin.name == org_name,
                    File_Admin.tenant_id == kb.tenant_id,
                    # File_Admin.source_type == FileSource.KNOWLEDGEBASE
                )
                file_record2.name = req['name']
                file_record2.save()
            except DoesNotExist:
                # 找不到记录说明没权限或不存在，直接跳过即可
                pass
            try:
                file_record3 = File_Group.get(
                    File_Group.name == org_name,
                    File_Group.tenant_id == kb.tenant_id,
                    # File_Group.source_type == FileSource.KNOWLEDGEBASE
                )

                # 👇 1. 将新名字赋值给 file_record
                
                
                file_record3.name = req['name']
                # 👇 2. 调用 save() 方法，将修改同步到数据库


                file_record3.save()
            except DoesNotExist:
                # 找不到记录说明没权限或不存在，直接跳过即可
                pass
            print(f"文件记录同步更新成功，新名字为: {req['name']}")



        if kb.pagerank != req.get("pagerank", 0):
            if req.get("pagerank", 0) > 0:
                await asyncio.to_thread(
                    settings.docStoreConn.update,
                    {"kb_id": kb.id},
                    {PAGERANK_FLD: req["pagerank"]},
                    search.index_name(kb.tenant_id),
                    kb.id,
                )
            else:
                # Elasticsearch requires PAGERANK_FLD be non-zero!
                await asyncio.to_thread(
                    settings.docStoreConn.update,
                    {"exists": PAGERANK_FLD},
                    {"remove": PAGERANK_FLD},
                    search.index_name(kb.tenant_id),
                    kb.id,
                )

        e, kb = KnowledgebaseService.get_by_id(kb.id)
        if not e:
            return get_data_error_result(
                message="Database error (Knowledgebase rename)!")
        errors = Connector2KbService.link_connectors(kb.id, [conn for conn in connectors], current_user.id)
        if errors:
            logging.error("Link KB errors: ", errors)
        kb = kb.to_dict()
        kb.update(req)
        kb["connectors"] = connectors

        return get_json_result(data=kb)
    except Exception as e:
        return server_error_response(e)


# @manager.route('/detail', methods=['GET'])  # noqa: F821
# @login_required
# def detail():
#     kb_id = request.args["kb_id"]
#     try:
#         if not KnowledgebaseService.accessible(kb_id, current_user.id):
#             return get_json_result(
#                 data=False, message='Only owner of dataset authorized for this operation.',
#                 code=RetCode.OPERATING_ERROR)

#         kb = KnowledgebaseService.get_detail(kb_id)
#         if not kb:
#             return get_json_result(data=False, message='Knowledgebase not found', code=RetCode.DATA_NOT_FOUND)

#         kb["size"] = DocumentService.get_total_size_by_kb_id(kb_id=kb["id"],keywords="", run_status=[], types=[])
#         kb["connectors"] = Connector2KbService.list_connectors(kb_id)

#         for key in ["graphrag_task_finish_at", "raptor_task_finish_at", "mindmap_task_finish_at"]:
#             if finish_at := kb.get(key):
#                 kb[key] = finish_at.strftime("%Y-%m-%d %H:%M:%S")

#         if AdminUser.query(user_id=current_user.id):
#             kb['is_admin'] = True
#         return get_json_result(data=kb)
#     except Exception as e:
#         return server_error_response(e)

# @manager.route('/detail', methods=['GET'])  # noqa: F821
# @login_required
# def detail():
#     kb_id = request.args["kb_id"]

#     try:
#         # if not KnowledgebaseService.accessible(kb_id, current_user.id):
#         #     return get_json_result(
#         #         data=False,
#         #         message='Only owner of dataset authorized for this operation.',
#         #         code=RetCode.OPERATING_ERROR,
#         #     )

#         kb = KnowledgebaseService.get_detail(kb_id)
#         if not kb:
#             return get_json_result(
#                 data=False,
#                 message='Knowledgebase not found',
#                 code=RetCode.DATA_NOT_FOUND,
#             )

#         # 颜色逻辑开始
#         tenant_id = kb.get("tenant_id")

#         cfg_map = getattr(settings, "GROUP_REFERENCE_TENANT_MAP", {}) or {}
#         reversed_map = {v: k for k, v in cfg_map.items()}

#         public_id = settings.REFERENCE_TENANT_ID

#         # 默认颜色：一级管理员/普通库
#         kb["color"] = 99

#         # 全局参考库
#         if tenant_id == public_id:
#             kb["group_name"] = "全局参考库"
#             kb["color"] = 3

#         # 一级管理员创建
#         if AdminUser.query(user_id=tenant_id, role_level=1):
#             kb["color"] = 1

#         # 二级管理员创建
#         if AdminUser.query(user_id=tenant_id, role_level=2):
#             kb["color"] = 2

#         # 分组参考库
#         if tenant_id in reversed_map:
#             group_id = reversed_map[tenant_id]

#             group_obj = Group.select(Group.group_name).where(
#                 Group.group_id == group_id
#             ).first()

#             kb["group_id"] = group_id
#             kb["group_name"] = group_obj.group_name if group_obj else None
#             kb["color"] = 3

            
#         # 颜色逻辑结束

#         kb["size"] = DocumentService.get_total_size_by_kb_id(
#             kb_id=kb["id"],
#             keywords="",
#             run_status=[],
#             types=[],
#         )

#         kb["connectors"] = Connector2KbService.list_connectors(kb_id)
#         print(kb['color'])

#         for key in [
#             "graphrag_task_finish_at",
#             "raptor_task_finish_at",
#             "mindmap_task_finish_at",
#         ]:
#             if finish_at := kb.get(key):
#                 kb[key] = finish_at.strftime("%Y-%m-%d %H:%M:%S")

#         if AdminUser.query(user_id=current_user.id):
#             kb['is_admin'] = True

#         return get_json_result(data=kb)

#     except Exception as e:
#         return server_error_response(e)

import time


@manager.route('/detail', methods=['GET'])  # noqa: F821
@login_required
def detail():
    """
    获取知识库详情。

    说明：
    - 全局参考库统一 color=3；
    - 部门参考库统一 color=3；
    - 一级管理员创建的库 color=1；
    - 普通知识库 color=99；
    - 已移除二级管理员判断；
    - 尽量减少重复查询；
    - 增加分段耗时日志，方便定位真正慢的部分。
    """

    request_start = time.perf_counter()

    kb_id = request.args.get("kb_id")

    if not kb_id:
        return get_json_result(
            data=False,
            message="kb_id is required",
            code=RetCode.ARGUMENT_ERROR,
        )

    kb_id = str(kb_id).strip()

    try:
        # --------------------------------------------------------------
        # 1. 查询知识库基本信息
        # --------------------------------------------------------------
        start = time.perf_counter()

        # 建议恢复权限校验。
        #
        # 注意：如果你的 accessible() 还是旧的 UserGroup 权限逻辑，
        # 需要同步改成新的角色/部门权限逻辑。
        #
        # if not KnowledgebaseService.accessible(
        #     kb_id,
        #     current_user.id,
        # ):
        #     return get_json_result(
        #         data=False,
        #         message="没有查看该知识库的权限",
        #         code=RetCode.OPERATING_ERROR,
        #     )

        kb = KnowledgebaseService.get_detail(kb_id)

        detail_cost = time.perf_counter() - start

        if not kb:
            return get_json_result(
                data=False,
                message="Knowledgebase not found",
                code=RetCode.DATA_NOT_FOUND,
            )

        # 防止 Service 返回的对象不是普通 dict。
        kb = dict(kb)

        tenant_id = str(
            kb.get("tenant_id") or ""
        ).strip()

        kb["color"] = 99
        kb["group_id"] = None
        kb["group_name"] = None

        # --------------------------------------------------------------
        # 2. 处理全局参考库和部门参考库配置
        # --------------------------------------------------------------
        start = time.perf_counter()

        reference_tenant_id = getattr(
            settings,
            "REFERENCE_TENANT_ID",
            None,
        )

        reference_tenant_id = (
            str(reference_tenant_id).strip()
            if reference_tenant_id
            else None
        )

        group_reference_map = getattr(
            settings,
            "GROUP_REFERENCE_TENANT_MAP",
            {},
        ) or {}

        # 配置中的 key/value 统一转成字符串，避免 UUID/string 类型比较失败。
        reversed_reference_map = {}

        for department_id, reference_id in (
            group_reference_map.items()
        ):
            if reference_id is None:
                continue

            reference_id = str(
                reference_id
            ).strip()

            department_id = str(
                department_id
            ).strip()

            if reference_id and department_id:
                reversed_reference_map[
                    reference_id
                ] = department_id

        department_id = reversed_reference_map.get(
            tenant_id
        )

        # --------------------------------------------------------------
        # 3. 处理知识库颜色和部门信息
        # --------------------------------------------------------------
        #
        # 优先级：
        #   全局参考库 > 部门参考库 > 一级管理员库 > 普通库
        #
        # 这样可以避免一个 tenant_id 同时被配置为参考库和管理员库时，
        # 后面的管理员判断覆盖前面的 color=3。
        # --------------------------------------------------------------
        if (
            reference_tenant_id
            and tenant_id == reference_tenant_id
        ):
            kb["group_name"] = "全局参考库"
            kb["color"] = 3

        elif department_id:
            kb["group_id"] = department_id
            kb["color"] = 3

            # 只有确定是部门参考库时才查询 Group。
            # 普通知识库不会执行这条 SQL。
            group_obj = (
                Group
                .select(Group.group_name)
                .where(
                    Group.group_id == department_id
                )
                .first()
            )

            if group_obj:
                kb["group_name"] = (
                    group_obj.group_name
                )

        else:
            # 只保留一级管理员逻辑，移除二级管理员查询。
            if AdminUser.query(
                user_id=tenant_id,
                role_level=1,
            ):
                kb["color"] = 1

        color_cost = time.perf_counter() - start

        # --------------------------------------------------------------
        # 4. 查询文档总大小
        # --------------------------------------------------------------
        start = time.perf_counter()

        kb["size"] = (
            DocumentService
            .get_total_size_by_kb_id(
                kb_id=kb.get("id") or kb_id,
                keywords="",
                run_status=[],
                types=[],
            )
        )

        size_cost = time.perf_counter() - start

        # --------------------------------------------------------------
        # 5. 查询连接器
        # --------------------------------------------------------------
        start = time.perf_counter()

        kb["connectors"] = (
            Connector2KbService
            .list_connectors(kb_id)
        )

        connector_cost = time.perf_counter() - start

        # --------------------------------------------------------------
        # 6. 格式化时间字段
        # --------------------------------------------------------------
        start = time.perf_counter()

        for key in (
            "graphrag_task_finish_at",
            "raptor_task_finish_at",
            "mindmap_task_finish_at",
        ):
            finish_at = kb.get(key)

            if not finish_at:
                continue

            if hasattr(finish_at, "strftime"):
                kb[key] = finish_at.strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            else:
                kb[key] = str(finish_at)

        # 当前登录用户是否是管理员。
        #
        # 这里保留原逻辑：AdminUser.query(user_id)
        # 如果你的业务只认一级超级管理员，建议加 role_level=1。
        kb["is_admin"] = bool(
            AdminUser.query(
                user_id=str(current_user.id),
                role_level=1,
            )
        )

        format_cost = time.perf_counter() - start

        total_cost = (
            time.perf_counter()
            - request_start
        )

        print(
            "[KB DETAIL] "
            f"kb_id={kb_id}, "
            f"basic={detail_cost:.4f}s, "
            f"color={color_cost:.4f}s, "
            f"size={size_cost:.4f}s, "
            f"connectors={connector_cost:.4f}s, "
            f"format={format_cost:.4f}s, "
            f"total={total_cost:.4f}s"
        )

        return get_json_result(
            data=kb
        )

    except Exception as e:
        total_cost = (
            time.perf_counter()
            - request_start
        )

        print(
            "[KB DETAIL] failed "
            f"kb_id={kb_id}, "
            f"total={total_cost:.4f}s, "
            f"error={repr(e)}"
        )

        return server_error_response(e)


@manager.route('/list', methods=['POST'])  # noqa: F821
@login_required
async def list_kbs():
    args = request.args
    keywords = args.get("keywords", "")
    page_number = int(args.get("page", 0))
    items_per_page = int(args.get("page_size", 0))
    parser_id = args.get("parser_id")
    orderby = args.get("orderby", "create_time")
    if args.get("desc", "true").lower() == "false":
        desc = False
    else:
        desc = True

    req = await get_request_json()
    owner_ids = req.get("owner_ids", [])
    
    is_admin = AdminUser.query(user_id=current_user.id, role_level=1)
    
    try:
        if not owner_ids:
            from api.db.services.user_group_service import UserGroupService
            tenants = UserGroupService.get_team_tenant_ids(current_user.id)
            kbs, total = KnowledgebaseService.get_by_tenant_ids(
                tenants, current_user.id, page_number,
                items_per_page, orderby, desc, keywords, parser_id,
                admin_bypass=bool(is_admin)
            )
        else:
            tenants = owner_ids
            kbs, total = KnowledgebaseService.get_by_tenant_ids(
                tenants, current_user.id, 0,
                0, orderby, desc, keywords, parser_id, admin_bypass=bool(is_admin))
            
            kbs = [kb for kb in kbs if kb["tenant_id"] in tenants]
            total = len(kbs)
            if page_number and items_per_page:
                kbs = kbs[(page_number-1)*items_per_page:page_number*items_per_page]
        return get_json_result(data={"kbs": kbs, "total": total})
    except Exception as e:
        return server_error_response(e)
    

# @manager.route('/list2', methods=['POST'])  # noqa: F821
# @login_required
# async def list_kbs2():
#     args = request.args
#     keywords = args.get("keywords", "")
#     page_number = int(args.get("page", 0))
#     items_per_page = int(args.get("page_size", 0))
#     parser_id = args.get("parser_id")
#     orderby = args.get("orderby", "create_time")
#     if args.get("desc", "true").lower() == "false":
#         desc = False
#     else:
#         desc = True

#     req = await get_request_json()
#     owner_ids = req.get("owner_ids", [])
    
#     is_admin = AdminUser.query(user_id=current_user.id, role_level=1)
    
#     try:
#         if not owner_ids:
#             from api.db.services.user_group_service import UserGroupService
#             tenants = UserGroupService.get_team_tenant_ids(current_user.id)
#             kbs, total = KnowledgebaseService.get_by_tenant_ids3(
#                 tenants, current_user.id, page_number,
#                 items_per_page, orderby, desc, keywords, parser_id,
#                 admin_bypass=bool(is_admin)
#             )
#         else:
#             tenants = owner_ids
#             kbs, total = KnowledgebaseService.get_by_tenant_ids(
#                 tenants, current_user.id, 0,
#                 0, orderby, desc, keywords, parser_id, admin_bypass=bool(is_admin))
            
#             kbs = [kb for kb in kbs if kb["tenant_id"] in tenants]
#             total = len(kbs)
#             if page_number and items_per_page:
#                 kbs = kbs[(page_number-1)*items_per_page:page_number*items_per_page]
#         return get_json_result(data={"kbs": kbs, "total": total})
#     except Exception as e:
#         return server_error_response(e)


@manager.route('/list2', methods=['POST'])  # noqa: F821
@login_required
async def list_kbs2():
    args = request.args
    keywords = args.get("keywords", "")
    page_number = int(args.get("page", 0))
    items_per_page = int(args.get("page_size", 0))
    parser_id = args.get("parser_id")
    orderby = args.get("orderby", "create_time")
    if args.get("desc", "true").lower() == "false":
        desc = False
    else:
        desc = True

    req = await get_request_json()
    owner_ids = req.get("owner_ids", [])
    
    is_admin = AdminUser.query(user_id=current_user.id, role_level=1)
    
    try:
        if not owner_ids:
            from api.db.services.user_group_service import UserGroupService
            tenants = UserGroupService.get_team_tenant_ids(current_user.id)
            kbs, total = KnowledgebaseService.get_by_tenant_ids(
                tenants, current_user.id, page_number,
                items_per_page, orderby, desc, keywords, parser_id,
                admin_bypass=bool(is_admin)
            )
        else:
            tenants = owner_ids
            kbs, total = KnowledgebaseService.get_by_tenant_ids(
                tenants, current_user.id, 0,
                0, orderby, desc, keywords, parser_id, admin_bypass=bool(is_admin))
            
            kbs = [kb for kb in kbs if kb["tenant_id"] in tenants]
            total = len(kbs)
            if page_number and items_per_page:
                kbs = kbs[(page_number-1)*items_per_page:page_number*items_per_page]
        return get_json_result(data={"kbs": kbs, "total": total})
    except Exception as e:
        return server_error_response(e)



@manager.route('/rm', methods=['post'])  # noqa: F821
@login_required
@validate_request("kb_id")
async def rm():
    req = await get_request_json()
    try:
        e, kb = KnowledgebaseService.get_by_id(req["kb_id"])
        if not e:
            return get_data_error_result(message="Can't find this dataset!")

        is_reference_kb = (settings.REFERENCE_TENANT_ID and kb.tenant_id == settings.REFERENCE_TENANT_ID) or (
            kb.tenant_id in KnowledgebaseService.get_all_group_reference_tenant_ids()
        )
        if is_reference_kb:
            if not KnowledgebaseService.writable(req["kb_id"], current_user.id):
                return get_json_result(
                    data=False,
                    message='No authorization.',
                    code=RetCode.AUTHENTICATION_ERROR,
                )
            kbs = [kb]
        else:
            is_admin = AdminUser.query(user_id=current_user.id, role_level=1)
            if not is_admin:
                kbs = KnowledgebaseService.query(
                    created_by=current_user.id, id=req["kb_id"])
                if not kbs:
                    return get_json_result(
                        data=False, message='Only owner of dataset authorized for this operation.',
                        code=RetCode.OPERATING_ERROR)
            else:
                kbs = [kb]

        def _rm_sync():
            for doc in DocumentService.query(kb_id=req["kb_id"]):
                # 删除doc
                if not DocumentService.remove_document(doc, kbs[0].tenant_id):
                    return get_data_error_result(
                        message="Database error (Document removal)!")
                
                f2d = File2DocumentService.get_by_document_id(doc.id)
                if f2d:
                    FileService.filter_delete([File.source_type == FileSource.KNOWLEDGEBASE, File.id == f2d[0].file_id])
                    FileAdminService.filter_delete([File_Admin.source_type == FileSource.KNOWLEDGEBASE, File_Admin.id == f2d[0].file_id])
                    # 如果删除的kb不属于 管理员自己的，二级表也删除
                    kb_list = KnowledgebaseService.query(id=req["kb_id"])
                    kb = kb_list[0] if kb_list else None
                    tenant_id = kb.tenant_id if kb else None
                    if tenant_id:
                        # 判断是否是一级管理员的
                        is_admin_create = AdminUser.query(user_id=tenant_id, role_level=1)
                        if not is_admin_create:
                            FileGroupService.filter_delete([File_Group.source_type == FileSource.KNOWLEDGEBASE, File_Group.id == f2d[0].file_id])



                File2DocumentService.delete_by_document_id(doc.id)
            FileService.filter_delete(
                [File.source_type == FileSource.KNOWLEDGEBASE, File.type == "folder", File.name == kbs[0].name])
            
            FileAdminService.filter_delete([File_Admin.source_type == FileSource.KNOWLEDGEBASE, File_Admin.type == "folder", File_Admin.name == kbs[0].name])
            # 如果删除的kb不属于 管理员自己的，二级表也删除
            kb_list = KnowledgebaseService.query(id=req["kb_id"])
            kb_del = kb_list[0] if kb_list else None
            print(kb_del)
            tenant_id = kb_del.tenant_id if kb_del else None

            if tenant_id:
                # 判断是否是一级管理员的
                is_admin_create = AdminUser.query(user_id=tenant_id, role_level=1)
                if not is_admin_create:
                    FileGroupService.filter_delete([File_Group.source_type == FileSource.KNOWLEDGEBASE, File_Group.type == "folder", File_Group.name == kbs[0].name])

            
            if not KnowledgebaseService.delete_by_id(req["kb_id"]):
                return get_data_error_result(
                    message="Database error (Knowledgebase removal)!")
            for kb in kbs:
                settings.docStoreConn.delete({"kb_id": kb.id}, search.index_name(kb.tenant_id), kb.id)
                settings.docStoreConn.deleteIdx(search.index_name(kb.tenant_id), kb.id)
                if hasattr(settings.STORAGE_IMPL, 'remove_bucket'):
                    settings.STORAGE_IMPL.remove_bucket(kb.id)
            return get_json_result(data=True)

        return await asyncio.to_thread(_rm_sync)
    except Exception as e:
        return server_error_response(e)


@manager.route('/<kb_id>/tags', methods=['GET'])  # noqa: F821
@login_required
def list_tags(kb_id):
    if not KnowledgebaseService.accessible(kb_id, current_user.id):
        return get_json_result(
            data=False,
            message='No authorization.',
            code=RetCode.AUTHENTICATION_ERROR
        )

    tenants = UserTenantService.get_tenants_by_user_id(current_user.id)
    tags = []
    for tenant in tenants:
        tags += settings.retriever.all_tags(tenant["tenant_id"], [kb_id])
    return get_json_result(data=tags)


@manager.route('/tags', methods=['GET'])  # noqa: F821
@login_required
def list_tags_from_kbs():
    kb_ids = request.args.get("kb_ids", "").split(",")
    for kb_id in kb_ids:
        if not KnowledgebaseService.accessible(kb_id, current_user.id):
            return get_json_result(
                data=False,
                message='No authorization.',
                code=RetCode.AUTHENTICATION_ERROR
            )

    tenants = UserTenantService.get_tenants_by_user_id(current_user.id)
    tags = []
    for tenant in tenants:
        tags += settings.retriever.all_tags(tenant["tenant_id"], kb_ids)
    return get_json_result(data=tags)


@manager.route('/<kb_id>/rm_tags', methods=['POST'])  # noqa: F821
@login_required
async def rm_tags(kb_id):
    req = await get_request_json()
    if not KnowledgebaseService.accessible(kb_id, current_user.id):
        return get_json_result(
            data=False,
            message='No authorization.',
            code=RetCode.AUTHENTICATION_ERROR
        )
    e, kb = KnowledgebaseService.get_by_id(kb_id)

    for t in req["tags"]:
        settings.docStoreConn.update({"tag_kwd": t, "kb_id": [kb_id]},
                                     {"remove": {"tag_kwd": t}},
                                     search.index_name(kb.tenant_id),
                                     kb_id)
    return get_json_result(data=True)


@manager.route('/<kb_id>/rename_tag', methods=['POST'])  # noqa: F821
@login_required
async def rename_tags(kb_id):
    req = await get_request_json()
    if not KnowledgebaseService.accessible(kb_id, current_user.id):
        return get_json_result(
            data=False,
            message='No authorization.',
            code=RetCode.AUTHENTICATION_ERROR
        )
    e, kb = KnowledgebaseService.get_by_id(kb_id)

    settings.docStoreConn.update({"tag_kwd": req["from_tag"], "kb_id": [kb_id]},
                                     {"remove": {"tag_kwd": req["from_tag"].strip()}, "add": {"tag_kwd": req["to_tag"]}},
                                     search.index_name(kb.tenant_id),
                                     kb_id)
    return get_json_result(data=True)


@manager.route('/<kb_id>/knowledge_graph', methods=['GET'])  # noqa: F821
@login_required
def knowledge_graph(kb_id):
    if not KnowledgebaseService.accessible(kb_id, current_user.id):
        return get_json_result(
            data=False,
            message='No authorization.',
            code=RetCode.AUTHENTICATION_ERROR
        )
    _, kb = KnowledgebaseService.get_by_id(kb_id)
    req = {
        "kb_id": [kb_id],
        "knowledge_graph_kwd": ["graph"]
    }

    obj = {"graph": {}, "mind_map": {}}
    if not settings.docStoreConn.indexExist(search.index_name(kb.tenant_id), kb_id):
        return get_json_result(data=obj)
    sres = settings.retriever.search(req, search.index_name(kb.tenant_id), [kb_id])
    if not len(sres.ids):
        return get_json_result(data=obj)

    for id in sres.ids[:1]:
        ty = sres.field[id]["knowledge_graph_kwd"]
        try:
            content_json = json.loads(sres.field[id]["content_with_weight"])
        except Exception:
            continue

        obj[ty] = content_json

    if "nodes" in obj["graph"]:
        obj["graph"]["nodes"] = sorted(obj["graph"]["nodes"], key=lambda x: x.get("pagerank", 0), reverse=True)[:256]
        if "edges" in obj["graph"]:
            node_id_set = { o["id"] for o in obj["graph"]["nodes"] }
            filtered_edges = [o for o in obj["graph"]["edges"] if o["source"] != o["target"] and o["source"] in node_id_set and o["target"] in node_id_set]
            obj["graph"]["edges"] = sorted(filtered_edges, key=lambda x: x.get("weight", 0), reverse=True)[:128]
    return get_json_result(data=obj)


@manager.route('/<kb_id>/knowledge_graph', methods=['DELETE'])  # noqa: F821
@login_required
def delete_knowledge_graph(kb_id):
    if not KnowledgebaseService.accessible(kb_id, current_user.id):
        return get_json_result(
            data=False,
            message='No authorization.',
            code=RetCode.AUTHENTICATION_ERROR
        )
    _, kb = KnowledgebaseService.get_by_id(kb_id)
    settings.docStoreConn.delete({"knowledge_graph_kwd": ["graph", "subgraph", "entity", "relation"]}, search.index_name(kb.tenant_id), kb_id)

    return get_json_result(data=True)


@manager.route("/get_meta", methods=["GET"])  # noqa: F821
@login_required
def get_meta():
    kb_ids = request.args.get("kb_ids", "").split(",")
    for kb_id in kb_ids:
        if not KnowledgebaseService.accessible(kb_id, current_user.id):
            return get_json_result(
                data=False,
                message='No authorization.',
                code=RetCode.AUTHENTICATION_ERROR
            )
    return get_json_result(data=DocumentService.get_meta_by_kbs(kb_ids))


@manager.route("/basic_info", methods=["GET"])  # noqa: F821
@login_required
def get_basic_info():
    kb_id = request.args.get("kb_id", "")
    if not KnowledgebaseService.accessible(kb_id, current_user.id):
        return get_json_result(
            data=False,
            message='No authorization.',
            code=RetCode.AUTHENTICATION_ERROR
        )

    basic_info = DocumentService.knowledgebase_basic_info(kb_id)
    print(basic_info)

    return get_json_result(data=basic_info)


@manager.route("/list_pipeline_logs", methods=["POST"])  # noqa: F821
@login_required
async def list_pipeline_logs():
    kb_id = request.args.get("kb_id")
    if not kb_id:
        return get_json_result(data=False, message='Lack of "KB ID"', code=RetCode.ARGUMENT_ERROR)

    keywords = request.args.get("keywords", "")

    page_number = int(request.args.get("page", 0))
    items_per_page = int(request.args.get("page_size", 0))
    orderby = request.args.get("orderby", "create_time")
    if request.args.get("desc", "true").lower() == "false":
        desc = False
    else:
        desc = True
    create_date_from = request.args.get("create_date_from", "")
    create_date_to = request.args.get("create_date_to", "")
    if create_date_to > create_date_from:
        return get_data_error_result(message="Create data filter is abnormal.")

    req = await get_request_json()

    operation_status = req.get("operation_status", [])
    if operation_status:
        invalid_status = {s for s in operation_status if s not in VALID_TASK_STATUS}
        if invalid_status:
            return get_data_error_result(message=f"Invalid filter operation_status status conditions: {', '.join(invalid_status)}")

    types = req.get("types", [])
    if types:
        invalid_types = {t for t in types if t not in VALID_FILE_TYPES}
        if invalid_types:
            return get_data_error_result(message=f"Invalid filter conditions: {', '.join(invalid_types)} type{'s' if len(invalid_types) > 1 else ''}")

    suffix = req.get("suffix", [])

    try:
        logs, tol = PipelineOperationLogService.get_file_logs_by_kb_id(kb_id, page_number, items_per_page, orderby, desc, keywords, operation_status, types, suffix, create_date_from, create_date_to)
        return get_json_result(data={"total": tol, "logs": logs})
    except Exception as e:
        return server_error_response(e)
    

@manager.route("/list_pipeline_logs_wasted", methods=["POST"])  # noqa: F821
@login_required
async def list_pipeline_logs_wasted():
    kb_id = request.args.get("kb_id")
    if not kb_id:
        return get_json_result(data=False, message='Lack of "KB ID"', code=RetCode.ARGUMENT_ERROR)

    keywords = request.args.get("keywords", "")

    page_number = int(request.args.get("page", 0))
    items_per_page = int(request.args.get("page_size", 0))
    orderby = request.args.get("orderby", "create_time")
    if request.args.get("desc", "true").lower() == "false":
        desc = False
    else:
        desc = True
    create_date_from = request.args.get("create_date_from", "")
    create_date_to = request.args.get("create_date_to", "")
    if create_date_to > create_date_from:
        return get_data_error_result(message="Create data filter is abnormal.")

    req = await get_request_json()

    operation_status = req.get("operation_status", [])
    if operation_status:
        invalid_status = {s for s in operation_status if s not in VALID_TASK_STATUS}
        if invalid_status:
            return get_data_error_result(message=f"Invalid filter operation_status status conditions: {', '.join(invalid_status)}")

    types = req.get("types", [])
    if types:
        invalid_types = {t for t in types if t not in VALID_FILE_TYPES}
        if invalid_types:
            return get_data_error_result(message=f"Invalid filter conditions: {', '.join(invalid_types)} type{'s' if len(invalid_types) > 1 else ''}")

    suffix = req.get("suffix", [])

    try:
        logs, tol = PipelineOperationLogService.get_file_logs_by_kb_id_wasted(kb_id, page_number, items_per_page, orderby, desc, keywords, operation_status, types, suffix, create_date_from, create_date_to)
        return get_json_result(data={"total": tol, "logs": logs})
    except Exception as e:
        return server_error_response(e)


@manager.route("/list_pipeline_dataset_logs", methods=["POST"])  # noqa: F821
@login_required
async def list_pipeline_dataset_logs():
    kb_id = request.args.get("kb_id")
    if not kb_id:
        return get_json_result(data=False, message='Lack of "KB ID"', code=RetCode.ARGUMENT_ERROR)

    page_number = int(request.args.get("page", 0))
    items_per_page = int(request.args.get("page_size", 0))
    orderby = request.args.get("orderby", "create_time")
    if request.args.get("desc", "true").lower() == "false":
        desc = False
    else:
        desc = True
    create_date_from = request.args.get("create_date_from", "")
    create_date_to = request.args.get("create_date_to", "")
    if create_date_to > create_date_from:
        return get_data_error_result(message="Create data filter is abnormal.")

    req = await get_request_json()

    operation_status = req.get("operation_status", [])
    if operation_status:
        invalid_status = {s for s in operation_status if s not in VALID_TASK_STATUS}
        if invalid_status:
            return get_data_error_result(message=f"Invalid filter operation_status status conditions: {', '.join(invalid_status)}")

    try:
        logs, tol = PipelineOperationLogService.get_dataset_logs_by_kb_id(kb_id, page_number, items_per_page, orderby, desc, operation_status, create_date_from, create_date_to)
        print(logs)
        return get_json_result(data={"total": tol, "logs": logs})
    except Exception as e:
        return server_error_response(e)


@manager.route("/delete_pipeline_logs", methods=["POST"])  # noqa: F821
@login_required
async def delete_pipeline_logs():
    kb_id = request.args.get("kb_id")
    if not kb_id:
        return get_json_result(data=False, message='Lack of "KB ID"', code=RetCode.ARGUMENT_ERROR)

    req = await get_request_json()
    log_ids = req.get("log_ids", [])
    print(log_ids)

    PipelineOperationLogService.delete_by_ids(log_ids)

    return get_json_result(data=True)

@manager.route("/delete_pipeline_logs_bydoc", methods=["POST"])  # noqa: F821
@login_required
async def delete_pipeline_logs_bydoc():
    kb_id = request.args.get("kb_id")
    if not kb_id:
        return get_json_result(data=False, message='Lack of "KB ID"', code=RetCode.ARGUMENT_ERROR)

    req = await get_request_json()
    log_ids = req.get("log_ids", [])
    print(log_ids)

    PipelineOperationLogService.delete_by_document_ids_from_log_ids(log_ids)

    return get_json_result(data=True)


@manager.route("/pipeline_log_detail", methods=["GET"])  # noqa: F821
@login_required
def pipeline_log_detail():
    log_id = request.args.get("log_id")
    if not log_id:
        return get_json_result(data=False, message='Lack of "Pipeline log ID"', code=RetCode.ARGUMENT_ERROR)

    ok, log = PipelineOperationLogService.get_by_id(log_id)
    if not ok:
        return get_data_error_result(message="Invalid pipeline log ID")

    return get_json_result(data=log.to_dict())

@manager.route("/pipeline_log_list", methods=["GET"])  # noqa: F821
@login_required
def pipeline_log_list():
    document_id = request.args.get("document_id")
    if not document_id:
        return get_json_result(
            data=False,
            message='Lack of "Document ID"',
            code=RetCode.ARGUMENT_ERROR,
        )

    logs = PipelineOperationLogService.query(
        document_id=document_id,
        order_by=PipelineOperationLog.create_time.desc(),
    )

    return get_json_result(data=[log.to_dict() for log in logs])


@manager.route("/run_graphrag", methods=["POST"])  # noqa: F821
@login_required
async def run_graphrag():
    req = await get_request_json()

    kb_id = req.get("kb_id", "")
    if not kb_id:
        return get_error_data_result(message='Lack of "KB ID"')

    ok, kb = KnowledgebaseService.get_by_id(kb_id)
    if not ok:
        return get_error_data_result(message="Invalid Knowledgebase ID")

    task_id = kb.graphrag_task_id
    if task_id:
        ok, task = TaskService.get_by_id(task_id)
        if not ok:
            logging.warning(f"A valid GraphRAG task id is expected for kb {kb_id}")

        if task and task.progress not in [-1, 1]:
            return get_error_data_result(message=f"Task {task_id} in progress with status {task.progress}. A Graph Task is already running.")

    documents, _ = DocumentService.get_by_kb_id(
        kb_id=kb_id,
        page_number=0,
        items_per_page=0,
        orderby="create_time",
        desc=False,
        keywords="",
        run_status=[],
        types=[],
        suffix=[],
    )
    if not documents:
        return get_error_data_result(message=f"No documents in Knowledgebase {kb_id}")

    sample_document = documents[0]
    document_ids = [document["id"] for document in documents]

    task_id = queue_raptor_o_graphrag_tasks(sample_doc_id=sample_document, ty="graphrag", priority=0, fake_doc_id=GRAPH_RAPTOR_FAKE_DOC_ID, doc_ids=list(document_ids))

    if not KnowledgebaseService.update_by_id(kb.id, {"graphrag_task_id": task_id}):
        logging.warning(f"Cannot save graphrag_task_id for kb {kb_id}")

    return get_json_result(data={"graphrag_task_id": task_id})


@manager.route("/trace_graphrag", methods=["GET"])  # noqa: F821
@login_required
def trace_graphrag():
    kb_id = request.args.get("kb_id", "")
    if not kb_id:
        return get_error_data_result(message='Lack of "KB ID"')

    ok, kb = KnowledgebaseService.get_by_id(kb_id)
    if not ok:
        return get_error_data_result(message="Invalid Knowledgebase ID")

    task_id = kb.graphrag_task_id
    if not task_id:
        return get_json_result(data={})

    ok, task = TaskService.get_by_id(task_id)
    if not ok:
        return get_json_result(data={})

    return get_json_result(data=task.to_dict())


@manager.route("/run_raptor", methods=["POST"])  # noqa: F821
@login_required
async def run_raptor():
    req = await get_request_json()

    kb_id = req.get("kb_id", "")
    if not kb_id:
        return get_error_data_result(message='Lack of "KB ID"')

    ok, kb = KnowledgebaseService.get_by_id(kb_id)
    if not ok:
        return get_error_data_result(message="Invalid Knowledgebase ID")

    task_id = kb.raptor_task_id
    if task_id:
        ok, task = TaskService.get_by_id(task_id)
        if not ok:
            logging.warning(f"A valid RAPTOR task id is expected for kb {kb_id}")

        if task and task.progress not in [-1, 1]:
            return get_error_data_result(message=f"Task {task_id} in progress with status {task.progress}. A RAPTOR Task is already running.")

    documents, _ = DocumentService.get_by_kb_id(
        kb_id=kb_id,
        page_number=0,
        items_per_page=0,
        orderby="create_time",
        desc=False,
        keywords="",
        run_status=[],
        types=[],
        suffix=[],
    )
    if not documents:
        return get_error_data_result(message=f"No documents in Knowledgebase {kb_id}")

    sample_document = documents[0]
    document_ids = [document["id"] for document in documents]

    task_id = queue_raptor_o_graphrag_tasks(sample_doc_id=sample_document, ty="raptor", priority=0, fake_doc_id=GRAPH_RAPTOR_FAKE_DOC_ID, doc_ids=list(document_ids))

    if not KnowledgebaseService.update_by_id(kb.id, {"raptor_task_id": task_id}):
        logging.warning(f"Cannot save raptor_task_id for kb {kb_id}")

    return get_json_result(data={"raptor_task_id": task_id})


@manager.route("/trace_raptor", methods=["GET"])  # noqa: F821
@login_required
def trace_raptor():
    kb_id = request.args.get("kb_id", "")
    if not kb_id:
        return get_error_data_result(message='Lack of "KB ID"')

    ok, kb = KnowledgebaseService.get_by_id(kb_id)
    if not ok:
        return get_error_data_result(message="Invalid Knowledgebase ID")

    task_id = kb.raptor_task_id
    if not task_id:
        return get_json_result(data={})

    ok, task = TaskService.get_by_id(task_id)
    if not ok:
        return get_error_data_result(message="RAPTOR Task Not Found or Error Occurred")

    return get_json_result(data=task.to_dict())


@manager.route("/run_mindmap", methods=["POST"])  # noqa: F821
@login_required
async def run_mindmap():
    req = await get_request_json()

    kb_id = req.get("kb_id", "")
    if not kb_id:
        return get_error_data_result(message='Lack of "KB ID"')

    ok, kb = KnowledgebaseService.get_by_id(kb_id)
    if not ok:
        return get_error_data_result(message="Invalid Knowledgebase ID")

    task_id = kb.mindmap_task_id
    if task_id:
        ok, task = TaskService.get_by_id(task_id)
        if not ok:
            logging.warning(f"A valid Mindmap task id is expected for kb {kb_id}")

        if task and task.progress not in [-1, 1]:
            return get_error_data_result(message=f"Task {task_id} in progress with status {task.progress}. A Mindmap Task is already running.")

    documents, _ = DocumentService.get_by_kb_id(
        kb_id=kb_id,
        page_number=0,
        items_per_page=0,
        orderby="create_time",
        desc=False,
        keywords="",
        run_status=[],
        types=[],
        suffix=[],
    )
    if not documents:
        return get_error_data_result(message=f"No documents in Knowledgebase {kb_id}")

    sample_document = documents[0]
    document_ids = [document["id"] for document in documents]

    task_id = queue_raptor_o_graphrag_tasks(sample_doc_id=sample_document, ty="mindmap", priority=0, fake_doc_id=GRAPH_RAPTOR_FAKE_DOC_ID, doc_ids=list(document_ids))

    if not KnowledgebaseService.update_by_id(kb.id, {"mindmap_task_id": task_id}):
        logging.warning(f"Cannot save mindmap_task_id for kb {kb_id}")

    return get_json_result(data={"mindmap_task_id": task_id})


@manager.route("/trace_mindmap", methods=["GET"])  # noqa: F821
@login_required
def trace_mindmap():
    kb_id = request.args.get("kb_id", "")
    if not kb_id:
        return get_error_data_result(message='Lack of "KB ID"')

    ok, kb = KnowledgebaseService.get_by_id(kb_id)
    if not ok:
        return get_error_data_result(message="Invalid Knowledgebase ID")

    task_id = kb.mindmap_task_id
    if not task_id:
        return get_json_result(data={})

    ok, task = TaskService.get_by_id(task_id)
    if not ok:
        return get_error_data_result(message="Mindmap Task Not Found or Error Occurred")

    return get_json_result(data=task.to_dict())


@manager.route("/unbind_task", methods=["DELETE"])  # noqa: F821
@login_required
def delete_kb_task():
    kb_id = request.args.get("kb_id", "")
    if not kb_id:
        return get_error_data_result(message='Lack of "KB ID"')
    ok, kb = KnowledgebaseService.get_by_id(kb_id)
    if not ok:
        return get_json_result(data=True)

    pipeline_task_type = request.args.get("pipeline_task_type", "")
    if not pipeline_task_type or pipeline_task_type not in [PipelineTaskType.GRAPH_RAG, PipelineTaskType.RAPTOR, PipelineTaskType.MINDMAP]:
        return get_error_data_result(message="Invalid task type")

    def cancel_task(task_id):
        REDIS_CONN.set(f"{task_id}-cancel", "x")

    kb_task_id_field: str = ""
    kb_task_finish_at: str = ""
    match pipeline_task_type:
        case PipelineTaskType.GRAPH_RAG:
            kb_task_id_field = "graphrag_task_id"
            task_id = kb.graphrag_task_id
            kb_task_finish_at = "graphrag_task_finish_at"
            cancel_task(task_id)
            settings.docStoreConn.delete({"knowledge_graph_kwd": ["graph", "subgraph", "entity", "relation"]}, search.index_name(kb.tenant_id), kb_id)
        case PipelineTaskType.RAPTOR:
            kb_task_id_field = "raptor_task_id"
            task_id = kb.raptor_task_id
            kb_task_finish_at = "raptor_task_finish_at"
            cancel_task(task_id)
            settings.docStoreConn.delete({"raptor_kwd": ["raptor"]}, search.index_name(kb.tenant_id), kb_id)
        case PipelineTaskType.MINDMAP:
            kb_task_id_field = "mindmap_task_id"
            task_id = kb.mindmap_task_id
            kb_task_finish_at = "mindmap_task_finish_at"
            cancel_task(task_id)
        case _:
            return get_error_data_result(message="Internal Error: Invalid task type")


    ok = KnowledgebaseService.update_by_id(kb_id, {kb_task_id_field: "", kb_task_finish_at: None})
    if not ok:
        return server_error_response(f"Internal error: cannot delete task {pipeline_task_type}")

    return get_json_result(data=True)

@manager.route("/check_embedding", methods=["post"])  # noqa: F821
@login_required
async def check_embedding():

    def _guess_vec_field(src: dict) -> str | None:
        for k in src or {}:
            if k.endswith("_vec"):
                return k
        return None

    def _as_float_vec(v):
        if v is None:
            return []
        if isinstance(v, str):
            return [float(x) for x in v.split("\t") if x != ""]
        if isinstance(v, (list, tuple, np.ndarray)):
            return [float(x) for x in v]
        return []

    def _to_1d(x):
        a = np.asarray(x, dtype=np.float32)
        return a.reshape(-1)

    def _cos_sim(a, b, eps=1e-12):
        a = _to_1d(a)
        b = _to_1d(b)
        na = np.linalg.norm(a)
        nb = np.linalg.norm(b)
        if na < eps or nb < eps:
            return 0.0
        return float(np.dot(a, b) / (na * nb))

    def sample_random_chunks_with_vectors(
        docStoreConn,
        tenant_id: str,
        kb_id: str,
        n: int = 5,
        base_fields=("docnm_kwd","doc_id","content_with_weight","page_num_int","position_int","top_int"),
    ):
        index_nm = search.index_name(tenant_id)

        res0 = docStoreConn.search(
            selectFields=[], highlightFields=[],
            condition={"kb_id": kb_id, "available_int": 1},
            matchExprs=[], orderBy=OrderByExpr(),
            offset=0, limit=1,
            indexNames=index_nm, knowledgebaseIds=[kb_id]
        )
        total = docStoreConn.get_total(res0)
        if total <= 0:
            return []

        n = min(n, total)
        offsets = sorted(random.sample(range(min(total,1000)), n))
        out = []

        for off in offsets:
            res1 = docStoreConn.search(
                selectFields=list(base_fields),
                highlightFields=[],
                condition={"kb_id": kb_id, "available_int": 1},
                matchExprs=[], orderBy=OrderByExpr(),
                offset=off, limit=1,
                indexNames=index_nm, knowledgebaseIds=[kb_id]
            )
            ids = docStoreConn.get_chunk_ids(res1)
            if not ids:
                continue

            cid = ids[0]
            full_doc = docStoreConn.get(cid, index_nm, [kb_id]) or {}
            vec_field = _guess_vec_field(full_doc)
            vec = _as_float_vec(full_doc.get(vec_field))

            out.append({
                "chunk_id": cid,
                "kb_id": kb_id,
                "doc_id": full_doc.get("doc_id"),
                "doc_name": full_doc.get("docnm_kwd"),
                "vector_field": vec_field,
                "vector_dim": len(vec),
                "vector": vec,
                "page_num_int": full_doc.get("page_num_int"),
                "position_int": full_doc.get("position_int"),
                "top_int": full_doc.get("top_int"),
                "content_with_weight": full_doc.get("content_with_weight") or "",
                "question_kwd": full_doc.get("question_kwd") or []
            })
        return out

    def _clean(s: str) -> str:
        s = re.sub(r"</?(table|td|caption|tr|th)( [^<>]{0,12})?>", " ", s or "")
        return s if s else "None"
    req = await get_request_json()
    kb_id = req.get("kb_id", "")
    embd_id = req.get("embd_id", "")
    n = int(req.get("check_num", 5))
    _, kb = KnowledgebaseService.get_by_id(kb_id)
    tenant_id = kb.tenant_id

    emb_mdl = LLMBundle(tenant_id, LLMType.EMBEDDING, embd_id)
    samples = sample_random_chunks_with_vectors(settings.docStoreConn, tenant_id=tenant_id, kb_id=kb_id, n=n)

    results, eff_sims = [], []
    for ck in samples:
        title = ck.get("doc_name") or "Title"
        txt_in = "\n".join(ck.get("question_kwd") or []) or ck.get("content_with_weight") or ""
        txt_in = _clean(txt_in)
        if not txt_in:
            results.append({"chunk_id": ck["chunk_id"], "reason": "no_text"})
            continue

        if not ck.get("vector"):
            results.append({"chunk_id": ck["chunk_id"], "reason": "no_stored_vector"})
            continue

        try:
            v, _ = emb_mdl.encode([title, txt_in])
            assert len(v[1]) == len(ck["vector"]), f"The dimension ({len(v[1])}) of given embedding model is different from the original ({len(ck['vector'])})"
            sim_content = _cos_sim(v[1], ck["vector"])
            title_w = 0.1
            qv_mix = title_w * v[0] + (1 - title_w) * v[1]
            sim_mix = _cos_sim(qv_mix, ck["vector"])
            sim = sim_content
            mode = "content_only"
            if sim_mix > sim:
                sim = sim_mix
                mode = "title+content"
        except Exception as e:
            return get_error_data_result(message=f"Embedding failure. {e}")

        eff_sims.append(sim)
        results.append({
            "chunk_id": ck["chunk_id"],
            "doc_id": ck["doc_id"],
            "doc_name": ck["doc_name"],
            "vector_field": ck["vector_field"],
            "vector_dim": ck["vector_dim"],
            "cos_sim": round(sim, 6),
        })

    summary = {
        "kb_id": kb_id,
        "model": embd_id,
        "sampled": len(samples),
        "valid": len(eff_sims),
        "avg_cos_sim": round(float(np.mean(eff_sims)) if eff_sims else 0.0, 6),
        "min_cos_sim": round(float(np.min(eff_sims)) if eff_sims else 0.0, 6),
        "max_cos_sim": round(float(np.max(eff_sims)) if eff_sims else 0.0, 6),
        "match_mode": mode,
    }
    if summary["avg_cos_sim"] > 0.9:
        return get_json_result(data={"summary": summary, "results": results})
    return get_json_result(code=RetCode.NOT_EFFECTIVE, message="Embedding model switch failed: the average similarity between old and new vectors is below 0.9, indicating incompatible vector spaces.", data={"summary": summary, "results": results})


@manager.route("name_map", methods=["POST"])  # noqa: F821
@login_required
async def get_kb_name_map():
    try:
        req = await request.json

        kb_ids = req.get("kb_ids", [])

        if not isinstance(kb_ids, list):
            return get_json_result(
                data=False,
                message="kb_ids must be a list.",
                code=RetCode.ARGUMENT_ERROR,
            )

        # 去重，过滤空值
        kb_ids = list({str(kb_id) for kb_id in kb_ids if kb_id})

        name_map = KnowledgebaseService.get_name_map_by_ids(kb_ids)

        return get_json_result(data=name_map)

    except Exception as e:
        return server_error_response(e)