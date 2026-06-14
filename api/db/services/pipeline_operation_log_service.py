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
