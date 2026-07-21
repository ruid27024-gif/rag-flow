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
import json
import logging
import os
from datetime import datetime, timedelta

from peewee import fn

from api.db import VALID_PIPELINE_TASK_TYPES, PipelineTaskType
from api.db.db_models import DB, Document, PipelineOperationLog
from api.db.services.canvas_service import UserCanvasService
from api.db.services.common_service import CommonService
from api.db.services.document_service import DocumentService
from api.db.services.knowledgebase_service import KnowledgebaseService
from api.db.services.task_service import GRAPH_RAPTOR_FAKE_DOC_ID
from common.misc_utils import get_uuid
from common.time_utils import current_timestamp, datetime_format


class PipelineOperationLogService(CommonService):
    model = PipelineOperationLog

    @classmethod
    def get_file_logs_fields(cls):
        return [
            cls.model.id,
            cls.model.document_id,
            cls.model.tenant_id,
            cls.model.kb_id,
            cls.model.pipeline_id,
            cls.model.pipeline_title,
            cls.model.parser_id,
            cls.model.document_name,
            cls.model.document_suffix,
            cls.model.document_type,
            cls.model.source_from,
            cls.model.progress,
            cls.model.progress_msg,
            cls.model.process_begin_at,
            cls.model.process_duration,
            cls.model.dsl,
            cls.model.task_type,
            cls.model.operation_status,
            cls.model.avatar,
            cls.model.status,
            cls.model.create_time,
            cls.model.create_date,
            cls.model.update_time,
            cls.model.update_date,
        ]

    @classmethod
    def get_dataset_logs_fields(cls):
        return [
            cls.model.id,
            cls.model.tenant_id,
            cls.model.kb_id,
            cls.model.progress,
            cls.model.progress_msg,
            cls.model.process_begin_at,
            cls.model.process_duration,
            cls.model.task_type,
            cls.model.operation_status,
            cls.model.avatar,
            cls.model.status,
            cls.model.create_time,
            cls.model.create_date,
            cls.model.update_time,
            cls.model.update_date,
        ]

    @classmethod
    def save(cls, **kwargs):
        """
        wrap this function in a transaction
        """
        sample_obj = cls.model(**kwargs).save(force_insert=True)
        return sample_obj

    @classmethod
    @DB.connection_context()
    def create(cls, document_id, pipeline_id, task_type, fake_document_ids=[], dsl: str = "{}"):
        referred_document_id = document_id

        if referred_document_id == GRAPH_RAPTOR_FAKE_DOC_ID and fake_document_ids:
            referred_document_id = fake_document_ids[0]

        ok, document = DocumentService.get_by_id(referred_document_id)
        if not ok:
            logging.warning(f"Document for referred_document_id {referred_document_id} not found")
            return None
        print("------------------------------------------------")
        DocumentService.update_progress_immediately([document.to_dict()])
        ok, document = DocumentService.get_by_id(referred_document_id)
        print("------------------------------------------------")
        print(document.to_dict())
        if not ok:
            logging.warning(f"Document for referred_document_id {referred_document_id} not found")
            return None
        if document.progress not in [1, -1]:
            return None
        operation_status = document.run

        if pipeline_id:
            ok, user_pipeline = UserCanvasService.get_by_id(pipeline_id)
            if not ok:
                raise RuntimeError(f"Pipeline {pipeline_id} not found")
            tenant_id = user_pipeline.user_id
            title = user_pipeline.title
            avatar = user_pipeline.avatar
        else:
            ok, kb_info = KnowledgebaseService.get_by_id(document.kb_id)
            if not ok:
                raise RuntimeError(f"Cannot find dataset {document.kb_id} for referred_document {referred_document_id}")

            tenant_id = kb_info.tenant_id
            title = document.parser_id
            avatar = document.thumbnail

        if task_type not in VALID_PIPELINE_TASK_TYPES:
            raise ValueError(f"Invalid task type: {task_type}")

        if task_type in [PipelineTaskType.GRAPH_RAG, PipelineTaskType.RAPTOR, PipelineTaskType.MINDMAP]:
            finish_at = document.process_begin_at + timedelta(seconds=document.process_duration)
            if task_type == PipelineTaskType.GRAPH_RAG:
                KnowledgebaseService.update_by_id(
                    document.kb_id,
                    {"graphrag_task_finish_at": finish_at},
                )
            elif task_type == PipelineTaskType.RAPTOR:
                KnowledgebaseService.update_by_id(
                    document.kb_id,
                    {"raptor_task_finish_at": finish_at},
                )
            elif task_type == PipelineTaskType.MINDMAP:
                KnowledgebaseService.update_by_id(
                    document.kb_id,
                    {"mindmap_task_finish_at": finish_at},
                )

        log = dict(
            id=get_uuid(),
            document_id=document_id,  # GRAPH_RAPTOR_FAKE_DOC_ID or real document_id
            tenant_id=tenant_id,
            kb_id=document.kb_id,
            pipeline_id=pipeline_id,
            pipeline_title=title,
            parser_id=document.parser_id,
            document_name=document.name,
            document_suffix=document.suffix,
            document_type=document.type,
            source_from=document.source_type.split("/")[0],
            progress=document.progress,
            progress_msg=document.progress_msg,
            process_begin_at=document.process_begin_at,
            process_duration=document.process_duration,
            dsl=json.loads(dsl),
            task_type=task_type,
            operation_status=operation_status,
            avatar=avatar,
        )
        log["create_time"] = current_timestamp()
        log["create_date"] = datetime_format(datetime.now())
        log["update_time"] = current_timestamp()
        log["update_date"] = datetime_format(datetime.now())

        with DB.atomic():
            obj = cls.save(**log)

            limit = int(os.getenv("PIPELINE_OPERATION_LOG_LIMIT", 10000))
            total = cls.model.select().where(cls.model.kb_id == document.kb_id).count()

            if total > limit:
                keep_ids = [m.id for m in cls.model.select(cls.model.id).where(cls.model.kb_id == document.kb_id).order_by(cls.model.create_time.desc()).limit(limit)]

                deleted = cls.model.delete().where(cls.model.kb_id == document.kb_id, cls.model.id.not_in(keep_ids)).execute()
                logging.info(f"[PipelineOperationLogService] Cleaned {deleted} old logs, kept latest {limit} for {document.kb_id}")

        return obj

    @classmethod
    @DB.connection_context()
    def record_pipeline_operation(cls, document_id, pipeline_id, task_type, fake_document_ids=[]):
        return cls.create(document_id=document_id, pipeline_id=pipeline_id, task_type=task_type, fake_document_ids=fake_document_ids)

    # @classmethod
    # @DB.connection_context()
    # def get_file_logs_by_kb_id(cls, kb_id, page_number, items_per_page, orderby, desc, keywords, operation_status, types, suffix, create_date_from=None, create_date_to=None):
    #     fields = cls.get_file_logs_fields()
    #     if keywords:
    #         logs = cls.model.select(*fields).where((cls.model.kb_id == kb_id), (fn.LOWER(cls.model.document_name).contains(keywords.lower())))
    #     else:
    #         logs = cls.model.select(*fields).where(cls.model.kb_id == kb_id)

    #     logs = logs.where(cls.model.document_id != GRAPH_RAPTOR_FAKE_DOC_ID)

    #     if operation_status:
    #         logs = logs.where(cls.model.operation_status.in_(operation_status))
    #     if types:
    #         logs = logs.where(cls.model.document_type.in_(types))
    #     if suffix:
    #         logs = logs.where(cls.model.document_suffix.in_(suffix))
    #     if create_date_from:
    #         logs = logs.where(cls.model.create_date >= create_date_from)
    #     if create_date_to:
    #         logs = logs.where(cls.model.create_date <= create_date_to)

    #     count = logs.count()
    #     if desc:
    #         logs = logs.order_by(cls.model.getter_by(orderby).desc())
    #     else:
    #         logs = logs.order_by(cls.model.getter_by(orderby).asc())

    #     if page_number and items_per_page:
    #         logs = logs.paginate(page_number, items_per_page)

    #     return list(logs.dicts()), count
    
    # @classmethod
    # @DB.connection_context()
    # def get_file_logs_by_kb_id(
    #     cls,
    #     kb_id,
    #     page_number,
    #     items_per_page,
    #     orderby,
    #     desc,
    #     keywords,
    #     operation_status,
    #     types,
    #     suffix,
    #     create_date_from=None,
    #     create_date_to=None
    # ):
    #     fields = cls.get_file_logs_fields()
    #     from peewee import fn, Case
    #     from collections import defaultdict
    #     from api.db.db_models import Task

    #     # LogCountAlias = cls.model.alias()

    #     # document_id_count = (
    #     #     LogCountAlias
    #     #     .select(fn.COUNT(LogCountAlias.id))
    #     #     .where(
    #     #         LogCountAlias.kb_id == cls.model.kb_id,
    #     #         LogCountAlias.document_id == cls.model.document_id,
    #     #         LogCountAlias.document_id != GRAPH_RAPTOR_FAKE_DOC_ID,
    #     #     )
    #     # ).alias("document_id_count")

    #     LogLatestAlias = cls.model.alias()

    #     latest_log_id = (
    #         LogLatestAlias
    #         .select(LogLatestAlias.id)
    #         .where(
    #             LogLatestAlias.kb_id == cls.model.kb_id,
    #             LogLatestAlias.document_id == cls.model.document_id,
    #             LogLatestAlias.document_id != GRAPH_RAPTOR_FAKE_DOC_ID,
    #         )
    #         .order_by(
    #             LogLatestAlias.create_date.desc(),
    #             LogLatestAlias.id.desc()
    #         )
    #         .limit(1)
    #     )

    #     is_latest_parse = Case(
    #         None,
    #         [
    #             (cls.model.id == latest_log_id, 1),
    #         ],
    #         0
    #     ).alias("is_latest_parse")

    #     fields = [
    #         *fields,
    #         is_latest_parse,
    #     ]

    #     if keywords:
    #         logs = cls.model.select(*fields).where(
    #             cls.model.kb_id == kb_id,
    #             fn.LOWER(cls.model.document_name).contains(keywords.lower())
    #         )
    #     else:
    #         logs = cls.model.select(*fields).where(
    #             cls.model.kb_id == kb_id
    #         )

    #     logs = logs.where(cls.model.document_id != GRAPH_RAPTOR_FAKE_DOC_ID)

    #     # 只保留每个 document_id 最新一条日志
    #     logs = logs.where(cls.model.id == latest_log_id)

    #     if operation_status:
    #         logs = logs.where(cls.model.operation_status.in_(operation_status))

    #     if types:
    #         logs = logs.where(cls.model.document_type.in_(types))

    #     if suffix:
    #         logs = logs.where(cls.model.document_suffix.in_(suffix))

    #     if create_date_from:
    #         logs = logs.where(cls.model.create_date >= create_date_from)

    #     if create_date_to:
    #         logs = logs.where(cls.model.create_date <= create_date_to)

    #     count = logs.count()

    #     if desc:
    #         logs = logs.order_by(cls.model.getter_by(orderby).desc())
    #     else:
    #         logs = logs.order_by(cls.model.getter_by(orderby).asc())

    #     if page_number and items_per_page:
    #         logs = logs.paginate(page_number, items_per_page)

    #     log_list = list(logs.dicts())

    #     document_ids = list({log["document_id"] for log in log_list if log.get("document_id")})
    #     doc_tasks = defaultdict(list)

    #     if document_ids:
    #         task_rows = (
    #             Task
    #             .select(Task.doc_id, Task.task_type, Task.progress, Task.progress_msg, Task.create_time)
    #             .where(Task.doc_id.in_(document_ids))
    #             .order_by(Task.doc_id, Task.create_time, Task.id)
    #         )

    #         for task in task_rows:
    #             task_type = (task.task_type or "").lower().strip()
    #             doc_tasks[task.doc_id].append({
    #                 "task_type": task_type,
    #                 "progress": task.progress,
    #                 "progress_msg": task.progress_msg,
    #                 "create_time": task.create_time,
    #             })

    #     for log in log_list:
            
    #         tasks = doc_tasks.get(log.get("document_id"), [])

    #         has_author_task = any(task["task_type"] == "parse_author_info" for task in tasks)
    #         has_parse_task = any(task["task_type"] == "" for task in tasks)

    #         latest_task = tasks[-1] if tasks else None
    #         latest_task_type = latest_task["task_type"] if latest_task else ""

    #         if has_author_task and has_parse_task:
    #             process_scene = "author_with_parse"
    #             process_scene_text = "解析全文"
    #         elif has_author_task:
    #             process_scene = "author_only"
    #             process_scene_text = "提取作者"
    #         elif has_parse_task:
    #             process_scene = "parse_only"
    #             process_scene_text = "解析全文"
    #         else:
    #             process_scene = "unknown"
    #             process_scene_text = "未知"

    #         if latest_task_type == "parse_author_info":
    #             latest_task_scene = "author_extract"
    #             latest_task_scene_text = "提取作者"
    #         elif latest_task_type == "":
    #             latest_task_scene = "full_parse"
    #             latest_task_scene_text = "解析全文"
    #         else:
    #             latest_task_scene = latest_task_type or "unknown"
    #             latest_task_scene_text = latest_task_type or "未知"
    #             if latest_task_type == "graphrag":
    #                 process_scene = "graph_parse"
    #                 process_scene_text = "知识图谱"
    #             else:
    #                 process_scene == "unknown"
    #                 process_scene_text = "raptor"

    #         log.update({
    #             "has_author_task": has_author_task,
    #             "has_parse_task": has_parse_task,
    #             "process_scene": process_scene,
    #             "process_scene_text": process_scene_text,
    #             "latest_task_type": latest_task_type,
    #             "latest_task_scene": latest_task_scene,
    #             "latest_task_scene_text": latest_task_scene_text,
    #             "latest_task_progress": latest_task["progress"] if latest_task else None,
    #             "latest_task_progress_msg": latest_task["progress_msg"] if latest_task else "",
    #         })

    #     return log_list, count

    # @classmethod
    # @DB.connection_context()
    # def get_file_logs_by_kb_id(
    #     cls,
    #     kb_id,
    #     page_number,
    #     items_per_page,
    #     orderby,
    #     desc,
    #     keywords,
    #     operation_status,
    #     types,
    #     suffix,
    #     create_date_from=None,
    #     create_date_to=None
    # ):
    #     fields = cls.get_file_logs_fields()

    #     from peewee import fn, Case, JOIN
    #     from api.db.db_models import Task

    #     LogLatestAlias = cls.model.alias()

    #     latest_log_update_date = (
    #         LogLatestAlias
    #         .select(fn.MAX(LogLatestAlias.update_date))
    #         .where(
    #             LogLatestAlias.kb_id == cls.model.kb_id,
    #             LogLatestAlias.document_id == cls.model.document_id,
    #             LogLatestAlias.document_id != GRAPH_RAPTOR_FAKE_DOC_ID,
    #         )
    #     )

    #     TaskLatestAlias = Task.alias()

    #     latest_task_update_time = (
    #         TaskLatestAlias
    #         .select(fn.MAX(TaskLatestAlias.update_time))
    #         .where(
    #             TaskLatestAlias.doc_id == cls.model.document_id
    #         )
    #     )

    #     TaskParseAlias = Task.alias()

    #     has_parse_task_query = (
    #         TaskParseAlias
    #         .select(TaskParseAlias.id)
    #         .where(
    #             TaskParseAlias.doc_id == cls.model.document_id,
    #             TaskParseAlias.task_type == "",
    #         )
    #         .limit(1)
    #     )

    #     is_latest_parse = Case(
    #         None,
    #         [
    #             (cls.model.update_date == latest_log_update_date, 1),
    #         ],
    #         0
    #     ).alias("is_latest_parse")

    #     has_parse_task = Case(
    #         None,
    #         [
    #             (fn.EXISTS(has_parse_task_query), 1),
    #         ],
    #         0
    #     ).alias("has_parse_task")

    #     fields = [
    #         *fields,
    #         is_latest_parse,
    #         has_parse_task,

    #         Task.task_type.alias("latest_task_type"),
    #         Task.progress.alias("latest_task_progress"),
    #         Task.progress_msg.alias("latest_task_progress_msg"),
    #         Task.update_time.alias("latest_task_update_time"),
    #     ]

    #     logs = (
    #         cls.model
    #         .select(*fields)
    #         .join(
    #             Task,
    #             JOIN.LEFT_OUTER,
    #             on=(
    #                 (Task.doc_id == cls.model.document_id) &
    #                 (Task.update_time == latest_task_update_time)
    #             )
    #         )
    #         .where(
    #             cls.model.kb_id == kb_id,
    #             cls.model.document_id != GRAPH_RAPTOR_FAKE_DOC_ID,
    #             cls.model.update_date == latest_log_update_date,
    #         )
    #     )

    #     if keywords:
    #         logs = logs.where(
    #             fn.LOWER(cls.model.document_name).contains(keywords.lower())
    #         )

    #     if operation_status:
    #         logs = logs.where(cls.model.operation_status.in_(operation_status))

    #     if types:
    #         logs = logs.where(cls.model.document_type.in_(types))

    #     if suffix:
    #         logs = logs.where(cls.model.document_suffix.in_(suffix))

    #     if create_date_from:
    #         logs = logs.where(cls.model.create_date >= create_date_from)

    #     if create_date_to:
    #         logs = logs.where(cls.model.create_date <= create_date_to)

    #     # 只展示 status 为 2 的日志
    #     logs = logs.where(cls.model.status != "2")

    #     count = logs.count()

    #     if desc:
    #         logs = logs.order_by(cls.model.getter_by(orderby).desc())
    #     else:
    #         logs = logs.order_by(cls.model.getter_by(orderby).asc())

    #     if page_number and items_per_page:
    #         logs = logs.paginate(page_number, items_per_page)

    #     log_list = list(logs.dicts())

    #     for log in log_list:
    #         raw_task_type = log.get("latest_task_type")
    #         has_parse_task = bool(log.get("has_parse_task"))

    #         if raw_task_type is None:
    #             latest_task_type = None
    #         else:
    #             latest_task_type = raw_task_type.lower().strip()

    #         if latest_task_type == "graphrag":
    #             process_scene = "graph_parse"
    #             process_scene_text = "知识图谱"

    #         elif latest_task_type == "raptor":
    #             process_scene = "raptor"
    #             process_scene_text = "raptor"

    #         elif has_parse_task:
    #             process_scene = "full_parse"
    #             process_scene_text = "解析全文"

    #         elif latest_task_type == "parse_author_info":
    #             process_scene = "author_extract"
    #             process_scene_text = "提取作者"

    #         elif latest_task_type:
    #             process_scene = latest_task_type
    #             process_scene_text = latest_task_type

    #         else:
    #             process_scene = "unknown"
    #             process_scene_text = "未知"

    #         log.update({
    #             "latest_task_type": latest_task_type or "",
    #             "has_parse_task": has_parse_task,

    #             "process_scene": process_scene,
    #             "process_scene_text": process_scene_text,

    #             "latest_task_scene": process_scene,
    #             "latest_task_scene_text": process_scene_text,

    #             "latest_task_progress": log.get("latest_task_progress"),
    #             "latest_task_progress_msg": log.get("latest_task_progress_msg") or "",
    #             "latest_task_update_time": log.get("latest_task_update_time"),
    #         })

    #     return log_list, count
    
    @classmethod
    @DB.connection_context()
    def get_file_logs_by_kb_id(
            cls,
            kb_id,
            page_number,
            items_per_page,
            orderby,
            desc,
            keywords,
            operation_status,
            types,
            suffix,
            create_date_from=None,
            create_date_to=None,
    ):
        from peewee import fn, JOIN, Case
        from api.db.db_models import Document, Task
        from api.db.services.task_service import GRAPH_RAPTOR_FAKE_DOC_ID

        Log = cls.model

        # =========================
        # Task 别名
        # =========================
        TaskActive = Task.alias()
        TaskAny = Task.alias()

        TaskActivePickAlias = Task.alias()
        TaskAnyPickAlias = Task.alias()
        TaskParseAlias = Task.alias()

        LogLatestAlias = Log.alias()

        # =========================
        # Task 类型优先级
        #
        # 0 普通全文解析 task_type == ""
        # 1 dataflow
        # 2 graphrag
        # 3 raptor
        # 9 parse_author_info
        #
        # parse_author_info 优先级最低，避免全文解析完成后页面显示成“提取作者”
        # =========================
        def task_priority_case(TaskAlias):
            return Case(
                None,
                [
                    # 普通全文解析，最高优先级
                    (TaskAlias.task_type == "", 0),

                    # dataflow 解析
                    (TaskAlias.task_type ** "dataflow%", 1),

                    # 知识图谱
                    (TaskAlias.task_type == "graphrag", 2),

                    # raptor
                    (TaskAlias.task_type == "raptor", 3),

                    # 提取作者，最低优先级
                    (TaskAlias.task_type == "parse_author_info", 9),
                ],
                5,
            )

        # =========================
        # 当前未完成任务
        #
        # 注意：
        # 只有 Document.run 本身处于运行中/排队中，才认为 active task 有效。
        #
        # 这样可以避免：
        # Document 已经成功 run == 3，
        # 但 Task 表里残留 progress = 0 / progress < 1 的脏任务，
        # 导致页面显示“排队中”。
        # =========================
        active_task_id_query = (
            TaskActivePickAlias
            .select(TaskActivePickAlias.id)
            .where(
                TaskActivePickAlias.doc_id == Document.id,
                TaskActivePickAlias.progress >= 0,
                TaskActivePickAlias.progress < 1,

                # 关键修复：文档不是运行/排队状态，就不要找 active task
                Document.run.in_(["1", "5", 1, 5]),
            )
            .order_by(
                task_priority_case(TaskActivePickAlias).asc(),
                TaskActivePickAlias.update_time.desc(),
            )
            .limit(1)
        )

        # =========================
        # fallback Task
        #
        # 没有 active_task 时，用它兜底。
        #
        # 注意：
        # 这里不能只按 update_time desc。
        # 因为 parse_author_info 通常在全文解析之后更新，
        # 如果只取最新，会导致解析完成后页面显示“提取作者完成”。
        #
        # 所以这里也要按任务优先级选择。
        # =========================
        latest_any_task_id_query = (
            TaskAnyPickAlias
            .select(TaskAnyPickAlias.id)
            .where(
                TaskAnyPickAlias.doc_id == Document.id
            )
            .order_by(
                task_priority_case(TaskAnyPickAlias).asc(),
                TaskAnyPickAlias.update_time.desc(),
            )
            .limit(1)
        )

        # =========================
        # 最新 pipeline_operation_log
        # =========================
        latest_log_update_date = (
            LogLatestAlias
            .select(fn.MAX(LogLatestAlias.update_date))
            .where(
                LogLatestAlias.kb_id == Document.kb_id,
                LogLatestAlias.document_id == Document.id,
                LogLatestAlias.document_id != GRAPH_RAPTOR_FAKE_DOC_ID,
            )
        )

        # =========================
        # 是否存在普通全文解析任务
        # task_type == "" 代表普通全文解析
        # =========================
        has_parse_task_query = (
            TaskParseAlias
            .select(TaskParseAlias.id)
            .where(
                TaskParseAlias.doc_id == Document.id,
                TaskParseAlias.task_type == "",
            )
            .limit(1)
        )

        has_parse_task = Case(
            None,
            [
                (fn.EXISTS(has_parse_task_query), 1),
            ],
            0,
        ).alias("has_parse_task")

        # =========================
        # 主查询：以 Document 为主表
        # =========================
        query = (
            Document
            .select(
                # ---------- Document 字段 ----------
                Document.id.alias("id"),
                Document.id.alias("document_id"),
                Document.kb_id.alias("kb_id"),

                Document.name.alias("document_name"),
                Document.suffix.alias("document_suffix"),
                Document.type.alias("document_type"),
                Document.source_type.alias("source_type"),

                Document.parser_id.alias("parser_id"),
                Document.pipeline_id.alias("document_pipeline_id"),
                Document.thumbnail.alias("document_avatar"),

                Document.progress.alias("document_progress"),
                Document.progress_msg.alias("document_progress_msg"),
                Document.process_begin_at.alias("document_process_begin_at"),
                Document.process_duration.alias("document_process_duration"),
                Document.run.alias("document_run"),

                Document.create_time.alias("create_time"),
                Document.create_date.alias("create_date"),
                Document.update_time.alias("update_time"),
                Document.update_date.alias("update_date"),

                # ---------- 当前优先展示的未完成 Task ----------
                TaskActive.id.alias("active_task_id"),
                TaskActive.task_type.alias("active_task_type"),
                TaskActive.progress.alias("active_task_progress"),
                TaskActive.progress_msg.alias("active_task_progress_msg"),
                TaskActive.begin_at.alias("active_task_begin_at"),
                TaskActive.process_duration.alias("active_task_process_duration"),
                TaskActive.update_time.alias("active_task_update_time"),

                # ---------- fallback Task ----------
                TaskAny.id.alias("latest_task_id"),
                TaskAny.task_type.alias("latest_task_type"),
                TaskAny.progress.alias("latest_task_progress"),
                TaskAny.progress_msg.alias("latest_task_progress_msg"),
                TaskAny.begin_at.alias("latest_task_begin_at"),
                TaskAny.process_duration.alias("latest_task_process_duration"),
                TaskAny.update_time.alias("latest_task_update_time"),

                # ---------- 最新日志字段 ----------
                Log.id.alias("latest_log_id"),
                Log.pipeline_id.alias("pipeline_id"),
                Log.pipeline_title.alias("pipeline_title"),
                Log.task_type.alias("log_task_type"),
                Log.operation_status.alias("latest_log_operation_status"),
                Log.progress.alias("latest_log_progress"),
                Log.progress_msg.alias("latest_log_progress_msg"),
                Log.process_begin_at.alias("latest_log_process_begin_at"),
                Log.process_duration.alias("latest_log_process_duration"),
                Log.avatar.alias("avatar"),
                Log.dsl.alias("dsl"),

                has_parse_task,
            )
            .join(
                TaskActive,
                JOIN.LEFT_OUTER,
                on=(TaskActive.id == active_task_id_query),
            )
            .switch(Document)
            .join(
                TaskAny,
                JOIN.LEFT_OUTER,
                on=(TaskAny.id == latest_any_task_id_query),
            )
            .switch(Document)
            .join(
                Log,
                JOIN.LEFT_OUTER,
                on=(
                    (Log.document_id == Document.id)
                    & (Log.update_date == latest_log_update_date)
                ),
            )
            .where(
                Document.kb_id == kb_id,
                Document.id != GRAPH_RAPTOR_FAKE_DOC_ID,
                Document.status == "1",
            )
        )

        # =========================
        # 查询条件
        # =========================
        if keywords:
            query = query.where(
                fn.LOWER(Document.name).contains(keywords.lower())
            )

        if types:
            query = query.where(Document.type.in_(types))

        if suffix:
            query = query.where(Document.suffix.in_(suffix))

        if create_date_from:
            query = query.where(Document.create_date >= create_date_from)

        if create_date_to:
            query = query.where(Document.create_date <= create_date_to)

        # =========================
        # 排序
        # =========================
        order_field_map = {
            "create_time": Document.create_time,
            "create_date": Document.create_date,
            "update_time": Document.update_time,
            "update_date": Document.update_date,
            "process_begin_at": Document.process_begin_at,
            "document_name": Document.name,
            "name": Document.name,
            "progress": Document.progress,
        }

        order_field = order_field_map.get(orderby, Document.create_time)

        if desc:
            query = query.order_by(order_field.desc())
        else:
            query = query.order_by(order_field.asc())

        rows = list(query.dicts())

        # =========================
        # 选择页面应该展示哪个任务
        # =========================
        def pick_display_task(row):
            """
            优先展示 active_task。

            active_task 已经在 SQL 里按任务类型优先级选过：

            全文解析 > dataflow > graphrag > raptor > 其他 > 提取作者

            如果没有 active_task，则展示 fallback task。
            fallback task 也按同样优先级选择，避免解析完成后显示“提取作者”。
            """

            if row.get("active_task_id"):
                return {
                    "id": row.get("active_task_id"),
                    "task_type": row.get("active_task_type"),
                    "progress": row.get("active_task_progress"),
                    "progress_msg": row.get("active_task_progress_msg") or "",
                    "begin_at": row.get("active_task_begin_at"),
                    "process_duration": row.get("active_task_process_duration"),
                    "update_time": row.get("active_task_update_time"),
                    "is_active": True,
                }

            if row.get("latest_task_id"):
                return {
                    "id": row.get("latest_task_id"),
                    "task_type": row.get("latest_task_type"),
                    "progress": row.get("latest_task_progress"),
                    "progress_msg": row.get("latest_task_progress_msg") or "",
                    "begin_at": row.get("latest_task_begin_at"),
                    "process_duration": row.get("latest_task_process_duration"),
                    "update_time": row.get("latest_task_update_time"),
                    "is_active": False,
                }

            return {
                "id": None,
                "task_type": "",
                "progress": None,
                "progress_msg": "",
                "begin_at": None,
                "process_duration": None,
                "update_time": None,
                "is_active": False,
            }

        # =========================
        # 推断 operation_status
        #
        # 前端 RunningStatus:
        # 0 未开始
        # 1 运行中
        # 2 已取消
        # 3 成功
        # 4 失败
        # 5 排队中
        # =========================
        def infer_operation_status(row, display_task):
            document_run = row.get("document_run")

            task_id = display_task.get("id")
            task_progress = display_task.get("progress")
            task_msg = display_task.get("progress_msg") or ""
            task_process_duration = display_task.get("process_duration")

            task_msg_lower = task_msg.lower()

            document_run_str = "" if document_run is None else str(document_run)

            # =========================
            # 关键修复：
            # Document 已经明确成功时，直接成功。
            # 防止 Task 表残留 progress = 0 / progress < 1 的数据导致显示排队中。
            # =========================
            if document_run_str == "3":
                return "3"

            # Document 明确取消
            if document_run_str == "2":
                return "2"

            # Document 明确失败
            if document_run_str == "4":
                return "4"

            # 没有任何 Task，优先用 document.run
            if not task_id:
                if document_run_str != "":
                    return document_run_str
                return "0"

            # 有任务但 progress 为空，认为排队中
            if task_progress is None:
                return "5"

            # 失败或取消
            if task_progress < 0:
                if (
                        "canceled" in task_msg_lower
                        or "cancelled" in task_msg_lower
                        or "取消" in task_msg_lower
                ):
                    return "2"
                return "4"

            # 成功
            if task_progress >= 1:
                return "3"

            # 排队中
            # 你的场景：progress 一开始不是 0，
            # 但是 process_duration == 0 且 progress_msg 是 Task has been received.
            if (
                    task_process_duration == 0
                    and (
                        "task has been received" in task_msg_lower
                        or "received" in task_msg_lower
                    )
            ):
                return "5"

            # progress 刚好为 0，也认为排队中
            if task_progress == 0:
                return "5"

            # 其他 0 < progress < 1
            return "1"

        # =========================
        # 推断具体任务显示
        # =========================
        def infer_process_scene(display_task, has_parse_task_flag):
            raw_task_type = display_task.get("task_type")
            task_type = raw_task_type.lower().strip() if raw_task_type else ""

            # 知识图谱
            if task_type == "graphrag":
                return {
                    "raw_task_type": raw_task_type or "",
                    "task_type": "graphrag",
                    "task_type_text": "GraphRAG",
                    "process_scene": "graph_parse",
                    "process_scene_text": "知识图谱",
                }

            # Raptor
            if task_type == "raptor":
                return {
                    "raw_task_type": raw_task_type or "",
                    "task_type": "raptor",
                    "task_type_text": "Raptor",
                    "process_scene": "raptor",
                    "process_scene_text": "Raptor",
                }

            # 提取作者
            if task_type == "parse_author_info":
                return {
                    "raw_task_type": raw_task_type or "",
                    "task_type": "parse_author_info",
                    "task_type_text": "提取作者",
                    "process_scene": "author_extract",
                    "process_scene_text": "提取作者",
                }

            # 普通全文解析
            # 数据库里 task_type 是空字符串，但是前端任务列要显示 Parse
            if task_type == "":
                return {
                    "raw_task_type": raw_task_type or "",
                    "task_type": "parse",
                    "task_type_text": "Parse",
                    "process_scene": "full_parse",
                    "process_scene_text": "解析全文",
                }

            # dataflow 也视为 Parse
            if task_type.startswith("dataflow"):
                return {
                    "raw_task_type": raw_task_type or "",
                    "task_type": "parse",
                    "task_type_text": "Parse",
                    "process_scene": "full_parse",
                    "process_scene_text": "解析全文",
                }

            # 兜底：如果这个文档有普通解析任务，也显示 Parse
            if has_parse_task_flag:
                return {
                    "raw_task_type": raw_task_type or "",
                    "task_type": "parse",
                    "task_type_text": "Parse",
                    "process_scene": "full_parse",
                    "process_scene_text": "解析全文",
                }

            return {
                "raw_task_type": raw_task_type or "",
                "task_type": task_type or "unknown",
                "task_type_text": task_type or "未知",
                "process_scene": task_type or "unknown",
                "process_scene_text": task_type or "未知",
            }

        log_list = []

        for row in rows:
            display_task = pick_display_task(row)

            # 状态
            row["operation_status"] = infer_operation_status(row, display_task)

            # 状态过滤
            if operation_status:
                valid_status = [str(s) for s in operation_status]
                if row["operation_status"] not in valid_status:
                    continue

            # source_from 前端兼容
            row["source_from"] = (row.get("source_type") or "local").split("/")[0]

            # progress 优先使用当前展示任务
            row["progress"] = (
                display_task.get("progress")
                if display_task.get("progress") is not None
                else row.get("document_progress") or 0
            )

            # 如果 document_run 已经成功，但 display_task 是历史任务，可以强制 progress = 1
            if str(row.get("document_run")) == "3":
                row["progress"] = 1

            # progress_msg 优先使用当前展示任务
            row["progress_msg"] = (
                display_task.get("progress_msg")
                or row.get("document_progress_msg")
                or row.get("latest_log_progress_msg")
                or ""
            )

            # process_begin_at 优先使用当前展示任务
            row["process_begin_at"] = (
                display_task.get("begin_at")
                or row.get("document_process_begin_at")
                or row.get("latest_log_process_begin_at")
            )

            # process_duration 优先使用当前展示任务
            row["process_duration"] = (
                display_task.get("process_duration")
                or row.get("document_process_duration")
                or row.get("latest_log_process_duration")
                or 0
            )

            # pipeline_title 兜底
            row["pipeline_title"] = (
                row.get("pipeline_title")
                or row.get("parser_id")
                or "general"
            )

            # avatar 兜底
            row["avatar"] = row.get("avatar") or row.get("document_avatar")

            has_parse_task_flag = bool(row.get("has_parse_task"))

            task_display = infer_process_scene(
                display_task,
                has_parse_task_flag,
            )

            normalized_task_type = task_display["task_type"]
            task_type_text = task_display["task_type_text"]
            process_scene = task_display["process_scene"]
            process_scene_text = task_display["process_scene_text"]

            # 原始数据库 task_type
            row["raw_task_type"] = task_display["raw_task_type"]

            # 标准化后的任务类型
            row["task_type"] = normalized_task_type
            row["latest_task_type"] = normalized_task_type

            # 给前端显示用的任务名称
            row["task_type_text"] = task_type_text
            row["latest_task_type_text"] = task_type_text

            # 关键：如果前端任务列用的是 log_task_type，这里也要覆盖
            row["log_task_type"] = task_type_text

            row["has_parse_task"] = has_parse_task_flag

            # 具体任务
            row["process_scene"] = process_scene
            row["process_scene_text"] = process_scene_text

            row["latest_task_scene"] = process_scene
            row["latest_task_scene_text"] = process_scene_text

            row["latest_task_progress"] = display_task.get("progress")
            row["latest_task_progress_msg"] = display_task.get("progress_msg") or ""
            row["latest_task_update_time"] = display_task.get("update_time")

            # 调试字段，可留可删
            row["display_task_id"] = display_task.get("id")
            row["display_task_is_active"] = display_task.get("is_active")

            log_list.append(row)

        count = len(log_list)

        # 因为 operation_status 是 Python 中推断出来的，
        # 所以分页放在状态过滤之后
        if page_number and items_per_page:
            start = (page_number - 1) * items_per_page
            end = start + items_per_page
            log_list = log_list[start:end]

        return log_list, count
    
    
    @classmethod
    @DB.connection_context()
    def get_file_logs_by_kb_id_wasted(
        cls,
        kb_id,
        page_number,
        items_per_page,
        orderby,
        desc,
        keywords,
        operation_status,
        types,
        suffix,
        create_date_from=None,
        create_date_to=None
    ):
        fields = cls.get_file_logs_fields()

        from peewee import fn, Case, JOIN
        from api.db.db_models import Task

        LogLatestAlias = cls.model.alias()

        latest_log_update_date = (
            LogLatestAlias
            .select(fn.MAX(LogLatestAlias.update_date))
            .where(
                LogLatestAlias.kb_id == cls.model.kb_id,
                LogLatestAlias.document_id == cls.model.document_id,
                LogLatestAlias.document_id != GRAPH_RAPTOR_FAKE_DOC_ID,
            )
        )

        TaskLatestAlias = Task.alias()

        latest_task_update_time = (
            TaskLatestAlias
            .select(fn.MAX(TaskLatestAlias.update_time))
            .where(
                TaskLatestAlias.doc_id == cls.model.document_id
            )
        )

        TaskParseAlias = Task.alias()

        has_parse_task_query = (
            TaskParseAlias
            .select(TaskParseAlias.id)
            .where(
                TaskParseAlias.doc_id == cls.model.document_id,
                TaskParseAlias.task_type == "",
            )
            .limit(1)
        )

        is_latest_parse = Case(
            None,
            [
                (cls.model.update_date == latest_log_update_date, 1),
            ],
            0
        ).alias("is_latest_parse")

        has_parse_task = Case(
            None,
            [
                (fn.EXISTS(has_parse_task_query), 1),
            ],
            0
        ).alias("has_parse_task")

        fields = [
            *fields,
            is_latest_parse,
            has_parse_task,

            Task.task_type.alias("latest_task_type"),
            Task.progress.alias("latest_task_progress"),
            Task.progress_msg.alias("latest_task_progress_msg"),
            Task.update_time.alias("latest_task_update_time"),
        ]

        logs = (
            cls.model
            .select(*fields)
            .join(
                Task,
                JOIN.LEFT_OUTER,
                on=(
                    (Task.doc_id == cls.model.document_id) &
                    (Task.update_time == latest_task_update_time)
                )
            )
            .where(
                cls.model.kb_id == kb_id,
                cls.model.document_id != GRAPH_RAPTOR_FAKE_DOC_ID,
                cls.model.update_date == latest_log_update_date,
            )
        )

        if keywords:
            logs = logs.where(
                fn.LOWER(cls.model.document_name).contains(keywords.lower())
            )

        if operation_status:
            logs = logs.where(cls.model.operation_status.in_(operation_status))

        if types:
            logs = logs.where(cls.model.document_type.in_(types))

        if suffix:
            logs = logs.where(cls.model.document_suffix.in_(suffix))

        if create_date_from:
            logs = logs.where(cls.model.create_date >= create_date_from)

        if create_date_to:
            logs = logs.where(cls.model.create_date <= create_date_to)

        # 只展示 status 为 2 的日志
        logs = logs.where(cls.model.status == "2")

        count = logs.count()

        if desc:
            logs = logs.order_by(cls.model.getter_by(orderby).desc())
        else:
            logs = logs.order_by(cls.model.getter_by(orderby).asc())

        if page_number and items_per_page:
            logs = logs.paginate(page_number, items_per_page)

        log_list = list(logs.dicts())

        for log in log_list:
            raw_task_type = log.get("latest_task_type")
            has_parse_task = bool(log.get("has_parse_task"))

            if raw_task_type is None:
                latest_task_type = None
            else:
                latest_task_type = raw_task_type.lower().strip()

            if latest_task_type == "graphrag":
                process_scene = "graph_parse"
                process_scene_text = "知识图谱"

            elif latest_task_type == "raptor":
                process_scene = "raptor"
                process_scene_text = "raptor"

            elif has_parse_task:
                process_scene = "full_parse"
                process_scene_text = "解析全文"

            elif latest_task_type == "parse_author_info":
                process_scene = "author_extract"
                process_scene_text = "提取作者"

            elif latest_task_type:
                process_scene = latest_task_type
                process_scene_text = latest_task_type

            else:
                process_scene = "unknown"
                process_scene_text = "未知"

            log.update({
                "latest_task_type": latest_task_type or "",
                "has_parse_task": has_parse_task,

                "process_scene": process_scene,
                "process_scene_text": process_scene_text,

                "latest_task_scene": process_scene,
                "latest_task_scene_text": process_scene_text,

                "latest_task_progress": log.get("latest_task_progress"),
                "latest_task_progress_msg": log.get("latest_task_progress_msg") or "",
                "latest_task_update_time": log.get("latest_task_update_time"),
            })

        return log_list, count
    

    # @classmethod
    # @DB.connection_context()
    # def get_file_logs_by_kb_id(
    #     cls,
    #     kb_id,
    #     page_number,
    #     items_per_page,
    #     orderby,
    #     desc,
    #     keywords,
    #     operation_status,
    #     types,
    #     suffix,
    #     create_date_from=None,
    #     create_date_to=None,
    # ):
    #     from peewee import fn, Case

    #     fields = cls.get_file_logs_fields()

    #     # 1. 统一构造过滤条件
    #     conditions = [
    #         cls.model.kb_id == kb_id,
    #         cls.model.document_id != GRAPH_RAPTOR_FAKE_DOC_ID,
    #     ]

    #     if keywords:
    #         conditions.append(
    #             fn.LOWER(cls.model.document_name).contains(keywords.lower())
    #         )

    #     if operation_status:
    #         conditions.append(cls.model.operation_status.in_(operation_status))

    #     if types:
    #         conditions.append(cls.model.document_type.in_(types))

    #     if suffix:
    #         conditions.append(cls.model.document_suffix.in_(suffix))

    #     if create_date_from:
    #         conditions.append(cls.model.create_date >= create_date_from)

    #     if create_date_to:
    #         conditions.append(cls.model.create_date <= create_date_to)

    #     # 2. 子查询：按 document_id 分组，每个文件按 create_date 倒序编号
    #     ranked_query = (
    #         cls.model
    #         .select(
    #             *fields,
    #             fn.ROW_NUMBER().over(
    #                 partition_by=[cls.model.document_id],
    #                 order_by=[cls.model.create_date.desc()]
    #             ).alias("rn")
    #         )
    #         .where(*conditions)
    #         .alias("ranked_logs")
    #     )

    #     # 3. 外层查询：只取每个 document_id 最新的一条 rn = 1
    #     final_query = (
    #         cls.model
    #         .select(
    #             ranked_query.c.id,
    #             ranked_query.c.kb_id,
    #             ranked_query.c.document_id,
    #             ranked_query.c.document_name,
    #             ranked_query.c.document_type,
    #             ranked_query.c.document_suffix,
    #             ranked_query.c.operation_status,
    #             ranked_query.c.operation_status.alias("status"),
    #             ranked_query.c.create_date,
    #             ranked_query.c.update_date,
    #             ranked_query.c.process_begin_at,
    #             ranked_query.c.process_duration,
    #             ranked_query.c.progress_msg,
    #             ranked_query.c.source_from,
    #             ranked_query.c.task_type,
    #             ranked_query.c.dsl,
    #             Case(
    #                 None,
    #                 [
    #                     (ranked_query.c.operation_status == 3, "成功"),
    #                 ],
    #                 "失败",
    #             ).alias("final_status"),
    #         )
    #         .from_(ranked_query)
    #         .where(ranked_query.c.rn == 1)
    #     )

    #     # 4. 统计总数：按 document_id 去重
    #     count_query = (
    #         cls.model
    #         .select(fn.COUNT(fn.DISTINCT(cls.model.document_id)))
    #         .where(*conditions)
    #     )

    #     count = count_query.scalar() or 0

    #     # 5. 排序字段映射，注意：这里必须用 ranked_query.c.xxx，不能用 cls.model.xxx
    #     order_field_map = {
    #         "id": ranked_query.c.id,
    #         "document_id": ranked_query.c.document_id,
    #         "document_name": ranked_query.c.document_name,
    #         "document_type": ranked_query.c.document_type,
    #         "document_suffix": ranked_query.c.document_suffix,
    #         "operation_status": ranked_query.c.operation_status,
    #         "status": ranked_query.c.operation_status,
    #         "create_date": ranked_query.c.create_date,
    #         "update_date": ranked_query.c.update_date,
    #         "process_begin_at": ranked_query.c.process_begin_at,
    #         "process_duration": ranked_query.c.process_duration,
    #     }

    #     order_field = order_field_map.get(orderby, ranked_query.c.create_date)

    #     if desc:
    #         final_query = final_query.order_by(order_field.desc())
    #     else:
    #         final_query = final_query.order_by(order_field.asc())

    #     # 6. 分页
    #     if page_number and items_per_page:
    #         final_query = final_query.paginate(page_number, items_per_page)

    #     return list(final_query.dicts()), count

    @classmethod
    @DB.connection_context()
    def get_documents_info(cls, id):
        fields = [Document.id, Document.name, Document.progress, Document.kb_id]
        return (
            cls.model.select(*fields)
            .join(Document, on=(cls.model.document_id == Document.id))
            .where(
                cls.model.id == id
            )
            .dicts()
        )
    
    @classmethod
    @DB.connection_context()
    def update_status_by_document_ids(cls, document_ids, status):
        if isinstance(document_ids, str):
            document_ids = [document_ids]

        if not document_ids:
            return 0

        return (
            cls.model
            .update(status=status)
            .where(cls.model.document_id.in_(document_ids))
            .execute()
        )
    
    @classmethod
    @DB.connection_context()
    def delete_by_document_ids(cls, document_ids):
        if isinstance(document_ids, str):
            document_ids = [document_ids]

        return (
            cls.model
            .delete()
            .where(cls.model.document_id.in_(document_ids))
            .execute()
        )
    
    @classmethod
    @DB.connection_context()
    def delete_by_document_ids_from_log_ids(cls, log_ids):
        if isinstance(log_ids, str):
            log_ids = [log_ids]

        document_ids = [
            item["document_id"]
            for item in cls.model
            .select(cls.model.document_id)
            .where(cls.model.id.in_(log_ids))
            .dicts()
            if item.get("document_id")
        ]

        if not document_ids:
            return 0

        return (
            cls.model
            .delete()
            .where(cls.model.document_id.in_(document_ids))
            .execute()
        )

    @classmethod
    @DB.connection_context()
    def get_dataset_logs_by_kb_id(cls, kb_id, page_number, items_per_page, orderby, desc, operation_status, create_date_from=None, create_date_to=None):
        fields = cls.get_dataset_logs_fields()
        logs = cls.model.select(*fields).where((cls.model.kb_id == kb_id), (cls.model.document_id == GRAPH_RAPTOR_FAKE_DOC_ID))

        if operation_status:
            logs = logs.where(cls.model.operation_status.in_(operation_status))
        if create_date_from:
            logs = logs.where(cls.model.create_date >= create_date_from)
        if create_date_to:
            logs = logs.where(cls.model.create_date <= create_date_to)

        count = logs.count()
        if desc:
            logs = logs.order_by(cls.model.getter_by(orderby).desc())
        else:
            logs = logs.order_by(cls.model.getter_by(orderby).asc())

        if page_number and items_per_page:
            logs = logs.paginate(page_number, items_per_page)

        return list(logs.dicts()), count
