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
import binascii
import logging
import re
import time
from copy import deepcopy
from datetime import datetime
from functools import partial
from timeit import default_timer as timer
from langfuse import Langfuse
from peewee import fn
from agentic_reasoning import DeepResearcher
from agnet_skills.agent_chat import async_chat_agent_mode
from api.db.services.file_service import FileService
from common.constants import LLMType, ParserType, StatusEnum
from api.db.db_models import DB, Dialog
from api.db.services.common_service import CommonService
from api.db.services.document_service import DocumentService
from api.db.services.knowledgebase_service import KnowledgebaseService
from api.db.services.langfuse_service import TenantLangfuseService
from api.db.services.llm_service import LLMBundle
from common.metadata_utils import apply_meta_data_filter
from api.db.services.tenant_llm_service import TenantLLMService
from common.time_utils import current_timestamp, datetime_format
from graphrag.general.mind_map_extractor import MindMapExtractor
from rag.app.resume import forbidden_select_fields4resume
from rag.app.tag import label_question
from rag.nlp.search import index_name
from rag.prompts.generator import chunks_format, citation_prompt, cross_languages, full_question, kb_prompt, keyword_extraction, message_fit_in, \
    PROMPT_JINJA_ENV, ASK_SUMMARY
from common.token_utils import num_tokens_from_string
from rag.utils.tavily_conn import Tavily
from common.string_utils import remove_redundant_spaces
from common import settings
import asyncio


class DialogService(CommonService):
    model = Dialog

    @classmethod
    def save(cls, **kwargs):
        """Save a new record to database.

        This method creates a new record in the database with the provided field values,
        forcing an insert operation rather than an update.

        Args:
            **kwargs: Record field values as keyword arguments.

        Returns:
            Model instance: The created record object.
        """
        sample_obj = cls.model(**kwargs).save(force_insert=True)
        return sample_obj

    @classmethod
    def update_many_by_id(cls, data_list):
        """Update multiple records by their IDs.

        This method updates multiple records in the database, identified by their IDs.
        It automatically updates the update_time and update_date fields for each record.

        Args:
            data_list (list): List of dictionaries containing record data to update.
                             Each dictionary must include an 'id' field.
        """
        with DB.atomic():
            for data in data_list:
                data["update_time"] = current_timestamp()
                data["update_date"] = datetime_format(datetime.now())
                cls.model.update(data).where(cls.model.id == data["id"]).execute()

    @classmethod
    @DB.connection_context()
    def get_list(cls, tenant_id, page_number, items_per_page, orderby, desc, id, name):
        chats = cls.model.select()
        if id:
            chats = chats.where(cls.model.id == id)
        if name:
            chats = chats.where(cls.model.name == name)
        chats = chats.where((cls.model.tenant_id == tenant_id) & (cls.model.status == StatusEnum.VALID.value))
        if desc:
            chats = chats.order_by(cls.model.getter_by(orderby).desc())
        else:
            chats = chats.order_by(cls.model.getter_by(orderby).asc())

        chats = chats.paginate(page_number, items_per_page)

        return list(chats.dicts())

    @classmethod
    @DB.connection_context()
    def get_by_tenant_ids(cls, joined_tenant_ids, user_id, page_number, items_per_page, orderby, desc, keywords, parser_id=None):
        from api.db.db_models import User

        fields = [
            cls.model.id,
            cls.model.tenant_id,
            cls.model.name,
            cls.model.description,
            cls.model.language,
            cls.model.llm_id,
            cls.model.llm_setting,
            cls.model.prompt_type,
            cls.model.prompt_config,
            cls.model.similarity_threshold,
            cls.model.vector_similarity_weight,
            cls.model.top_n,
            cls.model.top_k,
            cls.model.do_refer,
            cls.model.rerank_id,
            cls.model.kb_ids,
            cls.model.icon,
            cls.model.status,
            User.nickname,
            User.avatar.alias("tenant_avatar"),
            cls.model.update_time,
            cls.model.create_time,
        ]
        if keywords:
            dialogs = (
                cls.model.select(*fields)
                .join(User, on=(cls.model.tenant_id == User.id))
                .where(
                    (cls.model.tenant_id.in_(joined_tenant_ids) | (cls.model.tenant_id == user_id)) & (cls.model.status == StatusEnum.VALID.value),
                    (fn.LOWER(cls.model.name).contains(keywords.lower())),
                )
            )
        else:
            dialogs = (
                cls.model.select(*fields)
                .join(User, on=(cls.model.tenant_id == User.id))
                .where(
                    (cls.model.tenant_id.in_(joined_tenant_ids) | (cls.model.tenant_id == user_id)) & (cls.model.status == StatusEnum.VALID.value),
                )
            )
        if parser_id:
            dialogs = dialogs.where(cls.model.parser_id == parser_id)
        if desc:
            dialogs = dialogs.order_by(cls.model.getter_by(orderby).desc())
        else:
            dialogs = dialogs.order_by(cls.model.getter_by(orderby).asc())

        count = dialogs.count()

        if page_number and items_per_page:
            dialogs = dialogs.paginate(page_number, items_per_page)

        return list(dialogs.dicts()), count

    @classmethod
    @DB.connection_context()
    def get_all_dialogs_by_tenant_id(cls, tenant_id):
        fields = [cls.model.id]
        dialogs = cls.model.select(*fields).where(cls.model.tenant_id == tenant_id)
        dialogs.order_by(cls.model.create_time.asc())
        offset, limit = 0, 100
        res = []
        while True:
            d_batch = dialogs.offset(offset).limit(limit)
            _temp = list(d_batch.dicts())
            if not _temp:
                break
            res.extend(_temp)
            offset += limit
        return res


async def async_chat_solo(dialog, messages, stream=True):
    attachments = ""
    if "files" in messages[-1]:
        attachments = "\n\n".join(FileService.get_files(messages[-1]["files"]))
    if TenantLLMService.llm_id2llm_type(dialog.llm_id) == "image2text":
        chat_mdl = LLMBundle(dialog.tenant_id, LLMType.IMAGE2TEXT, dialog.llm_id)
    else:
        chat_mdl = LLMBundle(dialog.tenant_id, LLMType.CHAT, dialog.llm_id)

    prompt_config = dialog.prompt_config
    tts_mdl = None
    if prompt_config.get("tts"):
        tts_mdl = LLMBundle(dialog.tenant_id, LLMType.TTS)
    msg = [{"role": m["role"], "content": re.sub(r"##\d+\$\$", "", m["content"])} for m in messages if m["role"] != "system"]
    if attachments and msg:
        msg[-1]["content"] += attachments
    if stream:
        last_ans = ""
        delta_ans = ""
        answer = ""
        async for ans in chat_mdl.async_chat_streamly(prompt_config.get("system", ""), msg, dialog.llm_setting):
            answer = ans
            delta_ans = ans[len(last_ans):]
            if num_tokens_from_string(delta_ans) < 16:
                continue
            last_ans = answer
            yield {"answer": answer, "reference": {}, "audio_binary": tts(tts_mdl, delta_ans), "prompt": "", "created_at": time.time()}
            delta_ans = ""
        if delta_ans:
            yield {"answer": answer, "reference": {}, "audio_binary": tts(tts_mdl, delta_ans), "prompt": "", "created_at": time.time()}
    else:
        answer = await chat_mdl.async_chat(prompt_config.get("system", ""), msg, dialog.llm_setting)
        user_content = msg[-1].get("content", "[content not available]")
        logging.debug("User: {}|Assistant: {}".format(user_content, answer))
        yield {"answer": answer, "reference": {}, "audio_binary": tts(tts_mdl, answer), "prompt": "", "created_at": time.time()}


def get_models(dialog):
    embd_mdl, chat_mdl, rerank_mdl, tts_mdl = None, None, None, None
    kbs = KnowledgebaseService.get_by_ids(dialog.kb_ids)
    embedding_list = list(set([kb.embd_id for kb in kbs]))
    if len(embedding_list) > 1:
        raise Exception("**ERROR**: Knowledge bases use different embedding models.")

    if embedding_list:
        embd_mdl = LLMBundle(dialog.tenant_id, LLMType.EMBEDDING, embedding_list[0])
        if not embd_mdl:
            raise LookupError("Embedding model(%s) not found" % embedding_list[0])

    if TenantLLMService.llm_id2llm_type(dialog.llm_id) == "image2text":
        chat_mdl = LLMBundle(dialog.tenant_id, LLMType.IMAGE2TEXT, dialog.llm_id)
    else:
        chat_mdl = LLMBundle(dialog.tenant_id, LLMType.CHAT, dialog.llm_id)

    if dialog.rerank_id:
        rerank_mdl = LLMBundle(dialog.tenant_id, LLMType.RERANK, dialog.rerank_id)

    if dialog.prompt_config.get("tts"):
        tts_mdl = LLMBundle(dialog.tenant_id, LLMType.TTS)
    return kbs, embd_mdl, rerank_mdl, chat_mdl, tts_mdl


BAD_CITATION_PATTERNS = [
    re.compile(r"\(\s*ID\s*[: ]*\s*(\d+)\s*\)"),  # (ID: 12)
    re.compile(r"\[\s*ID\s*[: ]*\s*(\d+)\s*\]"),  # [ID: 12]
    re.compile(r"【\s*ID\s*[: ]*\s*(\d+)\s*】"),  # 【ID: 12】
    re.compile(r"ref\s*(\d+)", flags=re.IGNORECASE),  # ref12、REF 12
]


def repair_bad_citation_formats(answer: str, kbinfos: dict, idx: set):
    max_index = len(kbinfos["chunks"])

    def safe_add(i):
        if 0 <= i < max_index:
            idx.add(i)
            return True
        return False

    def find_and_replace(pattern, group_index=1, repl=lambda i: f"ID:{i}", flags=0):
        nonlocal answer

        def replacement(match):
            try:
                i = int(match.group(group_index))
                if safe_add(i):
                    return f"[{repl(i)}]"
            except Exception:
                pass
            return match.group(0)

        answer = re.sub(pattern, replacement, answer, flags=flags)

    for pattern in BAD_CITATION_PATTERNS:
        find_and_replace(pattern)

    return answer, idx

from api.apps import login_required, current_user
from api.db.db_models import AdminUser
from api.db.db_models import User, Role, SyncDept,PermissionApplication,RoleUser,StagedFileTag,Document,StagedFile
class FilePermissionLevel:
    PUBLIC = 1
    INTERNAL = 2


# 获取普通用户的文件权限等级
def get_user_file_permission_level(user_id):
    """
    获取用户拥有的最高文件权限等级。

    没有角色时，默认只能访问公开文件。
    """
    if not user_id:
        return FilePermissionLevel.PUBLIC

    query = (
        Role
        .select(
            Role.file_permission_level,
            Role.is_admin,
        )
        .join(
            RoleUser,
            on=(RoleUser.role_id == Role.id)
        )
        .where(
            RoleUser.user_id == str(user_id),
            Role.enabled == True,
        )
    )

    permission_level = FilePermissionLevel.PUBLIC

    for role in query:
        # 角色本身是管理员，也可以直接拥有内部文件权限
        if role.is_admin:
            return FilePermissionLevel.INTERNAL

        permission_level = max(
            permission_level,
            role.file_permission_level or FilePermissionLevel.PUBLIC
        )

    return permission_level

# 获取知识库中的公开文件 ID
def get_public_doc_ids_by_kb(kb_id):
    """
    获取指定知识库中 knowledge_level=public 的文档 ID。
    """

    query = (
        Document
        .select(Document.id)
        .join(
            StagedFile,
            on=(StagedFile.doc_id == Document.id)
        )
        .join(
            StagedFileTag,
            on=(StagedFileTag.stage_id == StagedFile.id)
        )
        .where(
            Document.kb_id == str(kb_id),
            Document.status == "1",
            StagedFileTag.type_code == "knowledge_level",
            StagedFileTag.option_code == "public",
        )
        .distinct()
    )

    return [str(row.id) for row in query]

async def async_chat(dialog, messages, stream=True, **kwargs):
    # 获取当前用户的id
    user_id = kwargs["user_id"]

    assert messages[-1]["role"] == "user", "The last content of this conversation is not from user."
    # # 无kb搜索的情况
    # if not dialog.kb_ids and not dialog.prompt_config.get("tavily_api_key"):
    #     # 直接走纯对话
    #     async for ans in async_chat_solo(dialog, messages, stream):
    #         yield ans
    #     return
    # 统一拷贝 prompt_config，兼容旧数据没有 agent_mod 的情况
    prompt_config = dict(dialog.prompt_config or {})


    reasoning_enabled = prompt_config.get("reasoning", False)
    agent_mod_enabled = prompt_config.get("agent_mod", False) or kwargs.get("agent_mod", False)

    # 无 kb 且非 Agent 模式，才走纯对话
    if not agent_mod_enabled and not dialog.kb_ids and not prompt_config.get("tavily_api_key"):
        async for ans in async_chat_solo(dialog, messages, stream):
            yield ans
        return

    chat_start_ts = timer()

    # 如果是图片理解模型
    if TenantLLMService.llm_id2llm_type(dialog.llm_id) == "image2text":
        llm_model_config = TenantLLMService.get_model_config(dialog.tenant_id, LLMType.IMAGE2TEXT, dialog.llm_id)
    # 否则chat
    else:
        llm_model_config = TenantLLMService.get_model_config(dialog.tenant_id, LLMType.CHAT, dialog.llm_id)


    max_tokens = llm_model_config.get("max_tokens", 8192)

    check_llm_ts = timer()

    # Langfuse 追踪初始化
    langfuse_tracer = None  
    trace_context = {}
    langfuse_keys = TenantLangfuseService.filter_by_tenant(tenant_id=dialog.tenant_id)
    if langfuse_keys:
        langfuse = Langfuse(public_key=langfuse_keys.public_key, secret_key=langfuse_keys.secret_key, host=langfuse_keys.host)
        if langfuse.auth_check():
            langfuse_tracer = langfuse
            trace_id = langfuse_tracer.create_trace_id()
            trace_context = {"trace_id": trace_id}

    check_langfuse_tracer_ts = timer()
    # 加载模型
    kbs, embd_mdl, rerank_mdl, chat_mdl, tts_mdl = get_models(dialog)
    toolcall_session, tools = kwargs.get("toolcall_session"), kwargs.get("tools")
    # 绑定工具
    if toolcall_session and tools:
        chat_mdl.bind_tools(toolcall_session, tools)
    bind_models_ts = timer()

    # 准备检索输入
    retriever = settings.retriever
    # 最近三条用户问题
    questions = [m["content"] for m in messages if m["role"] == "user"][-3:]
    # 附件处理
    attachments = kwargs["doc_ids"].split(",") if "doc_ids" in kwargs else []
    attachments_= ""
    # 前端传入的文档id
    if "doc_ids" in messages[-1]:
        attachments = messages[-1]["doc_ids"]

    # 上传的文件内容拼接到 system promp
    if "files" in messages[-1]:
        attachments_ = "\n\n".join(FileService.get_files(messages[-1]["files"]))

    # Prompt 参数处理
    # prompt_config = dialog.prompt_config

    # print(prompt_config)
    # 选择了哪些知识库
    field_map = KnowledgebaseService.get_field_map(dialog.kb_ids)
    # 尝试 SQL 检索（优先）
    # try to use sql if field mapping is good to go
    if field_map and not agent_mod_enabled:
        logging.debug("Use SQL to retrieval:{}".format(questions[-1]))
        ans = await use_sql(questions[-1], field_map, dialog.tenant_id, chat_mdl, prompt_config.get("quote", True), dialog.kb_ids)
        if ans:
            yield ans
            return

    # 参数补全 & 多轮处理
    for p in prompt_config["parameters"]:
        if p["key"] == "knowledge":
            continue
        if p["key"] not in kwargs and not p["optional"]:
            raise KeyError("Miss parameter: " + p["key"])
        if p["key"] not in kwargs:
            # prompt_config["system"] = prompt_config["system"].replace("{%s}" % p["key"], " ")
            prompt_config["system"] = prompt_config.get("system", "").replace("{%s}" % p["key"], " ")
    # 把多轮对话整合成一个完整的问题
    if len(questions) > 1 and prompt_config.get("refine_multiturn"):
        questions = [await full_question(dialog.tenant_id, dialog.llm_id, messages)]
        
        # 新增历史问题改写
        # last_question = "当前的用户问题是:" + questions[-1] + "\n"
        # pre_question = "前几轮的用户问题是:" + ",".join(questions[-10:-1])
        # questions = []
        # questions.append(last_question)
        # questions.append(pre_question)

    else:
        questions = questions[-1:]
    # 跨语言处理
    if prompt_config.get("cross_languages"):
        questions = [await cross_languages(dialog.tenant_id, dialog.llm_id, questions[0], prompt_config["cross_languages"])]

    # 按标签 / 元数据筛选文档
    if dialog.meta_data_filter:
        # {
        #     "author": {
        #         "张三": ["doc1", "doc2"],
        #         "李四": ["doc3"]
        #     },
        #     "year": {
        #         "2024": ["doc1"],
        #         "2023": ["doc2", "doc3"]
        #     },
        #     "tags": {
        #         "['合同', '法律']": ["doc1"]
        #     }
        # }

        print("00000000000000000...........................................0000000000000")
        metas = DocumentService.get_meta_by_kbs(dialog.kb_ids)
        meta_data_structure = {}
        SPECIAL_META_KEYS = {
            "school",
            "author",
            "publish_time",
        }
        # for key, values in meta_data.items():
        #     meta_data_structure[key] = list(values.keys()) if isinstance(values, dict) else values
        for key, values in metas.items():
            print(key)
            if key in SPECIAL_META_KEYS:
                continue
    
            meta_data_structure[key] = (
                list(values.keys())
                if isinstance(values, dict)
                else values
            )
        import json
        metadata_keys=json.dumps(meta_data_structure)

        attachments = await apply_meta_data_filter(
            dialog.meta_data_filter,
            metas,
            questions[-1],
            chat_mdl,
            attachments,
        )
    # 关键词增强
    if prompt_config.get("keyword", False):
        questions[-1] += await keyword_extraction(chat_mdl, questions[-1])

    refine_question_ts = timer()

    thought = ""
    kbinfos = {"total": 0, "chunks": [], "doc_aggs": []}
    knowledges = []
    has_knowledge_param = "knowledge" in [
        p["key"] for p in prompt_config.get("parameters", [])
    ]

    # 知识库检索核心
    if attachments is not None and "knowledge" in [p["key"] for p in prompt_config["parameters"]]:
        tenant_ids = list(set([kb.tenant_id for kb in kbs]))
        knowledges = []
        #  Deep Research（推理型）启动深度推理
        if prompt_config.get("reasoning", False):
        # if True:
            reasoner = DeepResearcher(
                chat_mdl,
                prompt_config,
                partial(
                    retriever.retrieval,
                    embd_mdl=embd_mdl,
                    tenant_ids=tenant_ids,
                    kb_ids=dialog.kb_ids,
                    page=1,
                    page_size=dialog.top_n,
                    similarity_threshold=0.2,
                    vector_similarity_weight=0.3,
                    doc_ids=attachments,
                ),
            )
            # # 流式返回思考过程
            # async for think in reasoner.thinking(kbinfos, attachments_ + " ".join(questions)):
            #     if isinstance(think, str):
            #         thought = think
            #         knowledges = [t for t in think.split("\n") if t]
            #     elif stream:
            #         yield think
        
            async for think in reasoner.thinking(
                kbinfos,
                attachments_ + " ".join(questions)
            ):
                if isinstance(think, dict):
                    snapshot = think.get("answer", "")
        
                    # 重点：DeepResearcher 现在是快照模式，所以这里必须覆盖
                    # 不能 +=
                    if snapshot:
                        thought = snapshot
        
                    if stream:
                        yield think
        
                elif isinstance(think, str):
                    if think:
                        thought = think
        
                    if stream:
                        yield {
                            "answer": think,
                            "reference": {},
                            "audio_binary": None,
                        }
        
            # thinking 结束后，再统一生成 knowledges
            thought_without_tag = re.sub(r"</?think\b[^>]*>", "", thought, flags=re.I)
        
            knowledges = [
                t.strip()
                for t in thought_without_tag.split("\n")
                if t.strip()
            ]

        # 2. Agent 模式，新加
        elif agent_mod_enabled:
        # if prompt_config.get("reasoning", False):
            async for ans in async_chat_agent_mode(
                    dialog=dialog,
                    messages=messages,
                    questions=questions,
                    attachments=attachments,
                    attachments_text=attachments_,
                    kbs=kbs,
                    embd_mdl=embd_mdl,
                    rerank_mdl=rerank_mdl,
                    chat_mdl=chat_mdl,
                    retriever=retriever,
                    prompt_config=prompt_config,
                    stream=stream,
                    **kwargs
            ):
                yield ans

            return

        # 普通 RAG 检索
        else:
            # 向量检索 重排序 TOC 增强 KG 检索 Tavily 搜索
            print("===============================检索的知识库id为===================================")
            print(dialog.kb_ids)
            selected_kbs = list(kbs)
            is_super_admin_user = AdminUser.query(user_id=user_id, role_level =1)
            if is_super_admin_user:
                user_file_permission_level = FilePermissionLevel.INTERNAL
            else:
                user_file_permission_level = await asyncio.to_thread(
                    get_user_file_permission_level,
                    user_id
                )

            can_access_internal_files = (
                is_super_admin_user
                or user_file_permission_level >= FilePermissionLevel.INTERNAL
            )
            

            # import asyncio
            import traceback

            public_doc_ids_by_kb = {}

            if not can_access_internal_files:
                public_doc_results = await asyncio.gather(
                    *[
                        asyncio.to_thread(
                            get_public_doc_ids_by_kb,
                            kb.id
                        )
                        for kb in selected_kbs
                    ]
                )

                public_doc_ids_by_kb = {
                    str(kb.id): doc_ids
                    for kb, doc_ids in zip(
                        selected_kbs,
                        public_doc_results
                    )
                }


            if embd_mdl:
                query = " ".join(questions)
                selected_kbs = list(kbs)
                total_top_n = max(1, int(dialog.top_n or 1))
                per_kb_top_n = total_top_n

                doc_aggs_by_id = {}

                kbinfos = {
                    "total": 0,
                    "chunks": [],
                    "doc_aggs": []
                }

                # current_user_id = str(current_user.id)

                # 1. 判断超级管理员
                is_super_admin_user = AdminUser.query(user_id=user_id, role_level =1)
        
                # 2. 获取普通用户角色权限
                if is_super_admin_user:
                    user_file_permission_level = (
                        FilePermissionLevel.INTERNAL
                    )
                else:
                    user_file_permission_level = await asyncio.to_thread(
                        get_user_file_permission_level,
                        user_id
                    )

                # 3. 判断是否能访问内部文件
                can_access_internal_files = (
                    is_super_admin_user
                    or user_file_permission_level
                    >= FilePermissionLevel.INTERNAL
                )

                # 4. 没有内部权限时，查询公开文件
                public_doc_ids_by_kb = {}

                if not can_access_internal_files:
                    public_doc_results = await asyncio.gather(
                        *[
                            asyncio.to_thread(
                                get_public_doc_ids_by_kb,
                                kb.id
                            )
                            for kb in selected_kbs
                        ]
                    )

                    public_doc_ids_by_kb = {
                        str(kb.id): doc_ids
                        for kb, doc_ids in zip(
                            selected_kbs,
                            public_doc_results
                        )
                    }

                sem = asyncio.Semaphore(8)

                async def retrieve_one_kb(kb):
                    async with sem:
                        kb_tenant_ids = [kb.tenant_id]
                        kb_id = str(kb.id)

                        try:
                            retrieval_doc_ids = attachments

                            if not can_access_internal_files:
                                public_doc_ids = set(
                                    str(doc_id)
                                    for doc_id in public_doc_ids_by_kb.get(
                                        kb_id,
                                        []
                                    )
                                )

                                if attachments:
                                    retrieval_doc_ids = [
                                        doc_id
                                        for doc_id in attachments
                                        if str(doc_id) in public_doc_ids
                                    ]
                                else:
                                    retrieval_doc_ids = list(public_doc_ids)
                                print("-------------------------------------------------------")
                                print(retrieval_doc_ids)
                                if not retrieval_doc_ids:
                                    return {
                                        "kb_id": kb.id,
                                        "total": 0,
                                        "chunks": [],
                                        "doc_aggs": [],
                                        "error": None,
                                    }

                            kb_result = await asyncio.to_thread(
                                retriever.retrieval,
                                query,
                                embd_mdl,
                                kb_tenant_ids,
                                [kb.id],
                                1,
                                per_kb_top_n,
                                dialog.similarity_threshold,
                                dialog.vector_similarity_weight,
                                doc_ids=retrieval_doc_ids,
                                top=dialog.top_k,
                                aggs=False,
                                rerank_mdl=rerank_mdl,
                                rank_feature=label_question(query, [kb]),
                            )

                            kb_chunks = kb_result.get("chunks", [])

                            if prompt_config.get("toc_enhance"):
                                cks = await asyncio.to_thread(
                                    retriever.retrieval_by_toc,
                                    query,
                                    kb_chunks,
                                    kb_tenant_ids,
                                    chat_mdl,
                                    per_kb_top_n,
                                )

                                if cks:
                                    kb_chunks = cks

                            kb_chunks = await asyncio.to_thread(
                                retriever.retrieval_by_children,
                                kb_chunks,
                                kb_tenant_ids,
                            )

                            for chunk in kb_chunks:
                                if not chunk.get("kb_id"):
                                    chunk["kb_id"] = kb.id

                            return {
                                "kb_id": kb.id,
                                "total": kb_result.get(
                                    "total",
                                    len(kb_chunks)
                                ),
                                "chunks": kb_chunks,
                                "doc_aggs": kb_result.get("doc_aggs", []),
                                "error": None,
                            }

                        except Exception as e:
                            traceback.print_exc()

                            return {
                                "kb_id": kb.id,
                                "total": 0,
                                "chunks": [],
                                "doc_aggs": [],
                                "error": e,
                            }

                tasks = [
                    asyncio.create_task(
                        retrieve_one_kb(kb)
                    )
                    for kb in selected_kbs
                ]

                results = await asyncio.gather(*tasks)

                for kb_data in results:
                    if kb_data["error"]:
                        print(f"知识库检索失败，kb_id={kb_data['kb_id']}, error={kb_data['error']}")
                        traceback.print_exception(
                            type(kb_data["error"]),
                            kb_data["error"],
                            kb_data["error"].__traceback__
                        )
                        continue

                    kbinfos["chunks"].extend(kb_data["chunks"])
                    kbinfos["total"] += kb_data["total"]

                    for doc_agg in kb_data["doc_aggs"]:
                        doc_id = doc_agg.get("doc_id")
                        if not doc_id:
                            continue

                        if doc_id not in doc_aggs_by_id:
                            doc_aggs_by_id[doc_id] = dict(doc_agg)
                        else:
                            doc_aggs_by_id[doc_id]["count"] = (
                                doc_aggs_by_id[doc_id].get("count", 0)
                                + doc_agg.get("count", 0)
                            )

                kbinfos["doc_aggs"] = list(doc_aggs_by_id.values())

                print("改写后的问题为：")
                print(questions)

            if prompt_config.get("tavily_api_key"):
                tav = Tavily(prompt_config["tavily_api_key"])
                tav_res = tav.retrieve_chunks(" ".join(questions))
                kbinfos["chunks"].extend(tav_res["chunks"])
                kbinfos["doc_aggs"].extend(tav_res["doc_aggs"])
            if prompt_config.get("use_kg"):
                ck = settings.kg_retriever.retrieval(" ".join(questions), tenant_ids, dialog.kb_ids, embd_mdl,
                                                       LLMBundle(dialog.tenant_id, LLMType.CHAT))
                if ck["content_with_weight"]:
                    kbinfos["chunks"].insert(0, ck)
            
            print("最终的召回结果为：============================================================\n")
            print(kbinfos)
            # 组装 Prompt
            knowledges = kb_prompt(kbinfos, max_tokens, source_kbs=dialog.kb_ids)

    logging.debug("{}->{}".format(" ".join(questions), "\n->".join(knowledges)))

    retrieval_ts = timer()
    # 没检索到 → 返回兜底答案
    if not knowledges and prompt_config.get("empty_response"):
        # 如果没召回就返回固定话术
        empty_res = prompt_config["empty_response"]
        yield {"answer": empty_res, "reference": kbinfos, "prompt": "\n\n### Query:\n%s" % " ".join(questions),
               "audio_binary": tts(tts_mdl, empty_res)}
        yield {"answer": prompt_config["empty_response"], "reference": kbinfos}
        return

    kwargs["knowledge"] = "\n------\n" + "\n\n------\n\n".join(knowledges)
    source_group_answer_prompt = ""
    if knowledges and len(dialog.kb_ids or []) > 1 and not prompt_config.get("reasoning", False):
        # 多知识库回答格式要求：只追加运行时指令，不改前端 prompt_config。
        selected_kb_ids = dialog.kb_ids if isinstance(dialog.kb_ids, list) else [dialog.kb_ids]
        selected_kb_names = []
        kbs_by_id = {kb.id: kb.name for kb in kbs}
        for kb_id in selected_kb_ids:
            kb_id = str(kb_id)
            kb_detail = KnowledgebaseService.get_detail(kb_id)
            kb_name = kb_detail["name"] if kb_detail else kbs_by_id.get(kb_id, f"未知知识库({kb_id})")
            selected_kb_names.append(kb_name)
        source_headings = "\n".join([f"【从{name}来说】" for name in selected_kb_names])
        source_group_answer_prompt = f"""
            # 来源分组回答要求

            你必须严格按照以下来源标签结构进行回答，但只输出有相关内容的来源标签：

            {source_headings}

            【综合总结】

            输出规则：
            1. 仅当某个“【从...来说】”标签对应的“【来源：...】”上下文中，存在与用户问题直接相关的内容时，才输出该标签及其回答。
            2. 如果某个来源未检索到相关内容，或内容与用户问题无关，必须完全跳过该来源标签，不要输出空标签、占位语或“未提及”等表述。
            3. 每个来源的回答必须严格基于其对应的“【来源：...】”上下文，不得使用其他来源内容，不得编造、推断或补充原文未包含的信息。
            4. “【综合总结】”必须放在最后，仅基于已输出的各来源内容进行总结。
            5. 不要先写总述，不要合并不同来源
            6. 请使用 Markdown 格式回答：
                - 一级主题用 ## 标题
                - 二级主题用 ### 标题
                - 具体内容用 - 列表
                - 不要使用空格缩进模拟层级。
            """

        # # 来源分组回答要求
        # 你必须严格按下面的标签结构输出，不要先写总述，不要合并不同来源，也不要使用 Markdown 标题符号 #：
        # {source_headings}
        # 【综合总结】

        # 规则：
        # 1. 每个“【从...来说】”标签都必须出现，标签下换行后用要点回答。
        # 2. 每个来源只能使用对应“【来源：...】”上下文里的内容；如果该来源未检索到相关内容，则直接略过该来源，不要编造。
        # 3. “【综合总结】”必须放在最后，总结各来源的共同结论、差异点和总体判断。
        # """

    print("相关的召回信息为----------------------------------------------------------------------")
    print(kwargs)
    gen_conf = dialog.llm_setting

    # 系统提示词语 + 文件内容
    msg = [{"role": "system", "content": prompt_config["system"].format(**kwargs) + source_group_answer_prompt + attachments_}]

    prompt4citation = ""
    if knowledges and (prompt_config.get("quote", True) and kwargs.get("quote", True)):
        prompt4citation = citation_prompt()
    msg.extend([{"role": m["role"], "content": re.sub(r"##\d+\$\$", "", m["content"])} for m in messages if m["role"] != "system"])
    # Token 裁剪 & 生成配置
    used_token_count, msg = message_fit_in(msg, int(max_tokens * 0.95))
    assert len(msg) >= 2, f"message_fit_in has bug: {msg}"
    prompt = msg[0]["content"]

    # 防止 prompt 超长
    if "max_tokens" in gen_conf:
        gen_conf["max_tokens"] = min(gen_conf["max_tokens"], max_tokens - used_token_count)

    # 装饰最终结果（decorate_answer）
    async def decorate_answer(answer):
        # 读取和修改这些外部变量的值
        nonlocal embd_mdl, prompt_config, knowledges, kwargs, kbinfos, prompt, retrieval_ts, questions, langfuse_tracer

        # 参考文献或知识库信息
        refs = []
        ans = answer.split("</think>")
        think = ""
        if len(ans) == 2:
            think = ans[0] + "</think>"
            answer = ans[1]

        print(questions)
        if metadata_keys:
            suggestion_system_prompt = f"""
                你是一个智能追问建议生成助手。

                请根据提供的对话历史，生成 3 个用户可能追问的简短问题。
                用户当前问题：
                {questions[-1]}

                AI 当前回答：
                {answer}

                优先围绕这些标签生成追问可用元数据标签和值：
                {metadata_keys}

                要求：
                . 问题要有深度或相关性。
                . 直接返回纯 JSON 数组，不要包含 Markdown 格式（如 ```json），例如：["问题1", "问题2", "问题3"]。
                """
        else:
            suggestion_system_prompt = f"""
            你是一个智能助手。请根据提供的对话历史，生成 3 个用户可能追问的简短问题。
            要求：
            . 问题要有深度或相关性。
            . 直接返回纯 JSON 数组，不要包含 Markdown 格式（如 ```json），例如：["问题1", "问题2", "问题3"]。
            用户: {questions[-1]}
            AI: {answer}
            """
        suggestions = await chat_mdl.async_chat(suggestion_system_prompt, [])
        print(suggestions)
        import json
        try:
            # 1. 拿到原始字符串 (例如: '["问题1", "问题2"]')
            raw_suggestions = await chat_mdl.async_chat(suggestion_system_prompt, [])

            # 2. 清洗数据 (防止模型不听话带上了 ```json ... ```)
            clean_text = raw_suggestions.replace("```json", "").replace("```", "").strip()

            # 3. 解析 JSON (把字符串变成 Python 列表)
            suggestions = json.loads(clean_text)

            # 确保它是列表类型 (防呆)
            if not isinstance(suggestions, list):
                suggestions = []

        except Exception as e:
            print(f"生成建议问题解析失败: {e}")
            suggestions = []  # 失败了给个空列表，别让程序崩了


        # 处理引用与知识库
        if knowledges and (prompt_config.get("quote", True) and kwargs.get("quote", True)):


            # 用于存储被引用的知识块的索引···
            idx = set([])
            # 判断是否需要自动插入引用 <--存在嵌入模型 (embd_mdl)，并且回答中还没有包含 [ID:x] 格式的引用标记。
            if embd_mdl and not re.search(r"\[ID:([0-9]+)\]", answer):
                # 调用 retriever.insert_citations 方法。它会根据回答内容和知识库块的文本、向量信息，自动在 answer 中插入引用标记（如 [ID:1]），并返回修改后的回答和被引用的知识块索引 idx。
                answer, idx = retriever.insert_citations(
                    answer,
                    [ck["content_ltks"] for ck in kbinfos["chunks"]],
                    [ck["vector"] for ck in kbinfos["chunks"]],
                    embd_mdl,
                    tkweight=1 - dialog.vector_similarity_weight,
                    vtweight=dialog.vector_similarity_weight,
                )
            # 如果回答中已经存在 [ID:x] 格式的标记，则通过正则表达式找出所有标记，并将有效的索引 i 添加到 idx 集合中。
            else:
                for match in re.finditer(r"\[ID:([0-9]+)\]", answer):
                    i = int(match.group(1))
                    if i < len(kbinfos["chunks"]):
                        idx.add(i)
            # 用于修复可能存在的错误引用格式
            answer, idx = repair_bad_citation_formats(answer, kbinfos, idx)

            # chunk序号 --> doc_id
            # idx = set([kbinfos["chunks"][int(i)]["doc_id"] for i in idx])
            doc_ids = set()

            for i in idx:
                try:
                    chunk = kbinfos["chunks"][int(i)]
                except Exception:
                    continue

                doc_id = chunk.get("doc_id") or chunk.get("document_id")

                if doc_id:
                    doc_ids.add(doc_id)

            idx = doc_ids

            # 从召回中过滤 引用的文档
            recall_docs = [d for d in kbinfos["doc_aggs"] if d["doc_id"] in idx]
            if not recall_docs:
                recall_docs = kbinfos["doc_aggs"]
            kbinfos["doc_aggs"] = recall_docs

            refs = deepcopy(kbinfos)
            for c in refs["chunks"]:
                if c.get("vector"):
                    del c["vector"]

            print("final_refs---------------------------------------------------------------")
            print(refs)
        if answer.lower().find("invalid key") >= 0 or answer.lower().find("invalid api") >= 0:
            answer += " Please set LLM API-Key in 'User Setting -> Model providers -> API-Key'"
        finish_chat_ts = timer()

        total_time_cost = (finish_chat_ts - chat_start_ts) * 1000
        check_llm_time_cost = (check_llm_ts - chat_start_ts) * 1000
        check_langfuse_tracer_cost = (check_langfuse_tracer_ts - check_llm_ts) * 1000
        bind_embedding_time_cost = (bind_models_ts - check_langfuse_tracer_ts) * 1000
        refine_question_time_cost = (refine_question_ts - bind_models_ts) * 1000
        retrieval_time_cost = (retrieval_ts - refine_question_ts) * 1000
        generate_result_time_cost = (finish_chat_ts - retrieval_ts) * 1000

        tk_num = num_tokens_from_string(think + answer)
        prompt += "\n\n### Query:\n%s" % " ".join(questions)
        prompt = (
            f"{prompt}\n\n"
            "## Time elapsed:\n"
            f"  - Total: {total_time_cost:.1f}ms\n"
            f"  - Check LLM: {check_llm_time_cost:.1f}ms\n"
            f"  - Check Langfuse tracer: {check_langfuse_tracer_cost:.1f}ms\n"
            f"  - Bind models: {bind_embedding_time_cost:.1f}ms\n"
            f"  - Query refinement(LLM): {refine_question_time_cost:.1f}ms\n"
            f"  - Retrieval: {retrieval_time_cost:.1f}ms\n"
            f"  - Generate answer: {generate_result_time_cost:.1f}ms\n\n"
            "## Token usage:\n"
            f"  - Generated tokens(approximately): {tk_num}\n"
            f"  - Token speed: {int(tk_num / (generate_result_time_cost / 1000.0))}/s"
        )

        # Add a condition check to call the end method only if langfuse_tracer exists
        if langfuse_tracer and "langfuse_generation" in locals():
            langfuse_output = "\n" + re.sub(r"^.*?(### Query:.*)", r"\1", prompt, flags=re.DOTALL)
            langfuse_output = {"time_elapsed:": re.sub(r"\n", "  \n", langfuse_output), "created_at": time.time()}
            langfuse_generation.update(output=langfuse_output)
            langfuse_generation.end()


        print("final_answer------------------------------------------------------")
        print(answer)
        if "知识库中未找到您要的答案" in answer:
            # 在赋值前增加一个类型检查
            if isinstance(refs, dict):
                refs["doc_aggs"] = []
            else:
                refs=[]

        return {"answer": think + answer, "reference": refs, "prompt": re.sub(r"\n", "  \n", prompt), "created_at": time.time(), "suggestions":suggestions}

    # Langfuse Generation 开始
    if langfuse_tracer:
        langfuse_generation = langfuse_tracer.start_generation(
            trace_context=trace_context, name="chat", model=llm_model_config["llm_name"],
            input={"prompt": prompt, "prompt4citation": prompt4citation, "messages": msg}
        )
    def build_id_doc_name_map(kbinfos):
        """
        构造：
        {
            "0": "文件A.pdf",
            "1": "文件B.pdf",
            "chunk_id_xxx": "文件A.pdf"
        }

        ID 数字优先对应 kbinfos["chunks"] 的下标。
        """
        chunks = kbinfos.get("chunks", []) or []
        doc_aggs = kbinfos.get("doc_aggs", []) or []

        doc_name_by_id = {}

        for doc in doc_aggs:
            doc_id = doc.get("doc_id")
            doc_name = (
                doc.get("doc_name")
                or doc.get("name")
                or doc.get("filename")
                or doc.get("file_name")
            )

            if doc_id and doc_name:
                doc_name_by_id[str(doc_id)] = str(doc_name)

        id_doc_name_map = {}

        for index, chunk in enumerate(chunks):
            doc_id = (
                chunk.get("doc_id")
                or chunk.get("document_id")
            )

            doc_name = (
                doc_name_by_id.get(str(doc_id))
                or chunk.get("doc_name")
                or chunk.get("document_name")
                or chunk.get("filename")
                or chunk.get("file_name")
            )

            if not doc_name:
                continue

            # 支持 THINK 里的 ID 0、ID 1、ID 12
            id_doc_name_map[str(index)] = str(doc_name)

            # 兜底：如果模型输出的是 chunk.id
            chunk_id = chunk.get("id")
            if chunk_id:
                id_doc_name_map[str(chunk_id)] = str(doc_name)

        return id_doc_name_map
    
    def replace_think_ids_with_doc_names(text, id_doc_name_map):
        """
        只替换 <think>...</think> 内部的 ID。
        支持流式场景：<think> 未闭合时也能替换。
        """
        if not text or not id_doc_name_map:
            return text

        def replace_id_group(full_match, id_group):
            ids = [
                x.strip()
                for x in re.split(r"[、,，\s]+", id_group)
                if x.strip()
            ]

            doc_names = []

            for id_text in ids:
                doc_name = id_doc_name_map.get(str(id_text))
                if doc_name:
                    doc_names.append(doc_name)

            if not doc_names:
                return full_match

            # 去重，避免多个 chunk 来自同一个文档时重复显示
            unique_doc_names = []
            seen = set()

            for name in doc_names:
                if name not in seen:
                    unique_doc_names.append(name)
                    seen.add(name)

            return "、".join(f"《{name}》" for name in unique_doc_names)

        def replace_in_think_body(think_body):
            next_text = think_body

            # 1. 支持：
            # ID 12
            # ID:12
            # ID：12
            # ID为12
            # ID为1、2、3
            # ID为0的
            next_text = re.sub(
                r"ID\s*(?:[:：]|为)?\s*((?:[A-Za-z0-9_-]+\s*[、,，\s]*)+)",
                lambda m: replace_id_group(m.group(0), m.group(1)),
                next_text,
                flags=re.IGNORECASE,
            )

            # 2. 支持连接词后面的单个 ID：
            # 和17
            # 及17
            # 与17
            # 、17
            # 到5
            # 至5
            next_text = re.sub(
                r"([和及与、到至])\s*([A-Za-z0-9_-]+)(?=(的|则|提到|涉及|介绍|讨论|分析|说明|指出|研究|讲|描述|认为|文件|以及|等|[，。,；;：:\)\]）】\s]|$))",
                lambda m: (
                    # “到/至5” 替换成 “和《文件名》”，语义更自然
                    f"和《{id_doc_name_map.get(str(m.group(2)))}》"
                    if m.group(1) in ["到", "至"] and id_doc_name_map.get(str(m.group(2)))
                    else (
                        f"{m.group(1)}《{id_doc_name_map.get(str(m.group(2)))}》"
                        if id_doc_name_map.get(str(m.group(2)))
                        else m.group(0)
                    )
                ),
                next_text,
            )

            # 3. 支持：
            # 以及17
            next_text = re.sub(
                r"(以及)\s*([A-Za-z0-9_-]+)(?=(的|则|提到|涉及|介绍|讨论|分析|说明|指出|研究|讲|描述|认为|文件|等|[，。,；;：:\)\]）】\s]|$))",
                lambda m: (
                    f"{m.group(1)}《{id_doc_name_map.get(str(m.group(2)))}》"
                    if id_doc_name_map.get(str(m.group(2)))
                    else m.group(0)
                ),
                next_text,
            )

            # 4. 支持：
            # 文献ID 17
            # 文献ID为17
            # 文献ID：17
            next_text = re.sub(
                r"文献\s*ID\s*(?:[:：]|为)?\s*([A-Za-z0-9_-]+)(?=(的|则|提到|涉及|介绍|讨论|分析|说明|指出|研究|讲|描述|认为|文件|以及|等|[，。,；;：:\)\]）】\s]|$))",
                lambda m: (
                    f"文献《{id_doc_name_map.get(str(m.group(1)))}》"
                    if id_doc_name_map.get(str(m.group(1)))
                    else m.group(0)
                ),
                next_text,
                flags=re.IGNORECASE,
            )

            # 5. 优化语义，避免 “《xxx.pdf》的文件”
            next_text = next_text.replace("》的文件", "》")

            return next_text

        lower_text = text.lower()
        result = []
        cursor = 0

        while cursor < len(text):
            think_start = lower_text.find("<think", cursor)

            # 没有 think，后面正文原样返回
            if think_start == -1:
                result.append(text[cursor:])
                break

            # think 前面的正文不替换
            result.append(text[cursor:think_start])

            open_tag_end = text.find(">", think_start)

            # 流式标签还没完整，例如 <thi 或 <think
            if open_tag_end == -1:
                result.append(text[think_start:])
                break

            # 保留 <think> 开始标签
            result.append(text[think_start:open_tag_end + 1])

            close_tag_start = lower_text.find("</think>", open_tag_end + 1)

            # 没有 </think>，说明正在流式输出 THINK 内容
            if close_tag_start == -1:
                think_body = text[open_tag_end + 1:]
                result.append(replace_in_think_body(think_body))
                break

            # 有完整闭合 THINK
            think_body = text[open_tag_end + 1:close_tag_start]
            result.append(replace_in_think_body(think_body))
            result.append(text[close_tag_start:close_tag_start + len("</think>")])

            cursor = close_tag_start + len("</think>")

        return "".join(result)
    
    # 流式 / 非流式输出
    id_doc_name_map = build_id_doc_name_map(kbinfos)
    print("id_doc_name_map:", id_doc_name_map)

    if stream:
        last_ans = ""
        answer = ""

        async for ans in chat_mdl.async_chat_streamly(
            prompt + prompt4citation,
            msg[1:],
            gen_conf,
            dialog_id=dialog.id
        ):
            if thought:
                ans = re.sub(r"^.*</think>", "", ans, flags=re.DOTALL)

            answer = ans
            delta_ans = ans[len(last_ans):]

            if num_tokens_from_string(delta_ans) < 16:
                continue

            last_ans = answer

            # 只替换 THINK 里的 ID，正文不动
            display_answer = replace_think_ids_with_doc_names(
                thought + answer,
                id_doc_name_map
            )

            # 实时的页面展示
            yield {
                "answer": display_answer,
                "reference": {},
                "audio_binary": tts(tts_mdl, delta_ans),
                "suggestions": []
            }

        delta_ans = answer[len(last_ans):]

        if delta_ans:
            display_answer = replace_think_ids_with_doc_names(
                thought + answer,
                id_doc_name_map
            )

            yield {
                "answer": display_answer,
                "reference": {},
                "audio_binary": tts(tts_mdl, delta_ans),
                "suggestions": []
            }

        # 最终交付仍然用原始 answer 做 decorate，避免影响引用解析
        # final_package = await decorate_answer(thought + answer)
        final_package = await decorate_answer(answer)

        if isinstance(final_package, dict):
            final_package["answer"] = thought + final_package.get("answer", "")

        # 最终展示也替换一下 THINK 里的 ID
        final_package["answer"] = replace_think_ids_with_doc_names(
            final_package.get("answer", thought + answer),
            id_doc_name_map
        )

        yield final_package

    else:
        answer = await chat_mdl.async_chat(prompt + prompt4citation, msg[1:], gen_conf)

        user_content = msg[-1].get("content", "[content not available]")
        logging.debug("User: {}|Assistant: {}".format(user_content, answer))

        res = await decorate_answer(answer)

        res["answer"] = replace_think_ids_with_doc_names(
            res.get("answer", answer),
            id_doc_name_map
        )

        res["audio_binary"] = tts(tts_mdl, answer)

        yield res


    # # 流式 / 非流式输出
    # if stream:
    #     id_doc_name_map = build_id_doc_name_map(kbinfos)
    #     print("id_doc_name_map:", id_doc_name_map)
    #     last_ans = ""
    #     answer = ""
    #     async for ans in chat_mdl.async_chat_streamly(prompt + prompt4citation, msg[1:], gen_conf,dialog_id=dialog.id):
    #         if thought:
    #             ans = re.sub(r"^.*</think>", "", ans, flags=re.DOTALL)
    #         answer = ans
    #         delta_ans = ans[len(last_ans):]
    #         if num_tokens_from_string(delta_ans) < 16:
    #             continue
    #         last_ans = answer
    #         # 实时的页面展示
    #         yield {"answer": thought + answer, "reference": {}, "audio_binary": tts(tts_mdl, delta_ans), "suggestions":[]}
    #     delta_ans = answer[len(last_ans):]
    #     if delta_ans:
    #         yield {"answer": thought + answer, "reference": {}, "audio_binary": tts(tts_mdl, delta_ans), "suggestions":[]}
    #     # 最终的交付
    #     final_package = await decorate_answer(thought + answer)
    #     yield final_package
    #     # yield decorate_answer(thought + answer)
    # else:
    #     answer = await chat_mdl.async_chat(prompt + prompt4citation, msg[1:], gen_conf)
    #     user_content = msg[-1].get("content", "[content not available]")
    #     logging.debug("User: {}|Assistant: {}".format(user_content, answer))
    #     res = decorate_answer(answer)
    #     res["audio_binary"] = tts(tts_mdl, answer)
    #     yield res

    # return


async def use_sql(question, field_map, tenant_id, chat_mdl, quota=True, kb_ids=None):
    sys_prompt = """
You are a Database Administrator. You need to check the fields of the following tables based on the user's list of questions and write the SQL corresponding to the last question.
Ensure that:
1. Field names should not start with a digit. If any field name starts with a digit, use double quotes around it.
2. Write only the SQL, no explanations or additional text.
"""
    user_prompt = """
Table name: {};
Table of database fields are as follows:
{}

Question are as follows:
{}
Please write the SQL, only SQL, without any other explanations or text.
""".format(index_name(tenant_id), "\n".join([f"{k}: {v}" for k, v in field_map.items()]), question)
    tried_times = 0

    async def get_table():
        nonlocal sys_prompt, user_prompt, question, tried_times
        sql = await chat_mdl.async_chat(sys_prompt, [{"role": "user", "content": user_prompt}], {"temperature": 0.06})
        sql = re.sub(r"^.*</think>", "", sql, flags=re.DOTALL)
        logging.debug(f"{question} ==> {user_prompt} get SQL: {sql}")
        sql = re.sub(r"[\r\n]+", " ", sql.lower())
        sql = re.sub(r".*select ", "select ", sql.lower())
        sql = re.sub(r" +", " ", sql)
        sql = re.sub(r"([;；]|```).*", "", sql)
        sql = re.sub(r"&", "and", sql)
        if sql[: len("select ")] != "select ":
            return None, None
        if not re.search(r"((sum|avg|max|min)\(|group by )", sql.lower()):
            if sql[: len("select *")] != "select *":
                sql = "select doc_id,docnm_kwd," + sql[6:]
            else:
                flds = []
                for k in field_map.keys():
                    if k in forbidden_select_fields4resume:
                        continue
                    if len(flds) > 11:
                        break
                    flds.append(k)
                sql = "select doc_id,docnm_kwd," + ",".join(flds) + sql[8:]

        if kb_ids:
            kb_filter = "(" + " OR ".join([f"kb_id = '{kb_id}'" for kb_id in kb_ids]) + ")"
            if "where" not in sql.lower():
                o = sql.lower().split("order by")
                if len(o) > 1:
                    sql = o[0] + f" WHERE {kb_filter}  order by " + o[1]
                else:
                    sql += f" WHERE {kb_filter}"
            else:
                sql += f" AND {kb_filter}"

        logging.debug(f"{question} get SQL(refined): {sql}")
        tried_times += 1
        return settings.retriever.sql_retrieval(sql, format="json"), sql

    try:
        tbl, sql = await get_table()
    except Exception as e:
        user_prompt = """
        Table name: {};
        Table of database fields are as follows:
        {}

        Question are as follows:
        {}
        Please write the SQL, only SQL, without any other explanations or text.


        The SQL error you provided last time is as follows:
        {}

        Please correct the error and write SQL again, only SQL, without any other explanations or text.
        """.format(index_name(tenant_id), "\n".join([f"{k}: {v}" for k, v in field_map.items()]), question, e)
        try:
            tbl, sql = await get_table()
        except Exception:
            return

    if len(tbl["rows"]) == 0:
        return None

    docid_idx = set([ii for ii, c in enumerate(tbl["columns"]) if c["name"] == "doc_id"])
    doc_name_idx = set([ii for ii, c in enumerate(tbl["columns"]) if c["name"] == "docnm_kwd"])
    column_idx = [ii for ii in range(len(tbl["columns"])) if ii not in (docid_idx | doc_name_idx)]

    # compose Markdown table
    columns = (
            "|" + "|".join(
        [re.sub(r"(/.*|（[^（）]+）)", "", field_map.get(tbl["columns"][i]["name"], tbl["columns"][i]["name"])) for i in column_idx]) + (
                "|Source|" if docid_idx and docid_idx else "|")
    )

    line = "|" + "|".join(["------" for _ in range(len(column_idx))]) + ("|------|" if docid_idx and docid_idx else "")

    rows = ["|" + "|".join([remove_redundant_spaces(str(r[i])) for i in column_idx]).replace("None", " ") + "|" for r in tbl["rows"]]
    rows = [r for r in rows if re.sub(r"[ |]+", "", r)]
    if quota:
        rows = "\n".join([r + f" ##{ii}$$ |" for ii, r in enumerate(rows)])
    else:
        rows = "\n".join([r + f" ##{ii}$$ |" for ii, r in enumerate(rows)])
    rows = re.sub(r"T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]+Z)?\|", "|", rows)

    if not docid_idx or not doc_name_idx:
        logging.warning("SQL missing field: " + sql)
        return {"answer": "\n".join([columns, line, rows]), "reference": {"chunks": [], "doc_aggs": []}, "prompt": sys_prompt}

    docid_idx = list(docid_idx)[0]
    doc_name_idx = list(doc_name_idx)[0]
    doc_aggs = {}
    for r in tbl["rows"]:
        if r[docid_idx] not in doc_aggs:
            doc_aggs[r[docid_idx]] = {"doc_name": r[doc_name_idx], "count": 0}
        doc_aggs[r[docid_idx]]["count"] += 1
    return {
        "answer": "\n".join([columns, line, rows]),
        "reference": {
            "chunks": [{"doc_id": r[docid_idx], "docnm_kwd": r[doc_name_idx]} for r in tbl["rows"]],
            "doc_aggs": [{"doc_id": did, "doc_name": d["doc_name"], "count": d["count"]} for did, d in doc_aggs.items()],
        },
        "prompt": sys_prompt,
    }

def clean_tts_text(text: str) -> str:
    if not text:
        return ""

    text = text.encode("utf-8", "ignore").decode("utf-8", "ignore")

    text = re.sub(r"[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]", "", text)

    emoji_pattern = re.compile(
        "[\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF"
        "\U00002700-\U000027BF"
        "\U0001F900-\U0001F9FF"
        "\U0001FA70-\U0001FAFF"
        "\U0001FAD0-\U0001FAFF]+",
        flags=re.UNICODE
    )
    text = emoji_pattern.sub("", text)

    text = re.sub(r"\s+", " ", text).strip()

    MAX_LEN = 500
    if len(text) > MAX_LEN:
        text = text[:MAX_LEN]

    return text

def tts(tts_mdl, text):
    if not tts_mdl or not text:
        return None
    text = clean_tts_text(text)
    if not text:
        return None
    bin = b""
    try:
        for chunk in tts_mdl.tts(text):
            bin += chunk
    except Exception as e:
        logging.error(f"TTS failed: {e}, text={text!r}")
        return None
    return binascii.hexlify(bin).decode("utf-8")

async def async_ask(question, kb_ids, tenant_id, chat_llm_name=None, search_config={}):
    doc_ids = search_config.get("doc_ids", [])
    rerank_mdl = None
    kb_ids = search_config.get("kb_ids", kb_ids)
    chat_llm_name = search_config.get("chat_id", chat_llm_name)
    rerank_id = search_config.get("rerank_id", "")
    meta_data_filter = search_config.get("meta_data_filter")

    kbs = KnowledgebaseService.get_by_ids(kb_ids)
    embedding_list = list(set([kb.embd_id for kb in kbs]))

    is_knowledge_graph = all([kb.parser_id == ParserType.KG for kb in kbs])
    retriever = settings.retriever if not is_knowledge_graph else settings.kg_retriever

    embd_mdl = LLMBundle(tenant_id, LLMType.EMBEDDING, embedding_list[0])
    chat_mdl = LLMBundle(tenant_id, LLMType.CHAT, chat_llm_name)
    if rerank_id:
        rerank_mdl = LLMBundle(tenant_id, LLMType.RERANK, rerank_id)
    max_tokens = chat_mdl.max_length
    tenant_ids = list(set([kb.tenant_id for kb in kbs]))

    if meta_data_filter:
        metas = DocumentService.get_meta_by_kbs(kb_ids)
        doc_ids = await apply_meta_data_filter(meta_data_filter, metas, question, chat_mdl, doc_ids)

    kbinfos = retriever.retrieval(
        question=question,
        embd_mdl=embd_mdl,
        tenant_ids=tenant_ids,
        kb_ids=kb_ids,
        page=1,
        page_size=12,
        similarity_threshold=search_config.get("similarity_threshold", 0.1),
        vector_similarity_weight=search_config.get("vector_similarity_weight", 0.3),
        top=search_config.get("top_k", 1024),
        doc_ids=doc_ids,
        aggs=False,
        rerank_mdl=rerank_mdl,
        rank_feature=label_question(question, kbs)
    )

    knowledges = kb_prompt(kbinfos, max_tokens)
    sys_prompt = PROMPT_JINJA_ENV.from_string(ASK_SUMMARY).render(knowledge="\n".join(knowledges))

    msg = [{"role": "user", "content": question}]

    def decorate_answer(answer):
        nonlocal knowledges, kbinfos, sys_prompt
        answer, idx = retriever.insert_citations(answer, [ck["content_ltks"] for ck in kbinfos["chunks"]], [ck["vector"] for ck in kbinfos["chunks"]],
                                                 embd_mdl, tkweight=0.7, vtweight=0.3)
        idx = set([kbinfos["chunks"][int(i)]["doc_id"] for i in idx])
        recall_docs = [d for d in kbinfos["doc_aggs"] if d["doc_id"] in idx]
        if not recall_docs:
            recall_docs = kbinfos["doc_aggs"]
        kbinfos["doc_aggs"] = recall_docs
        refs = deepcopy(kbinfos)
        for c in refs["chunks"]:
            if c.get("vector"):
                del c["vector"]

        if answer.lower().find("invalid key") >= 0 or answer.lower().find("invalid api") >= 0:
            answer += " Please set LLM API-Key in 'User Setting -> Model Providers -> API-Key'"
        refs["chunks"] = chunks_format(refs)
        return {"answer": answer, "reference": refs}

    answer = ""
    async for ans in chat_mdl.async_chat_streamly(sys_prompt, msg, {"temperature": 0.1}):
        answer = ans
        yield {"answer": answer, "reference": {}}
    yield decorate_answer(answer)


async def gen_mindmap(question, kb_ids, tenant_id, search_config={}):
    meta_data_filter = search_config.get("meta_data_filter", {})
    doc_ids = search_config.get("doc_ids", [])
    rerank_id = search_config.get("rerank_id", "")
    rerank_mdl = None
    kbs = KnowledgebaseService.get_by_ids(kb_ids)
    if not kbs:
        return {"error": "No KB selected"}
    embedding_list = list(set([kb.embd_id for kb in kbs]))
    tenant_ids = list(set([kb.tenant_id for kb in kbs]))

    embd_mdl = LLMBundle(tenant_id, LLMType.EMBEDDING, llm_name=embedding_list[0])
    chat_mdl = LLMBundle(tenant_id, LLMType.CHAT, llm_name=search_config.get("chat_id", ""))
    if rerank_id:
        rerank_mdl = LLMBundle(tenant_id, LLMType.RERANK, rerank_id)

    if meta_data_filter:
        metas = DocumentService.get_meta_by_kbs(kb_ids)
        doc_ids = await apply_meta_data_filter(meta_data_filter, metas, question, chat_mdl, doc_ids)

    ranks = settings.retriever.retrieval(
        question=question,
        embd_mdl=embd_mdl,
        tenant_ids=tenant_ids,
        kb_ids=kb_ids,
        page=1,
        page_size=12,
        similarity_threshold=search_config.get("similarity_threshold", 0.2),
        vector_similarity_weight=search_config.get("vector_similarity_weight", 0.3),
        top=search_config.get("top_k", 1024),
        doc_ids=doc_ids,
        aggs=False,
        rerank_mdl=rerank_mdl,
        rank_feature=label_question(question, kbs),
    )
    mindmap = MindMapExtractor(chat_mdl)
    mind_map = await mindmap([c["content_with_weight"] for c in ranks["chunks"]])
    return mind_map.output
