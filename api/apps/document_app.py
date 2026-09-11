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
#  limitations under the License
#
import asyncio
import json
import os.path
import pathlib
import re
import os
from pathlib import Path
from quart import request, make_response
from api.apps import current_user, login_required
from api.common.check_team_permission import check_kb_team_permission, check_kb_team_write_permission,user_has_operation_permission
from api.constants import FILE_NAME_LEN_LIMIT, IMG_BASE64_PREFIX
from api.db import VALID_FILE_TYPES, FileType
from api.db.db_models import Task, SyncDept, SyncPerson,StagedFileTag,StagedFile,KnowledgeTagOption,KnowledgeTagType,OAApprovalRequest,StagedFileApprovalRequest,StagedFileApprovalTask,OAApprovalTask,Knowledgebase
from api.db.services import duplicate_name
from api.db.services.document_service import DocumentService, doc_upload_and_parse
from common.metadata_utils import meta_filter, convert_conditions
from api.db.services.file2document_service import File2DocumentService
from api.db.services.stagedfile_service import StagedFileService

from api.db.services.file_service import FileService
from api.db.services.knowledgebase_service import KnowledgebaseService
from api.db.services.operationlog_service import OperationLogService

from api.db.services.task_service import TaskService, cancel_all_task_of
from api.db.services.user_service import UserTenantService
from common.misc_utils import get_uuid
from api.utils.api_utils import (
    get_data_error_result,
    get_json_result,
    server_error_response,
    validate_request, get_request_json,
)
from api.utils.file_utils import filename_type, thumbnail
from common.file_utils import get_project_base_directory
from common.constants import RetCode, VALID_TASK_STATUS, ParserType, TaskStatus
from api.utils.web_utils import CONTENT_TYPE_MAP, html2pdf, is_valid_url
from deepdoc.parser.html_parser import RAGFlowHtmlParser
from rag.nlp import search, rag_tokenizer
from common import settings
from api.db.services.pipeline_operation_log_service import PipelineOperationLogService
from api.db.db_models import DB
from api.utils.file_utils import filename_type, read_potential_broken_pdf, thumbnail_img, sanitize_path
from api.db.services.operationlog_service import OperationLogService
from api.db.db_models import StagedFile, StagedFileTag, User

import re


def normalize_document_version(version):
    """
    空版本、1、1.0、v1、v1.0 最终都转换为 v1.0。
    """

    if version is None or str(version).strip() == "":
        return "v1.0"

    value = str(version).strip().lower()

    if value.startswith("v"):
        value = value[1:]

    if not re.fullmatch(r"\d+(?:\.\d+)?", value):
        raise ValueError(
            "版本号格式错误，只允许 1、1.0、2.3、v1.0、v2.3"
        )

    if "." not in value:
        value = f"{value}.0"

    major, minor = value.split(".", 1)

    return f"v{int(major)}.{int(minor)}"

# 新增报告推送接口
@manager.route("/upload/report", methods=["POST"])  # noqa: F821
# @validate_request("dept_id", "user_id") 
async def upload_report():
    # 知识库id
    form = await request.form
    dept_id = form.get("dept_id")  # 部门id
    user_id = form.get("user_id")  # 用户id
    file_name = form.get("file_name")
    print(file_name)
    file_name2 = form.get("file_name2")
    print(file_name2)
    dept_id = int(dept_id)
    user_id = int(user_id)
    print(f"部门id：{dept_id}")



    dep_obj = SyncDept.select(SyncDept.mdmName).where(
            SyncDept.mdmCode == dept_id
        ).first()
    
    user_obj = SyncPerson.select(SyncPerson.mdmName).where(
        SyncPerson.mdmCode == user_id
    ).first()

    # 3. 校验数据是否存在
    if not dep_obj or not user_obj:
        missing = []
        if not dep_obj: missing.append("部门")
        if not user_obj: missing.append("用户")
        return get_json_result(
            data=False, 
            message=f"未找到对应的{'、'.join(missing)}信息，请检查 dept_id 和 user_id 是否正确", 
            code=RetCode.ARGUMENT_ERROR
        )

    # 4. 提取名称（转为字符串）
    dep_name = dep_obj.mdmName
    user_name = user_obj.mdmName


    cfg_map = getattr(settings, "GROUP_REFERENCE_TENANT_MAP", {}) or {}
    print(cfg_map)
    nfg_map = getattr(settings, "GROUP_NAME_ID_MAP", {}) or {}
    print(nfg_map)
    # 2. 通过部门id --> 组号
    kb_name = dep_name + "报告库"
    # 3. 通过组号 --> 公共库 user_id
    # tenant_id = "c79873e6395a11f1b4e6345a60aae1f7"
    tenant_id = cfg_map.get(nfg_map.get(dep_name))

    # 7. 如果 tenant_id 也没找到，也返回错误
    if not tenant_id:
        return get_json_result(
            data=False, 
            message=f"部门 '{dep_name}' 未配置对应的租户ID，请检查系统配置", 
            code=RetCode.ARGUMENT_ERROR
        )

    if '（' in dep_name:
        dep_name = dep_name.split('（')[0]
    kb_name = dep_name + "报告库"

    # 4. 获取kb_id 通过知识库的名称 以及公共库的tenant_id (如果没有就创建1个）
    kb = KnowledgebaseService.model.select().where(
        (KnowledgebaseService.model.tenant_id == tenant_id) & 
        (KnowledgebaseService.model.name == kb_name)
    ).first()



    # kb_id = kb.id
    if not kb:   
        # try:
            # return get_json_result(data=False, message='Lack of "KB ID"', code=RetCode.ARGUMENT_ERROR)
            # 新建一个知识库
        req = {
        "name": kb_name,  # 知识库名称
        "embd_id": "text-embedding-v2@Tongyi-Qianwen",
        "language": "Chinese",
        "parse_type": 1,
        "parser_id": "paper",
        "pipeline_id": ""}

        # 创建1个知识库
        e, res = KnowledgebaseService.create_with_name(
        name = req.pop("name", None),
        tenant_id = tenant_id,
        parser_id = req.pop("parser_id", None),
        **req)

        kb_id = res["id"]

        try:
            if not KnowledgebaseService.save(**res):
                return get_data_error_result()
            
        except Exception as e:
            return server_error_response(e)
        # except Exception as err:
        #     return get_json_result(data=False, message="系统内部错误", code=RetCode.SERVER_ERROR)
    
    else:
        kb_id = kb.id

    # kb_id = "cfc8ad543c9a11f18845345a60aae1f7"
    # 文件
    files = await request.files
    if "file" not in files:
        return get_json_result(data=False, message="No file part!", code=RetCode.ARGUMENT_ERROR)
    
    file_objs = files.getlist("file")

    for file_obj in file_objs:
        file_obj.filename = file_name2
        if file_obj.filename == "":
            return get_json_result(data=False, message="No file selected!", code=RetCode.ARGUMENT_ERROR)
        if len(file_obj.filename.encode("utf-8")) > FILE_NAME_LEN_LIMIT:
            return get_json_result(data=False, message=f"File name must be {FILE_NAME_LEN_LIMIT} bytes or less.", code=RetCode.ARGUMENT_ERROR)

    # 获取知识库行信息
    e, kb = KnowledgebaseService.get_by_id(kb_id)
    if not e:
        raise LookupError("Can't find this dataset!")
    # 鉴权
    if not check_kb_team_write_permission(kb, tenant_id):
        return get_json_result(data=False, message="No authorization.", code=RetCode.AUTHENTICATION_ERROR)

    # 上传到文本库
    err, files = await asyncio.to_thread(FileService.upload_document, kb, file_objs, tenant_id)
    if err:
        quota_errs = [e for e in err if isinstance(e, str) and e.startswith("QUOTA:")]
        if quota_errs:
            msg = "\n".join([e.split("QUOTA:", 1)[1].strip() for e in quota_errs])
            return get_json_result(data=files, message=msg, code=RetCode.OPERATING_ERROR)
        return get_json_result(data=files, message="\n".join(err), code=RetCode.SERVER_ERROR)
    
    if not files:
        return get_json_result(data=files, message="There seems to be an issue with your file format. Please verify it is correct and not corrupted.", code=RetCode.DATA_ERROR)
    
    files = [f[0] for f in files]  # remove the blob

    # 如果上传完成，则对上传的每个文件进行作者信息解析任务
    from api.db.db_utils import bulk_insert_into_db
    from rag.utils.redis_conn import REDIS_CONN
    from datetime import datetime
    tasks = []
    doc_ids = []
    for file in files:
        DocumentService.update_by_id(
            file["id"],
            {
                "run": TaskStatus.RUNNING.value,
                "progress": 0,
                "progress_msg": "",
                "process_begin_at": datetime.now(),
            },
        )
        doc_ids.append(file["id"])
        task = {
            "id": get_uuid(),
            "doc_id": file["id"],
            "task_type": "parse_author_info",
            "progress": 0.0,
            "from_page": 0,
            "to_page": 100000000,
            "begin_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        tasks.append(task)


    if tasks:
        bulk_insert_into_db(Task, tasks, True)
        for task in tasks:
            REDIS_CONN.queue_product(settings.get_svr_queue_name(0), message=task)

    # 解析的任务
    req = {
        "doc_ids": doc_ids,
        "run": TaskStatus.RUNNING.value,
    }
    try:
        def _run_sync():
            # 遍历传入的文档id
            for doc_id in req["doc_ids"]:
                # 查数据库看文档是否存在
                e, doc = DocumentService.get_by_id(doc_id)
                if not e:
                    return get_json_result(data=False, message="No authorization.", code=RetCode.AUTHENTICATION_ERROR)
                # 通过文档找到所属的知识库（Knowledgebase），看知识库是否存在
                e, kb = KnowledgebaseService.get_by_id(doc.kb_id)
                if not e:
                    return get_data_error_result(message="Can't find this dataset!")
                
                # # 确保当前用户有权限修改这个知识库（防止越权操作）。
                # if not check_kb_team_write_permission(kb, tenant_id):
                #     return get_json_result(data=False, message="No authorization.", code=RetCode.AUTHENTICATION_ERROR)
            # 用于在多次解析间共享表格数量信息的临时字典
            kb_table_num_map = {}
            for id in req["doc_ids"]:
                # 当前信息
                info = {"run": str(req["run"]), "progress": 0}

                # 如果是“重新运行”且要求“删除旧数据”
                if str(req["run"]) == TaskStatus.RUNNING.value and req.get("delete", False):
                    info["progress_msg"] = ""
                    info["chunk_num"] = 0
                    info["token_num"] = 0

                # 二次检查：再次获取租户 ID 和文档对象（为了安全，防止在长循环中数据状态变化）
                tenant_id = DocumentService.get_tenant_id(id)
                if not tenant_id:
                    return get_data_error_result(message="Tenant not found!")
                e, doc = DocumentService.get_by_id(id)
                if not e:
                    return get_data_error_result(message="Document not found!")

                # 处理“取消”指令
                if str(req["run"]) == TaskStatus.CANCEL.value:
                    if str(doc.run) == TaskStatus.RUNNING.value:
                        cancel_all_task_of(id)
                    else:
                        return get_data_error_result(message="Cannot cancel a task that is not in RUNNING status")
                # 处理“重新运行”清理
                if all([("delete" not in req or req["delete"]), str(req["run"]) == TaskStatus.RUNNING.value, str(doc.run) == TaskStatus.DONE.value]):
                    DocumentService.clear_chunk_num_when_rerun(doc.id)

                # 更新数据库状态
                DocumentService.update_by_id(id, info)
                # 物理删除旧数据 es0
                if req.get("delete", False):
                    TaskService.filter_delete([Task.doc_id == id])
                    if settings.docStoreConn.indexExist(search.index_name(tenant_id), doc.kb_id):
                        settings.docStoreConn.delete({"doc_id": id}, search.index_name(tenant_id), doc.kb_id)

                # 启动解析任务
                if str(req["run"]) == TaskStatus.RUNNING.value:
                    doc_dict = doc.to_dict()
                    DocumentService.run(tenant_id, doc_dict, kb_table_num_map)
                    
                    # Create parse_author_info task if not exists
                    from api.db.services.task_service import TaskService
                    from api.db.db_utils import bulk_insert_into_db
                    from rag.utils.redis_conn import REDIS_CONN
                    from datetime import datetime
                    
                    existing_task = TaskService.get_task_by_doc_id_and_type(doc.id, "parse_author_info")
                    if not existing_task:
                        task = {
                            "id": get_uuid(),
                            "doc_id": doc.id,
                            "task_type": "parse_author_info",
                            "progress": 0.0,
                            "from_page": 0,
                            "to_page": 100000000,
                            "begin_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        }
                        bulk_insert_into_db(Task, [task], True)
                        REDIS_CONN.queue_product(settings.get_svr_queue_name(0), message=task)

            return get_json_result(data=True)

        return await asyncio.to_thread(_run_sync)
    except Exception as e:
        return server_error_response(e)

# # 知识库的上传
# @manager.route("/upload", methods=["POST"])  # noqa: F821
# @login_required
# @validate_request("kb_id")
# async def upload():
#     # 获取知识库id
#     form = await request.form
#     kb_id = form.get("kb_id")

#     if not kb_id:
#         return get_json_result(data=False, message='Lack of "KB ID"', code=RetCode.ARGUMENT_ERROR)
    
#     # 获取文件
#     files = await request.files
#     if "file" not in files:
#         return get_json_result(data=False, message="No file part!", code=RetCode.ARGUMENT_ERROR)

    
#     file_objs = files.getlist("file")
#     for file_obj in file_objs:
#         if file_obj.filename == "":
#             return get_json_result(data=False, message="No file selected!", code=RetCode.ARGUMENT_ERROR)
#         if len(file_obj.filename.encode("utf-8")) > FILE_NAME_LEN_LIMIT:
#             return get_json_result(data=False, message=f"File name must be {FILE_NAME_LEN_LIMIT} bytes or less.", code=RetCode.ARGUMENT_ERROR)

#     # 获取知识库行信息
#     e, kb = KnowledgebaseService.get_by_id(kb_id)
#     if not e:
#         raise LookupError("Can't find this dataset!")
    
#     # 鉴权 
#     if not check_kb_team_write_permission(kb, current_user.id):
#         return get_json_result(data=False, message="No authorization.", code=RetCode.AUTHENTICATION_ERROR)

#     # 上传到文本库
#     err, files = await asyncio.to_thread(FileService.upload_document, kb, file_objs, current_user.id)
#     if err:
#         quota_errs = [e for e in err if isinstance(e, str) and e.startswith("QUOTA:")]
#         if quota_errs:
#             msg = "\n".join([e.split("QUOTA:", 1)[1].strip() for e in quota_errs])
#             return get_json_result(data=files, message=msg, code=RetCode.OPERATING_ERROR)
#         return get_json_result(data=files, message="\n".join(err), code=RetCode.SERVER_ERROR)
    
#     if not files:
#         return get_json_result(data=files, message="There seems to be an issue with your file format. Please verify it is correct and not corrupted.", code=RetCode.DATA_ERROR)
    
#     files = [f[0] for f in files]  # remove the blob

#     # 如果上传完成，则对上传的每个文件进行作者信息解析任务
#     from api.db.db_utils import bulk_insert_into_db
#     from rag.utils.redis_conn import REDIS_CONN
#     from datetime import datetime
#     tasks = []
#     for file in files:
#         DocumentService.update_by_id(
#             file["id"],
#             {
#                 "run": TaskStatus.RUNNING.value,
#                 "progress": 0,
#                 "progress_msg": "",
#                 "process_begin_at": datetime.now(),
#             },
#         )
#         task = {
#             "id": get_uuid(),
#             "doc_id": file["id"],
#             "task_type": "parse_author_info",
#             "progress": 0.0,
#             "from_page": 0,
#             "to_page": 100000000,
#             "begin_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
#         }
#         tasks.append(task)

#     if tasks:
#         bulk_insert_into_db(Task, tasks, True)
#         for task in tasks:
#             REDIS_CONN.queue_product(settings.get_svr_queue_name(0), message=task)

#     return get_json_result(data=files)

def validate_knowledge_tags(tags: dict):
    """
    前端传入格式：
    {
        "subject": ["medicine"],
        "doc_type": ["paper"],
        "keyword": ["ai", "imaging"]
    }

    返回 normalized_tags：
    {
        "subject": ["medicine"],
        "doc_type": ["paper"],
        "keyword": ["ai", "imaging"]
    }
    """

    if not isinstance(tags, dict):
        raise ValueError("Tags must be an object.")

    tag_types = list(
        KnowledgeTagType.select()
        .where(KnowledgeTagType.enabled == True)
    )

    type_map = {
        t.type_code: t
        for t in tag_types
    }

    options = list(
        KnowledgeTagOption.select()
        .where(KnowledgeTagOption.enabled == True)
    )

    option_map = {}

    for opt in options:
        option_map.setdefault(opt.type_code, set()).add(opt.option_code)

    normalized = {}

    # 校验前端传过来的标签
    for type_code, selected_options in tags.items():
        if type_code not in type_map:
            raise ValueError(f"Invalid tag type: {type_code}")

        if not isinstance(selected_options, list):
            raise ValueError(f"Tag value of {type_code} must be a list.")

        # 去重，保持顺序
        selected_options = list(dict.fromkeys(selected_options))

        tag_type = type_map[type_code]

        # 单选标签不能传多个
        if not tag_type.multi_select and len(selected_options) > 1:
            raise ValueError(f"{tag_type.type_name} only allows single select.")

        valid_options = option_map.get(type_code, set())

        for option_code in selected_options:
            if option_code not in valid_options:
                raise ValueError(
                    f"Invalid option {option_code} for tag type {type_code}."
                )

        normalized[type_code] = selected_options

    # 校验必填标签
    for tag_type in tag_types:
        if tag_type.required:
            selected = normalized.get(tag_type.type_code)

            if not selected:
                raise ValueError(f"{tag_type.type_name} is required.")

    return normalized

# @manager.route("/upload", methods=["POST"])  # noqa: F821
# @login_required
# @validate_request("kb_id")
# async def upload():
#     import os
#     import json
#     import logging
#     from pathlib import Path
#     from datetime import datetime

#     # =========================
#     # 1. 获取表单参数
#     # =========================
#     form = await request.form

#     # 先固定当前用户 ID，后面不要反复直接用 current_user.id
#     if not current_user or not getattr(current_user, "id", None):
#         return get_json_result(
#             data=False,
#             message="No authorization.",
#             code=RetCode.AUTHENTICATION_ERROR,
#         )

#     user_id = current_user.id


#     kb_id = form.get("kb_id")
#     tags_text = form.get("tags")
#     # parse_on_creation_text = form.get("parseOnCreation", "false")
#     # parse_on_approval = str(parse_on_creation_text).lower() in [
#     #     "true",
#     #     "1",
#     #     "yes",
#     #     "on",
#     # ]

#     if not kb_id:
#         return get_json_result(
#             data=False,
#             message='Lack of "KB ID"',
#             code=RetCode.ARGUMENT_ERROR,
#         )

#     # =========================
#     # 2. 解析 tags
#     # =========================
#     try:
#         tags = json.loads(tags_text or "{}")
#     except Exception:
#         return get_json_result(
#             data=False,
#             message="Invalid tags format.",
#             code=RetCode.ARGUMENT_ERROR,
#         )

#     # =========================
#     # 3. 校验 tags
#     # =========================
#     try:
#         normalized_tags = validate_knowledge_tags(tags)
#     except Exception as e:
#         return get_json_result(
#             data=False,
#             message=str(e),
#             code=RetCode.ARGUMENT_ERROR,
#         )

#     # =========================
#     # 4. 获取文件
#     # =========================
#     files = await request.files

#     if "file" not in files:
#         return get_json_result(
#             data=False,
#             message="No file part!",
#             code=RetCode.ARGUMENT_ERROR,
#         )

#     file_objs = files.getlist("file")

#     if not file_objs:
#         return get_json_result(
#             data=False,
#             message="No file selected!",
#             code=RetCode.ARGUMENT_ERROR,
#         )

#     # =========================
#     # 5. 基础文件校验
#     # =========================
#     for file_obj in file_objs:
#         if file_obj.filename == "":
#             return get_json_result(
#                 data=False,
#                 message="No file selected!",
#                 code=RetCode.ARGUMENT_ERROR,
#             )

#         if len(file_obj.filename.encode("utf-8")) > FILE_NAME_LEN_LIMIT:
#             return get_json_result(
#                 data=False,
#                 message=f"File name must be {FILE_NAME_LEN_LIMIT} bytes or less.",
#                 code=RetCode.ARGUMENT_ERROR,
#             )

#         filetype = filename_type(file_obj.filename)

#         if filetype == FileType.OTHER.value:
#             return get_json_result(
#                 data=False,
#                 message=f"{file_obj.filename}: This type of file has not been supported yet!",
#                 code=RetCode.ARGUMENT_ERROR,
#             )

#     # =========================
#     # 6. 获取知识库
#     # =========================
#     e, kb = KnowledgebaseService.get_by_id(kb_id)

#     if not e:
#         raise LookupError("Can't find this dataset!")

#     # =========================
#     # 7. 权限校验
#     # =========================
#     if not check_kb_team_write_permission(kb, user_id):
#         return get_json_result(
#             data=False,
#             message="No authorization.",
#             code=RetCode.AUTHENTICATION_ERROR,
#         )

#     # 本次上传实际审批链。不要直接使用 get_kb_approvers，
#     # 因为需要排除上传人自己。
#     approval_chain = StagedFileService.get_upload_approvers(
#         kb_id=kb.id,
#         uploader_user_id=user_id,
#     )
#     level_1_approvers = approval_chain.get("level_1", [])
#     level_2_approvers = approval_chain.get("level_2", [])

#     # =========================
#     # 8. 生成本次上传批次 ID
#     # =========================
#     batch_id = get_uuid()

#     # =========================
#     # 9. 创建服务器本地暂存目录
#     # =========================
#     # 默认放到项目目录下：/home/zyb/rag-flow/runtime/staging_upload
#     # 当前文件：/home/zyb/rag-flow/api/apps/document_app.py
#     # parents[0] = /home/zyb/rag-flow/api/apps
#     # parents[1] = /home/zyb/rag-flow/api
#     # parents[2] = /home/zyb/rag-flow
#     # runtime/staging_upload/{kb_id}/{user_id}/文件名
#     project_root = Path(__file__).resolve().parents[2]

#     base_stage_dir = os.environ.get(
#         "STAGING_UPLOAD_DIR",
#         str(project_root / "runtime" / "staging_upload"),
#     )

#     stage_dir = os.path.join(
#         base_stage_dir,
#         kb.id,
#         user_id,
#     )

#     os.makedirs(stage_dir, exist_ok=True)

#     staged_files = []

#     # 如果中途失败，用于清理已经保存的本地文件
#     saved_paths = []

#     try:
#         # =========================
#         # 10. 循环处理每个文件
#         # =========================

#         def get_available_stage_path(stage_dir, filename):
#             safe_name = Path(filename).name
#             stem = Path(safe_name).stem
#             suffix = Path(safe_name).suffix

#             candidate = os.path.join(stage_dir, safe_name)
#             index = 1

#             while os.path.exists(candidate):
#                 candidate = os.path.join(
#                     stage_dir,
#                     f"{stem}({index}){suffix}",
#                 )
#                 index += 1

#             return candidate
#         for file_obj in file_objs:
#             filename = file_obj.filename

#             stage_id = get_uuid()

#             suffix = Path(filename).suffix

#             # 实际落盘文件名不要直接使用用户上传的 filename
#             # 防止重名、路径穿越、特殊字符问题
#             # local_filename = f"{stage_id}{suffix}"

#             stage_path = get_available_stage_path(stage_dir, filename)

#             # 读取上传文件内容
#             blob = file_obj.read()

#             # 写入服务器本地暂存区
#             with open(stage_path, "wb") as f:
#                 f.write(blob)

#             saved_paths.append(stage_path)

#             now = datetime.now()

#             # =========================
#             # 11. 写入数据库
#             # =========================
#             # 如果你的项目里 DB 是 Peewee 数据库对象，建议使用 DB.atomic()
#             # 如果没有 DB.atomic，可以去掉 with DB.atomic()
#             with DB.atomic():
#                 StagedFile.insert({
#                     "id": stage_id,
#                     "batch_id": batch_id,
#                     "kb_id": kb.id,
#                     "tenant_id": kb.tenant_id,
#                     "user_id": user_id,
#                     "filename": filename,
#                     "path": stage_path,
#                     "size": len(blob),
#                     "status": "pending",

#                     # 保存上传当时的实际审批人员快照
#                     "approval_level_1": level_1_approvers,
#                     "approval_level_2": level_2_approvers,

#                     "created_at": now,
#                 }).execute()

#                 tag_rows = []

#                 # 本次上传面板选择的一套标签，复制给每个文件
#                 for type_code, option_codes in normalized_tags.items():
#                     for option_code in option_codes:
#                         tag_rows.append({
#                             "stage_id": stage_id,
#                             "type_code": type_code,
#                             "option_code": option_code,
#                             "create_time": now,
#                         })

#                 if tag_rows:
#                     StagedFileTag.insert_many(tag_rows).execute()

#             staged_files.append({
#                 "id": stage_id,
#                 "batch_id": batch_id,
#                 "kb_id": kb.id,
#                 "tenant_id": kb.tenant_id,
#                 "filename": filename,
#                 "path": stage_path,
#                 "size": len(blob),
#                 "status": "pending",
#                 "tags": normalized_tags,
#             })

#     except Exception as e:
#         logging.exception("Stage upload failed.")

#         # =========================
#         # 12. 失败时清理已经落盘的文件
#         # =========================
#         for path in saved_paths:
#             try:
#                 if os.path.exists(path):
#                     os.remove(path)
#             except Exception:
#                 logging.exception("Remove staged file failed: %s", path)

#         return get_json_result(
#             data=staged_files,
#             message=str(e),
#             code=RetCode.SERVER_ERROR,
#         )

#     # =========================
#     # 13. 返回暂存结果
#     # =========================
#     return get_json_result(
#     data={
#         "batch_id": batch_id,
#         "files": staged_files,
#         "approvers": approval_chain,
#     }
# )

import hmac
import hashlib
import json


def make_oa_signature(payload: dict, secret: str) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hmac.new(
        secret.encode("utf-8"),
        raw.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

# 模拟发送OA侧
async def send_oa_approval_request(
    batch_id,
    kb,
    uploader_id,
    staged_files,
    normalized_tags,
    approval_chain,
):
    import os
    import httpx
    import time

    # oa_url = os.environ.get("OA_APPROVAL_URL")
    # callback_url = os.environ.get("OA_CALLBACK_URL")
    oa_url='http://127.0.0.1:9380/v1/document/oa/mock/create'
    callback_url='http://127.0.0.1:9380/v1/document/oa/approval/callback'
    oa_app_id = os.environ.get("OA_APP_ID", "ragflow")
    oa_secret = os.environ.get("OA_SECRET", "")

    if not oa_url:
        raise RuntimeError("Missing OA_APPROVAL_URL")

    if not callback_url:
        raise RuntimeError("Missing OA_CALLBACK_URL")

    payload = {
        "app_id": oa_app_id,
        "request_type": "ragflow_document_upload_approval",
        "batch_id": batch_id,
        "kb_id": kb.id,
        "tenant_id": kb.tenant_id,
        "uploader_user_id": uploader_id,
        "callback_url": callback_url,
        "timestamp": int(time.time()),
        "files": [
            {
                "stage_id": f["id"],
                "filename": f["filename"],
                "size": f["size"],
                "url": f["url"],
                "bucket": f.get("bucket"),
                "object_name": f.get("object_name"),
                "tags": f.get("tags", {}),
            }
            for f in staged_files
        ],
        "tags": normalized_tags,
        "approvers": approval_chain,
    }

    signature = make_oa_signature(payload, oa_secret) if oa_secret else ""

    headers = {
        "Content-Type": "application/json",
        "X-OA-App-Id": oa_app_id,
    }

    if signature:
        headers["X-OA-Signature"] = signature

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            oa_url,
            json=payload,
            headers=headers,
        )

    if resp.status_code >= 400:
        raise RuntimeError(f"Submit OA approval failed: {resp.status_code}, {resp.text}")

    try:
        result = resp.json()
    except Exception:
        raise RuntimeError(f"Invalid OA response: {resp.text}")

    return result

"""
校验参数
保存本地
上传 MinIO 临时桶
生成 presigned URL
写 StagedFile / StagedFileTag
发给 OA 创建审批单
保存 OA 返回的 oa_request_id
"""
@manager.route("/upload", methods=["POST"])  # noqa: F821
@login_required
@validate_request("kb_id")
async def upload():
    import os
    import json
    import logging
    from pathlib import Path
    from datetime import datetime, timedelta
    from io import BytesIO
    import httpx

    form = await request.form

    # 1. 登录校验
    if not current_user or not getattr(current_user, "id", None):
        return get_json_result(
            data=False,
            message="No authorization.",
            code=RetCode.AUTHENTICATION_ERROR,
        )

    uploader_id = current_user.id
    kb_id = form.get("kb_id")
    tags_text = form.get("tags")
    version_text = form.get("version")
    print(version_text)
    try:
        document_version = normalize_document_version(
            version_text
        )
    except ValueError as e:
        return get_json_result(
            data=False,
            message=str(e),
            code=RetCode.ARGUMENT_ERROR,
        )
    # 新增判断当前用户是否存在上传权限
    # 判断用户是否拥有上传权限
    if not user_has_operation_permission(uploader_id, "upload"):
        return get_json_result(
            data=False,
            message="没有上传权限",
            code=RetCode.FORBIDDEN,
        )

    if not kb_id:
        return get_json_result(
            data=False,
            message='Lack of "KB ID"',
            code=RetCode.ARGUMENT_ERROR,
        )

    # 2. 标签解析
    try:
        tags = json.loads(tags_text or "{}")
    except Exception:
        return get_json_result(
            data=False,
            message="Invalid tags format.",
            code=RetCode.ARGUMENT_ERROR,
        )

    try:
        normalized_tags = validate_knowledge_tags(tags)
    except Exception as e:
        return get_json_result(
            data=False,
            message=str(e),
            code=RetCode.ARGUMENT_ERROR,
        )

    # 3. 文件校验
    files = await request.files
    if "file" not in files:
        return get_json_result(
            data=False,
            message="No file part!",
            code=RetCode.ARGUMENT_ERROR,
        )

    file_objs = files.getlist("file")
    if not file_objs:
        return get_json_result(
            data=False,
            message="No file selected!",
            code=RetCode.ARGUMENT_ERROR,
        )

    for file_obj in file_objs:
        if file_obj.filename == "":
            return get_json_result(
                data=False,
                message="No file selected!",
                code=RetCode.ARGUMENT_ERROR,
            )

        if len(file_obj.filename.encode("utf-8")) > FILE_NAME_LEN_LIMIT:
            return get_json_result(
                data=False,
                message=f"File name must be {FILE_NAME_LEN_LIMIT} bytes or less.",
                code=RetCode.ARGUMENT_ERROR,
            )

        filetype = filename_type(file_obj.filename)
        if filetype == FileType.OTHER.value:
            return get_json_result(
                data=False,
                message=f"{file_obj.filename}: This type of file has not been supported yet!",
                code=RetCode.ARGUMENT_ERROR,
            )

    # 4. 知识库校验
    e, kb = KnowledgebaseService.get_by_id(kb_id)
    if not e:
        raise LookupError("Can't find this dataset!")

    if not check_kb_team_write_permission(kb, uploader_id):
        return get_json_result(
            data=False,
            message="No authorization.",
            code=RetCode.AUTHENTICATION_ERROR,
        )

    # 5. 获取审批人
    approval_chain = StagedFileService.get_upload_approvers(
        kb_id=kb.id,
        uploader_user_id=uploader_id,
    )
    level_1_approvers = approval_chain.get("level_1", [])
    level_2_approvers = approval_chain.get("level_2", [])

    # 6. RAGFlow 本地计算初始审批状态
    if level_1_approvers:
        init_status = "pending_level_1"
        init_current_level = 1
    elif level_2_approvers:
        init_status = "pending_level_2"
        init_current_level = 2
    else:
        init_status = "approved"
        init_current_level = 0

    batch_id = get_uuid()

    project_root = Path(__file__).resolve().parents[2]
    base_stage_dir = os.environ.get(
        "STAGING_UPLOAD_DIR",
        str(project_root / "runtime" / "staging_upload"),
    )

    stage_dir = os.path.join(base_stage_dir, kb.id, uploader_id)
    os.makedirs(stage_dir, exist_ok=True)

    temp_bucket = os.environ.get("STAGING_MINIO_BUCKET", "temp-upload")
    client = settings.STORAGE_IMPL.conn

    staged_files = []
    saved_paths = []
    saved_objects = []

    def get_available_stage_path(stage_dir, filename):
        safe_name = Path(filename).name
        stem = Path(safe_name).stem
        suffix = Path(safe_name).suffix

        candidate = os.path.join(stage_dir, safe_name)
        index = 1
        while os.path.exists(candidate):
            candidate = os.path.join(stage_dir, f"{stem}({index}){suffix}")
            index += 1
        return candidate

    try:
        # 7. 创建 MinIO 临时桶
        if not client.bucket_exists(temp_bucket):
            client.make_bucket(temp_bucket)

        # 8. 逐文件暂存
        for file_obj in file_objs:
            filename = file_obj.filename
            safe_filename = Path(filename).name
            stage_id = get_uuid()

            object_name = f"{kb.id}/{uploader_id}/{batch_id}/{stage_id}/{safe_filename}"

            blob = file_obj.read()

            # 保存本地
            stage_path = get_available_stage_path(stage_dir, safe_filename)
            with open(stage_path, "wb") as f:
                f.write(blob)
            saved_paths.append(stage_path)

            # 上传 MinIO 临时桶
            client.put_object(
                temp_bucket,
                object_name,
                BytesIO(blob),
                len(blob),
            )
            saved_objects.append((temp_bucket, object_name))

            # 生成预签名 URL
            file_url = client.presigned_get_object(
                temp_bucket,
                object_name,
                expires=timedelta(days=7),
            )

            now = datetime.now()

            # 写暂存文件表和标签表
            with DB.atomic():
                StagedFile.insert({
                    "id": stage_id,
                    "batch_id": batch_id,
                    "kb_id": kb.id,
                    "tenant_id": kb.tenant_id,
                    "user_id": uploader_id,
                    "filename": filename,
                    "path": stage_path,
                    "size": len(blob),
                    # 新增
                    "version": document_version,
                    "status": "pending",
                    "approval_level_1": level_1_approvers,
                    "approval_level_2": level_2_approvers,
                    "minio_bucket": temp_bucket,
                    "minio_object_name": object_name,
                    "url": file_url,
                    "created_at": now,
                }).execute()

                tag_rows = []
                for type_code, option_codes in normalized_tags.items():
                    for option_code in option_codes:
                        tag_rows.append({
                            "stage_id": stage_id,
                            "type_code": type_code,
                            "option_code": option_code,
                            "create_time": now,
                        })

                if tag_rows:
                    StagedFileTag.insert_many(tag_rows).execute()

            staged_files.append({
                "id": stage_id,
                "batch_id": batch_id,
                "kb_id": kb.id,
                "tenant_id": kb.tenant_id,
                "user_id": uploader_id,
                "filename": filename,
                "version": document_version,
                "path": stage_path,
                "bucket": temp_bucket,
                "object_name": object_name,
                "url": file_url,
                "size": len(blob),
                "status": "pending",
                "tags": normalized_tags,
            })

        # 9. 提交给 OA
        # 建议正式环境使用环境变量
        # oa_url = os.environ.get("OA_APPROVAL_URL")
        # callback_url = os.environ.get("OA_CALLBACK_URL")

        oa_url = "http://localhost:9222/v1/document/oa/approval/create"
        callback_url = "http://localhost:9222/v1/document/oa/approval/callback"
        oa_app_id = os.environ.get("OA_APP_ID", "ragflow")
        oa_secret = os.environ.get("OA_SECRET", "")

        if not oa_url:
            raise RuntimeError("Missing OA_APPROVAL_URL")
        if not callback_url:
            raise RuntimeError("Missing OA_CALLBACK_URL")

        oa_payload = {
            "app_id": oa_app_id,
            "batch_id": batch_id,
            "kb_id": kb.id,
            "tenant_id": kb.tenant_id,
            "uploader_user_id": uploader_id,
            "callback_url": callback_url,
            "files": staged_files,
            "approvers": approval_chain,
            "timestamp": int(datetime.now().timestamp()),
        }

        headers = {
            "Content-Type": "application/json",
            "X-OA-App-Id": oa_app_id,
        }
        if oa_secret:
            headers["X-OA-Signature"] = make_oa_signature(oa_payload, oa_secret)

        async with httpx.AsyncClient(timeout=30) as http_client:
            resp = await http_client.post(
                oa_url,
                json=oa_payload,
                headers=headers,
            )

        if resp.status_code >= 400:
            raise RuntimeError(
                f"Submit OA approval failed: {resp.status_code}, {resp.text}"
            )

        # 10. 极简协议：OA 只返回 request_id
        oa_resp_json = resp.json()
        print(oa_resp_json)

        oa_data = oa_resp_json.get("data", {})
        oa_request_id = oa_data.get("request_id")

        if not oa_request_id:
            raise RuntimeError(f"OA response missing request_id: {resp.text}")

        now = datetime.now()

        # 11. 写 RAGFlow 审批主表和审批任务表
        with DB.atomic():
            StagedFileApprovalRequest.insert({
                "id": oa_request_id,
                "batch_id": batch_id,
                "kb_id": kb.id,
                "tenant_id": kb.tenant_id,
                "uploader_user_id": uploader_id,
                "status": init_status,
                "current_level": init_current_level,
                "callback_url": callback_url,
                "created_at": now,
                "updated_at": now,
            }).execute()

            # 一级审批任务：每个审批人一条，不按文件拆
            for approver in level_1_approvers:
                approver_user_id = approver["user_id"] if isinstance(approver, dict) else approver
                approver_name = approver.get("name") if isinstance(approver, dict) else None

                StagedFileApprovalTask.insert({
                    "approval_id": oa_request_id,
                    "batch_id": batch_id,
                    "level": 1,
                    "approver_user_id": approver_user_id,
                    "approver_name": approver_name,
                    "status": "pending",
                    "created_at": now,
                    "updated_at": now,
                }).execute()

            # 二级审批任务：每个审批人一条，不按文件拆
            for approver in level_2_approvers:
                approver_user_id = approver["user_id"] if isinstance(approver, dict) else approver
                approver_name = approver.get("name") if isinstance(approver, dict) else None

                StagedFileApprovalTask.insert({
                    "approval_id": oa_request_id,
                    "batch_id": batch_id,
                    "level": 2,
                    "approver_user_id": approver_user_id,
                    "approver_name": approver_name,
                    "status": "waiting",
                    "created_at": now,
                    "updated_at": now,
                }).execute()

            # 整批文件状态更新为已提交 OA
            StagedFile.update({
                "status": "oa_submitted",
            }).where(
                StagedFile.batch_id == batch_id
            ).execute()

        return get_json_result(
            data={
                "batch_id": batch_id,
                "oa_request_id": oa_request_id,
                "oa_status": "submitted",
                "files": staged_files,
                "approvers": approval_chain,
                "oa_response": oa_resp_json,
            }
        )

    except Exception as e:
        logging.exception("Stage upload failed.")

        # 清理本地暂存文件
        for path in saved_paths:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception:
                logging.exception("Remove staged file failed: %s", path)

        # 清理 MinIO 临时对象
        for bucket, obj_name in saved_objects:
            try:
                client.remove_object(bucket, obj_name)
            except Exception:
                logging.exception(
                    "Remove staged minio object failed: %s/%s",
                    bucket,
                    obj_name,
                )

        return get_json_result(
            data=staged_files,
            message=str(e),
            code=RetCode.SERVER_ERROR,
        )

# OA 侧：创建审批单 (写入主表 和 审批任务表 激活1级 等待2级)
@manager.route("/oa/approval/create", methods=["POST"])  # OA 侧接口
async def create_approval_request():
    import os
    from datetime import datetime

    oa_secret = os.environ.get("OA_SECRET", "")
    expected_app_id = os.environ.get("OA_APP_ID", "ragflow")

    data = await request.get_json()
    if not data:
        return get_json_result(
            data=False,
            message="Empty request body.",
            code=RetCode.ARGUMENT_ERROR,
        )

    if data.get("app_id") != expected_app_id:
        return get_json_result(
            data=False,
            message="Invalid app_id.",
            code=RetCode.AUTHENTICATION_ERROR,
        )

    recv_signature = request.headers.get("X-OA-Signature", "")
    if oa_secret:
        expected_signature = make_oa_signature(data, oa_secret)
        if recv_signature != expected_signature:
            return get_json_result(
                data=False,
                message="Invalid signature.",
                code=RetCode.AUTHENTICATION_ERROR,
            )

    batch_id = data["batch_id"]
    kb_id = data["kb_id"]
    tenant_id = data["tenant_id"]
    uploader_user_id = data["uploader_user_id"]
    callback_url = data["callback_url"]
    files = data.get("files", [])
    approvers = data.get("approvers", {})

    level_1 = approvers.get("level_1", [])
    level_2 = approvers.get("level_2", [])

    if not files:
        return get_json_result(
            data=False,
            message="no files",
            code=RetCode.ARGUMENT_ERROR,
        )

    approval_id = get_uuid()

    if level_1:
        status = "pending_level_1"
        current_level = 1
    elif level_2:
        status = "pending_level_2"
        current_level = 2
    else:
        status = "approved"
        current_level = 0

    now = datetime.now()

    with DB.atomic():
        OAApprovalRequest.insert({
            "id": approval_id,
            "batch_id": batch_id,
            "kb_id": kb_id,
            "tenant_id": tenant_id,
            "uploader_user_id": uploader_user_id,
            "callback_url": callback_url,
            "status": status,
            "current_level": current_level,
            "files_json": files,
            "approvers_json": approvers,
            "created_at": now,
            "updated_at": now,
        }).execute()

        for approver in level_1:
            approver_user_id = approver["user_id"] if isinstance(approver, dict) else approver
            approver_name = approver.get("name") if isinstance(approver, dict) else None

            OAApprovalTask.insert({
                "approval_id": approval_id,
                "batch_id": batch_id,
                "level": 1,
                "approver_user_id": approver_user_id,
                "approver_name": approver_name,
                "status": "pending",
                "created_at": now,
                "updated_at": now,
            }).execute()

        for approver in level_2:
            approver_user_id = approver["user_id"] if isinstance(approver, dict) else approver
            approver_name = approver.get("name") if isinstance(approver, dict) else None

            OAApprovalTask.insert({
                "approval_id": approval_id,
                "batch_id": batch_id,
                "level": 2,
                "approver_user_id": approver_user_id,
                "approver_name": approver_name,
                "status": "waiting",
                "created_at": now,
                "updated_at": now,
            }).execute()

    # 极简协议：只返回 request_id
    return get_json_result(
        data={
            "request_id": approval_id,
        }
    )

@manager.route("/oa/approval/level1/tasks", methods=["GET"])  # noqa: F821
async def list_level1_approval_tasks():
    approver_user_id = str(
        request.args.get("approver_user_id") or ""
    ).strip()

    if not approver_user_id:
        return get_json_result(
            data=False,
            message="Missing approver_user_id.",
            code=RetCode.ARGUMENT_ERROR,
        )

    tasks = list(
        OAApprovalTask.select()
        .where(
            (OAApprovalTask.approver_user_id == approver_user_id) &
            (OAApprovalTask.level == 1) &
            (OAApprovalTask.status == "pending")
        )
        .order_by(OAApprovalTask.created_at.desc())
    )

    rows = []

    for task in tasks:
        approval = OAApprovalRequest.select().where(
            OAApprovalRequest.id == task.approval_id
        ).first()

        if not approval:
            continue

        files = approval.files_json or []
        approvers = approval.approvers_json or {}

        rows.append({
            "approval_id": approval.id,
            "batch_id": approval.batch_id,
            "kb_id": approval.kb_id,
            "tenant_id": approval.tenant_id,
            "uploader_user_id": approval.uploader_user_id,
            "approval_status": approval.status,
            "current_level": approval.current_level,
            "task_id": getattr(task, "id", None),
            "task_level": task.level,
            "task_status": task.status,
            "approver_user_id": task.approver_user_id,
            "approver_name": task.approver_name,
            "file_count": len(files),
            "files": files,
            "level_1_approvers": approvers.get("level_1", []),
            "created_at": (
                approval.created_at.strftime("%Y-%m-%d %H:%M:%S")
                if approval.created_at else None
            ),
            "updated_at": (
                approval.updated_at.strftime("%Y-%m-%d %H:%M:%S")
                if approval.updated_at else None
            ),
        })

    return get_json_result(data=rows)

@manager.route("/oa/approval/detail", methods=["GET"])  # noqa: F821
async def approval_detail():
    approval_id = request.args.get("approval_id")

    if not approval_id:
        return get_json_result(
            data=False,
            message="Missing approval_id.",
            code=RetCode.ARGUMENT_ERROR,
        )

    approval = OAApprovalRequest.select().where(
        OAApprovalRequest.id == approval_id
    ).first()

    if not approval:
        return get_json_result(
            data=False,
            message="Approval request not found.",
            code=RetCode.DATA_ERROR,
        )

    files = approval.files_json or []
    approvers = approval.approvers_json or {}

    level1_tasks = list(
        OAApprovalTask.select().where(
            (OAApprovalTask.approval_id == approval_id) &
            (OAApprovalTask.level == 1)
        ).order_by(OAApprovalTask.created_at.asc())
    )

    tasks = []

    for task in level1_tasks:
        tasks.append({
            "task_id": task.id if hasattr(task, "id") else None,
            "approval_id": task.approval_id,
            "batch_id": task.batch_id,
            "level": task.level,
            "approver_user_id": task.approver_user_id,
            "approver_name": task.approver_name,
            "status": task.status,
            "comment": getattr(task, "comment", ""),
            "created_at": task.created_at.strftime("%Y-%m-%d %H:%M:%S") if task.created_at else None,
            "updated_at": task.updated_at.strftime("%Y-%m-%d %H:%M:%S") if task.updated_at else None,
        })

    return get_json_result(
        data={
            "approval_id": approval.id,
            "batch_id": approval.batch_id,
            "kb_id": approval.kb_id,
            "tenant_id": approval.tenant_id,
            "uploader_user_id": approval.uploader_user_id,
            "callback_url": approval.callback_url,
            "status": approval.status,
            "current_level": approval.current_level,

            "files": files,
            "approvers": approvers,
            "level_1_approvers": approvers.get("level_1", []),
            "tasks": tasks,

            "created_at": approval.created_at.strftime("%Y-%m-%d %H:%M:%S") if approval.created_at else None,
            "updated_at": approval.updated_at.strftime("%Y-%m-%d %H:%M:%S") if approval.updated_at else None,
        }
    )


@manager.route("/oa/approval/decision", methods=["POST"])  # noqa: F821
async def approval_decision():
    import os
    import httpx
    from datetime import datetime

    req = await get_request_json()

    approval_id = req.get("approval_id")
    approver_user_id = req.get("approver_user_id")
    approver_user_name = req.get("approver_user_name")
    result = req.get("result")
    comment = req.get("comment", "")

    if not approval_id:
        return get_json_result(
            data=False,
            message="Missing approval_id.",
            code=RetCode.ARGUMENT_ERROR,
        )

    if not approver_user_id:
        return get_json_result(
            data=False,
            message="Missing approver_user_id.",
            code=RetCode.ARGUMENT_ERROR,
        )

    if result not in ["approved", "rejected"]:
        return get_json_result(
            data=False,
            message="Invalid result, must be approved or rejected.",
            code=RetCode.ARGUMENT_ERROR,
        )

    approval = OAApprovalRequest.select().where(
        OAApprovalRequest.id == approval_id
    ).first()

    if not approval:
        return get_json_result(
            data=False,
            message="Approval request not found.",
            code=RetCode.DATA_ERROR,
        )

    if approval.status in ["approved", "rejected", "callback_success", "imported"]:
        return get_json_result(
            data={
                "approval_id": approval_id,
                "status": approval.status,
                "message": "Already processed.",
            }
        )

    task = OAApprovalTask.select().where(
        (OAApprovalTask.approval_id == approval_id) &
        (OAApprovalTask.level == 1) &
        (OAApprovalTask.approver_user_id == approver_user_id) &
        (OAApprovalTask.status == "pending")
    ).first()

    if not task:
        return get_json_result(
            data=False,
            message="No pending level 1 approval task found.",
            code=RetCode.AUTHENTICATION_ERROR,
        )

    now = datetime.now()

    # 1. 更新 OA 侧审批状态
    with DB.atomic():
        task_update_data = {
            "status": result,
            "updated_at": now,
        }

        if hasattr(OAApprovalTask, "comment"):
            task_update_data["comment"] = comment

        OAApprovalTask.update(task_update_data).where(
            OAApprovalTask.id == task.id
        ).execute()

        OAApprovalRequest.update({
            "status": result,
            "current_level": 0,
            "updated_at": now,
        }).where(
            OAApprovalRequest.id == approval_id
        ).execute()

    # 2. 固定回调 RAGFlow 地址
    callback_url = "http://127.0.0.1:9380/v1/document/oa/approval/callback"

    callback_payload = {
        "oa_request_id": approval.id,
        "result": result,
        "comment": comment,
        "approver": {
            "user_id": approver_user_id,
            "user_name": approver_user_name,
        },
        "timestamp": int(now.timestamp()),
    }

    headers = {
        "Content-Type": "application/json",
    }

    oa_secret = os.environ.get("OA_SECRET", "")
    if oa_secret:
        headers["X-OA-Signature"] = make_oa_signature(
            callback_payload,
            oa_secret,
        )

    # 3. 回调 RAGFlow
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                callback_url,
                json=callback_payload,
                headers=headers,
            )

        try:
            callback_response = resp.json()
        except Exception:
            callback_response = {"raw": resp.text}

        callback_code = callback_response.get("code")

        if resp.status_code >= 400 or callback_code not in [0, "0", None]:
            with DB.atomic():
                OAApprovalRequest.update({
                    "status": "callback_failed",
                }).where(
                    OAApprovalRequest.id == approval_id
                ).execute()

            return get_json_result(
                data={
                    "approval_id": approval_id,
                    "result": result,
                    "callback_url": callback_url,
                    "callback_status_code": resp.status_code,
                    "callback_response": callback_response,
                },
                message=callback_response.get("message") or f"Callback failed: {resp.status_code}",
                code=RetCode.SERVER_ERROR,
            )

        # 4. 回调成功
        with DB.atomic():
            OAApprovalRequest.update({
                "status": "callback_success",
                "updated_at": datetime.now(),
            }).where(
                OAApprovalRequest.id == approval_id
            ).execute()

        return get_json_result(
            data={
                "approval_id": approval_id,
                "result": result,
                "callback_url": callback_url,
                "callback_status": "success",
                "callback_response": callback_response,
            }
        )

    except Exception as e:
        with DB.atomic():
            OAApprovalRequest.update({
                "status": "callback_failed",
                "updated_at": datetime.now(),
            }).where(
                OAApprovalRequest.id == approval_id
            ).execute()

        return get_json_result(
            data=False,
            message=f"Callback exception: {str(e)}",
            code=RetCode.SERVER_ERROR,
        )

# OA 审批动作处理
# {
#   "approval_id": "oa_xxx",
#   "batch_id": "batch_xxx",
#   "approver_user_id": "u1",
#   "approver_name": "张三",
#   "level": 1,
#   "action": "approved",
#   "comment": "同意"
# }


@manager.route("/oa/approval/task/handle", methods=["POST"])
async def handle_approval_task():
    import os
    from datetime import datetime

    oa_secret = os.environ.get("OA_SECRET", "")
    expected_app_id = os.environ.get("OA_APP_ID", "ragflow")

    data = await request.get_json()
    if not data:
        return get_json_result(
            data=False,
            message="Empty request body.",
            code=RetCode.ARGUMENT_ERROR,
        )

    approval_id = data["approval_id"]
    batch_id = data["batch_id"]
    approver_user_id = data["approver_user_id"]
    approver_name = data.get("approver_name", "")
    level = data["level"]
    action = data["action"]   # approved / rejected
    comment = data.get("comment", "")

    approval = OAApprovalRequest.get_or_none(OAApprovalRequest.id == approval_id)
    if not approval:
        return get_json_result(
            data=False,
            message="approval not found",
            code=RetCode.NOT_FOUND,
        )

    if approval.status in ["approved", "rejected"]:
        return get_json_result(
            data=True,
            message="already finished",
        )

    task = OAApprovalTask.get_or_none(
        (OAApprovalTask.approval_id == approval_id) &
        (OAApprovalTask.batch_id == batch_id) &
        (OAApprovalTask.level == level) &
        (OAApprovalTask.approver_user_id == approver_user_id)
    )

    if not task:
        return get_json_result(
            data=False,
            message="task not found",
            code=RetCode.NOT_FOUND,
        )

    if task.status in ["approved", "rejected"]:
        return get_json_result(
            data=True,
            message="task already processed",
        )

    now = datetime.now()

    with DB.atomic():
        task.status = action
        task.comment = comment
        task.action_time = now
        task.updated_at = now
        task.save()

    # 每次动作都回调 RAGFlow
    callback_payload = {
        "app_id": expected_app_id,
        "request_id": approval_id,
        "batch_id": batch_id,
        "level": level,
        "approver_user_id": approver_user_id,
        "approver_name": approver_name,
        "action": action,
        "comment": comment,
        "timestamp": int(now.timestamp()),
    }

    await callback_ragflow(approval, callback_payload, oa_secret)

    if action == "rejected":
        with DB.atomic():
            approval.status = "rejected"
            approval.result = "rejected"
            approval.comment = comment
            approval.finished_at = now
            approval.updated_at = now
            approval.save()

        return get_json_result(
            data={
                "approval_id": approval_id,
                "result": "rejected",
            }
        )

    # 检查当前级别是否全部通过
    same_level_tasks = list(
        OAApprovalTask.select().where(
            (OAApprovalTask.approval_id == approval_id) &
            (OAApprovalTask.level == level)
        )
    )

    if any(t.status == "rejected" for t in same_level_tasks):
        with DB.atomic():
            approval.status = "rejected"
            approval.result = "rejected"
            approval.comment = comment
            approval.finished_at = now
            approval.updated_at = now
            approval.save()

        return get_json_result(
            data={
                "approval_id": approval_id,
                "result": "rejected",
            }
        )

    if not all(t.status == "approved" for t in same_level_tasks):
        return get_json_result(
            data={
                "approval_id": approval_id,
                "status": f"waiting_level_{level}_others",
            }
        )

    # 当前级别都通过，进入下一级
    next_level = level + 1
    next_level_tasks = list(
        OAApprovalTask.select().where(
            (OAApprovalTask.approval_id == approval_id) &
            (OAApprovalTask.level == next_level)
        )
    )

    if next_level_tasks:
        with DB.atomic():
            for t in next_level_tasks:
                t.status = "pending"
                t.updated_at = now
                t.save()

            approval.status = f"pending_level_{next_level}"
            approval.current_level = next_level
            approval.updated_at = now
            approval.save()

        return get_json_result(
            data={
                "approval_id": approval_id,
                "status": f"moved_to_level_{next_level}",
            }
        )

    # 没有下一级，最终通过
    with DB.atomic():
        approval.status = "approved"
        approval.result = "approved"
        approval.finished_at = now
        approval.updated_at = now
        approval.save()

    final_payload = {
        "app_id": expected_app_id,
        "request_id": approval_id,
        "batch_id": batch_id,
        "result": "approved",
        "comment": "all approved",
        "timestamp": int(now.timestamp()),
        "event": "approval_finished",
    }

    await callback_ragflow(approval, final_payload, oa_secret)

    return get_json_result(
        data={
            "approval_id": approval_id,
            "result": "approved",
        }
    )

# OA 回调 RAGFlow
async def callback_ragflow(approval, payload, oa_secret):
    import httpx

    signature = make_oa_signature(payload, oa_secret) if oa_secret else ""

    headers = {
        "Content-Type": "application/json",
        "X-OA-App-Id": payload["app_id"],
    }
    if signature:
        headers["X-OA-Signature"] = signature

    async with httpx.AsyncClient(timeout=30) as client:
        await client.post(
            approval.callback_url,
            json=payload,
            headers=headers,
        )

# RAGFlow 侧完整伪代码
# {
#   "app_id": "ragflow",
#   "request_id": "oa_xxx",
#   "batch_id": "batch_xxx",
#   "level": 1,
#   "approver_user_id": "u1",
#   "approver_name": "张三",
#   "action": "approved",
#   "comment": "同意",
#   "timestamp": 1730000000
# }

# {
#   "app_id": "ragflow",
#   "request_id": "oa_xxx",
#   "batch_id": "batch_xxx",
#   "level": 1,
#   "approver_user_id": "u2",
#   "approver_name": "李四",
#   "action": "rejected",
#   "comment": "资料不完整",
#   "timestamp": 1730000001
# }

class LocalStagedUploadFile:
    """
    适配 FileService.upload_document 需要的 file 对象。
    FileService.upload_document 只需要 filename 和 read()。
    """

    def __init__(self, filename, path):
        self.filename = filename
        self.path = path

    def read(self):
        with open(self.path, "rb") as f:
            return f.read()

def create_parse_author_info_task(doc_id):
    """
    无条件创建 parse_author_info 任务，并投递队列。
    对齐原上传流程：上传成功后先直接创建任务。
    """
    from datetime import datetime
    from api.db.db_utils import bulk_insert_into_db
    from rag.utils.redis_conn import REDIS_CONN

    now = datetime.now()

    task = {
        "id": get_uuid(),
        "doc_id": doc_id,
        "task_type": "parse_author_info",
        "progress": 0.0,
        "from_page": 0,
        "to_page": 100000000,
        "begin_at": now.strftime("%Y-%m-%d %H:%M:%S"),
    }

    bulk_insert_into_db(Task, [task], True)

    REDIS_CONN.queue_product(
        settings.get_svr_queue_name(0),
        message=task,
    )

    return task

def create_parse_author_info_task_if_not_exists(doc_id):
    """
    兜底创建 parse_author_info 任务。
    对齐 /run 里的逻辑：如果任务不存在才补一个。
    """
    from api.db.services.task_service import TaskService

    existing_task = TaskService.get_task_by_doc_id_and_type(
        doc_id,
        "parse_author_info",
    )

    if existing_task:
        return None

    return create_parse_author_info_task(doc_id)

# def get_staged_file_tags_map(stage_id):
#     """
#     查询暂存文件标签。
#     返回结构：
#     {
#         type_code: [option_code_1, option_code_2]
#     }
#     """
#     tag_rows = list(
#         StagedFileTag.select().where(
#             StagedFileTag.stage_id == stage_id
#         )
#     )

#     tags_map = {}

#     for row in tag_rows:
#         type_code = row.type_code
#         option_code = row.option_code

#         if not type_code or not option_code:
#             continue

#         tags_map.setdefault(type_code, [])

#         if option_code not in tags_map[type_code]:
#             tags_map[type_code].append(option_code)

#     return tags_map

def get_staged_file_tags_map(stage_id):
    """
    查询暂存文件标签，并将 option_code 转换为 option_name。

    返回结构：
    {
        type_code: [option_name_1, option_name_2]
    }

    例如：
    {
        "document_type": ["通知", "公告"]
    }
    """

    tag_rows = list(
        StagedFileTag
        .select(
            StagedFileTag.type_code,
            StagedFileTag.option_code,
        )
        .where(
            StagedFileTag.stage_id == stage_id
        )
    )

    if not tag_rows:
        return {}

    type_codes = {
        row.type_code
        for row in tag_rows
        if row.type_code
    }

    option_codes = {
        row.option_code
        for row in tag_rows
        if row.option_code
    }

    if not type_codes or not option_codes:
        return {}

    # 批量查询选项，避免每个标签单独查询一次数据库
    option_rows = list(
        KnowledgeTagOption
        .select(
            KnowledgeTagOption.type_code,
            KnowledgeTagOption.option_code,
            KnowledgeTagOption.option_name,
        )
        .where(
            (KnowledgeTagOption.type_code.in_(type_codes))
            & (KnowledgeTagOption.option_code.in_(option_codes))
        )
    )

    option_name_map = {
        (
            row.type_code,
            row.option_code,
        ): row.option_name
        for row in option_rows
    }

    tags_map = {}

    for row in tag_rows:
        type_code = row.type_code
        option_code = row.option_code

        if not type_code or not option_code:
            continue

        option_name = option_name_map.get(
            (type_code, option_code),
            option_code,
        )

        # 如果 option_name 为空，则保留 option_code
        option_name = option_name or option_code

        tags_map.setdefault(type_code, [])

        if option_name not in tags_map[type_code]:
            tags_map[type_code].append(option_name)

    return tags_map

def import_staged_files_and_run_by_callback(kb, staged_files, uploader_user_id):
    """
    OA 审批通过后，把暂存文件真正入知识库，并启动解析。

    流程：
    1. 单文件逐个入库
    2. 回写 staged_file.doc_id / committed_at
    3. 将暂存标签写入 Document.meta_fields
    4. 无条件创建 parse_author_info 任务
    5. 启动正文解析 DocumentService.run
    6. 兜底检查 parse_author_info 任务，不存在则补
    """

    import os
    import logging
    from datetime import datetime

    imported_docs = []
    import_errors = []
    kb_table_num_map = {}

    for staged in staged_files:
        try:
            # 幂等：已经回写过 doc_id，说明已经入库过
            if getattr(staged, "doc_id", None):
                imported_docs.append({
                    "stage_id": staged.id,
                    "doc_id": staged.doc_id,
                    "filename": staged.filename,
                    "status": "already_imported",
                })
                continue

            now = datetime.now()

            StagedFile.update({
                "status": "importing",
                "error_msg": None,
            }).where(
                StagedFile.id == staged.id
            ).execute()

            # 1. 构造 FileService.upload_document 需要的文件对象
            if staged.path and os.path.exists(staged.path):
                file_obj = LocalStagedUploadFile(
                    filename=staged.filename,
                    path=staged.path,
                )
            else:
                if not staged.minio_bucket or not staged.minio_object_name:
                    raise RuntimeError(
                        f"暂存文件不存在: {staged.filename}"
                    )

                client = settings.STORAGE_IMPL.conn
                resp = client.get_object(
                    staged.minio_bucket,
                    staged.minio_object_name,
                )

                try:
                    blob = resp.read()
                finally:
                    resp.close()
                    resp.release_conn()

                class MemoryUploadFile:
                    def __init__(self, filename, blob):
                        self.filename = filename
                        self._blob = blob

                    def read(self):
                        return self._blob

                file_obj = MemoryUploadFile(
                    staged.filename,
                    blob,
                )

            # 2. 真正入知识库
            # err, uploaded_files = FileService.upload_document(
            #     kb,
            #     [file_obj],
            #     uploader_user_id,
            # )
            err, uploaded_files = FileService.upload_document(
                kb,
                [file_obj],
                uploader_user_id,
                version=getattr(staged, "version", None),
                current_stage_id=staged.id,
            )

            if err:
                raise RuntimeError("\n".join(err))

            if not uploaded_files:
                raise RuntimeError(
                    f"文件入库失败: {staged.filename}"
                )

            # FileService.upload_document 返回 [(doc, blob)]
            doc = uploaded_files[0][0]
            doc_id = doc["id"]
            now = datetime.now()

            # 3. 回写暂存文件状态、正式 doc_id、入库时间
            StagedFile.update({
                "status": "imported",
                "doc_id": doc_id,
                "committed_at": now,
                "error_msg": None,
            }).where(
                StagedFile.id == staged.id
            ).execute()

            # 4. 查询暂存标签，写入正式文档 meta_fields
            tags_map = get_staged_file_tags_map(staged.id)

            success, doc_obj = DocumentService.get_by_id(doc_id)
            meta_fields = (
                dict(doc_obj.meta_fields)
                if success and doc_obj and doc_obj.meta_fields
                else {}
            )

            # 如果你确认 type_code 不会和作者解析字段冲突，可以顶层合并
            meta_fields.update(tags_map)

            # # 如果你还想保留来源信息，可以打开这几个字段
            # meta_fields.update({
            #     "stage_id": staged.id,
            #     "batch_id": staged.batch_id,
            #     "source": "oa_upload",
            # })

            DocumentService.update_by_id(
                doc_id,
                {
                    "meta_fields": meta_fields,
                    "run": TaskStatus.RUNNING.value,
                    "progress": 0,
                    "progress_msg": "",
                    "process_begin_at": now,
                },
            )

            # 5. 对齐原上传流程：先无条件创建作者信息解析任务
            create_parse_author_info_task(doc_id)

            # 6. 启动正文解析任务
            tenant_id = DocumentService.get_tenant_id(doc_id)
            if not tenant_id:
                raise RuntimeError(f"Tenant not found: {doc_id}")

            e, doc_obj = DocumentService.get_by_id(doc_id)
            if not e:
                raise RuntimeError(f"Document not found: {doc_id}")

            DocumentService.run(
                tenant_id,
                doc_obj.to_dict(),
                kb_table_num_map,
            )

            # 7. 对齐 /run 流程：兜底检查 parse_author_info 是否存在
            create_parse_author_info_task_if_not_exists(doc_id)

            imported_docs.append({
                "stage_id": staged.id,
                "doc_id": doc_id,
                "filename": staged.filename,
                "status": "imported",
                "doc": doc,
            })

        except Exception as e:
            logging.exception(
                "Import staged file failed: %s",
                getattr(staged, "filename", ""),
            )

            error_msg = str(e)

            import_errors.append({
                "stage_id": staged.id,
                "filename": staged.filename,
                "error": error_msg,
            })

            StagedFile.update({
                "status": "import_failed",
                "error_msg": error_msg,
            }).where(
                StagedFile.id == staged.id
            ).execute()

    return imported_docs, import_errors


from datetime import datetime
@manager.route("/oa/approval/callback", methods=["POST"])  # noqa: F821
async def oa_approval_callback():
    """
    OA 审批回调：
    {
      "oa_request_id": "oa_req_99887766",
      "result": "approved",
      "comment": "同意",
      "approver": {
        "user_id": "系统用户ID",
        "user_name": "审批人姓名"
      },
      "timestamp": 1730000000
    }
    """
    import logging
    from datetime import datetime

    try:
        req = await get_request_json()

        oa_request_id = req.get("oa_request_id")
        result = req.get("result")
        comment = req.get("comment", "")
        approver = req.get("approver") or {}
        timestamp = req.get("timestamp")

        if not oa_request_id:
            return get_json_result(
                data=False,
                message="Missing oa_request_id",
                code=RetCode.ARGUMENT_ERROR,
            )

        if result not in ["approved", "rejected"]:
            return get_json_result(
                data=False,
                message="Invalid result, must be approved or rejected",
                code=RetCode.ARGUMENT_ERROR,
            )

        approver_user_id = approver.get("user_id")
        approver_user_name = approver.get("user_name")

        approval = StagedFileApprovalRequest.select().where(
            StagedFileApprovalRequest.id == oa_request_id
        ).first()

        if not approval:
            return get_json_result(
                data=False,
                message=f"Approval request not found: {oa_request_id}",
                code=RetCode.DATA_ERROR,
            )

        batch_id = approval.batch_id
        kb_id = approval.kb_id
        uploader_user_id = approval.uploader_user_id

        # 幂等处理
        if approval.status in ["imported", "rejected"]:
            return get_json_result(
                data={
                    "oa_request_id": oa_request_id,
                    "batch_id": batch_id,
                    "status": approval.status,
                    "message": "Already processed",
                }
            )

        if approval.status == "importing":
            return get_json_result(
                data={
                    "oa_request_id": oa_request_id,
                    "batch_id": batch_id,
                    "status": "importing",
                    "message": "Import is already running",
                }
            )

        e, kb = KnowledgebaseService.get_by_id(kb_id)
        if not e:
            return get_data_error_result(message="Can't find this dataset!")

        staged_files = list(
            StagedFile.select()
            .where(StagedFile.batch_id == batch_id)
            .order_by(StagedFile.created_at.asc(), StagedFile.id.asc())
        )

        if not staged_files:
            return get_json_result(
                data=False,
                message=f"No staged files found for batch_id: {batch_id}",
                code=RetCode.DATA_ERROR,
            )

        now = datetime.now()

        # 拒绝：只更新状态，不入库
        if result == "rejected":
            with DB.atomic():
                StagedFileApprovalRequest.update({
                    "status": "rejected",
                }).where(
                    StagedFileApprovalRequest.id == oa_request_id
                ).execute()

                StagedFile.update({
                    "status": "rejected",
                    "approved_at": now,
                    "approved_by": approver_user_id,
                    "error_msg": comment,
                }).where(
                    StagedFile.batch_id == batch_id
                ).execute()

                task_update_data = {
                    "status": "rejected",
                }

                if hasattr(StagedFileApprovalTask, "comment"):
                    task_update_data["comment"] = comment

                if approver_user_id:
                    StagedFileApprovalTask.update(task_update_data).where(
                        (StagedFileApprovalTask.approval_id == oa_request_id) &
                        (StagedFileApprovalTask.approver_user_id == approver_user_id)
                    ).execute()
                else:
                    StagedFileApprovalTask.update(task_update_data).where(
                        StagedFileApprovalTask.approval_id == oa_request_id
                    ).execute()

            return get_json_result(
                data={
                    "oa_request_id": oa_request_id,
                    "batch_id": batch_id,
                    "status": "rejected",
                    "comment": comment,
                    "approver": approver,
                    "timestamp": timestamp,
                }
            )

        # 通过：先记录审批时间和审批人
        with DB.atomic():
            StagedFileApprovalRequest.update({
                "status": "importing",
            }).where(
                StagedFileApprovalRequest.id == oa_request_id
            ).execute()

            StagedFile.update({
                "status": "approved",
                "approved_at": now,
                "approved_by": approver_user_id,
                "error_msg": None,
            }).where(
                StagedFile.batch_id == batch_id
            ).execute()

            task_update_data = {
                "status": "approved",
            }

            if hasattr(StagedFileApprovalTask, "comment"):
                task_update_data["comment"] = comment

            if approver_user_id:
                StagedFileApprovalTask.update(task_update_data).where(
                    (StagedFileApprovalTask.approval_id == oa_request_id) &
                    (StagedFileApprovalTask.approver_user_id == approver_user_id)
                ).execute()
            else:
                StagedFileApprovalTask.update(task_update_data).where(
                    StagedFileApprovalTask.approval_id == oa_request_id
                ).execute()

       # 真正入库并启动解析
        imported_docs, import_errors = await asyncio.to_thread(
            import_staged_files_and_run_by_callback,
            kb,
            staged_files,
            uploader_user_id,
        )

        # 记录上传操作日志
        try:
            # 重新查询，拿到回写后的 doc_id/status/committed_at
            latest_staged_files = list(
                StagedFile
                .select()
                .where(StagedFile.batch_id == batch_id)
                .order_by(StagedFile.created_at.asc(), StagedFile.id.asc())
            )

            stage_ids = [sf.id for sf in latest_staged_files]

            # 查询这些暂存文件的标签
            staged_tags = list(
                StagedFileTag
                .select()
                .where(StagedFileTag.stage_id.in_(stage_ids))
                .dicts()
            ) if stage_ids else []

            tags_by_stage_id = {}

            for tag in staged_tags:
                stage_id = tag["stage_id"]

                if stage_id not in tags_by_stage_id:
                    tags_by_stage_id[stage_id] = []

                tags_by_stage_id[stage_id].append({
                    "type_code": tag["type_code"],
                    "option_code": tag["option_code"],
                })

            uploader = User.get_or_none(User.id == str(uploader_user_id))

            for sf in latest_staged_files:
                # 只记录真正生成 doc_id 的文件
                if not sf.doc_id:
                    continue

                file_tags = tags_by_stage_id.get(sf.id, [])

                OperationLogService.add_log(
                    user_id=sf.user_id,
                    user_name=getattr(uploader, "nickname", None),
                    user_email=getattr(uploader, "email", None),

                    kb_id=sf.kb_id,
                    kb_name=getattr(kb, "name", None),

                    target_id=sf.doc_id,
                    target_name=sf.filename,

                    action="upload",
                    status="success",
                    message="文件上传成功",

                    before_data={
                        "staged_file_id": sf.id,
                        "batch_id": sf.batch_id,
                        "filename": sf.filename,
                        "size": sf.size,
                        "tags": file_tags,
                        "status": "approved",
                    },

                    after_data={
                        "staged_file_id": sf.id,
                        "batch_id": sf.batch_id,
                        "kb_id": sf.kb_id,
                        "tenant_id": sf.tenant_id,
                        "user_id": sf.user_id,
                        "doc_id": sf.doc_id,
                        "filename": sf.filename,
                        "size": sf.size,
                        "status": sf.status,
                        "tags": file_tags,
                        "approved_at": (
                            sf.approved_at.strftime("%Y-%m-%d %H:%M:%S")
                            if sf.approved_at else None
                        ),
                        "approved_by": sf.approved_by,
                        "committed_at": (
                            sf.committed_at.strftime("%Y-%m-%d %H:%M:%S")
                            if sf.committed_at else None
                        ),
                        "oa_request_id": oa_request_id,
                        "approver_user_id": approver_user_id,
                        "approver_user_name": approver_user_name,
                    },

                    request_obj=request,
                )

        except Exception:
            logging.exception("Add upload operation log failed.")


        final_status = "imported"
        if import_errors and imported_docs:
            final_status = "partial_imported"
        elif import_errors and not imported_docs:
            final_status = "import_failed"

        with DB.atomic():
            StagedFileApprovalRequest.update({
                "status": final_status,
            }).where(
                StagedFileApprovalRequest.id == oa_request_id
            ).execute()

        return get_json_result(
            data={
                "oa_request_id": oa_request_id,
                "batch_id": batch_id,
                "status": final_status,
                "imported_docs": imported_docs,
                "import_errors": import_errors,
                "approver": {
                    "user_id": approver_user_id,
                    "user_name": approver_user_name,
                },
                "comment": comment,
                "timestamp": timestamp,
            }
        )

    except Exception as e:
        logging.exception("OA approval callback failed.")
        return server_error_response(e)


# @manager.route("/oa/approval/callback", methods=["POST"])
# async def oa_approval_callback():
#     import os
#     import logging
#     from datetime import datetime

#     oa_secret = os.environ.get("OA_SECRET", "")
#     expected_app_id = os.environ.get("OA_APP_ID", "ragflow")

#     data = await request.get_json()
#     if not data:
#         return get_json_result(
#             data=False,
#             message="Empty callback body.",
#             code=RetCode.ARGUMENT_ERROR,
#         )

#     # 1. 校验 app_id
#     if data.get("app_id") != expected_app_id:
#         return get_json_result(
#             data=False,
#             message="Invalid app_id.",
#             code=RetCode.AUTHENTICATION_ERROR,
#         )

#     # 2. 校验签名
#     recv_signature = request.headers.get("X-OA-Signature", "")
#     if oa_secret:
#         expected_signature = make_oa_signature(data, oa_secret)
#         if recv_signature != expected_signature:
#             return get_json_result(
#                 data=False,
#                 message="Invalid signature.",
#                 code=RetCode.AUTHENTICATION_ERROR,
#             )

#     # 3. 公共字段
#     approval_id = data.get("request_id")
#     batch_id = data.get("batch_id")
#     event = data.get("event", "task_updated")
#     comment = data.get("comment", "")

#     if not approval_id or not batch_id:
#         return get_json_result(
#             data=False,
#             message="Missing request_id or batch_id.",
#             code=RetCode.ARGUMENT_ERROR,
#         )

#     approval = StagedFileApprovalRequest.get_or_none(
#         (StagedFileApprovalRequest.id == approval_id) &
#         (StagedFileApprovalRequest.batch_id == batch_id)
#     )
#     if not approval:
#         return get_json_result(
#             data=False,
#             message="Approval request not found.",
#             code=RetCode.NOT_FOUND,
#         )

#     now = datetime.now()

#     # =========================================================
#     # 事件一：OA 审批单最终完成
#     # event = approval_finished
#     # =========================================================
#     if event == "approval_finished":
#         result = data.get("result")

#         if result not in ["approved", "rejected"]:
#             return get_json_result(
#                 data=False,
#                 message="Invalid result.",
#                 code=RetCode.ARGUMENT_ERROR,
#             )

#         # 幂等处理：如果已经处理完成，直接返回成功
#         if approval.status in ["approved", "rejected"] and approval.result == result:
#             return get_json_result(
#                 data={
#                     "batch_id": batch_id,
#                     "request_id": approval_id,
#                     "result": result,
#                     "status": "already_processed",
#                 },
#                 message="Approval already processed.",
#             )

#         # 最终拒绝：整批文件拒绝
#         if result == "rejected":
#             with DB.atomic():
#                 approval.status = "rejected"
#                 approval.result = "rejected"
#                 approval.comment = comment
#                 approval.finished_at = now
#                 approval.updated_at = now
#                 approval.save()

#                 StagedFile.update({
#                     StagedFile.status: "rejected",
#                 }).where(
#                     StagedFile.batch_id == batch_id
#                 ).execute()

#             return get_json_result(
#                 data={
#                     "batch_id": batch_id,
#                     "request_id": approval_id,
#                     "result": "rejected",
#                 },
#                 message="Approval rejected.",
#             )

#         # 最终通过：整批文件正式入库
#         if result == "approved":
#             try:
#                 with DB.atomic():
#                     approval.status = "approved"
#                     approval.result = "approved"
#                     approval.comment = comment
#                     approval.finished_at = now
#                     approval.updated_at = now
#                     approval.save()

#                     StagedFile.update({
#                         StagedFile.status: "approved",
#                     }).where(
#                         StagedFile.batch_id == batch_id
#                     ).execute()

#                 # =================================================
#                 # 正式入库 + 解析
#                 # 这里放你的正式导入逻辑
#                 # =================================================
#                 # import_staged_files_after_approval(batch_id)

#                 with DB.atomic():
#                     StagedFile.update({
#                         StagedFile.status: "committed",
#                         StagedFile.committed_at: now,
#                     }).where(
#                         StagedFile.batch_id == batch_id
#                     ).execute()

#             except Exception as e:
#                 logging.exception("Handle approved final callback failed.")
#                 return get_json_result(
#                     data=False,
#                     message=str(e),
#                     code=RetCode.SERVER_ERROR,
#                 )

#             return get_json_result(
#                 data={
#                     "batch_id": batch_id,
#                     "request_id": approval_id,
#                     "result": "approved",
#                     "next": "parsed",
#                 },
#                 message="Approval approved and imported.",
#             )

#     # =========================================================
#     # 事件二：单个审批人任务更新
#     # event = task_updated
#     # =========================================================
#     if event != "task_updated":
#         return get_json_result(
#             data=False,
#             message=f"Unsupported event: {event}",
#             code=RetCode.ARGUMENT_ERROR,
#         )

#     level = data.get("level")
#     approver_user_id = data.get("approver_user_id")
#     approver_name = data.get("approver_name", "")
#     action = data.get("action")   # approved / rejected

#     if level is None:
#         return get_json_result(
#             data=False,
#             message="Missing level.",
#             code=RetCode.ARGUMENT_ERROR,
#         )

#     if not approver_user_id:
#         return get_json_result(
#             data=False,
#             message="Missing approver_user_id.",
#             code=RetCode.ARGUMENT_ERROR,
#         )

#     if action not in ["approved", "rejected"]:
#         return get_json_result(
#             data=False,
#             message="Invalid action.",
#             code=RetCode.ARGUMENT_ERROR,
#         )

#     task = StagedFileApprovalTask.get_or_none(
#         (StagedFileApprovalTask.approval_id == approval_id) &
#         (StagedFileApprovalTask.batch_id == batch_id) &
#         (StagedFileApprovalTask.level == level) &
#         (StagedFileApprovalTask.approver_user_id == approver_user_id)
#     )

#     if not task:
#         return get_json_result(
#             data=False,
#             message="Approval task not found.",
#             code=RetCode.NOT_FOUND,
#         )

#     # 幂等处理：同一个任务重复回调
#     if task.status in ["approved", "rejected"]:
#         return get_json_result(
#             data={
#                 "batch_id": batch_id,
#                 "request_id": approval_id,
#                 "status": "task_already_processed",
#                 "task_status": task.status,
#             },
#             message="Task already processed.",
#         )

#     # 更新审批任务
#     with DB.atomic():
#         task.status = action
#         task.comment = comment
#         task.action_time = now
#         task.updated_at = now

#         if approver_name and not task.approver_name:
#             task.approver_name = approver_name

#         task.save()

#     # 任意一个审批人拒绝，整批拒绝
#     if action == "rejected":
#         with DB.atomic():
#             approval.status = "rejected"
#             approval.result = "rejected"
#             approval.comment = comment
#             approval.finished_at = now
#             approval.updated_at = now
#             approval.save()

#             StagedFile.update({
#                 StagedFile.status: "rejected",
#             }).where(
#                 StagedFile.batch_id == batch_id
#             ).execute()

#         return get_json_result(
#             data={
#                 "batch_id": batch_id,
#                 "request_id": approval_id,
#                 "result": "rejected",
#             },
#             message="Approval rejected.",
#         )

#     # 查询当前审批单的所有本地任务
#     all_tasks = list(
#         StagedFileApprovalTask.select().where(
#             StagedFileApprovalTask.approval_id == approval_id
#         )
#     )

#     # 如果有任何拒绝，整批拒绝
#     if any(t.status == "rejected" for t in all_tasks):
#         with DB.atomic():
#             approval.status = "rejected"
#             approval.result = "rejected"
#             approval.comment = comment
#             approval.finished_at = now
#             approval.updated_at = now
#             approval.save()

#             StagedFile.update({
#                 StagedFile.status: "rejected",
#             }).where(
#                 StagedFile.batch_id == batch_id
#             ).execute()

#         return get_json_result(
#             data={
#                 "batch_id": batch_id,
#                 "request_id": approval_id,
#                 "result": "rejected",
#             },
#             message="Approval rejected.",
#         )

#     # 当前级别任务是否全部通过
#     same_level_tasks = [
#         t for t in all_tasks if t.level == level
#     ]

#     same_level_done = all(
#         t.status == "approved" for t in same_level_tasks
#     )

#     # 当前级别还没全部通过
#     if not same_level_done:
#         return get_json_result(
#             data={
#                 "batch_id": batch_id,
#                 "request_id": approval_id,
#                 "status": f"waiting_level_{level}_others",
#             },
#             message="Task updated, waiting other approvers in same level.",
#         )

#     # 当前级别全部通过，但不在 RAGFlow callback 里推进最终入库
#     # 是否进入下一级、是否最终完成，由 OA 侧决定
#     # RAGFlow 只等待 OA 发 approval_finished 事件
#     return get_json_result(
#         data={
#             "batch_id": batch_id,
#             "request_id": approval_id,
#             "status": f"level_{level}_approved_waiting_oa_next_event",
#         },
#         message="Level approved, waiting OA final callback or next level approval.",
#     )

def merge_status(status_list):
    """
    聚合状态：
    rejected > pending > approved > waiting
    """
    if not status_list:
        return "waiting"

    if any(s == "rejected" for s in status_list):
        return "rejected"

    if any(s == "pending" for s in status_list):
        return "pending"

    if all(s in ("approved", "skipped") for s in status_list):
        return "approved"

    if all(s == "waiting" for s in status_list):
        return "waiting"

    return "waiting"

from collections import defaultdict

def build_approval_graph(approval):
    """
    构建整个审批单的审批图，不再按 stage_id
    """
    tasks = list(
        StagedFileApprovalTask
        .select()
        .where(
            StagedFileApprovalTask.approval_id == approval.id
        )
        .order_by(
            StagedFileApprovalTask.level.asc(),
            StagedFileApprovalTask.approver_user_id.asc(),
            StagedFileApprovalTask.id.asc(),
        )
    )

    # level -> approver_user_id -> tasks
    level_approver_map = defaultdict(lambda: defaultdict(list))

    for t in tasks:
        level_approver_map[t.level][t.approver_user_id].append(t)

    levels = []
    display_levels = sorted(set([1, 2] + list(level_approver_map.keys())))

    for level in display_levels:
        approver_map = level_approver_map.get(level, {})
        approvers = []

        for approver_user_id, approver_tasks in sorted(approver_map.items(), key=lambda x: x[0]):
            status_list = [x.status for x in approver_tasks]
            approver_status = merge_status(status_list)

            approver_name = None
            for x in approver_tasks:
                if x.approver_name:
                    approver_name = x.approver_name
                    break

            approvers.append({
                "approver_user_id": approver_user_id,
                "approver_name": approver_name,
                "status": approver_status,
                "task_count": len(approver_tasks),
                "pending_count": sum(1 for x in approver_tasks if x.status == "pending"),
                "approved_count": sum(1 for x in approver_tasks if x.status == "approved"),
                "rejected_count": sum(1 for x in approver_tasks if x.status == "rejected"),
                "waiting_count": sum(1 for x in approver_tasks if x.status == "waiting"),
                "skipped_count": sum(1 for x in approver_tasks if x.status == "skipped"),
                "tasks": [
                    {
                        "task_id": x.id,
                        "level": x.level,
                        "status": x.status,
                        "comment": x.comment,
                        "action_time": x.action_time.isoformat() if x.action_time else None,
                        "created_at": x.created_at.isoformat() if x.created_at else None,
                        "updated_at": x.updated_at.isoformat() if x.updated_at else None,
                    }
                    for x in approver_tasks
                ],
            })

        level_status = merge_status([x["status"] for x in approvers])

        if not approvers:
            if approval.current_level == level and approval.status not in ("approved", "committed", "rejected"):
                level_status = "pending"
            else:
                level_status = "waiting"

        levels.append({
            "level": level,
            "title": "一级审批" if level == 1 else "二级审批" if level == 2 else f"{level}级审批",
            "status": level_status,
            "approver_count": len(approvers),
            "approvers": approvers,
        })

    request_status = approval.status or "pending"

    if request_status in ("approved", "committed"):
        commit_status = "done"
    elif request_status == "rejected":
        commit_status = "blocked"
    else:
        commit_status = "waiting"

    nodes = [
        {
            "id": "submit",
            "type": "submit",
            "title": "提交审批",
            "status": "done",
            "current": False,
            "user_id": approval.uploader_user_id,
        }
    ]

    for level_item in levels:
        nodes.append({
            "id": f"level_{level_item['level']}",
            "type": "approval",
            "title": level_item["title"],
            "level": level_item["level"],
            "status": level_item["status"],
            "current": (
                approval.current_level == level_item["level"]
                and request_status not in ("approved", "committed", "rejected")
            ),
            "approver_count": level_item["approver_count"],
            "approvers": level_item["approvers"],
        })

    nodes.append({
        "id": "commit",
        "type": "commit",
        "title": "提交知识库",
        "status": commit_status,
        "current": False,
    })

    edges = []
    for i in range(len(nodes) - 1):
        edges.append({
            "source": nodes[i]["id"],
            "target": nodes[i + 1]["id"],
        })

    return {
        "approval_id": approval.id,
        "batch_id": approval.batch_id,
        "status": approval.status,
        "current_level": approval.current_level,
        "nodes": nodes,
        "edges": edges,
        "levels": levels,
    }

@manager.route("/oa/approval/graph", methods=["GET"])
async def approval_graph():
    """
    获取审批流程图
    GET /v1/document/oa/approval/graph?approval_id=xxx
    或 ?batch_id=xxx
    """
    approval_id = request.args.get("approval_id")
    batch_id = request.args.get("batch_id")

    if not approval_id and not batch_id:
        return get_json_result(
            code=RetCode.ARGUMENT_ERROR,
            message="approval_id or batch_id is required",
            data=None,
        )

    try:
        query = StagedFileApprovalRequest.select()

        if approval_id:
            query = query.where(StagedFileApprovalRequest.id == approval_id)
        else:
            query = query.where(StagedFileApprovalRequest.batch_id == batch_id)

        approval = query.first()

        if not approval:
            return get_json_result(
                code=RetCode.DATA_ERROR,
                message="approval request not found",
                data=None,
            )

        graph_data = build_approval_graph(approval)
        return get_json_result(data=graph_data)

    except Exception as e:
        # logging.exception("Build approval graph failed.")
        return get_json_result(
            code=RetCode.SERVER_ERROR,
            message=str(e),
            data=None,
        )


# {
#   "types": {
#     "knowledge_category": {
#       "type_code": "knowledge_category",
#       "type_name": "知识分类",
#       "multi_select": true,
#       "required": true,
#       "options": [
#         {
#           "option_code": "pulping",
#           "option_name": "制浆"
#         }
#       ]
#     }
#   }
# }

@manager.route("/knowledge/tags/options", methods=["GET"])  # noqa: F821
@login_required
async def knowledge_tag_options():
    try:
        type_rows = list(
            KnowledgeTagType.select(
                KnowledgeTagType.type_code,
                KnowledgeTagType.type_name,
                KnowledgeTagType.multi_select,
                KnowledgeTagType.required,
                KnowledgeTagType.sort_order,
            )
            .where(KnowledgeTagType.enabled == True)
            .order_by(
                KnowledgeTagType.sort_order.asc(),
                KnowledgeTagType.id.asc(),
            )
        )

        option_rows = list(
            KnowledgeTagOption.select(
                KnowledgeTagOption.type_code,
                KnowledgeTagOption.option_code,
                KnowledgeTagOption.option_name,
                KnowledgeTagOption.sort_order,
            )
            .where(KnowledgeTagOption.enabled == True)
            .order_by(
                KnowledgeTagOption.type_code.asc(),
                KnowledgeTagOption.sort_order.asc(),
                KnowledgeTagOption.id.asc(),
            )
        )

        type_map = {}

        for row in type_rows:
            type_map[row.type_code] = {
                "type_code": row.type_code,
                "type_name": row.type_name,
                "multi_select": bool(row.multi_select),
                "required": bool(row.required),
                "sort_order": row.sort_order,
                "options": [],
            }

        for row in option_rows:
            if row.type_code not in type_map:
                continue

            type_map[row.type_code]["options"].append(
                {
                    "option_code": row.option_code,
                    "option_name": row.option_name,
                    "sort_order": row.sort_order,
                }
            )

        return get_json_result(
            data={
                "types": type_map,
            }
        )

    except Exception as e:
        return server_error_response(e)

@manager.route("/web_crawl", methods=["POST"])  # noqa: F821
@login_required
@validate_request("kb_id", "name", "url")
async def web_crawl():
    form = await request.form
    kb_id = form.get("kb_id")
    if not kb_id:
        return get_json_result(data=False, message='Lack of "KB ID"', code=RetCode.ARGUMENT_ERROR)
    name = form.get("name")
    url = form.get("url")
    if not is_valid_url(url):
        return get_json_result(data=False, message="The URL format is invalid", code=RetCode.ARGUMENT_ERROR)
    e, kb = KnowledgebaseService.get_by_id(kb_id)
    if not e:
        raise LookupError("Can't find this dataset!")
    if not check_kb_team_write_permission(kb, current_user.id):
        return get_json_result(data=False, message="No authorization.", code=RetCode.AUTHENTICATION_ERROR)

    max_doc_num_per_kb = int(os.environ.get("MAX_DOC_NUM_PER_KB", "100"))
    from api.db.db_models import AdminUser
    if max_doc_num_per_kb > 0 and not AdminUser.query(user_id=current_user.id):
        current_doc_count = DocumentService.count_by_kb_id(kb.id, "", [], [])
        if int(current_doc_count or 0) + 1 > max_doc_num_per_kb:
            return get_json_result(
                data=False,
                message=f"非管理员账户每个知识库最多只能上传 {max_doc_num_per_kb} 篇文件。",
                code=RetCode.OPERATING_ERROR,
            )

    blob = html2pdf(url)
    if not blob:
        return server_error_response(ValueError("Download failure."))

    root_folder = FileService.get_root_folder(current_user.id)
    pf_id = root_folder["id"]
    FileService.init_knowledgebase_docs(pf_id, current_user.id)
    kb_root_folder = FileService.get_kb_folder(current_user.id)
    kb_folder = FileService.new_a_file_from_kb(kb.tenant_id, kb.name, kb_root_folder["id"])

    try:
        filename = duplicate_name(DocumentService.query, name=name + ".pdf", kb_id=kb.id)
        filetype = filename_type(filename)
        if filetype == FileType.OTHER.value:
            raise RuntimeError("This type of file has not been supported yet!")

        location = filename
        while settings.STORAGE_IMPL.obj_exist(kb_id, location):
            location += "_"
        settings.STORAGE_IMPL.put(kb_id, location, blob)
        doc = {
            "id": get_uuid(),
            "kb_id": kb.id,
            "parser_id": kb.parser_id,
            "parser_config": kb.parser_config,
            "created_by": current_user.id,
            "type": filetype,
            "name": filename,
            "location": location,
            "size": len(blob),
            "thumbnail": thumbnail(filename, blob),
            "suffix": Path(filename).suffix.lstrip("."),
        }
        if doc["type"] == FileType.VISUAL:
            doc["parser_id"] = ParserType.PICTURE.value
        if doc["type"] == FileType.AURAL:
            doc["parser_id"] = ParserType.AUDIO.value
        if re.search(r"\.(ppt|pptx|pages)$", filename):
            doc["parser_id"] = ParserType.PRESENTATION.value
        if re.search(r"\.(eml)$", filename):
            doc["parser_id"] = ParserType.EMAIL.value
        DocumentService.insert(doc)
        FileService.add_file_from_kb(doc, kb_folder["id"], kb.tenant_id)
    except Exception as e:
        return server_error_response(e)
    return get_json_result(data=True)


@manager.route("/create", methods=["POST"])  # noqa: F821
@login_required
@validate_request("name", "kb_id")
async def create():
    req = await get_request_json()
    kb_id = req["kb_id"]
    if not kb_id:
        return get_json_result(data=False, message='Lack of "KB ID"', code=RetCode.ARGUMENT_ERROR)
    if len(req["name"].encode("utf-8")) > FILE_NAME_LEN_LIMIT:
        return get_json_result(data=False, message=f"File name must be {FILE_NAME_LEN_LIMIT} bytes or less.", code=RetCode.ARGUMENT_ERROR)

    if req["name"].strip() == "":
        return get_json_result(data=False, message="File name can't be empty.", code=RetCode.ARGUMENT_ERROR)
    req["name"] = req["name"].strip()

    try:
        e, kb = KnowledgebaseService.get_by_id(kb_id)
        if not e:
            return get_data_error_result(message="Can't find this dataset!")
        if not check_kb_team_write_permission(kb, current_user.id):
            return get_json_result(data=False, message="No authorization.", code=RetCode.AUTHENTICATION_ERROR)

        if DocumentService.query(name=req["name"], kb_id=kb_id):
            return get_data_error_result(message="Duplicated document name in the same dataset.")

        # 1. 获取创建并将.knowladge挂到根上
        kb_root_folder = FileService.get_kb_folder(kb.tenant_id)

        if not kb_root_folder:
            return get_data_error_result(message="Cannot find the root folder.")
        
        # 2. 知识库挂接到.knowladge
        kb_folder = FileService.new_a_file_from_kb(
            kb.tenant_id,
            kb.name,
            kb_root_folder["id"],
        )
        if not kb_folder:
            return get_data_error_result(message="Cannot find the kb folder for this file.")

        doc = DocumentService.insert(
            {
                "id": get_uuid(),
                "kb_id": kb.id,
                "parser_id": kb.parser_id,
                "pipeline_id": kb.pipeline_id,
                "parser_config": kb.parser_config,
                "created_by": current_user.id,
                "type": FileType.VIRTUAL,
                "name": req["name"],
                "suffix": Path(req["name"]).suffix.lstrip("."),
                "location": "",
                "size": 0,
            }
        )

        FileService.add_file_from_kb(doc.to_dict(), kb_folder["id"], kb.tenant_id)

        return get_json_result(data=doc.to_json())
    except Exception as e:
        return server_error_response(e)

from collections import defaultdict
import json


def build_document_tag_metadata(doc_ids):
    """
    根据正式 doc_id 批量查询暂存标签，并转换为中文展示结构。

    返回：
    {
        "doc_id": {
            "tag_metadata": {
                "knowledge_category": {
                    "type_name": "知识分类",
                    "options": [
                        {
                            "code": "pulping",
                            "name": "制浆"
                        }
                    ]
                }
            },
            "meta_fields_display": {
                "knowledge_category": ["制浆"]
            }
        }
    }
    """
    if not doc_ids:
        return {}

    # doc_id -> stage_id 列表
    doc_stage_map = defaultdict(list)

    staged_rows = (
        StagedFile
        .select(
            StagedFile.doc_id,
            StagedFile.id,
        )
        .where(
            StagedFile.doc_id.in_(doc_ids)
        )
    )

    for row in staged_rows:
        if row.doc_id:
            doc_stage_map[str(row.doc_id)].append(str(row.id))

    all_stage_ids = [
        stage_id
        for stage_ids in doc_stage_map.values()
        for stage_id in stage_ids
    ]

    if not all_stage_ids:
        return {}

    # stage_id -> type_code -> option_code 列表
    stage_tag_map = defaultdict(lambda: defaultdict(list))

    tag_rows = (
        StagedFileTag
        .select(
            StagedFileTag.stage_id,
            StagedFileTag.type_code,
            StagedFileTag.option_code,
        )
        .where(
            StagedFileTag.stage_id.in_(all_stage_ids)
        )
    )

    type_codes = set()
    option_codes_by_type = defaultdict(set)

    for row in tag_rows:
        stage_id = str(row.stage_id)
        type_code = str(row.type_code)
        option_code = str(row.option_code)

        stage_tag_map[stage_id][type_code].append(option_code)
        type_codes.add(type_code)
        option_codes_by_type[type_code].add(option_code)

    if not type_codes:
        return {}

    # 查询标签类型名称
    type_name_map = {}

    type_rows = (
        KnowledgeTagType
        .select(
            KnowledgeTagType.type_code,
            KnowledgeTagType.type_name,
        )
        .where(
            KnowledgeTagType.type_code.in_(list(type_codes))
        )
    )

    for row in type_rows:
        type_name_map[str(row.type_code)] = row.type_name

    # 查询标签选项名称
    option_name_map = defaultdict(dict)

    option_rows = (
        KnowledgeTagOption
        .select(
            KnowledgeTagOption.type_code,
            KnowledgeTagOption.option_code,
            KnowledgeTagOption.option_name,
        )
        .where(
            KnowledgeTagOption.type_code.in_(list(type_codes))
        )
    )

    for row in option_rows:
        type_code = str(row.type_code)
        option_code = str(row.option_code)

        # 只保存本次实际使用的 option
        if option_code in option_codes_by_type[type_code]:
            option_name_map[type_code][option_code] = row.option_name

    result = {}

    for doc_id, stage_ids in doc_stage_map.items():
        tag_metadata = {}
        meta_fields_display = {}

        for stage_id in stage_ids:
            type_map = stage_tag_map.get(stage_id, {})

            for type_code, option_codes in type_map.items():
                type_name = type_name_map.get(type_code, type_code)

                option_rows_for_type = tag_metadata.setdefault(
                    type_code,
                    {
                        "type_name": type_name,
                        "options": [],
                    },
                )

                display_values = meta_fields_display.setdefault(
                    type_code,
                    [],
                )

                for option_code in option_codes:
                    option_name = option_name_map[type_code].get(
                        option_code,
                        option_code,
                    )

                    option_item = {
                        "code": option_code,
                        "name": option_name,
                    }

                    # 避免多个 stage 或重复标签造成重复返回
                    if option_item not in option_rows_for_type["options"]:
                        option_rows_for_type["options"].append(
                            option_item
                        )

                    if option_name not in display_values:
                        display_values.append(option_name)

        result[doc_id] = {
            "tag_metadata": tag_metadata,
            "meta_fields_display": meta_fields_display,
        }

    return result

# @manager.route("/list", methods=["POST"])  # noqa: F821
# @login_required
# async def list_docs():
#     kb_id = request.args.get("kb_id")
#     if not kb_id:
#         return get_json_result(data=False, message='Lack of "KB ID"', code=RetCode.ARGUMENT_ERROR)
#     ok, kb = KnowledgebaseService.get_by_id(kb_id)
#     if not ok:
#         return get_json_result(data=False, message="Dataset not found.", code=RetCode.DATA_ERROR)
    
#     # if not check_kb_team_permission(kb, current_user.id):
#     #     return get_json_result(data=False, message="Only owner or team members are authorized for this operation.", code=RetCode.OPERATING_ERROR)
#     keywords = request.args.get("keywords", "")

#     page_number = int(request.args.get("page", 0))
#     items_per_page = int(request.args.get("page_size", 0))
#     orderby = request.args.get("orderby", "create_time")
#     if request.args.get("desc", "true").lower() == "false":
#         desc = False
#     else:
#         desc = True
#     create_time_from = int(request.args.get("create_time_from", 0))
#     create_time_to = int(request.args.get("create_time_to", 0))

#     req = await get_request_json()

#     run_status = req.get("run_status", [])
#     if run_status:
#         invalid_status = {s for s in run_status if s not in VALID_TASK_STATUS}
#         if invalid_status:
#             return get_data_error_result(message=f"Invalid filter run status conditions: {', '.join(invalid_status)}")

#     types = req.get("types", [])
#     if types:
#         invalid_types = {t for t in types if t not in VALID_FILE_TYPES}
#         if invalid_types:
#             return get_data_error_result(message=f"Invalid filter conditions: {', '.join(invalid_types)} type{'s' if len(invalid_types) > 1 else ''}")

#     suffix = req.get("suffix", [])
#     metadata_condition = req.get("metadata_condition", {}) or {}
#     if metadata_condition and not isinstance(metadata_condition, dict):
#         return get_data_error_result(message="metadata_condition must be an object.")

#     doc_ids_filter = None
#     if metadata_condition:
#         metas = DocumentService.get_flatted_meta_by_kbs([kb_id])
#         doc_ids_filter = meta_filter(metas, convert_conditions(metadata_condition), metadata_condition.get("logic", "and"))
#         if metadata_condition.get("conditions") and not doc_ids_filter:
#             return get_json_result(data={"total": 0, "docs": []})

#     try:
#         docs, tol = DocumentService.get_by_kb_id(kb_id, page_number, items_per_page, orderby, desc, keywords, run_status, types, suffix, doc_ids_filter)

#         from collections import defaultdict
#         from api.db.db_models import Task

#         doc_ids = [doc["id"] for doc in docs]
#         doc_tasks = defaultdict(list)

#         if doc_ids:
#             task_rows = (
#                 Task.select(Task.doc_id, Task.task_type, Task.progress, Task.progress_msg, Task.begin_at)
#                 .where(Task.doc_id.in_(doc_ids))
#                 .order_by(Task.begin_at)
#             )

#             for task in task_rows:
#                 task_type = (task.task_type or "").lower().strip()
#                 doc_tasks[task.doc_id].append({
#                     "task_type": task_type,
#                     "progress": task.progress,
#                     "progress_msg": task.progress_msg,
#                     "begin_at": task.begin_at,
#                 })
#         if create_time_from or create_time_to:
#             filtered_docs = []
#             for doc in docs:
#                 doc_create_time = doc.get("create_time", 0)
#                 if (create_time_from == 0 or doc_create_time >= create_time_from) and (create_time_to == 0 or doc_create_time <= create_time_to):
#                     filtered_docs.append(doc)
#             docs = filtered_docs
#         for doc_item in docs:
#             tasks = doc_tasks.get(doc_item["id"], [])

#             has_author_task = any(t["task_type"] == "parse_author_info" for t in tasks)
#             has_parse_task = any(t["task_type"] == "" for t in tasks)

#             doc_item["has_author_task"] = has_author_task
#             doc_item["has_parse_task"] = has_parse_task

#             if has_author_task and has_parse_task:
#                 doc_item["process_scene"] = "author_with_parse"
#             elif has_author_task:
#                 doc_item["process_scene"] = "author_only"
#             elif has_parse_task:
#                 doc_item["process_scene"] = "parse_only"
#             else:
#                 doc_item["process_scene"] = "unknown"

#             latest_task = tasks[-1] if tasks else None
#             doc_item["latest_task_type"] = latest_task["task_type"] if latest_task else ""

#             if doc_item["thumbnail"] and not doc_item["thumbnail"].startswith(IMG_BASE64_PREFIX):
#                 doc_item["thumbnail"] = f"/v1/document/image/{kb_id}-{doc_item['thumbnail']}"
#             if doc_item.get("source_type"):
#                 doc_item["source_type"] = doc_item["source_type"].split("/")[0]
#             # 将字段的meta_fields字段解析出新的字段，并且整理为我们需要的作者、学校、论文发布时间
#             if doc_item.get("meta_fields"):
#                 meta_fields = doc_item["meta_fields"]
#                 # 确保 meta_fields 是一个字典
#                 if isinstance(meta_fields, str):
#                     try:
#                         meta_fields = json.loads(meta_fields)
#                     except json.JSONDecodeError:
#                         meta_fields = {}
#                 # 确保 meta_fields 是一个字典
#                 if isinstance(meta_fields, dict):
#                     doc_item["author"] = meta_fields.get("author", "")
#                     doc_item["school"] = meta_fields.get("school", "")
#                     doc_item["publish_time"] = meta_fields.get("publish_time", "")
#                 else:
#                     doc_item["author"] = ""
#                     doc_item["school"] = ""
#                     doc_item["publish_time"] = ""

#         # 新增显示本周文件占比
#         from datetime import datetime, timedelta, time
#         from api.db.db_models import Document

#         now = datetime.now()
#         this_week_start = datetime.combine(
#             now.date() - timedelta(days=now.weekday()),
#             time.min,
#         )

#         this_week_start_ts = int(this_week_start.timestamp() * 1000)

#         this_week_count = Document.select().where(
#             Document.kb_id == kb_id,
#             Document.create_time >= this_week_start_ts,
#             Document.status != "2",
#         ).count()

#         week_file_ratio = 0 if tol == 0 else round(this_week_count / tol * 100, 2)

#         return get_json_result(data={"total": tol, "docs": docs,
#                                      "week_growth_rate": week_file_ratio,
#                                         "this_week_count": this_week_count,})
#     except Exception as e:
#         return server_error_response(e) 

# @manager.route("/list", methods=["POST"])  # noqa: F821
# @login_required
# async def list_docs():
#     import json
#     from collections import defaultdict
#     from datetime import datetime, timedelta, time

#     from api.db.db_models import (
#         Document,
#         KnowledgeTagOption,
#         KnowledgeTagType,
#         StagedFile,
#         StagedFileTag,
#         Task,
#     )

#     kb_id = request.args.get("kb_id")

#     if not kb_id:
#         return get_json_result(
#             data=False,
#             message='Lack of "KB ID"',
#             code=RetCode.ARGUMENT_ERROR,
#         )

#     ok, kb = KnowledgebaseService.get_by_id(kb_id)
#     if not ok:
#         return get_json_result(
#             data=False,
#             message="Dataset not found.",
#             code=RetCode.DATA_ERROR,
#         )

#     keywords = request.args.get("keywords", "")

#     page_number = int(request.args.get("page", 0))
#     items_per_page = int(request.args.get("page_size", 0))

#     orderby = request.args.get("orderby", "create_time")
#     desc = request.args.get("desc", "true").lower() != "false"

#     create_time_from = int(
#         request.args.get("create_time_from", 0)
#     )
#     create_time_to = int(
#         request.args.get("create_time_to", 0)
#     )

#     req = await get_request_json()

#     run_status = req.get("run_status", [])
#     if run_status:
#         invalid_status = {
#             status for status in run_status
#             if status not in VALID_TASK_STATUS
#         }

#         if invalid_status:
#             return get_data_error_result(
#                 message=(
#                     "Invalid filter run status conditions: "
#                     f"{', '.join(invalid_status)}"
#                 )
#             )

#     types = req.get("types", [])
#     if types:
#         invalid_types = {
#             file_type for file_type in types
#             if file_type not in VALID_FILE_TYPES
#         }

#         if invalid_types:
#             return get_data_error_result(
#                 message=(
#                     "Invalid filter conditions: "
#                     f"{', '.join(invalid_types)} type"
#                     f"{'s' if len(invalid_types) > 1 else ''}"
#                 )
#             )

#     suffix = req.get("suffix", [])

#     metadata_condition = (
#         req.get("metadata_condition", {}) or {}
#     )

#     if metadata_condition and not isinstance(
#         metadata_condition,
#         dict,
#     ):
#         return get_data_error_result(
#             message="metadata_condition must be an object."
#         )

#     doc_ids_filter = None

#     if metadata_condition:
#         metas = DocumentService.get_flatted_meta_by_kbs([kb_id])

#         doc_ids_filter = meta_filter(
#             metas,
#             convert_conditions(metadata_condition),
#             metadata_condition.get("logic", "and"),
#         )

#         if (
#             metadata_condition.get("conditions")
#             and not doc_ids_filter
#         ):
#             return get_json_result(
#                 data={
#                     "total": 0,
#                     "docs": [],
#                 }
#             )

#     try:
#         docs, total = DocumentService.get_by_kb_id(
#             kb_id,
#             page_number,
#             items_per_page,
#             orderby,
#             desc,
#             keywords,
#             run_status,
#             types,
#             suffix,
#             doc_ids_filter,
#         )

#         # 查询当前页文档对应的解析任务
#         doc_ids = [
#             doc["id"]
#             for doc in docs
#             if doc.get("id")
#         ]

#         doc_tasks = defaultdict(list)

#         if doc_ids:
#             task_rows = (
#                 Task.select(
#                     Task.doc_id,
#                     Task.task_type,
#                     Task.progress,
#                     Task.progress_msg,
#                     Task.begin_at,
#                 )
#                 .where(Task.doc_id.in_(doc_ids))
#                 .order_by(Task.begin_at.asc())
#             )

#             for task in task_rows:
#                 task_type = (
#                     task.task_type or ""
#                 ).lower().strip()

#                 doc_tasks[str(task.doc_id)].append({
#                     "task_type": task_type,
#                     "progress": task.progress,
#                     "progress_msg": task.progress_msg,
#                     "begin_at": task.begin_at,
#                 })

#         # 按创建时间再次过滤。
#         # 保留你原来的行为。
#         if create_time_from or create_time_to:
#             filtered_docs = []

#             for doc in docs:
#                 doc_create_time = doc.get(
#                     "create_time",
#                     0,
#                 )

#                 if (
#                     (
#                         create_time_from == 0
#                         or doc_create_time >= create_time_from
#                     )
#                     and
#                     (
#                         create_time_to == 0
#                         or doc_create_time <= create_time_to
#                     )
#                 ):
#                     filtered_docs.append(doc)

#             docs = filtered_docs

#         # ---------------------------------------------------------
#         # 批量查询文档标签
#         #
#         # Document.id
#         #     -> StagedFile.doc_id
#         #     -> StagedFile.id
#         #     -> StagedFileTag.stage_id
#         # ---------------------------------------------------------
#         document_tag_data = defaultdict(
#             lambda: {
#                 "tag_metadata": {},
#                 "meta_fields_display": {},
#             }
#         )

#         if doc_ids:
#             # doc_id -> stage_id
#             doc_stage_map = defaultdict(list)

#             staged_rows = (
#                 StagedFile.select(
#                     StagedFile.id,
#                     StagedFile.doc_id,
#                 )
#                 .where(
#                     StagedFile.doc_id.in_(doc_ids)
#                 )
#             )

#             stage_ids = []

#             for staged in staged_rows:
#                 if not staged.doc_id:
#                     continue

#                 doc_id = str(staged.doc_id)
#                 stage_id = str(staged.id)

#                 doc_stage_map[doc_id].append(stage_id)
#                 stage_ids.append(stage_id)

#             if stage_ids:
#                 # stage_id -> type_code -> option_code 列表
#                 stage_tag_map = defaultdict(
#                     lambda: defaultdict(list)
#                 )

#                 type_codes = set()

#                 tag_rows = (
#                     StagedFileTag.select(
#                         StagedFileTag.stage_id,
#                         StagedFileTag.type_code,
#                         StagedFileTag.option_code,
#                     )
#                     .where(
#                         StagedFileTag.stage_id.in_(stage_ids)
#                     )
#                 )

#                 for tag in tag_rows:
#                     stage_id = str(tag.stage_id)
#                     type_code = str(tag.type_code)
#                     option_code = str(tag.option_code)

#                     if not type_code or not option_code:
#                         continue

#                     if (
#                         option_code
#                         not in stage_tag_map[stage_id][type_code]
#                     ):
#                         stage_tag_map[stage_id][type_code].append(
#                             option_code
#                         )

#                     type_codes.add(type_code)

#                 # 查询类型名称
#                 type_name_map = {}

#                 if type_codes:
#                     type_rows = (
#                         KnowledgeTagType.select(
#                             KnowledgeTagType.type_code,
#                             KnowledgeTagType.type_name,
#                         )
#                         .where(
#                             KnowledgeTagType.type_code.in_(
#                                 list(type_codes)
#                             )
#                         )
#                     )   

#                     for tag_type in type_rows:
#                         type_name_map[
#                             str(tag_type.type_code)
#                         ] = tag_type.type_name

#                 # 查询选项名称
#                 option_name_map = defaultdict(dict)

#                 if type_codes:
#                     option_rows = (
#                         KnowledgeTagOption.select(
#                             KnowledgeTagOption.type_code,
#                             KnowledgeTagOption.option_code,
#                             KnowledgeTagOption.option_name,
#                         )
#                         .where(
#                             KnowledgeTagOption.type_code.in_(
#                                 list(type_codes)
#                             )
#                         )
#                     )

#                     for option in option_rows:
#                         type_code = str(option.type_code)
#                         option_code = str(option.option_code)

#                         option_name_map[type_code][option_code] = (
#                             option.option_name
#                         )

#                 # 将标签按 doc_id 汇总
#                 for doc_id, doc_stage_ids in doc_stage_map.items():
#                     tag_metadata = {}
#                     meta_fields_display = {}

#                     for stage_id in doc_stage_ids:
#                         type_map = stage_tag_map.get(
#                             stage_id,
#                             {},
#                         )

#                         for type_code, option_codes in type_map.items():
#                             type_name = type_name_map.get(
#                                 type_code,
#                                 type_code,
#                             )

#                             tag_item = tag_metadata.setdefault(
#                                 type_code,
#                                 {
#                                     "type_code": type_code,
#                                     "type_name": type_name,
#                                     "options": [],
#                                 },
#                             )

#                             display_values = (
#                                 meta_fields_display.setdefault(
#                                     type_code,
#                                     [],
#                                 )
#                             )

#                             for option_code in option_codes:
#                                 option_name = (
#                                     option_name_map[type_code].get(
#                                         option_code,
#                                         option_code,
#                                     )
#                                 )

#                                 option_item = {
#                                     "option_code": option_code,
#                                     "option_name": option_name,
#                                 }

#                                 if (
#                                     option_item
#                                     not in tag_item["options"]
#                                 ):
#                                     tag_item["options"].append(
#                                         option_item
#                                     )

#                                 if (
#                                     option_name
#                                     not in display_values
#                                 ):
#                                     display_values.append(
#                                         option_name
#                                     )

#                     document_tag_data[doc_id] = {
#                         "tag_metadata": tag_metadata,
#                         "meta_fields_display": (
#                             meta_fields_display
#                         ),
#                     }

#         # ---------------------------------------------------------
#         # 整理每篇文档的返回数据
#         # ---------------------------------------------------------
#         for doc_item in docs:
#             doc_id = str(doc_item["id"])
#             tasks = doc_tasks.get(doc_id, [])

#             has_author_task = any(
#                 task["task_type"] == "parse_author_info"
#                 for task in tasks
#             )

#             has_parse_task = any(
#                 task["task_type"] == ""
#                 for task in tasks
#             )

#             doc_item["has_author_task"] = has_author_task
#             doc_item["has_parse_task"] = has_parse_task

#             if has_author_task and has_parse_task:
#                 doc_item["process_scene"] = (
#                     "author_with_parse"
#                 )
#             elif has_author_task:
#                 doc_item["process_scene"] = "author_only"
#             elif has_parse_task:
#                 doc_item["process_scene"] = "parse_only"
#             else:
#                 doc_item["process_scene"] = "unknown"

#             latest_task = tasks[-1] if tasks else None

#             doc_item["latest_task_type"] = (
#                 latest_task["task_type"]
#                 if latest_task
#                 else ""
#             )

#             if (
#                 doc_item.get("thumbnail")
#                 and not doc_item["thumbnail"].startswith(
#                     IMG_BASE64_PREFIX
#                 )
#             ):
#                 doc_item["thumbnail"] = (
#                     f"/v1/document/image/"
#                     f"{kb_id}-{doc_item['thumbnail']}"
#                 )

#             if doc_item.get("source_type"):
#                 doc_item["source_type"] = (
#                     doc_item["source_type"].split("/")[0]
#                 )

#             # 从 meta_fields 中解析作者、学校、发布时间
#             meta_fields = doc_item.get("meta_fields") or {}

#             if isinstance(meta_fields, str):
#                 try:
#                     meta_fields = json.loads(meta_fields)
#                 except json.JSONDecodeError:
#                     meta_fields = {}

#             if not isinstance(meta_fields, dict):
#                 meta_fields = {}

#             doc_item["meta_fields"] = meta_fields

#             doc_item["author"] = meta_fields.get(
#                 "author",
#                 "",
#             )

#             doc_item["school"] = meta_fields.get(
#                 "school",
#                 "",
#             )

#             doc_item["publish_time"] = meta_fields.get(
#                 "publish_time",
#                 "",
#             )

#             # 标签中文展示数据
#             tag_data = document_tag_data.get(
#                 doc_id,
#                 {
#                     "tag_metadata": {},
#                     "meta_fields_display": {},
#                 },
#             )

#             doc_item["tag_metadata"] = tag_data[
#                 "tag_metadata"
#             ]

#             doc_item["meta_fields_display"] = tag_data[
#                 "meta_fields_display"
#             ]

#         # 新增显示本周文件占比
#         now = datetime.now()

#         this_week_start = datetime.combine(
#             now.date() - timedelta(days=now.weekday()),
#             time.min,
#         )

#         this_week_start_ts = int(
#             this_week_start.timestamp() * 1000
#         )

#         this_week_count = (
#             Document.select()
#             .where(
#                 (Document.kb_id == kb_id) &
#                 (Document.create_time >= this_week_start_ts) &
#                 (Document.status != "2")
#             )
#             .count()
#         )

#         week_file_ratio = (
#             0
#             if total == 0
#             else round(this_week_count / total * 100, 2)
#         )

#         return get_json_result(
#             data={
#                 "total": total,
#                 "docs": docs,
#                 "week_growth_rate": week_file_ratio,
#                 "this_week_count": this_week_count,
#             }
#         )

#     except Exception as e:
#         return server_error_response(e)
from api.db.db_models import AdminUser

@manager.route("/list", methods=["POST"])  # noqa: F821
@login_required
async def list_docs():
    import json
    from collections import defaultdict
    from datetime import datetime, timedelta, time

    from api.apps import current_user

    from api.db.db_models import (
        Document,
        KnowledgeTagOption,
        KnowledgeTagType,
        Role,
        RoleUser,
        StagedFile,
        StagedFileTag,
        Task,
    )

    PUBLIC = 1
    INTERNAL = 2


    def get_current_user_id():
        """
        获取当前登录用户 ID。

        你项目里现在用的是：
        from api.apps import current_user

        所以这里做兼容处理。
        """

        if current_user is None:
            return None

        if hasattr(current_user, "user_id"):
            return str(current_user.user_id)

        if hasattr(current_user, "id"):
            return str(current_user.id)

        if hasattr(current_user, "get_id"):
            user_id = current_user.get_id()
            if user_id:
                return str(user_id)

        if isinstance(current_user, dict):
            for key in ["user_id", "id", "uid"]:
                if current_user.get(key):
                    return str(current_user.get(key))

        return None

    def get_current_super_admin(user_id):
        if not user_id:
            return False

        admin = AdminUser.query(user_id=user_id, role_level=1)
        return bool(admin)
    
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

    def serialize_current_role_permissions(role):
        operation_permission_map = {
            "view": 1,
            "upload": 2,
            "download": 4,
            "delete": 8,
            "edit": 16,
        }

        if role is None:
            return None

        try:
            file_permission_level = int(role.file_permission_level or PUBLIC)
        except Exception:
            file_permission_level = PUBLIC

        try:
            operation_permission_mask = int(role.operation_permission_mask or 0)
        except Exception:
            operation_permission_mask = 0

        is_admin = bool(role.is_admin)

        operation_permissions = {
            key: True if is_admin else bool(operation_permission_mask & value)
            for key, value in operation_permission_map.items()
        }

        operation_permission_names = []
        name_map = {
            "view": "查看",
            "upload": "上传",
            "download": "下载",
            "delete": "删除",
            "edit": "编辑",
        }

        for key, allowed in operation_permissions.items():
            if allowed:
                operation_permission_names.append(name_map[key])

        return {
            "role_id": role.id,
            "role_name": role.role_name,
            "enabled": bool(role.enabled),
            "is_admin": is_admin,
            "file_permission_level": file_permission_level,
            "file_permission_name": "内部" if file_permission_level == INTERNAL else "公开",
            "operation_permission_mask": operation_permission_mask,
            "operation_permissions": operation_permissions,
            "operation_permission_names": operation_permission_names,
            "need_approval": bool(role.need_approval),
            "approval_order": role.approval_order or 0,
            "department_id": role.department_id,
            "cover_child_dept": bool(role.cover_child_dept),
        }

    def get_doc_visibility_from_tags(tag_data):
        """
        根据标签判断文档是公开还是内部。

        返回：
        1 = 公开
        2 = 内部

        当前逻辑：
        - 只要 option_code 或 option_name 中出现“内部”，认为是内部文档
        - 只要 option_code 或 option_name 中出现“公开”，认为是公开文档
        - 没有相关标签时，默认公开
        """

        if not tag_data:
            return PUBLIC

        tag_metadata = tag_data.get("tag_metadata") or {}
        meta_fields_display = (
            tag_data.get("meta_fields_display") or {}
        )

        internal_values = {
            "internal",
            "INTERNAL",
            "内部",
            "内部文件",
            "内部文档",
            "2",
        }

        public_values = {
            "public",
            "PUBLIC",
            "公开",
            "公开文件",
            "公开文档",
            "1",
        }

        # 1. 从 tag_metadata 判断
        for _, tag_item in tag_metadata.items():
            options = tag_item.get("options") or []

            for option in options:
                option_code = str(
                    option.get("option_code", "")
                ).strip()

                option_name = str(
                    option.get("option_name", "")
                ).strip()

                if (
                    option_code in internal_values
                    or option_name in internal_values
                ):
                    return INTERNAL

                if (
                    option_code in public_values
                    or option_name in public_values
                ):
                    return PUBLIC

        # 2. 从 meta_fields_display 判断
        for _, values in meta_fields_display.items():
            if not isinstance(values, list):
                values = [values]

            for value in values:
                value = str(value).strip()

                if value in internal_values:
                    return INTERNAL

                if value in public_values:
                    return PUBLIC

        # 3. 没有公开/内部标签时默认公开
        return PUBLIC

    def can_view_document(role, visibility_level, is_super_admin=False):
        try:
            visibility_level = int(visibility_level)
        except Exception:
            visibility_level = PUBLIC

        if is_super_admin:
            return True

        if role is None:
            return visibility_level == PUBLIC

        if not role.enabled:
            return False

        if role.is_admin:
            return True

        if visibility_level == PUBLIC:
            return True

        if visibility_level == INTERNAL:
            try:
                return int(role.file_permission_level) == INTERNAL
            except Exception:
                return False

        return False

    kb_id = request.args.get("kb_id")

    if not kb_id:
        return get_json_result(
            data=False,
            message='Lack of "KB ID"',
            code=RetCode.ARGUMENT_ERROR,
        )

    ok, kb = KnowledgebaseService.get_by_id(kb_id)
    if not ok:
        return get_json_result(
            data=False,
            message="Dataset not found.",
            code=RetCode.DATA_ERROR,
        )

    # ---------------------------------------------------------
    # 查询当前用户角色，只查一次
    # ---------------------------------------------------------
    current_user_id = get_current_user_id()
    current_role = get_current_user_role(current_user_id)
    is_super_admin = get_current_super_admin(current_user_id)
    

    def serialize_super_admin_permissions():
        return {
            "role_id": "super_admin",
            "role_name": "超级管理员",
            "enabled": True,
            "is_admin": True,
            "file_permission_level": INTERNAL,
            "file_permission_name": "内部",
            "operation_permission_mask": 31,  # 1|2|4|8|16
            "operation_permissions": {
                "view": True,
                "upload": True,
                "download": True,
                "delete": True,
                "edit": True,
            },
            "operation_permission_names": ["查看", "上传", "下载", "删除", "编辑"],
            "need_approval": False,
            "approval_order": 0,
            "department_id": None,
            "cover_child_dept": True,
        }

    if is_super_admin:
        current_user_role = serialize_super_admin_permissions()
    else:
        current_user_role = serialize_current_role_permissions(current_role)

    keywords = request.args.get("keywords", "")

    page_number = int(request.args.get("page", 0))
    items_per_page = int(request.args.get("page_size", 0))

    orderby = request.args.get("orderby", "create_time")
    desc = request.args.get("desc", "true").lower() != "false"

    create_time_from = int(
        request.args.get("create_time_from", 0)
    )
    create_time_to = int(
        request.args.get("create_time_to", 0)
    )

    req = await get_request_json()

    run_status = req.get("run_status", [])
    if run_status:
        invalid_status = {
            status for status in run_status
            if status not in VALID_TASK_STATUS
        }

        if invalid_status:
            return get_data_error_result(
                message=(
                    "Invalid filter run status conditions: "
                    f"{', '.join(invalid_status)}"
                )
            )

    types = req.get("types", [])
    if types:
        invalid_types = {
            file_type for file_type in types
            if file_type not in VALID_FILE_TYPES
        }

        if invalid_types:
            return get_data_error_result(
                message=(
                    "Invalid filter conditions: "
                    f"{', '.join(invalid_types)} type"
                    f"{'s' if len(invalid_types) > 1 else ''}"
                )
            )

    suffix = req.get("suffix", [])

    metadata_condition = (
    req.get("metadata_condition", {}) or {}
    )

    # 新增：读取作者、学校、日期
    author = str(req.get("author", "") or "").strip()
    school = str(req.get("school", "") or "").strip()
    print(school)

    publish_date_start = str(
        req.get("publish_date_start", "") or ""
    ).strip()

    publish_date_end = str(
        req.get("publish_date_end", "") or ""
    ).strip()

    # 兼容 publish_date 对象
    publish_date = req.get("publish_date") or {}

    if not publish_date_start:
        publish_date_start = str(
            publish_date.get("start", "") or ""
        ).strip()

    if not publish_date_end:
        publish_date_end = str(
            publish_date.get("end", "") or ""
        ).strip()



    def clean_filter_values(values):
        if not values:
            return []

        if not isinstance(values, list):
            values = [values]

        result = []

        for value in values:
            if value is None:
                continue

            value = str(value).strip()

            if value:
                result.append(value)

        return result


    def intersect_doc_ids(current_ids, new_ids):
        """
        多个筛选条件之间取交集。

        current_ids:
        - None 表示之前还没有筛选过
        - set/list 表示已有筛选结果
        """
        new_ids = {
            str(doc_id)
            for doc_id in new_ids
            if doc_id
        }

        if current_ids is None:
            return new_ids

        return {
            str(doc_id)
            for doc_id in current_ids
            if doc_id
        } & new_ids


    def return_empty_if_no_docs(doc_ids):
        """
        如果筛选后没有任何文档，直接返回空结果。
        """
        return doc_ids is not None and len(doc_ids) == 0


    def empty_document_list_result():
        """
        统一返回空列表。
        """
        return get_json_result(
            data={
                "total": 0,
                "docs": [],
                "week_growth_rate": 0,
                "this_week_count": 0,
                "current_user_role": current_user_role,
            }
        )
    def get_meta_field(meta, field):
        """
        从文档 metadata 中获取字段值。

        兼容几种常见结构：
        1. 直接结构：
        {"author": "张三"}

        2. meta_fields：
        {"meta_fields": {"author": "张三"}}

        3. meta_fields_display：
        {"meta_fields_display": {"author": ["张三"]}}
        """

        if not isinstance(meta, dict):
            return None

        # 直接字段
        if field in meta:
            return meta.get(field)

        # 常见嵌套字段
        for container_name in [
            "meta_fields",
            "meta_fields_display",
            "metadata",
            "meta",
        ]:
            container = meta.get(container_name)

            if isinstance(container, dict) and field in container:
                return container.get(field)

        return None

    def value_to_text(value):
        """
        将字符串、列表、数字等统一转成文本。
        """
        if value is None:
            return ""

        if isinstance(value, list):
            return " ".join(
                str(item).strip()
                for item in value
                if str(item).strip()
            )

        if isinstance(value, dict):
            # 兼容标签对象
            values = []

            for key in [
                "option_name",
                "option_code",
                "name",
                "label",
                "value",
            ]:
                if value.get(key) is not None:
                    values.append(str(value.get(key)))

            return " ".join(values)

        return str(value).strip()


    def fuzzy_match_meta(meta_value, keyword):
        """
        元数据模糊匹配，不区分大小写。

        例如：
        keyword = "东北林业"
        meta_value = "东北林业大学"
        返回 True
        """
        keyword = str(keyword or "").strip()

        if not keyword:
            return True

        if meta_value is None:
            return False

        if isinstance(meta_value, list):
            return any(
                fuzzy_match_meta(item, keyword)
                for item in meta_value
            )

        actual_text = value_to_text(meta_value).casefold()
        keyword_text = keyword.casefold()

        return keyword_text in actual_text

    from datetime import datetime
    import re

    def normalize_date(value):
        if value is None or value == "":
            return None

        text = str(value).strip()
        if text.lower() == "none":
            return None

        try:
            # 2024年1月
            match = re.fullmatch(r'(\d{4})年(\d{1,2})月', text)
            if match:
                year, month = map(int, match.groups())
                if 1 <= month <= 12:
                    return datetime(year, month, 1).date()
                return None

            # 2024年1月2日
            match = re.fullmatch(r'(\d{4})年(\d{1,2})月(\d{1,2})日', text)
            if match:
                year, month, day = map(int, match.groups())
                return datetime(year, month, day).date()

            # 2024-01 / 2024.01
            match = re.fullmatch(r'(\d{4})[-.](\d{1,2})', text)
            if match:
                year, month = map(int, match.groups())
                if 1 <= month <= 12:
                    return datetime(year, month, 1).date()
                return None

            # 2024-01-01 / 2024.01.01 / 2024/01/01
            text2 = text.replace("/", "-")[:10]
            for fmt in ["%Y-%m-%d", "%Y.%m.%d"]:
                try:
                    return datetime.strptime(text2, fmt).date()
                except ValueError:
                    pass

        except Exception:
            return None

        return None

    def filter_docs_by_metadata(
        metas,
        author="",
        school="",
        date_start="",
        date_end="",
    ):
        start_date = normalize_date(date_start)
        end_date = normalize_date(date_end)

        if not isinstance(metas, dict):
            return set()

        def match_field(field_name, query):
            """在某个字段的倒排索引里，找所有匹配 query 的 doc_id"""
            if not query:
                return None

            field_map = metas.get(field_name, {})
            if not isinstance(field_map, dict):
                return set()

            matched_ids = set()
            for value, doc_ids in field_map.items():
                if fuzzy_match_meta(value, query):
                    matched_ids.update(doc_ids if isinstance(doc_ids, list) else [doc_ids])

            return matched_ids

        result = None  # 用于做交集

        # 作者筛选
        if author:
            ids = match_field("author", author)
            result = ids if result is None else result & ids

        # 学校筛选
        if school:
            ids = match_field("school", school)
            result = ids if result is None else result & ids

        # 时间筛选
        if start_date or end_date:
            date_fields = ("publish_date", "publish_time", "create_time", "created_at", "date")
            matched_ids = set()

            for field_name in date_fields:
                field_map = metas.get(field_name, {})
                if not isinstance(field_map, dict):
                    continue

                for value, doc_ids in field_map.items():
                    actual_date = normalize_date(value)
                    if actual_date is None:
                        continue

                    if start_date and actual_date < start_date:
                        continue
                    if end_date and actual_date > end_date:
                        continue

                    matched_ids.update(doc_ids if isinstance(doc_ids, list) else [doc_ids])

            result = matched_ids if result is None else result & matched_ids

        return result or set()

    

    # ---------------------------------------------------------
    # 清洗前端传来的筛选条件
    # ---------------------------------------------------------
    import time
    start_time = time.time()
    version = clean_filter_values(
        req.get("version", [])
    )

    document_status = clean_filter_values(
        req.get("document_status", [])
    )

    applicable_lines = clean_filter_values(
        req.get("applicable_lines", [])
    )

    knowledge_category = clean_filter_values(
        req.get("knowledge_category", [])
    )

    knowledge_level = clean_filter_values(
        req.get("knowledge_level", [])
    )

    knowledge_type = clean_filter_values(
        req.get("knowledge_type", [])
    )
    end_time = time.time()
    print("step1:", end_time - start_time)

    # ---------------------------------------------------------
    # metadata_condition 校验
    # ---------------------------------------------------------

    if metadata_condition and not isinstance(
        metadata_condition,
        dict,
    ):
        return get_data_error_result(
            message="metadata_condition must be an object."
        )


    # ---------------------------------------------------------
    # doc_ids_filter 用来收集所有额外筛选后的 Document.id
    #
    # None 表示暂时没有额外 doc_id 限制
    # set(...) 表示已经筛选出来的文档 ID
    # ---------------------------------------------------------

    doc_ids_filter = None


    # ---------------------------------------------------------
    # 元数据过滤
    # ---------------------------------------------------------

    has_custom_metadata_filter = bool(
        author
        or school
        or publish_date_start
        or publish_date_end
    )

    if metadata_condition or has_custom_metadata_filter:
        metas = DocumentService.get_flatted_meta_by_kbs([kb_id])

        # 1. 保留原来的 metadata_condition 过滤
        if metadata_condition:
            metadata_doc_ids = meta_filter(
                metas,
                convert_conditions(metadata_condition),
                metadata_condition.get("logic", "and"),
            )

            doc_ids_filter = intersect_doc_ids(
                doc_ids_filter,
                metadata_doc_ids,
            )

            if return_empty_if_no_docs(doc_ids_filter):
                return empty_document_list_result()

        # 2. 作者、学校、时间过滤
        if has_custom_metadata_filter:
            custom_metadata_doc_ids = filter_docs_by_metadata(
                metas=metas,
                author=author,
                school=school,
                date_start=publish_date_start,
                date_end=publish_date_end,
            )

            doc_ids_filter = intersect_doc_ids(
                doc_ids_filter,
                custom_metadata_doc_ids,
            )

            if return_empty_if_no_docs(doc_ids_filter):
                return empty_document_list_result()


    # ---------------------------------------------------------
    # 文档状态过滤 Document.status
    # 前端字段：document_status
    # 后端表字段：Document.status
    # ---------------------------------------------------------

    if document_status:
        status_doc_rows = (
            Document
            .select(Document.id)
            .where(
                (Document.kb_id == kb_id) &
                (Document.status.in_(document_status))
            )
        )

        status_doc_ids = [
            row.id
            for row in status_doc_rows
            if row.id
        ]

        doc_ids_filter = intersect_doc_ids(
            doc_ids_filter,
            status_doc_ids,
        )

        if return_empty_if_no_docs(doc_ids_filter):
            return empty_document_list_result()


    # ---------------------------------------------------------
    # 版本过滤 StagedFile.version
    # 前端字段：version
    # 后端表字段：StagedFile.version
    # ---------------------------------------------------------

    if version:
        version_values = set()

        for item in version:
            raw_value = str(item).strip()

            if not raw_value:
                continue

            version_values.add(raw_value)

            # 兼容前端传 v1.0，数据库存 1.0
            if raw_value.lower().startswith("v"):
                version_values.add(raw_value[1:])
            else:
                version_values.add(f"v{raw_value}")

        version_condition = StagedFile.version.in_(
            list(version_values)
        )

        # 如果前端选择 v1.0，兼容数据库 version 为空的情况
        normalized_versions = {
            str(item).lower()
            for item in version_values
        }

        if (
            "v1.0" in normalized_versions
            or "1.0" in normalized_versions
        ):
            version_condition = (
                version_condition |
                StagedFile.version.is_null(True) |
                (StagedFile.version == "")
            )

        version_doc_rows = (
            StagedFile
            .select(StagedFile.doc_id)
            .where(
                (StagedFile.kb_id == kb_id) &
                (StagedFile.doc_id.is_null(False)) &
                version_condition
            )
            .distinct()
        )

        version_doc_ids = [
            row.doc_id
            for row in version_doc_rows
            if row.doc_id
        ]

        doc_ids_filter = intersect_doc_ids(
            doc_ids_filter,
            version_doc_ids,
        )

        if return_empty_if_no_docs(doc_ids_filter):
            return empty_document_list_result()


    # ---------------------------------------------------------
    # 标签过滤 StagedFileTag
    #
    # 关系：
    # Document.id -> StagedFile.doc_id
    # StagedFile.id -> StagedFileTag.stage_id
    #
    # 规则：
    # - 同一个 type_code 内部多个 option_code 是 OR
    # - 不同 type_code 之间是 AND
    # ---------------------------------------------------------

    tag_filter_map = {
        "applicable_lines": applicable_lines,
        "knowledge_category": knowledge_category,
        "knowledge_level": knowledge_level,
        "knowledge_type": knowledge_type,
    }

    for type_code, option_codes in tag_filter_map.items():
        if not option_codes:
            continue

        tag_doc_rows = (
            StagedFile
            .select(StagedFile.doc_id)
            .join(
                StagedFileTag,
                on=(
                    StagedFile.id ==
                    StagedFileTag.stage_id
                ),
            )
            .where(
                (StagedFile.kb_id == kb_id) &
                (StagedFile.doc_id.is_null(False)) &
                (StagedFileTag.type_code == type_code) &
                (StagedFileTag.option_code.in_(option_codes))
            )
            .distinct()
        )

        tag_doc_ids = [
            row.doc_id
            for row in tag_doc_rows
            if row.doc_id
        ]

        doc_ids_filter = intersect_doc_ids(
            doc_ids_filter,
            tag_doc_ids,
        )

        if return_empty_if_no_docs(doc_ids_filter):
            return empty_document_list_result()

    try:
        # docs, total = DocumentService.get_by_kb_id(
        #     kb_id,
        #     page_number,
        #     items_per_page,
        #     orderby,
        #     desc,
        #     keywords,
        #     run_status,
        #     types,
        #     suffix,
        #     doc_ids_filter,
        # )
        start_time = time.time()
        docs, total = DocumentService.get_by_kb_id(
            kb_id,
            page_number,
            items_per_page,
            orderby,
            desc,
            keywords,
            run_status,
            types,
            suffix,
            list(doc_ids_filter) if doc_ids_filter is not None else None,
        )
        end_time = time.time()
        print("查询基础表格耗时:", end_time - start_time)

        # 当前页文档 ID
        doc_ids = [
            doc["id"]
            for doc in docs
            if doc.get("id")
        ]

        # ---------------------------------------------------------
        # 查询当前页文档对应的解析任务
        # ---------------------------------------------------------
        doc_tasks = defaultdict(list)
        start_time = time.time()
        if doc_ids:
            pass
            task_rows = (
                Task.select(
                    Task.doc_id,
                    Task.task_type,
                    Task.progress,
                    Task.progress_msg,
                    Task.begin_at,
                )
                .where(Task.doc_id.in_(doc_ids))
                .order_by(Task.begin_at.asc())
            )

            for task in task_rows:
                task_type = (
                    task.task_type or ""
                ).lower().strip()

                doc_tasks[str(task.doc_id)].append({
                    "task_type": task_type,
                    "progress": task.progress,
                    "progress_msg": task.progress_msg,
                    "begin_at": task.begin_at,
                })
        end_time = time.time()
        print("查询解析任务耗时:", end_time - start_time)

        # ---------------------------------------------------------
        # 按创建时间再次过滤
        # 保留原来的行为
        # ---------------------------------------------------------
        if create_time_from or create_time_to:
            filtered_docs = []

            for doc in docs:
                doc_create_time = doc.get(
                    "create_time",
                    0,
                )

                if (
                    (
                        create_time_from == 0
                        or doc_create_time >= create_time_from
                    )
                    and
                    (
                        create_time_to == 0
                        or doc_create_time <= create_time_to
                    )
                ):
                    filtered_docs.append(doc)

            docs = filtered_docs

            # 过滤后重新整理 doc_ids
            doc_ids = [
                doc["id"]
                for doc in docs
                if doc.get("id")
            ]

        # ---------------------------------------------------------
        # 批量查询文档标签和版本号
        #
        # 标签关系：
        # Document.id
        #     -> StagedFile.doc_id
        #     -> StagedFile.id
        #     -> StagedFileTag.stage_id
        #
        # 版本关系：
        # Document.id
        #     -> StagedFile.doc_id
        #     -> StagedFile.version
        # ---------------------------------------------------------
        document_tag_data = defaultdict(
            lambda: {
                "tag_metadata": {},
                "meta_fields_display": {},
            }
        )

        # doc_id -> version
        document_version_map = {}

        start_time = time.time()
        if doc_ids:
            # doc_id -> stage_id list
            doc_stage_map = defaultdict(list)

            staged_rows = (
                StagedFile.select(
                    StagedFile.id,
                    StagedFile.doc_id,
                    StagedFile.version,
                    StagedFile.committed_at,
                    StagedFile.created_at,
                )
                .where(
                    (StagedFile.doc_id.in_(doc_ids)) &
                    (StagedFile.kb_id == kb_id)
                )
                .order_by(
                    StagedFile.committed_at.desc(),
                    StagedFile.created_at.desc(),
                    StagedFile.id.desc(),
                )
            )

            stage_ids = []

            for staged in staged_rows:
                if not staged.doc_id:
                    continue

                current_doc_id = str(staged.doc_id)
                stage_id = str(staged.id)

                # 标签查询使用
                doc_stage_map[current_doc_id].append(
                    stage_id
                )

                stage_ids.append(stage_id)

                # 获取当前文档版本
                # 因为查询已经按最新时间倒序，
                # 所以同一个 doc_id 只取第一条。
                if current_doc_id not in document_version_map:
                    raw_version = str(
                        getattr(staged, "version", None)
                        or ""
                    ).strip()

                    if not raw_version:
                        display_version = "v1.0"
                    elif raw_version.lower().startswith("v"):
                        display_version = raw_version
                    else:
                        display_version = f"v{raw_version}"

                    document_version_map[current_doc_id] = (
                        display_version
                    )

            if stage_ids:
                # stage_id -> type_code -> option_code list
                stage_tag_map = defaultdict(
                    lambda: defaultdict(list)
                )

                type_codes = set()

                tag_rows = (
                    StagedFileTag.select(
                        StagedFileTag.stage_id,
                        StagedFileTag.type_code,
                        StagedFileTag.option_code,
                    )
                    .where(
                        StagedFileTag.stage_id.in_(
                            stage_ids
                        )
                    )
                )

                for tag in tag_rows:
                    stage_id = str(tag.stage_id)
                    type_code = str(
                        tag.type_code or ""
                    ).strip()
                    option_code = str(
                        tag.option_code or ""
                    ).strip()

                    if not type_code or not option_code:
                        continue

                    if (
                        option_code
                        not in stage_tag_map[
                            stage_id
                        ][type_code]
                    ):
                        stage_tag_map[
                            stage_id
                        ][type_code].append(
                            option_code
                        )

                    type_codes.add(type_code)

                # 查询标签类型名称
                type_name_map = {}

                if type_codes:
                    type_rows = (
                        KnowledgeTagType.select(
                            KnowledgeTagType.type_code,
                            KnowledgeTagType.type_name,
                        )
                        .where(
                            KnowledgeTagType.type_code.in_(
                                list(type_codes)
                            )
                        )
                    )

                    for tag_type in type_rows:
                        type_name_map[
                            str(tag_type.type_code)
                        ] = tag_type.type_name

                # 查询标签选项名称
                option_name_map = defaultdict(dict)

                if type_codes:
                    option_rows = (
                        KnowledgeTagOption.select(
                            KnowledgeTagOption.type_code,
                            KnowledgeTagOption.option_code,
                            KnowledgeTagOption.option_name,
                        )
                        .where(
                            KnowledgeTagOption.type_code.in_(
                                list(type_codes)
                            )
                        )
                    )

                    for option in option_rows:
                        current_type_code = str(
                            option.type_code
                        )

                        current_option_code = str(
                            option.option_code
                        )

                        option_name_map[
                            current_type_code
                        ][current_option_code] = (
                            option.option_name
                        )

                # 将标签按 doc_id 汇总
                for (
                    current_doc_id,
                    doc_stage_ids,
                ) in doc_stage_map.items():
                    tag_metadata = {}
                    meta_fields_display = {}

                    for stage_id in doc_stage_ids:
                        type_map = stage_tag_map.get(
                            stage_id,
                            {},
                        )

                        for (
                            type_code,
                            option_codes,
                        ) in type_map.items():
                            type_name = type_name_map.get(
                                type_code,
                                type_code,
                            )

                            tag_item = (
                                tag_metadata.setdefault(
                                    type_code,
                                    {
                                        "type_code": (
                                            type_code
                                        ),
                                        "type_name": (
                                            type_name
                                        ),
                                        "options": [],
                                    },
                                )
                            )

                            display_values = (
                                meta_fields_display.setdefault(
                                    type_code,
                                    [],
                                )
                            )

                            for option_code in option_codes:
                                option_name = (
                                    option_name_map[
                                        type_code
                                    ].get(
                                        option_code,
                                        option_code,
                                    )
                                )

                                option_item = {
                                    "option_code": (
                                        option_code
                                    ),
                                    "option_name": (
                                        option_name
                                    ),
                                }

                                if (
                                    option_item
                                    not in tag_item["options"]
                                ):
                                    tag_item[
                                        "options"
                                    ].append(
                                        option_item
                                    )

                                if (
                                    option_name
                                    not in display_values
                                ):
                                    display_values.append(
                                        option_name
                                    )

                    document_tag_data[
                        current_doc_id
                    ] = {
                        "tag_metadata": tag_metadata,
                        "meta_fields_display": (
                            meta_fields_display
                        ),
                    }
        end_time = time.time()
        
        print("获取标签耗费:", end_time - start_time)
        # ---------------------------------------------------------
        # 整理每篇文档的返回数据
        # ---------------------------------------------------------
        start_time = time.time()
        for doc_item in docs:
            doc_id = str(doc_item["id"])
            # 返回文档版本号
            doc_item["version"] = (
                document_version_map.get(doc_id)
                or "v1.0"
            )

            tasks = doc_tasks.get(doc_id, [])

            has_author_task = any(
                task["task_type"] == "parse_author_info"
                for task in tasks
            )

            has_parse_task = any(
                task["task_type"] == ""
                for task in tasks
            )

            doc_item["has_author_task"] = has_author_task
            doc_item["has_parse_task"] = has_parse_task

            if has_author_task and has_parse_task:
                doc_item["process_scene"] = (
                    "author_with_parse"
                )
            elif has_author_task:
                doc_item["process_scene"] = "author_only"
            elif has_parse_task:
                doc_item["process_scene"] = "parse_only"
            else:
                doc_item["process_scene"] = "unknown"

            latest_task = tasks[-1] if tasks else None

            doc_item["latest_task_type"] = (
                latest_task["task_type"]
                if latest_task
                else ""
            )

            if (
                doc_item.get("thumbnail")
                and not doc_item["thumbnail"].startswith(
                    IMG_BASE64_PREFIX
                )
            ):
                doc_item["thumbnail"] = (
                    f"/v1/document/image/"
                    f"{kb_id}-{doc_item['thumbnail']}"
                )

            if doc_item.get("source_type"):
                doc_item["source_type"] = (
                    doc_item["source_type"].split("/")[0]
                )

            # 从 meta_fields 中解析作者、学校、发布时间
            meta_fields = doc_item.get("meta_fields") or {}

            if isinstance(meta_fields, str):
                try:
                    meta_fields = json.loads(meta_fields)
                except json.JSONDecodeError:
                    meta_fields = {}

            if not isinstance(meta_fields, dict):
                meta_fields = {}

            doc_item["meta_fields"] = meta_fields

            doc_item["author"] = meta_fields.get(
                "author",
                "",
            )

            doc_item["school"] = meta_fields.get(
                "school",
                "",
            )

            doc_item["publish_time"] = meta_fields.get(
                "publish_time",
                "",
            )

            # 标签中文展示数据
            tag_data = document_tag_data.get(
                doc_id,
                {
                    "tag_metadata": {},
                    "meta_fields_display": {},
                },
            )

            doc_item["tag_metadata"] = tag_data[
                "tag_metadata"
            ]

            doc_item["meta_fields_display"] = tag_data[
                "meta_fields_display"
            ]

            # -----------------------------------------------------
            # 新增：根据标签判断公开 / 内部
            # -----------------------------------------------------
            visibility_level = get_doc_visibility_from_tags(
                tag_data
            )

            doc_item["visibility_level"] = visibility_level

            doc_item["visibility_name"] = (
                "内部"
                if visibility_level == INTERNAL
                else "公开"
            )

            doc_item["can_view"] = can_view_document(
                current_role,
                visibility_level,
                is_super_admin,
            )
        end_time = time.time()
        print("拼接返回结果耗时:", end_time - start_time)

        # ---------------------------------------------------------
        # 新增显示本周文件占比
        # ---------------------------------------------------------
        start_time = time.time()
        now = datetime.now()
        from datetime import datetime, timedelta, time
        this_week_start = datetime.combine(
            now.date() - timedelta(days=now.weekday()),
            time.min,
        )

        this_week_start_ts = int(
            this_week_start.timestamp() * 1000
        )

        this_week_count = (
            Document.select()
            .where(
                (Document.kb_id == kb_id) &
                (Document.create_time >= this_week_start_ts) &
                (Document.status != "2")
            )
            .count()
        )

        week_file_ratio = (
            0
            if total == 0
            else round(this_week_count / total * 100, 2)
        )
        import time
        end_time = time.time()
        print("显示本周占比耗时:", end_time - start_time)

        return get_json_result(
            data={
                "total": total,
                "docs": docs,
                "week_growth_rate": week_file_ratio,
                "this_week_count": this_week_count,
                "current_user_role": current_user_role,
            }
        )

    except Exception as e:
        return server_error_response(e)

@manager.route("/list_wasted", methods=["POST"])  # noqa: F821
@login_required
async def list_docs_wasted():
    kb_id = request.args.get("kb_id")
    if not kb_id:
        return get_json_result(data=False, message='Lack of "KB ID"', code=RetCode.ARGUMENT_ERROR)
    ok, kb = KnowledgebaseService.get_by_id(kb_id)
    if not ok:
        return get_json_result(data=False, message="Dataset not found.", code=RetCode.DATA_ERROR)
    if not check_kb_team_permission(kb, current_user.id):
        return get_json_result(data=False, message="Only owner or team members are authorized for this operation.", code=RetCode.OPERATING_ERROR)
    keywords = request.args.get("keywords", "")

    page_number = int(request.args.get("page", 0))
    items_per_page = int(request.args.get("page_size", 0))
    orderby = request.args.get("orderby", "create_time")
    if request.args.get("desc", "true").lower() == "false":
        desc = False
    else:
        desc = True
    create_time_from = int(request.args.get("create_time_from", 0))
    create_time_to = int(request.args.get("create_time_to", 0))

    req = await get_request_json()

    run_status = req.get("run_status", [])
    if run_status:
        invalid_status = {s for s in run_status if s not in VALID_TASK_STATUS}
        if invalid_status:
            return get_data_error_result(message=f"Invalid filter run status conditions: {', '.join(invalid_status)}")

    types = req.get("types", [])
    if types:
        invalid_types = {t for t in types if t not in VALID_FILE_TYPES}
        if invalid_types:
            return get_data_error_result(message=f"Invalid filter conditions: {', '.join(invalid_types)} type{'s' if len(invalid_types) > 1 else ''}")

    suffix = req.get("suffix", [])
    metadata_condition = req.get("metadata_condition", {}) or {}
    if metadata_condition and not isinstance(metadata_condition, dict):
        return get_data_error_result(message="metadata_condition must be an object.")

    doc_ids_filter = None
    if metadata_condition:
        metas = DocumentService.get_flatted_meta_by_kbs([kb_id])
        doc_ids_filter = meta_filter(metas, convert_conditions(metadata_condition), metadata_condition.get("logic", "and"))
        if metadata_condition.get("conditions") and not doc_ids_filter:
            return get_json_result(data={"total": 0, "docs": []})

    try:
        docs, tol = DocumentService.get_by_kb_id_wasted(kb_id, page_number, items_per_page, orderby, desc, keywords, run_status, types, suffix, doc_ids_filter)

        from collections import defaultdict
        from api.db.db_models import Task

        doc_ids = [doc["id"] for doc in docs]
        doc_tasks = defaultdict(list)

        if doc_ids:
            task_rows = (
                Task.select(Task.doc_id, Task.task_type, Task.progress, Task.progress_msg, Task.begin_at)
                .where(Task.doc_id.in_(doc_ids))
                .order_by(Task.begin_at)
            )

            for task in task_rows:
                task_type = (task.task_type or "").lower().strip()
                doc_tasks[task.doc_id].append({
                    "task_type": task_type,
                    "progress": task.progress,
                    "progress_msg": task.progress_msg,
                    "begin_at": task.begin_at,
                })
        if create_time_from or create_time_to:
            filtered_docs = []
            for doc in docs:
                doc_create_time = doc.get("create_time", 0)
                if (create_time_from == 0 or doc_create_time >= create_time_from) and (create_time_to == 0 or doc_create_time <= create_time_to):
                    filtered_docs.append(doc)
            docs = filtered_docs
        for doc_item in docs:
            tasks = doc_tasks.get(doc_item["id"], [])

            has_author_task = any(t["task_type"] == "parse_author_info" for t in tasks)
            has_parse_task = any(t["task_type"] == "" for t in tasks)

            doc_item["has_author_task"] = has_author_task
            doc_item["has_parse_task"] = has_parse_task

            if has_author_task and has_parse_task:
                doc_item["process_scene"] = "author_with_parse"
            elif has_author_task:
                doc_item["process_scene"] = "author_only"
            elif has_parse_task:
                doc_item["process_scene"] = "parse_only"
            else:
                doc_item["process_scene"] = "unknown"

            latest_task = tasks[-1] if tasks else None
            doc_item["latest_task_type"] = latest_task["task_type"] if latest_task else ""

            if doc_item["thumbnail"] and not doc_item["thumbnail"].startswith(IMG_BASE64_PREFIX):
                doc_item["thumbnail"] = f"/v1/document/image/{kb_id}-{doc_item['thumbnail']}"
            if doc_item.get("source_type"):
                doc_item["source_type"] = doc_item["source_type"].split("/")[0]
            # 将字段的meta_fields字段解析出新的字段，并且整理为我们需要的作者、学校、论文发布时间
            if doc_item.get("meta_fields"):
                meta_fields = doc_item["meta_fields"]
                # 确保 meta_fields 是一个字典
                if isinstance(meta_fields, str):
                    try:
                        meta_fields = json.loads(meta_fields)
                    except json.JSONDecodeError:
                        meta_fields = {}
                # 确保 meta_fields 是一个字典
                if isinstance(meta_fields, dict):
                    doc_item["author"] = meta_fields.get("author", "")
                    doc_item["school"] = meta_fields.get("school", "")
                    doc_item["publish_time"] = meta_fields.get("publish_time", "")
                else:
                    doc_item["author"] = ""
                    doc_item["school"] = ""
                    doc_item["publish_time"] = ""

        # 新增显示本周文件占比
        from datetime import datetime, timedelta, time
        from api.db.db_models import Document

        now = datetime.now()
        this_week_start = datetime.combine(
            now.date() - timedelta(days=now.weekday()),
            time.min,
        )

        this_week_start_ts = int(this_week_start.timestamp() * 1000)

        this_week_count = Document.select().where(
            Document.kb_id == kb_id,
            Document.create_time >= this_week_start_ts,
        ).count()

        week_file_ratio = 0 if tol == 0 else round(this_week_count / tol * 100, 2)

        return get_json_result(data={"total": tol, "docs": docs,
                                     "week_growth_rate": week_file_ratio,
                                        "this_week_count": this_week_count,})
    except Exception as e:
        return server_error_response(e)


# @manager.route("/filter", methods=["POST"])  # noqa: F821
# @login_required
# async def get_filter():
#     req = await get_request_json()

#     kb_id = req.get("kb_id")
#     if not kb_id:
#         return get_json_result(data=False, message='Lack of "KB ID"', code=RetCode.ARGUMENT_ERROR)
#     ok, kb = KnowledgebaseService.get_by_id(kb_id)
#     if not ok:
#         return get_json_result(data=False, message="Dataset not found.", code=RetCode.DATA_ERROR)
#     # if not check_kb_team_permission(kb, current_user.id):
#     #     return get_json_result(data=False, message="Only owner or team members are authorized for this operation.", code=RetCode.OPERATING_ERROR)

#     keywords = req.get("keywords", "")

#     suffix = req.get("suffix", [])

#     run_status = req.get("run_status", [])
#     if run_status:
#         invalid_status = {s for s in run_status if s not in VALID_TASK_STATUS}
#         if invalid_status:
#             return get_data_error_result(message=f"Invalid filter run status conditions: {', '.join(invalid_status)}")

#     types = req.get("types", [])
#     if types:
#         invalid_types = {t for t in types if t not in VALID_FILE_TYPES}
#         if invalid_types:
#             return get_data_error_result(message=f"Invalid filter conditions: {', '.join(invalid_types)} type{'s' if len(invalid_types) > 1 else ''}")

#     try:
#         filter, total = DocumentService.get_filter_by_kb_id(kb_id, keywords, run_status, types, suffix)
#         return get_json_result(data={"total": total, "filter": filter})
#     except Exception as e:
#         return server_error_response(e)


@manager.route("/filter", methods=["POST"])  # noqa: F821
@login_required
async def get_filter():
    req = await get_request_json()

    kb_id = req.get("kb_id")

    if not kb_id:
        return get_json_result(
            data=False,
            message='Lack of "KB ID"',
            code=RetCode.ARGUMENT_ERROR,
        )

    ok, kb = KnowledgebaseService.get_by_id(kb_id)

    if not ok:
        return get_json_result(
            data=False,
            message="Dataset not found.",
            code=RetCode.DATA_ERROR,
        )

    # 建议恢复权限检查
    # if not check_kb_team_permission(
    #     kb,
    #     current_user.id,
    # ):
    #     return get_json_result(
    #         data=False,
    #         message=(
    #             "Only owner or team members are "
    #             "authorized for this operation."
    #         ),
    #         code=RetCode.OPERATING_ERROR,
    #     )

    # keywords 只表示文件名关键词
    keywords = req.get("keywords", "")

    if keywords is None:
        keywords = ""

    if not isinstance(keywords, str):
        return get_data_error_result(
            message='"keywords" must be a string.'
        )

    try:
        filter_result, total = (
            DocumentService.get_filter_by_kb_id(
                kb_id=kb_id,
                keywords=keywords,
            )
        )

        return get_json_result(
            data={
                "total": total,
                "filter": filter_result,
            }
        )

    except Exception as e:
        return server_error_response(e)

@manager.route("/filter_wasted", methods=["POST"])  # noqa: F821
@login_required
async def get_filter_wasted():
    req = await get_request_json()

    kb_id = req.get("kb_id")
    if not kb_id:
        return get_json_result(data=False, message='Lack of "KB ID"', code=RetCode.ARGUMENT_ERROR)
    ok, kb = KnowledgebaseService.get_by_id(kb_id)
    if not ok:
        return get_json_result(data=False, message="Dataset not found.", code=RetCode.DATA_ERROR)
    if not check_kb_team_permission(kb, current_user.id):
        return get_json_result(data=False, message="Only owner or team members are authorized for this operation.", code=RetCode.OPERATING_ERROR)

    keywords = req.get("keywords", "")

    suffix = req.get("suffix", [])

    run_status = req.get("run_status", [])
    if run_status:
        invalid_status = {s for s in run_status if s not in VALID_TASK_STATUS}
        if invalid_status:
            return get_data_error_result(message=f"Invalid filter run status conditions: {', '.join(invalid_status)}")

    types = req.get("types", [])
    if types:
        invalid_types = {t for t in types if t not in VALID_FILE_TYPES}
        if invalid_types:
            return get_data_error_result(message=f"Invalid filter conditions: {', '.join(invalid_types)} type{'s' if len(invalid_types) > 1 else ''}")

    try:
        filter, total = DocumentService.get_filter_by_kb_id_wasted(kb_id, keywords, run_status, types, suffix)
        return get_json_result(data={"total": total, "filter": filter})
    except Exception as e:
        return server_error_response(e)


@manager.route("/infos", methods=["POST"])  # noqa: F821
@login_required
async def doc_infos():
    req = await get_request_json()
    doc_ids = req["doc_ids"]
    for doc_id in doc_ids:
        if not DocumentService.accessible(doc_id, current_user.id):
            return get_json_result(data=False, message="No authorization.", code=RetCode.AUTHENTICATION_ERROR)
    docs = DocumentService.get_by_ids(doc_ids)
    return get_json_result(data=list(docs.dicts()))


@manager.route("/metadata/summary", methods=["POST"])  # noqa: F821
@login_required
async def metadata_summary():
    req = await get_request_json()
    kb_id = req.get("kb_id")
    if not kb_id:
        return get_json_result(data=False, message='Lack of "KB ID"', code=RetCode.ARGUMENT_ERROR)

    tenants = UserTenantService.query(user_id=current_user.id)
    if not KnowledgebaseService.accessible(kb_id, current_user.id):
        return get_json_result(data=False, message="Only owner of dataset authorized for this operation.", code=RetCode.OPERATING_ERROR)

    try:
        summary = DocumentService.get_metadata_summary(kb_id)
        return get_json_result(data={"summary": summary})
    except Exception as e:
        return server_error_response(e)


@manager.route("/metadata/update", methods=["POST"])  # noqa: F821
@login_required
async def metadata_update():
    req = await get_request_json()
    kb_id = req.get("kb_id")
    if not kb_id:
        return get_json_result(data=False, message='Lack of "KB ID"', code=RetCode.ARGUMENT_ERROR)
    # 判断用户是否拥有编辑权限
    if not user_has_operation_permission(current_user.id, "edit"):
        return get_json_result(
            data=False,
            message="没有编辑权限",
            code=RetCode.FORBIDDEN,
    )

    tenants = UserTenantService.query(user_id=current_user.id)
    if not KnowledgebaseService.writable(kb_id, current_user.id):
        return get_json_result(data=False, message="Only owner of dataset authorized for this operation.", code=RetCode.OPERATING_ERROR)

    selector = req.get("selector", {}) or {}
    updates = req.get("updates", []) or []
    deletes = req.get("deletes", []) or []

    if not isinstance(selector, dict):
        return get_json_result(data=False, message="selector must be an object.", code=RetCode.ARGUMENT_ERROR)
    if not isinstance(updates, list) or not isinstance(deletes, list):
        return get_json_result(data=False, message="updates and deletes must be lists.", code=RetCode.ARGUMENT_ERROR)

    metadata_condition = selector.get("metadata_condition", {}) or {}
    if metadata_condition and not isinstance(metadata_condition, dict):
        return get_json_result(data=False, message="metadata_condition must be an object.", code=RetCode.ARGUMENT_ERROR)

    document_ids = selector.get("document_ids", []) or []
    if document_ids and not isinstance(document_ids, list):
        return get_json_result(data=False, message="document_ids must be a list.", code=RetCode.ARGUMENT_ERROR)

    for upd in updates:
        if not isinstance(upd, dict) or not upd.get("key") or "value" not in upd:
            return get_json_result(data=False, message="Each update requires key and value.", code=RetCode.ARGUMENT_ERROR)
    for d in deletes:
        if not isinstance(d, dict) or not d.get("key"):
            return get_json_result(data=False, message="Each delete requires key.", code=RetCode.ARGUMENT_ERROR)

    kb_doc_ids = KnowledgebaseService.list_documents_by_ids([kb_id])
    target_doc_ids = set(kb_doc_ids)
    if document_ids:
        invalid_ids = set(document_ids) - set(kb_doc_ids)
        if invalid_ids:
            return get_json_result(data=False, message=f"These documents do not belong to dataset {kb_id}: {', '.join(invalid_ids)}", code=RetCode.ARGUMENT_ERROR)
        target_doc_ids = set(document_ids)

    if metadata_condition:
        metas = DocumentService.get_flatted_meta_by_kbs([kb_id])
        filtered_ids = set(meta_filter(metas, convert_conditions(metadata_condition), metadata_condition.get("logic", "and")))
        target_doc_ids = target_doc_ids & filtered_ids
        if metadata_condition.get("conditions") and not target_doc_ids:
            return get_json_result(data={"updated": 0, "matched_docs": 0})

    target_doc_ids = list(target_doc_ids)
    updated = DocumentService.batch_update_metadata(kb_id, target_doc_ids, updates, deletes)
    return get_json_result(data={"updated": updated, "matched_docs": len(target_doc_ids)})

# 获取缩略图的
@manager.route("/thumbnails", methods=["GET"])  # noqa: F821
# @login_required
def thumbnails():
    print("获取缩略图")
    doc_ids = request.args.getlist("doc_ids")
    if not doc_ids:
        return get_json_result(data=False, message='Lack of "Document ID"', code=RetCode.ARGUMENT_ERROR)

    try:
        docs = DocumentService.get_thumbnails(doc_ids)

        for doc_item in docs:
            if doc_item["thumbnail"] and not doc_item["thumbnail"].startswith(IMG_BASE64_PREFIX):
                doc_item["thumbnail"] = f"/v1/document/image/{doc_item['kb_id']}-{doc_item['thumbnail']}"

        return get_json_result(data={d["id"]: d["thumbnail"] for d in docs})
    except Exception as e:
        return server_error_response(e)


@manager.route("/change_status", methods=["POST"])  # noqa: F821
@login_required
@validate_request("doc_ids", "status")
async def change_status():
    req = await get_request_json()
    doc_ids = req.get("doc_ids", [])
    status = str(req.get("status", ""))

    if status not in ["0", "1"]:
        return get_json_result(data=False, message='"Status" must be either 0 or 1!', code=RetCode.ARGUMENT_ERROR)
    # 判断用户是否拥有编辑权限
    if not user_has_operation_permission(current_user.id, "edit"):
        return get_json_result(
            data=False,
            message="没有编辑权限",
            code=RetCode.FORBIDDEN,
    )

    result = {}
    # for doc_id in doc_ids:
    #     try:
    #         e, doc = DocumentService.get_by_id(doc_id)
    #         if not e:
    #             result[doc_id] = {"error": "No authorization."}
    #             continue
    #         e, kb = KnowledgebaseService.get_by_id(doc.kb_id)
    #         if not e:
    #             result[doc_id] = {"error": "Can't find this dataset!"}
    #             continue
    #         if not check_kb_team_write_permission(kb, current_user.id):
    #             result[doc_id] = {"error": "No authorization."}
    #             continue
    #         if not DocumentService.update_by_id(doc_id, {"status": str(status)}):
    #             result[doc_id] = {"error": "Database error (Document update)!"}
    #             continue

    #         PipelineOperationLogService.update_status_by_document_ids(
    #             doc_id,
    #             status,
    #         )


    #         status_int = int(status)
    #         if not settings.docStoreConn.update({"doc_id": doc_id}, {"available_int": status_int}, search.index_name(kb.tenant_id), doc.kb_id):
    #             result[doc_id] = {"error": "Database error (docStore update)!"}
    #         result[doc_id] = {"status": status}
    #     except Exception as e:
    #         result[doc_id] = {"error": f"Internal server error: {str(e)}"}
    for doc_id in doc_ids:
        try:
            e, doc = DocumentService.get_by_id(doc_id)
            if not e:
                result[doc_id] = {"error": "No authorization."}
                continue
            e, kb = KnowledgebaseService.get_by_id(doc.kb_id)
            if not e:
                result[doc_id] = {"error": "Can't find this dataset!"}
                continue
            if not check_kb_team_write_permission(kb, current_user.id):
                result[doc_id] = {"error": "No authorization."}
                continue

            # ====== 新增：获取旧状态，用于 before_data ======
            old_status = doc.status  # 假设 Document 模型有 status 字段

            # 更新文档状态
            if not DocumentService.update_by_id(doc_id, {"status": str(status)}):
                result[doc_id] = {"error": "Database error (Document update)!"}
                continue

            PipelineOperationLogService.update_status_by_document_ids(
                doc_id,
                status,
            )

            status_int = int(status)
            docstore_ok = settings.docStoreConn.update(
                {"doc_id": doc_id}, {"available_int": status_int},
                search.index_name(kb.tenant_id), doc.kb_id
            )
            if not docstore_ok: 
                result[doc_id] = {"error": "Database error (docStore update)!"}
                # 注意：此时文档状态已更新，但 docStore 更新失败，日志中可记录该异常
                # 可以根据业务决定是否回滚，或继续记录日志（但标记为部分失败）

            # 在更新前获取 old_status，更新后 status 为传入的值
            old_status = doc.status  # "0" 或 "1"
            # ...执行更新...

            # 确定日志 action
            action_type = "enable" if status == "1" else "disable"
            status_text = "开启" if status == "1" else "关闭"
            old_status_text = "开启" if old_status == "1" else "关闭"

            OperationLogService.add_log(
                user_id=current_user.id,
                user_name=getattr(current_user, "nickname", None),
                user_email=getattr(current_user, "email", None),

                kb_id=doc.kb_id,
                kb_name=getattr(kb, "name", None),

                target_id=doc.id,
                target_name=doc.name,

                action=action_type,               # "enable" 或 "disable"
                status="success",                 # 可根据 docStore 结果调整
                message=f"{status_text}",  # 例如“文档由「关闭」开启”

                before_data={
                    "doc_id": doc.id,
                    "doc_name": doc.name,
                    "kb_id": doc.kb_id,
                    "status_code": old_status,
                    "status_text": old_status_text,
                },
                after_data={
                    "doc_id": doc.id,
                    "doc_name": doc.name,
                    "kb_id": doc.kb_id,
                    "kb_name": getattr(kb, "name", None),
                    "status_code": status,
                    "status_text": status_text,
                },

                request_obj=request,
            )

            # 最后记录结果
            result[doc_id] = {"status": status}

        except Exception as e:
            result[doc_id] = {"error": f"Internal server error: {str(e)}"}

    return get_json_result(data=result)

# 软删除
@manager.route("/rm", methods=["POST"])  # noqa: F821
@login_required
@validate_request("doc_id")
async def rm():
    req = await get_request_json()
    doc_ids = req["doc_id"]
    if isinstance(doc_ids, str):
        doc_ids = [doc_ids]

    # 判断用户是否拥有编辑权限
    if not user_has_operation_permission(current_user.id, "delete"):
        return get_json_result(
            data=False,
            message="没有删除权限",
            code=RetCode.FORBIDDEN,
    )

    for doc_id in doc_ids:
        e, doc = DocumentService.get_by_id(doc_id)
        if not e:
            return get_json_result(data=False, message="No authorization.", code=RetCode.AUTHENTICATION_ERROR)

        e, kb = KnowledgebaseService.get_by_id(doc.kb_id)
        if not e:
            return get_data_error_result(message="Can't find this dataset!")

        # if not check_kb_team_write_permission(kb, current_user.id):
        #     return get_json_result(data=False, message="No authorization.", code=RetCode.AUTHENTICATION_ERROR)

    try:
        for doc_id in doc_ids:
            DocumentService.update_by_id(doc_id, {"status": "2"})

        await asyncio.to_thread(
            PipelineOperationLogService.update_status_by_document_ids,
            
            doc_ids,
            "2",
        )

        return get_json_result(data=True)
    except Exception as e:
        return server_error_response(e)

# 回收站删除
@manager.route("/rm_wasted", methods=["POST"])  # noqa: F821
@login_required
@validate_request("doc_id")
async def rm_wasted():
    req = await get_request_json()
    doc_ids = req["doc_id"]
    if isinstance(doc_ids, str):
        doc_ids = [doc_ids]
    # 判断用户是否拥有编辑权限
    if not user_has_operation_permission(current_user.id, "delete"):
        return get_json_result(
            data=False,
            message="没有删除权限",
            code=RetCode.FORBIDDEN,
    )

    for doc_id in doc_ids:
        e, doc = DocumentService.get_by_id(doc_id)
        if not e:
            return get_json_result(data=False, message="No authorization.", code=RetCode.AUTHENTICATION_ERROR)
        e, kb = KnowledgebaseService.get_by_id(doc.kb_id)
        if not e:
            return get_data_error_result(message="Can't find this dataset!")
        if not check_kb_team_write_permission(kb, current_user.id):
            return get_json_result(data=False, message="No authorization.", code=RetCode.AUTHENTICATION_ERROR)

    errors = await asyncio.to_thread(FileService.delete_docs, doc_ids, current_user.id)

    if errors:
        return get_json_result(data=False, message=errors, code=RetCode.SERVER_ERROR)
    
    await asyncio.to_thread(
        PipelineOperationLogService.delete_by_document_ids,
        doc_ids,
    )

    return get_json_result(data=True)


@manager.route("/run", methods=["POST"])  # noqa: F821
@login_required
@validate_request("doc_ids", "run")
async def run():
    req = await get_request_json()
    # 判断用户是否拥有上传限
    if not user_has_operation_permission(current_user.id, "upload"):
        return get_json_result(
            data=False,
            message="没有上传权限",
            code=RetCode.FORBIDDEN,
    )
    try:
        def _run_sync():
            # 遍历传入的文档id
            for doc_id in req["doc_ids"]:
                # 查数据库看文档是否存在
                e, doc = DocumentService.get_by_id(doc_id)
                if not e:
                    return get_json_result(data=False, message="No authorization.", code=RetCode.AUTHENTICATION_ERROR)
                # 通过文档找到所属的知识库（Knowledgebase），看知识库是否存在
                e, kb = KnowledgebaseService.get_by_id(doc.kb_id)
                if not e:
                    return get_data_error_result(message="Can't find this dataset!")
                
                # 确保当前用户有权限修改这个知识库（防止越权操作）。
                # if not check_kb_team_write_permission(kb, current_user.id):
                #     return get_json_result(data=False, message="No authorization.", code=RetCode.AUTHENTICATION_ERROR)
            # 用于在多次解析间共享表格数量信息的临时字典
            kb_table_num_map = {}
            for id in req["doc_ids"]:
                # 当前信息
                info = {"run": str(req["run"]), "progress": 0}

                # 如果是“重新运行”且要求“删除旧数据”
                if str(req["run"]) == TaskStatus.RUNNING.value and req.get("delete", False):
                    info["progress_msg"] = ""
                    info["chunk_num"] = 0
                    info["token_num"] = 0

                # 二次检查：再次获取租户 ID 和文档对象（为了安全，防止在长循环中数据状态变化）
                tenant_id = DocumentService.get_tenant_id(id)
                if not tenant_id:
                    return get_data_error_result(message="Tenant not found!")
                e, doc = DocumentService.get_by_id(id)
                if not e:
                    return get_data_error_result(message="Document not found!")

                # 处理“取消”指令
                if str(req["run"]) == TaskStatus.CANCEL.value:
                    if str(doc.run) == TaskStatus.RUNNING.value:
                        cancel_all_task_of(id)
                    else:
                        return get_data_error_result(message="Cannot cancel a task that is not in RUNNING status")
                # 处理“重新运行”清理
                if all([("delete" not in req or req["delete"]), str(req["run"]) == TaskStatus.RUNNING.value, str(doc.run) == TaskStatus.DONE.value]):
                    DocumentService.clear_chunk_num_when_rerun(doc.id)

                # 更新数据库状态
                DocumentService.update_by_id(id, info)
                # 物理删除旧数据 es0
                if req.get("delete", False):
                    TaskService.filter_delete([Task.doc_id == id])
                    if settings.docStoreConn.indexExist(search.index_name(tenant_id), doc.kb_id):
                        settings.docStoreConn.delete({"doc_id": id}, search.index_name(tenant_id), doc.kb_id)

                # 启动解析任务
                if str(req["run"]) == TaskStatus.RUNNING.value:
                    doc_dict = doc.to_dict()
                    DocumentService.run(tenant_id, doc_dict, kb_table_num_map)
                    
                    # Create parse_author_info task if not exists
                    from api.db.services.task_service import TaskService
                    from api.db.db_utils import bulk_insert_into_db
                    from rag.utils.redis_conn import REDIS_CONN
                    from datetime import datetime
                    
                    existing_task = TaskService.get_task_by_doc_id_and_type(doc.id, "parse_author_info")
                    if not existing_task:
                        task = {
                            "id": get_uuid(),
                            "doc_id": doc.id,
                            "task_type": "parse_author_info",
                            "progress": 0.0,
                            "from_page": 0,
                            "to_page": 100000000,
                            "begin_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        }
                        bulk_insert_into_db(Task, [task], True)
                        REDIS_CONN.queue_product(settings.get_svr_queue_name(0), message=task)

            return get_json_result(data=True)

        return await asyncio.to_thread(_run_sync)
    except Exception as e:
        return server_error_response(e)


# @manager.route("/rename", methods=["POST"])  # noqa: F821
# @login_required
# @validate_request("doc_id", "name")
# async def rename():
#     req = await get_request_json()
#     # 判断用户是否拥有编辑权限
#     if not user_has_operation_permission(current_user.id, "edit"):
#         return get_json_result(
#             data=False,
#             message="没有编辑权限",
#             code=RetCode.FORBIDDEN,
#     )
#     try:
#         def _rename_sync():
#             e, doc = DocumentService.get_by_id(req["doc_id"])
#             if not e:
#                 return get_data_error_result(message="Document not found!")
#             e, kb = KnowledgebaseService.get_by_id(doc.kb_id)
#             if not e:
#                 return get_data_error_result(message="Can't find this dataset!")
#             # if not check_kb_team_write_permission(kb, current_user.id):
#             #     return get_json_result(data=False, message="No authorization.", code=RetCode.AUTHENTICATION_ERROR)
#             if pathlib.Path(req["name"].lower()).suffix != pathlib.Path(doc.name.lower()).suffix:
#                 return get_json_result(data=False, message="文件的扩展名无法更改。", code=RetCode.ARGUMENT_ERROR)
#             if len(req["name"].encode("utf-8")) > FILE_NAME_LEN_LIMIT:
#                 return get_json_result(data=False, message=f"File name must be {FILE_NAME_LEN_LIMIT} bytes or less.", code=RetCode.ARGUMENT_ERROR)

#             for d in DocumentService.query(name=req["name"], kb_id=doc.kb_id):
#                 if d.name == req["name"]:
#                     return get_data_error_result(message="Duplicated document name in the same dataset.")

#             if not DocumentService.update_by_id(req["doc_id"], {"name": req["name"]}):
#                 return get_data_error_result(message="Database error (Document rename)!")

#             informs = File2DocumentService.get_by_document_id(req["doc_id"])
#             if informs:
#                 e, file = FileService.get_by_id(informs[0].file_id)
#                 FileService.update_by_id(file.id, {"name": req["name"]})

#             tenant_id = DocumentService.get_tenant_id(req["doc_id"])
#             title_tks = rag_tokenizer.tokenize(req["name"])
#             es_body = {
#                 "docnm_kwd": req["name"],
#                 "title_tks": title_tks,
#                 "title_sm_tks": rag_tokenizer.fine_grained_tokenize(title_tks),
#             }
#             if settings.docStoreConn.indexExist(search.index_name(tenant_id), doc.kb_id):
#                 settings.docStoreConn.update(
#                     {"doc_id": req["doc_id"]},
#                     es_body,
#                     search.index_name(tenant_id),
#                     doc.kb_id,
#                 )
#             return get_json_result(data=True)

#         return await asyncio.to_thread(_rename_sync)

#     except Exception as e:
#         return server_error_response(e)

@manager.route("/rename", methods=["POST"])  # noqa: F821
@login_required
@validate_request("doc_id", "name")
async def rename():
    req = await get_request_json()

    user_id = str(current_user.id)
    user_name = getattr(current_user, "nickname", None)
    user_email = getattr(current_user, "email", None)

    # 判断用户是否拥有编辑权限
    if not user_has_operation_permission(user_id, "edit"):
        return get_json_result(
            data=False,
            message="没有编辑权限",
            code=RetCode.FORBIDDEN,
        )

    try:
        def _rename_sync():
            e, doc = DocumentService.get_by_id(req["doc_id"])
            if not e:
                return get_data_error_result(message="Document not found!")

            e, kb = KnowledgebaseService.get_by_id(doc.kb_id)
            if not e:
                return get_data_error_result(message="Can't find this dataset!")

            old_name = doc.name
            new_name = req["name"]

            if pathlib.Path(new_name.lower()).suffix != pathlib.Path(old_name.lower()).suffix:
                return get_json_result(
                    data=False,
                    message="文件的扩展名无法更改。",
                    code=RetCode.ARGUMENT_ERROR,
                )

            if len(new_name.encode("utf-8")) > FILE_NAME_LEN_LIMIT:
                return get_json_result(
                    data=False,
                    message=f"File name must be {FILE_NAME_LEN_LIMIT} bytes or less.",
                    code=RetCode.ARGUMENT_ERROR,
                )

            for d in DocumentService.query(name=new_name, kb_id=doc.kb_id):
                if d.name == new_name:
                    return get_data_error_result(
                        message="Duplicated document name in the same dataset."
                    )

            if not DocumentService.update_by_id(req["doc_id"], {"name": new_name}):
                return get_data_error_result(message="Database error (Document rename)!")

            informs = File2DocumentService.get_by_document_id(req["doc_id"])
            if informs:
                e, file = FileService.get_by_id(informs[0].file_id)
                if e:
                    FileService.update_by_id(file.id, {"name": new_name})

            tenant_id = DocumentService.get_tenant_id(req["doc_id"])
            title_tks = rag_tokenizer.tokenize(new_name)

            es_body = {
                "docnm_kwd": new_name,
                "title_tks": title_tks,
                "title_sm_tks": rag_tokenizer.fine_grained_tokenize(title_tks),
            }

            if settings.docStoreConn.indexExist(search.index_name(tenant_id), doc.kb_id):
                settings.docStoreConn.update(
                    {"doc_id": req["doc_id"]},
                    es_body,
                    search.index_name(tenant_id),
                    doc.kb_id,
                )

            # 记录重命名操作日志
            OperationLogService.add_log(
                user_id=user_id,
                user_name=user_name,
                user_email=user_email,

                kb_id=doc.kb_id,
                kb_name=getattr(kb, "name", None),

                target_id=doc.id,
                target_name=new_name,

                action="rename",
                status="success",
                message="文件重命名成功",

                before_data={
                    "doc_id": doc.id,
                    "name": old_name,
                },
                after_data={
                    "doc_id": doc.id,
                    "name": new_name,
                },

                request_obj=request,
            )

            return get_json_result(data=True)

        return await asyncio.to_thread(_rename_sync)

    except Exception as e:
        return server_error_response(e)

# # 获取原始文件
# @manager.route("/get/<doc_id>", methods=["GET"])  # noqa: F821
# # @login_required
# async def get(doc_id):
#     print("获取二进制流")
#     if not user_has_operation_permission(current_user.id, "download"):
#         return get_json_result(
#             data=False,
#             message="没有下载权限",
#             code=RetCode.FORBIDDEN,
#     )
#     try:
#         e, doc = DocumentService.get_by_id(doc_id)
#         if not e:
#             return get_data_error_result(message="Document not found!")

#         b, n = File2DocumentService.get_storage_address(doc_id=doc_id)
#         print(b, n)
#         data = await asyncio.to_thread(settings.STORAGE_IMPL.get, b, n)
#         response = await make_response(data)

#         # --- 👇 核心修改开始：优先信任文件头检测 ---

#         real_content_type = None

#         # 确保 data 是 bytes 类型并进行魔数检测
#         if isinstance(data, bytes):
#             # 检查是否是 PDF (%PDF)
#             if data.startswith(b'%PDF'):
#                 real_content_type = 'application/pdf'
#                 print(f"⚠️ 修正：文件 {doc.name} 实际是 PDF，将强制设置为 PDF 类型。")

#             # 检查是否是 DOCX (PK...) - 可选，为了严谨可以加上
#             elif data.startswith(b'PK'):
#                 # 简单判断，实际上 docx/pptx/xlsx 都是 zip 格式
#                 if doc.name.lower().endswith('.docx'):
#                     real_content_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
#                 elif doc.name.lower().endswith('.pptx'):
#                     real_content_type = 'application/vnd.openxmlformats-officedocument.presentationml.presentationml'
#                 else:
#                     # 如果不知道具体是什么，但肯定是 zip 类，暂时不覆盖，交给后面逻辑处理
#                     pass

#         # 如果检测到了真实类型，直接设置并返回，不再执行后面的文件名逻辑
#         if real_content_type:
#             response.headers.set("Content-Type", real_content_type)
#             # 建议：同时也修正下载时的文件名，防止浏览器混淆
#             # response.headers.set("Content-Disposition", f'inline; filename="{doc.id}.pdf"')
#             return response

#         # --- 👆 核心修改结束 ---

#         ext = re.search(r"\.([^.]+)$", doc.name.lower())
#         ext = ext.group(1) if ext else None 
#         if ext:
#             if doc.type == FileType.VISUAL.value:

#                 content_type = CONTENT_TYPE_MAP.get(ext, f"image/{ext}")
#             else:
#                 content_type = CONTENT_TYPE_MAP.get(ext, f"application/{ext}")
#             response.headers.set("Content-Type", content_type)


#         return response
#     except Exception as e:
#         return server_error_response(e)

# 获取原始文件
@manager.route("/get/<doc_id>", methods=["GET"])  # noqa: F821
@login_required
async def get(doc_id):
    print("获取二进制流")

    user_id = str(current_user.id)
    user_name = getattr(current_user, "nickname", None)
    user_email = getattr(current_user, "email", None)

    if not user_has_operation_permission(user_id, "download"):
        return get_json_result(
            data=False, 
            message="没有下载权限",
            code=RetCode.FORBIDDEN,
        )

    try:
        e, doc = DocumentService.get_by_id(doc_id)
        if not e:
            return get_data_error_result(message="Document not found!")

        e, kb = KnowledgebaseService.get_by_id(doc.kb_id)
        if not e:
            return get_data_error_result(message="Can't find this dataset!")

        b, n = File2DocumentService.get_storage_address(doc_id=doc_id)
        print(b, n)

        data = await asyncio.to_thread(settings.STORAGE_IMPL.get, b, n)
        response = await make_response(data)

        # 记录下载成功日志
        OperationLogService.add_log(
            user_id=user_id,
            user_name=user_name,
            user_email=user_email,

            kb_id=doc.kb_id,
            kb_name=getattr(kb, "name", None),

            target_id=doc.id,
            target_name=doc.name,

            action="download",
            status="success",
            message="文件下载成功",

            before_data={
                "doc_id": doc.id,
                "doc_name": doc.name,
                "kb_id": doc.kb_id,
            },
            after_data={
                "doc_id": doc.id,
                "doc_name": doc.name,
                "kb_id": doc.kb_id,
                "kb_name": getattr(kb, "name", None),
                "storage_bucket": b,
                "storage_object": n,
            },

            request_obj=request,
        )

        real_content_type = None

        if isinstance(data, bytes):
            if data.startswith(b'%PDF'):
                real_content_type = 'application/pdf'
                print(f"⚠️ 修正：文件 {doc.name} 实际是 PDF，将强制设置为 PDF 类型。")

            elif data.startswith(b'PK'):
                if doc.name.lower().endswith('.docx'):
                    real_content_type = (
                        'application/vnd.openxmlformats-officedocument.'
                        'wordprocessingml.document'
                    )
                elif doc.name.lower().endswith('.pptx'):
                    real_content_type = (
                        'application/vnd.openxmlformats-officedocument.'
                        'presentationml.presentation'
                    )

        if real_content_type:
            response.headers.set("Content-Type", real_content_type)
            return response

        ext = re.search(r"\.([^.]+)$", doc.name.lower())
        ext = ext.group(1) if ext else None

        if ext:
            if doc.type == FileType.VISUAL.value:
                content_type = CONTENT_TYPE_MAP.get(ext, f"image/{ext}")
            else:
                content_type = CONTENT_TYPE_MAP.get(ext, f"application/{ext}")

            response.headers.set("Content-Type", content_type)

        return response

    except Exception as e:
        return server_error_response(e)



@manager.route("/download/<attachment_id>", methods=["GET"])  # noqa: F821
@login_required
async def download_attachment(attachment_id):
    try:
        ext = request.args.get("ext", "markdown")
        data = await asyncio.to_thread(settings.STORAGE_IMPL.get, current_user.id, attachment_id)
        response = await make_response(data)
        response.headers.set("Content-Type", CONTENT_TYPE_MAP.get(ext, f"application/{ext}"))

        return response

    except Exception as e:
        return server_error_response(e)


@manager.route("/change_parser", methods=["POST"])  # noqa: F821
@login_required
@validate_request("doc_id")
async def change_parser():

    req = await get_request_json()
    e, doc = DocumentService.get_by_id(req["doc_id"])
    if not e:
        return get_data_error_result(message="Document not found!")
    e, kb = KnowledgebaseService.get_by_id(doc.kb_id)
    if not e:
        return get_data_error_result(message="Can't find this dataset!")
    if not check_kb_team_write_permission(kb, current_user.id):
        return get_json_result(data=False, message="No authorization.", code=RetCode.AUTHENTICATION_ERROR)

    def reset_doc():
        nonlocal doc
        e = DocumentService.update_by_id(doc.id, {"pipeline_id": req["pipeline_id"], "parser_id": req["parser_id"], "progress": 0, "progress_msg": "", "run": TaskStatus.UNSTART.value})
        if not e:
            return get_data_error_result(message="Document not found!")
        if doc.token_num > 0:
            e = DocumentService.increment_chunk_num(doc.id, doc.kb_id, doc.token_num * -1, doc.chunk_num * -1, doc.process_duration * -1)
            if not e:
                return get_data_error_result(message="Document not found!")
            tenant_id = DocumentService.get_tenant_id(req["doc_id"])
            if not tenant_id:
                return get_data_error_result(message="Tenant not found!")
            if settings.docStoreConn.indexExist(search.index_name(tenant_id), doc.kb_id):
                settings.docStoreConn.delete({"doc_id": doc.id}, search.index_name(tenant_id), doc.kb_id)
        return None

    try:
        if "pipeline_id" in req and req["pipeline_id"] != "":
            if doc.pipeline_id == req["pipeline_id"]:
                return get_json_result(data=True)
            DocumentService.update_by_id(doc.id, {"pipeline_id": req["pipeline_id"]})
            reset_doc()
            return get_json_result(data=True)

        if doc.parser_id.lower() == req["parser_id"].lower():
            if "parser_config" in req:
                if req["parser_config"] == doc.parser_config:
                    return get_json_result(data=True)
            else:
                return get_json_result(data=True)

        if (doc.type == FileType.VISUAL and req["parser_id"] != "picture") or (re.search(r"\.(ppt|pptx|pages)$", doc.name) and req["parser_id"] != "presentation"):
            return get_data_error_result(message="Not supported yet!")
        if "parser_config" in req:
            DocumentService.update_parser_config(doc.id, req["parser_config"])
        reset_doc()
        return get_json_result(data=True)
    except Exception as e:
        return server_error_response(e)


@manager.route("/image/<image_id>", methods=["GET"])  # noqa: F821
# @login_required
async def get_image(image_id):
    try:
        arr = image_id.split("-")
        if len(arr) != 2:
            return get_data_error_result(message="Image not found.")
        bkt, nm = image_id.split("-")
        data = await asyncio.to_thread(settings.STORAGE_IMPL.get, bkt, nm)
        response = await make_response(data)
        response.headers.set("Content-Type", "image/JPEG")
        return response
    except Exception as e:
        return server_error_response(e)


@manager.route("/upload_and_parse", methods=["POST"])  # noqa: F821
@login_required
@validate_request("conversation_id")
async def upload_and_parse():
    files = await request.files
    if "file" not in files:
        return get_json_result(data=False, message="No file part!", code=RetCode.ARGUMENT_ERROR)

    file_objs = files.getlist("file")
    for file_obj in file_objs:
        if file_obj.filename == "":
            return get_json_result(data=False, message="No file selected!", code=RetCode.ARGUMENT_ERROR)

    form = await request.form
    try:
        doc_ids = doc_upload_and_parse(form.get("conversation_id"), file_objs, current_user.id)
        return get_json_result(data=doc_ids)
    except Exception as e:
        msg = str(e)
        if "QUOTA:" in msg:
            msg = msg.split("QUOTA:", 1)[1].strip()
            return get_json_result(data=False, message=msg, code=RetCode.OPERATING_ERROR)
        return server_error_response(e)


@manager.route("/parse", methods=["POST"])  # noqa: F821
@login_required
async def parse():
    req = await get_request_json()
    url = req.get("url", "")
    if url:
        if not is_valid_url(url):
            return get_json_result(data=False, message="The URL format is invalid", code=RetCode.ARGUMENT_ERROR)
        download_path = os.path.join(get_project_base_directory(), "logs/downloads")
        os.makedirs(download_path, exist_ok=True)
        from seleniumwire.webdriver import Chrome, ChromeOptions

        options = ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_experimental_option("prefs", {"download.default_directory": download_path, "download.prompt_for_download": False, "download.directory_upgrade": True, "safebrowsing.enabled": True})
        driver = Chrome(options=options)
        driver.get(url)
        res_headers = [r.response.headers for r in driver.requests if r and r.response]
        if len(res_headers) > 1:
            sections = RAGFlowHtmlParser().parser_txt(driver.page_source)
            driver.quit()
            return get_json_result(data="\n".join(sections))

        class File:
            filename: str
            filepath: str

            def __init__(self, filename, filepath):
                self.filename = filename
                self.filepath = filepath

            def read(self):
                with open(self.filepath, "rb") as f:
                    return f.read()

        r = re.search(r"filename=\"([^\"]+)\"", str(res_headers))
        if not r or not r.group(1):
            return get_json_result(data=False, message="Can't not identify downloaded file", code=RetCode.ARGUMENT_ERROR)
        f = File(r.group(1), os.path.join(download_path, r.group(1)))
        txt = FileService.parse_docs([f], current_user.id)
        return get_json_result(data=txt)

    files = await request.files
    if "file" not in files:
        return get_json_result(data=False, message="No file part!", code=RetCode.ARGUMENT_ERROR)

    file_objs = files.getlist("file")
    txt = FileService.parse_docs(file_objs, current_user.id)

    return get_json_result(data=txt)


# @manager.route("/set_meta", methods=["POST"])  # noqa: F821
# @login_required
# @validate_request("doc_id", "meta")
# async def set_meta():
#     req = await get_request_json()
#     try:
#         meta = json.loads(req["meta"])
#         if not isinstance(meta, dict):
#             return get_json_result(data=False, message="Only dictionary type supported.", code=RetCode.ARGUMENT_ERROR)
#         for k, v in meta.items():
#             if isinstance(v, list):
#                 if not all(isinstance(i, (str, int, float)) for i in v):
#                     return get_json_result(data=False, message=f"The type is not supported in list: {v}", code=RetCode.ARGUMENT_ERROR)
#             elif not isinstance(v, (str, int, float)):
#                 return get_json_result(data=False, message=f"The type is not supported: {v}", code=RetCode.ARGUMENT_ERROR)
#     except Exception as e:
#         return get_json_result(data=False, message=f"Json syntax error: {e}", code=RetCode.ARGUMENT_ERROR)
#     if not isinstance(meta, dict):
#         return get_json_result(data=False, message='Meta data should be in Json map format, like {"key": "value"}', code=RetCode.ARGUMENT_ERROR)

#     try:
#         e, doc = DocumentService.get_by_id(req["doc_id"])
#         if not e:
#             return get_data_error_result(message="Document not found!")

#         e, kb = KnowledgebaseService.get_by_id(doc.kb_id)
#         if not e:
#             return get_data_error_result(message="Can't find this dataset!")
#         if not check_kb_team_write_permission(kb, current_user.id):
#             return get_json_result(data=False, message="No authorization.", code=RetCode.AUTHENTICATION_ERROR)

#         if not DocumentService.update_by_id(req["doc_id"], {"meta_fields": meta}):
#             return get_data_error_result(message="Database error (meta updates)!")

#         return get_json_result(data=True)
#     except Exception as e:
#         return server_error_response(e)

@manager.route("/set_meta", methods=["POST"])  # noqa: F821
@login_required
@validate_request("doc_id", "meta")
async def set_meta():
    req = await get_request_json()
    try:
        meta = json.loads(req["meta"])
        if not isinstance(meta, dict):
            return get_json_result(data=False, message="Only dictionary type supported.", code=RetCode.ARGUMENT_ERROR)
        for k, v in meta.items():
            if isinstance(v, list):
                if not all(isinstance(i, (str, int, float)) for i in v):
                    return get_json_result(data=False, message=f"The type is not supported in list: {v}", code=RetCode.ARGUMENT_ERROR)
            elif not isinstance(v, (str, int, float)):
                return get_json_result(data=False, message=f"The type is not supported: {v}", code=RetCode.ARGUMENT_ERROR)
    except Exception as e:
        return get_json_result(data=False, message=f"Json syntax error: {e}", code=RetCode.ARGUMENT_ERROR)
    if not isinstance(meta, dict):
        return get_json_result(data=False, message='Meta data should be in Json map format, like {"key": "value"}', code=RetCode.ARGUMENT_ERROR)

    try:
        e, doc = DocumentService.get_by_id(req["doc_id"])
        if not e:
            return get_data_error_result(message="Document not found!")

        # 记录旧 meta（用于 before_data）
        old_meta = doc.meta_fields or {}
        if isinstance(old_meta, str):
            try:
                old_meta = json.loads(old_meta)
            except (TypeError, ValueError):
                old_meta = {}
        if not isinstance(old_meta, dict):
            old_meta = {}

        e, kb = KnowledgebaseService.get_by_id(doc.kb_id)
        if not e:
            return get_data_error_result(message="Can't find this dataset!")
        if not check_kb_team_write_permission(kb, current_user.id):
            return get_json_result(data=False, message="No authorization.", code=RetCode.AUTHENTICATION_ERROR)

        if not DocumentService.update_by_id(req["doc_id"], {"meta_fields": meta}):
            return get_data_error_result(message="Database error (meta updates)!")

        # ====== 新增：记录操作日志 ======
        try:
            user_id = current_user.id
            user_name = getattr(current_user, "nickname", None)
            user_email = getattr(current_user, "email", None)
            kb_name = getattr(kb, "name", None)

            OperationLogService.add_log(
                user_id=user_id,
                user_name=user_name,
                user_email=user_email,

                kb_id=doc.kb_id,
                kb_name=kb_name,

                target_id=doc.id,
                target_name=doc.name,

                action="update_meta",
                status="success",
                message="更新文档元数据",

                before_data={
                    "doc_id": doc.id,
                    "doc_name": doc.name,
                    "kb_id": doc.kb_id,
                    "meta_fields": old_meta,  # 旧完整元数据
                },
                after_data={
                    "doc_id": doc.id,
                    "doc_name": doc.name,
                    "kb_id": doc.kb_id,
                    "kb_name": kb_name,
                    "meta_fields": meta,      # 新完整元数据
                },

                request_obj=request,
            )
        except Exception as log_e:
            # 日志记录失败不影响主流程
            print(f"操作日志记录失败: {log_e}")   # 生产环境可改用 logging.error

        return get_json_result(data=True)
    except Exception as e:
        return server_error_response(e)


@manager.route("/upload_info", methods=["POST"])  # noqa: F821
async def upload_info():
    files = await request.files
    file = files['file'] if files and files.get("file") else None
    try:
        return get_json_result(data=FileService.upload_info(current_user.id, file, request.args.get("url")))
    except Exception as e:
        return  server_error_response(e)

@manager.route('/staged_file/list', methods=['POST'])
@login_required
@validate_request("kb_id")
async def list_staged_file():
    req = await get_request_json()

    kb_id = req["kb_id"]

    status = req.get("status")
    page = int(req.get("page", 1))
    page_size = int(req.get("page_size", 20))

    if page <= 0:
        page = 1

    if page_size <= 0:
        page_size = 20

    if page_size > 100:
        page_size = 100

    # 如果 current_user 有 tenant_id，就这样取
    tenant_id = current_user.id

    data = StagedFileService.list_by_kb(
        kb_id=kb_id,
        tenant_id=tenant_id,
        current_user=current_user,
        status=status,
        page=page,
        page_size=page_size,
        include_deleted=False,
    )
    print(data)
    return get_json_result(data=data)

@manager.route("/knowledge/tags/update-one", methods=["POST"])  # noqa: F821
@login_required
async def update_one_knowledge_tag():
    import json
    from datetime import datetime

    print("修改标签")
    try:
        req = await get_request_json()

        doc_id = req.get("doc_id")
        type_code = req.get("type_code")
        option_codes = req.get("option_codes", [])

        if not doc_id:
            return get_json_result(
                data=False,
                message="Missing doc_id.",
                code=RetCode.ARGUMENT_ERROR,
            )

        if not type_code:
            return get_json_result(
                data=False,
                message="Missing type_code.",
                code=RetCode.ARGUMENT_ERROR,
            )

        if option_codes is None:
            option_codes = []

        if not isinstance(option_codes, list):
            option_codes = [option_codes]

        # 清理选项编码，并去除空值
        option_codes = [
            str(item).strip()
            for item in option_codes
            if item is not None and str(item).strip()
        ]

        # 如果同一个选项被重复提交，只保留一个
        option_codes = list(dict.fromkeys(option_codes))

        # 1. 查询文档
        ok, doc = DocumentService.get_by_id(doc_id)

        if not ok or not doc:
            return get_json_result(
                data=False,
                message="Document not found.",
                code=RetCode.DATA_ERROR,
            )

        # 2. 查询标签类型
        tag_type = (
            KnowledgeTagType
            .select()
            .where(
                (KnowledgeTagType.type_code == type_code)
                & (KnowledgeTagType.enabled == True)
            )
            .first()
        )

        if not tag_type:
            return get_json_result(
                data=False,
                message=f"Tag type not found or disabled: {type_code}",
                code=RetCode.DATA_ERROR,
            )

        # 3. 查询合法选项
        option_rows = list(
            KnowledgeTagOption
            .select(
                KnowledgeTagOption.option_code,
                KnowledgeTagOption.option_name,
            )
            .where(
                (KnowledgeTagOption.type_code == type_code)
                & (KnowledgeTagOption.enabled == True)
            )
        )

        valid_option_codes = {
            row.option_code
            for row in option_rows
        }

        invalid_options = [
            code
            for code in option_codes
            if code not in valid_option_codes
        ]

        if invalid_options:
            return get_json_result(
                data=False,
                message=(
                    f"Invalid option_code for {type_code}: "
                    f"{', '.join(invalid_options)}"
                ),
                code=RetCode.ARGUMENT_ERROR,
            )

        # 4. 单选字段只允许一个值
        if not tag_type.multi_select and len(option_codes) > 1:
            return get_json_result(
                data=False,
                message=(
                    f"Tag type '{type_code}' does not allow "
                    "multiple values."
                ),
                code=RetCode.ARGUMENT_ERROR,
            )

        # 5. 必填字段不允许为空
        if tag_type.required and not option_codes:
            return get_json_result(
                data=False,
                message=f"Tag type '{type_code}' is required.",
                code=RetCode.ARGUMENT_ERROR,
            )

        # 6. 查询文档对应的暂存文件
        staged_files = list(
            StagedFile
            .select()
            .where(StagedFile.doc_id == doc_id)
            .order_by(
                StagedFile.committed_at.desc(nulls="LAST"),
                StagedFile.created_at.desc(),
            )
        )

        stage_ids = [
            staged_file.id
            for staged_file in staged_files
        ]

        now = datetime.now()

        # 在更新前，保存旧值（从 doc.meta_fields 中读取）
        old_meta = doc.meta_fields or {}
        if isinstance(old_meta, str):
            try:
                old_meta = json.loads(old_meta)
            except (TypeError, ValueError):
                old_meta = {}
        if not isinstance(old_meta, dict):
            old_meta = {}

        old_option_codes = old_meta.get(type_code, [])
        if not isinstance(old_option_codes, list):
            old_option_codes = [old_option_codes] if old_option_codes else []

        # 清理 old_option_codes（确保是字符串列表）
        old_option_codes = [str(c).strip() for c in old_option_codes if c and str(c).strip()]



        # DocumentService.update_by_id() 不放在该事务中调用，
        # 避免它内部的 ConnectionContext 关闭事务连接。
        with DB.atomic():
            # 7. 解析并更新 Document.meta_fields
            meta_fields = doc.meta_fields or {}

            if isinstance(meta_fields, str):
                try:
                    meta_fields = json.loads(meta_fields)
                except (TypeError, ValueError):
                    meta_fields = {}

            if not isinstance(meta_fields, dict):
                meta_fields = {}

            # 复制一份，避免直接修改从数据库读取的对象引用
            meta_fields = dict(meta_fields)
            meta_fields[type_code] = option_codes

            # doc 是 DocumentService.get_by_id() 返回的模型实例。
            # 直接使用它的模型类更新，避免调用带独立连接上下文的服务方法。
            document_model = type(doc)

            updated_count = (
                document_model
                .update(
                    meta_fields=meta_fields,
                )
                .where(document_model.id == doc_id)
                .execute()
            )

            if updated_count == 0:
                raise RuntimeError(
                    f"Failed to update document meta_fields: {doc_id}"
                )

            # 8. 更新 StagedFileTag 中当前标签类型的数据
            if stage_ids:
                (
                    StagedFileTag
                    .delete()
                    .where(
                        (StagedFileTag.stage_id.in_(stage_ids))
                        & (StagedFileTag.type_code == type_code)
                    )
                    .execute()
                )

                tag_rows = [
                    {
                        "stage_id": stage_id,
                        "type_code": type_code,
                        "option_code": option_code,
                        "create_time": now,
                    }
                    for stage_id in stage_ids
                    for option_code in option_codes
                ]

                if tag_rows:
                    StagedFileTag.insert_many(tag_rows).execute()

        

        # 9. 返回选项中文名称
        option_name_map = {
            row.option_code: row.option_name
            for row in option_rows
        }


        # 事务成功后，记录日志
        try:
            # 获取用户信息
            user_id = current_user.id
            user_name = getattr(current_user, "nickname", None)
            user_email = getattr(current_user, "email", None)

            # 获取知识库信息
            e, kb = KnowledgebaseService.get_by_id(doc.kb_id)
            kb_name = getattr(kb, "name", None) if e else None

            # 选项名称映射
            option_name_map = {row.option_code: row.option_name for row in option_rows}
            def codes_to_names(codes):
                return [option_name_map.get(c, c) for c in codes]

            old_names = codes_to_names(old_option_codes)
            new_names = codes_to_names(option_codes)

            # 构造日志消息
            old_text = "、".join(old_names) if old_names else "空"
            new_text = "、".join(new_names) if new_names else "空"
            message = f"更新标签「{tag_type.type_name}」从「{old_text}」变为「{new_text}」"

            OperationLogService.add_log(
                user_id=user_id,
                user_name=user_name,
                user_email=user_email,

                kb_id=doc.kb_id,
                kb_name=kb_name,

                target_id=doc.id,
                target_name=doc.name,

                action="update_tags",
                status="success",
                message=message,

                before_data={
                    "doc_id": doc.id,
                    "doc_name": doc.name,
                    "kb_id": doc.kb_id,
                    "type_code": type_code,
                    "type_name": tag_type.type_name,
                    "option_codes": old_option_codes,
                    "option_names": old_names,
                },
                after_data={
                    "doc_id": doc.id,
                    "doc_name": doc.name,
                    "kb_id": doc.kb_id,
                    "kb_name": kb_name,
                    "type_code": type_code,
                    "type_name": tag_type.type_name,
                    "option_codes": option_codes,
                    "option_names": new_names,
                },

                request_obj=request,
            )
        except Exception as log_e:
            # 日志记录失败不应影响接口返回
            print(f"日志记录失败: {log_e}")   # 生产环境可改用 logging.error

        # 最终返回结果
        return get_json_result(
            data={
                "doc_id": doc_id,
                "stage_ids": stage_ids,
                "type_code": type_code,
                "type_name": tag_type.type_name,
                "option_codes": option_codes,
                "option_names": [option_name_map.get(c, c) for c in option_codes],
                "meta_fields": meta_fields,
            }
        )

    except Exception as e:
        return server_error_response(e)
    
@manager.route("/operation_logs", methods=["POST"])  # noqa: F821
@login_required
async def list_operation_logs():
    req = await get_request_json()

    kb_id = req.get("kb_id")  # 可选
    page = int(req.get("page", 1))
    page_size = int(req.get("page_size", 20))
    action = req.get("action")
    keyword = req.get("keyword")

    try:
        logs, total = OperationLogService.list_by_kb_id(
            kb_id=kb_id,
            page_number=page,
            items_per_page=page_size,
            action=action,
            keyword=keyword,
        )

        return get_json_result(
            data={
                "logs": logs,
                "total": total,
                "page": page,
                "page_size": page_size,
            }
        )

    except Exception as e:
        return get_json_result(
            data=False,
            message=str(e),
            code=RetCode.EXCEPTION_ERROR,
        )