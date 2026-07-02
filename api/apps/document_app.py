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
from api.common.check_team_permission import check_kb_team_permission, check_kb_team_write_permission
from api.constants import FILE_NAME_LEN_LIMIT, IMG_BASE64_PREFIX
from api.db import VALID_FILE_TYPES, FileType
from api.db.db_models import Task, SyncDept, SyncPerson
from api.db.services import duplicate_name
from api.db.services.document_service import DocumentService, doc_upload_and_parse
from common.metadata_utils import meta_filter, convert_conditions
from api.db.services.file2document_service import File2DocumentService
from api.db.services.file_service import FileService
from api.db.services.knowledgebase_service import KnowledgebaseService
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


# 知识库的上传
@manager.route("/upload", methods=["POST"])  # noqa: F821
@login_required
@validate_request("kb_id")
async def upload():
    # 获取知识库id
    form = await request.form
    kb_id = form.get("kb_id")

    if not kb_id:
        return get_json_result(data=False, message='Lack of "KB ID"', code=RetCode.ARGUMENT_ERROR)
    
    # 获取文件
    files = await request.files
    if "file" not in files:
        return get_json_result(data=False, message="No file part!", code=RetCode.ARGUMENT_ERROR)

    
    file_objs = files.getlist("file")
    for file_obj in file_objs:
        if file_obj.filename == "":
            return get_json_result(data=False, message="No file selected!", code=RetCode.ARGUMENT_ERROR)
        if len(file_obj.filename.encode("utf-8")) > FILE_NAME_LEN_LIMIT:
            return get_json_result(data=False, message=f"File name must be {FILE_NAME_LEN_LIMIT} bytes or less.", code=RetCode.ARGUMENT_ERROR)

    # 获取知识库行信息
    e, kb = KnowledgebaseService.get_by_id(kb_id)
    if not e:
        raise LookupError("Can't find this dataset!")
    
    # 鉴权 
    if not check_kb_team_write_permission(kb, current_user.id):
        return get_json_result(data=False, message="No authorization.", code=RetCode.AUTHENTICATION_ERROR)

    # 上传到文本库
    err, files = await asyncio.to_thread(FileService.upload_document, kb, file_objs, current_user.id)
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

    return get_json_result(data=files)


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


@manager.route("/list", methods=["POST"])  # noqa: F821
@login_required
async def list_docs():
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
        docs, tol = DocumentService.get_by_kb_id(kb_id, page_number, items_per_page, orderby, desc, keywords, run_status, types, suffix, doc_ids_filter)

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
            Document.status != "2",
        ).count()

        week_file_ratio = 0 if tol == 0 else round(this_week_count / tol * 100, 2)

        return get_json_result(data={"total": tol, "docs": docs,
                                     "week_growth_rate": week_file_ratio,
                                        "this_week_count": this_week_count,})
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


@manager.route("/filter", methods=["POST"])  # noqa: F821
@login_required
async def get_filter():
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
        filter, total = DocumentService.get_filter_by_kb_id(kb_id, keywords, run_status, types, suffix)
        return get_json_result(data={"total": total, "filter": filter})
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

    result = {}
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
            if not DocumentService.update_by_id(doc_id, {"status": str(status)}):
                result[doc_id] = {"error": "Database error (Document update)!"}
                continue

            PipelineOperationLogService.update_status_by_document_ids(
                doc_id,
                status,
            )


            status_int = int(status)
            if not settings.docStoreConn.update({"doc_id": doc_id}, {"available_int": status_int}, search.index_name(kb.tenant_id), doc.kb_id):
                result[doc_id] = {"error": "Database error (docStore update)!"}
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

    for doc_id in doc_ids:
        e, doc = DocumentService.get_by_id(doc_id)
        if not e:
            return get_json_result(data=False, message="No authorization.", code=RetCode.AUTHENTICATION_ERROR)

        e, kb = KnowledgebaseService.get_by_id(doc.kb_id)
        if not e:
            return get_data_error_result(message="Can't find this dataset!")

        if not check_kb_team_write_permission(kb, current_user.id):
            return get_json_result(data=False, message="No authorization.", code=RetCode.AUTHENTICATION_ERROR)

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
                if not check_kb_team_write_permission(kb, current_user.id):
                    return get_json_result(data=False, message="No authorization.", code=RetCode.AUTHENTICATION_ERROR)
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


@manager.route("/rename", methods=["POST"])  # noqa: F821
@login_required
@validate_request("doc_id", "name")
async def rename():
    req = await get_request_json()
    try:
        def _rename_sync():
            e, doc = DocumentService.get_by_id(req["doc_id"])
            if not e:
                return get_data_error_result(message="Document not found!")
            e, kb = KnowledgebaseService.get_by_id(doc.kb_id)
            if not e:
                return get_data_error_result(message="Can't find this dataset!")
            if not check_kb_team_write_permission(kb, current_user.id):
                return get_json_result(data=False, message="No authorization.", code=RetCode.AUTHENTICATION_ERROR)
            if pathlib.Path(req["name"].lower()).suffix != pathlib.Path(doc.name.lower()).suffix:
                return get_json_result(data=False, message="The extension of file can't be changed", code=RetCode.ARGUMENT_ERROR)
            if len(req["name"].encode("utf-8")) > FILE_NAME_LEN_LIMIT:
                return get_json_result(data=False, message=f"File name must be {FILE_NAME_LEN_LIMIT} bytes or less.", code=RetCode.ARGUMENT_ERROR)

            for d in DocumentService.query(name=req["name"], kb_id=doc.kb_id):
                if d.name == req["name"]:
                    return get_data_error_result(message="Duplicated document name in the same dataset.")

            if not DocumentService.update_by_id(req["doc_id"], {"name": req["name"]}):
                return get_data_error_result(message="Database error (Document rename)!")

            informs = File2DocumentService.get_by_document_id(req["doc_id"])
            if informs:
                e, file = FileService.get_by_id(informs[0].file_id)
                FileService.update_by_id(file.id, {"name": req["name"]})

            tenant_id = DocumentService.get_tenant_id(req["doc_id"])
            title_tks = rag_tokenizer.tokenize(req["name"])
            es_body = {
                "docnm_kwd": req["name"],
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
            return get_json_result(data=True)

        return await asyncio.to_thread(_rename_sync)

    except Exception as e:
        return server_error_response(e)

# 获取原始文件
@manager.route("/get/<doc_id>", methods=["GET"])  # noqa: F821
# @login_required
async def get(doc_id):
    print("获取二进制流")
    try:
        e, doc = DocumentService.get_by_id(doc_id)
        if not e:
            return get_data_error_result(message="Document not found!")

        b, n = File2DocumentService.get_storage_address(doc_id=doc_id)
        print(b, n)
        data = await asyncio.to_thread(settings.STORAGE_IMPL.get, b, n)
        response = await make_response(data)

        # --- 👇 核心修改开始：优先信任文件头检测 ---

        real_content_type = None

        # 确保 data 是 bytes 类型并进行魔数检测
        if isinstance(data, bytes):
            # 检查是否是 PDF (%PDF)
            if data.startswith(b'%PDF'):
                real_content_type = 'application/pdf'
                print(f"⚠️ 修正：文件 {doc.name} 实际是 PDF，将强制设置为 PDF 类型。")

            # 检查是否是 DOCX (PK...) - 可选，为了严谨可以加上
            elif data.startswith(b'PK'):
                # 简单判断，实际上 docx/pptx/xlsx 都是 zip 格式
                if doc.name.lower().endswith('.docx'):
                    real_content_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                elif doc.name.lower().endswith('.pptx'):
                    real_content_type = 'application/vnd.openxmlformats-officedocument.presentationml.presentationml'
                else:
                    # 如果不知道具体是什么，但肯定是 zip 类，暂时不覆盖，交给后面逻辑处理
                    pass

        # 如果检测到了真实类型，直接设置并返回，不再执行后面的文件名逻辑
        if real_content_type:
            response.headers.set("Content-Type", real_content_type)
            # 建议：同时也修正下载时的文件名，防止浏览器混淆
            # response.headers.set("Content-Disposition", f'inline; filename="{doc.id}.pdf"')
            return response

        # --- 👆 核心修改结束 ---

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

        e, kb = KnowledgebaseService.get_by_id(doc.kb_id)
        if not e:
            return get_data_error_result(message="Can't find this dataset!")
        if not check_kb_team_write_permission(kb, current_user.id):
            return get_json_result(data=False, message="No authorization.", code=RetCode.AUTHENTICATION_ERROR)

        if not DocumentService.update_by_id(req["doc_id"], {"meta_fields": meta}):
            return get_data_error_result(message="Database error (meta updates)!")

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
