import logging
import time
import uuid
import json
from pathlib import Path
from functools import partial

from agent.canvas import Canvas
from agnet_skills.agent1 import Agent, AgentParam


from agent.tools.base import LLMToolPluginCallSession
import os
import json
from pathlib import Path

import asyncio
import json
from typing import Any
from rag.app.tag import label_question
from rag.prompts.generator import kb_prompt


class SimpleWriteFileTool:
    """
    一个简单的写文件工具。

    工具名：write_file

    LLM 调用格式大概是：
    {
      "name": "write_file",
      "arguments": {
        "filename": "agent_report.md",
        "content": "xxx"
      }
    }
    """

    def __init__(self, base_dir="./agent_outputs"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._output = {}

    def get_meta(self):
        return {
            "type": "function",
            "function": {
                "name": "write_file",
                "description": "Write text content to a local file.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filename": {
                            "type": "string",
                            "description": "The file name to write, for example report.md or result.txt."
                        },
                        "content": {
                            "type": "string",
                            "description": "The text content to write into the file."
                        }
                    },
                    "required": ["filename", "content"]
                }
            }
        }

    def _safe_path(self, filename: str) -> Path:
        """
        防止模型传 ../../xxx 这种路径。
        只允许写入 base_dir 下面。
        """
        filename = filename.strip() or "output.txt"

        # 去掉危险路径，只保留文件名
        safe_name = Path(filename).name

        if not safe_name:
            safe_name = "output.txt"

        return self.base_dir / safe_name

    async def _invoke_async(self, **kwargs):
        filename = kwargs.get("filename", "output.txt")
        content = kwargs.get("content", "")

        file_path = self._safe_path(filename)

        file_path.write_text(content, encoding="utf-8")

        result = {
            "ok": True,
            "filename": file_path.name,
            "path": str(file_path.resolve()),
            "bytes": len(content.encode("utf-8")),
            "message": f"File written successfully: {file_path.resolve()}"
        }

        self._output["content"] = result
        self._output["json"] = result

        return result

    def _invoke(self, **kwargs):
        return asyncio.run(self._invoke_async(**kwargs))

    async def invoke_async(self, **kwargs):
        return await self._invoke_async(**kwargs)

    def invoke(self, **kwargs):
        return self._invoke(**kwargs)

    def output(self, key=None):
        if key is None:
            return self._output
        return self._output.get(key)

    def set_output(self, key, value):
        self._output[key] = value

    def reset(self):
        self._output = {}

class AgentKnowledgeSearchTool:
    """
    给 Agent 使用的知识库检索工具。

    工具名：search_my_dateset

    LLM 调用格式：
    {
        "name": "search_my_dateset",
        "arguments": {
            "query": "用户问题关键词"
        }
    }
    """

    def __init__(
        self,
        retriever,
        embd_mdl,
        rerank_mdl,
        chat_mdl,
        kbs,
        kb_ids,
        top_n=8,
        top_k=1024,
        similarity_threshold=0.2,
        vector_similarity_weight=0.3,
        doc_ids=None,
        prompt_config=None,
    ):
        self.retriever = retriever
        self.embd_mdl = embd_mdl
        self.rerank_mdl = rerank_mdl
        self.chat_mdl = chat_mdl

        self.kbs = list(kbs or [])
        self.kb_ids = kb_ids or []

        self.top_n = int(top_n or 8)
        self.top_k = int(top_k or 1024)
        self.similarity_threshold = float(similarity_threshold or 0.2)
        self.vector_similarity_weight = float(vector_similarity_weight or 0.3)

        self.doc_ids = doc_ids or []
        self.prompt_config = prompt_config or {}

        self._output = {}

        self.last_kbinfos = {
            "total": 0,
            "chunks": [],
            "doc_aggs": []
        }

    def get_meta(self):
        """
        返回 OpenAI function tools 格式。
        """
        return {
            "type": "function",
            "function": {
                "name": "search_my_dateset",
                "description": (
                    "Search relevant content from selected knowledge bases or datasets. "
                    "Use this tool when the user asks questions that require knowledge base, "
                    "documents, enterprise internal materials, manuals, reports, policies, or files."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": (
                                "The search query. Extract the most important keywords or "
                                "a rewritten question from the user's request."
                            )
                        }
                    },
                    "required": ["query"]
                }
            }
        }

    async def invoke_async(self, **kwargs):
        return await self._invoke_async(**kwargs)

    def invoke(self, **kwargs):
        """
        同步入口。LLMToolPluginCallSession 如果走同步分支，会调用这个。
        注意：这个通常会在 asyncio.to_thread 里执行。
        """
        return asyncio.run(self._invoke_async(**kwargs))

    async def _invoke_async(self, **kwargs):
        query = kwargs.get("query", "")

        if not query or not str(query).strip():
            result = {
                "ok": False,
                "message": "query is empty",
                "total": 0,
                "chunks": [],
                "doc_aggs": []
            }
            self._output["json"] = result
            self._output["content"] = result
            self._output["reference"] = {
                "total": 0,
                "chunks": [],
                "doc_aggs": []
            }
            return result

        query = str(query).strip()

        if not self.kbs:
            result = {
                "ok": False,
                "message": "No knowledge base is selected.",
                "total": 0,
                "chunks": [],
                "doc_aggs": []
            }
            self._output["json"] = result
            self._output["content"] = result
            self._output["reference"] = {
                "total": 0,
                "chunks": [],
                "doc_aggs": []
            }
            return result

        tenant_ids = list(set([kb.tenant_id for kb in self.kbs]))

        # 1. 执行检索
        kbinfos = await asyncio.to_thread(
            self.retriever.retrieval,
            query,
            self.embd_mdl,
            tenant_ids,
            self.kb_ids,
            1,
            self.top_n,
            self.similarity_threshold,
            self.vector_similarity_weight,
            doc_ids=self.doc_ids,
            top=self.top_k,
            aggs=True,
            rerank_mdl=self.rerank_mdl,
            rank_feature=label_question(query, self.kbs),
        )

        if not kbinfos:
            kbinfos = {
                "total": 0,
                "chunks": [],
                "doc_aggs": []
            }

        chunks = kbinfos.get("chunks", []) or []

        # 2. TOC 增强
        if self.prompt_config.get("toc_enhance"):
            cks = await asyncio.to_thread(
                self.retriever.retrieval_by_toc,
                query,
                chunks,
                tenant_ids,
                self.chat_mdl,
                self.top_n
            )

            if cks:
                chunks = cks

        # 3. 子块增强
        chunks = await asyncio.to_thread(
            self.retriever.retrieval_by_children,
            chunks,
            tenant_ids
        )

        # 4. KG 检索，可选
        if self.prompt_config.get("use_kg"):
            from common import settings
            from api.db.services.llm_service import LLMBundle
            from common.constants import LLMType

            try:
                ck = await asyncio.to_thread(
                    settings.kg_retriever.retrieval,
                    query,
                    tenant_ids,
                    self.kb_ids,
                    self.embd_mdl,
                    LLMBundle(self.kbs[0].tenant_id, LLMType.CHAT)
                )

                if ck and ck.get("content_with_weight"):
                    ck["content"] = ck["content_with_weight"]
                    ck.pop("content_with_weight", None)
                    chunks.insert(0, ck)
            except Exception as e:
                # KG 失败不影响主检索
                print(f"KG retrieval failed: {e}")

        # 5. 清理 chunk，避免返回 vector 太大
        safe_chunks = []

        for ck in chunks:
            ck2 = dict(ck)
            ck2.pop("vector", None)
            safe_chunks.append(ck2)

        kbinfos["chunks"] = safe_chunks
        kbinfos["total"] = kbinfos.get("total", len(safe_chunks))
        kbinfos["doc_aggs"] = kbinfos.get("doc_aggs", []) or []

        self.last_kbinfos = {
            "total": kbinfos["total"],
            "chunks": safe_chunks,
            "doc_aggs": kbinfos["doc_aggs"]
        }

        # 6. 如果没有召回
        if not safe_chunks:
            empty_response = self.prompt_config.get(
                "empty_response",
                "知识库中未找到您要的答案！"
            )

            result = {
                "ok": False,
                "message": empty_response,
                "total": 0,
                "chunks": [],
                "doc_aggs": []
            }

            self._output["json"] = result
            self._output["content"] = empty_response
            self._output["reference"] = self.last_kbinfos

            return result

        # 7. 格式化成 Agent 易读的知识库上下文
        formalized_content = "\n".join(
            kb_prompt(
                self.last_kbinfos,
                200000,
                True
            )
        )

        # 8. 返回给 Agent 的内容
        # 注意：不要把所有原始字段都给模型，否则 token 很大。
        simplified_chunks = []

        for idx, ck in enumerate(safe_chunks[: self.top_n]):
            simplified_chunks.append({
                "id": idx,
                "content": (
                    ck.get("content")
                    or ck.get("content_ltks")
                    or ck.get("content_with_weight")
                    or ""
                ),
                "doc_id": ck.get("doc_id"),
                "doc_name": (
                    ck.get("doc_name")
                    or ck.get("document_name")
                    or ck.get("filename")
                    or ck.get("file_name")
                )
            })

        result = {
            "ok": True,
            "query": query,
            "total": self.last_kbinfos["total"],
            "knowledge": formalized_content,
            "chunks": simplified_chunks,
            "doc_aggs": self.last_kbinfos["doc_aggs"]
        }

        self._output["json"] = result
        self._output["content"] = formalized_content
        self._output["reference"] = self.last_kbinfos

        return result

    def output(self, key=None):
        if key is None:
            return self._output
        return self._output.get(key)

    def set_output(self, key, value):
        self._output[key] = value

    def reset(self):
        self._output = {}
        self.last_kbinfos = {
            "total": 0,
            "chunks": [],
            "doc_aggs": []
        }

def prepare_agent_skills():
    """
    准备 Agent skills 目录。

    skills/
      index.md
      knowledge_search/
        manifest.json
        skill.md
      file_writer/
        manifest.json
        skill.md
    """

    skill_root = Path("./skills")
    skill_root.mkdir(parents=True, exist_ok=True)

    os.environ["AGENT_SKILL_ROOT"] = str(skill_root)

    # Base Phase 可见的技能索引
    (skill_root / "index.md").write_text(
        """# Available Skills

## knowledge_search

Use this skill when the user asks a question that requires searching knowledge bases, datasets, documents, enterprise files, reports, manuals, policies, or internal materials.

## file_writer

Use this skill when the user asks to create, write, save, or export a text file, markdown file, report, document, note, or plan.
""",
        encoding="utf-8"
    )

    # knowledge_search skill
    knowledge_dir = skill_root / "knowledge_search"
    knowledge_dir.mkdir(parents=True, exist_ok=True)

    (knowledge_dir / "manifest.json").write_text(
        json.dumps(
            {
                "name": "knowledge_search",
                "description": "Search selected knowledge bases and datasets.",
                "tools": [
                    "search_my_dateset"
                ]
            },
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    (knowledge_dir / "skill.md").write_text(
        """# Knowledge Search Skill

You specialize in searching knowledge bases and datasets.

Procedure:

1. Understand the user's question.
2. Extract a concise and accurate search query.
3. Call `search_my_dateset` with:
   - `query`
4. Read the returned `knowledge` and `chunks` carefully.
5. Answer based only on the retrieved knowledge.
6. If the retrieved content is empty, insufficient, or irrelevant, say exactly:
   知识库中未找到您要的答案！
7. After completing the knowledge-based answer, call `complete_task`.

Rules:

- Do not fabricate facts.
- Do not answer from general knowledge when the user asks based on the knowledge base.
- Use Chinese if the user asks in Chinese.
- Give detailed answers if the retrieved knowledge contains details.
""",
        encoding="utf-8"
    )

    # file_writer skill
    file_dir = skill_root / "file_writer"
    file_dir.mkdir(parents=True, exist_ok=True)

    (file_dir / "manifest.json").write_text(
        json.dumps(
            {
                "name": "file_writer",
                "description": "Create and write text files.",
                "tools": [
                    "write_file"
                ]
            },
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    (file_dir / "skill.md").write_text(
        """# File Writer Skill

You specialize in creating and writing text files.

Procedure:

1. Understand what file the user wants.
2. Decide a suitable filename if the user did not provide one.
3. Prepare high-quality text content.
4. Call `write_file` with:
   - `filename`
   - `content`
5. After the file has been written, call `complete_task`.

Rules:

- Use markdown format when writing reports or technical plans.
- If the user asks for Chinese content, write in Chinese.
- Do not claim the file was written unless the `write_file` tool succeeds.
- After tool success, summarize the saved file path and content briefly.
""",
        encoding="utf-8"
    )

def build_agent_step_display(event: dict) -> str:
    name = event.get("name")
    args = event.get("arguments") or {}
    result = event.get("result")
    elapsed_time = event.get("elapsed_time")

    def _result_get(key, default=""):
        if isinstance(result, dict):
            return result.get(key, default)
        return default

    def _cost_text():
        if elapsed_time is not None:
            return f"，耗时 {elapsed_time:.2f}s"
        return ""

    def _short_text(text, max_len=4000):
        text = "" if text is None else str(text)
        if len(text) > max_len:
            return text[:max_len] + "\n...内容过长，已截断..."
        return text

    if name == "base_next_step":
        response = _result_get("response", "")
        step = _result_get("step", "")

        text = f"Agent 正在 Base Phase 分析任务，并选择下一步 Skill{_cost_text()}。\n"

        if response:
            text += f"\nBase Phase 第 {step} 轮模型输出：\n```json\n{_short_text(response)}\n```\n"

        return text
    if name == "before_read_skill":
        skill_name = args.get("skill_name", "")
        reason = args.get("reason", "")

        text = f"Agent 准备读取 Skill：{skill_name or 'unknown'}。\n"

        if reason:
            text += f"读取原因：{reason}\n"

        return text
    if name == "read_skill":
        skill = ""
        reason = ""
        description = ""
        tools = []

        try:
            if isinstance(result, dict):
                skill = result.get("skill") or ""
                reason = result.get("reason") or ""
                description = result.get("description") or ""
                tools = result.get("tools") or []
        except Exception:
            pass

        text = f"Agent 已读取 Skill：{skill or 'unknown'}。\n"

        if description:
            text += f"Skill 描述：{description}\n"

        if tools:
            text += f"Skill 可用工具：{tools}\n"

        if reason:
            text += f"选择原因：{reason}\n"

        return text
    if name == "read_skill_error":
        skill_name = args.get("skill_name", "")
        error = ""

        try:
            if isinstance(result, dict):
                error = result.get("error") or ""
        except Exception:
            pass

        text = f"Agent 读取 Skill 失败：{skill_name or 'unknown'}。\n"

        if error:
            text += f"错误信息：{error}\n"

        return text

    if name == "enter_skill_phase":
        skill = ""
        tools = []
        missing_tools = []

        try:
            if isinstance(result, dict):
                skill = result.get("skill") or ""
                tools = result.get("tools") or []
                missing_tools = result.get("missing_tools") or []
        except Exception:
            skill = ""

        text = f"Agent 进入 Skill 阶段：{skill or 'unknown'}。\n"

        if tools:
            text += f"当前 Skill 可用工具：{tools}\n"

        if missing_tools:
            text += f"缺失工具：{missing_tools}\n"

        return text

    if name == "skill_next_step":
        skill = _result_get("skill", "unknown")
        response = _result_get("response", "")
        step = _result_get("step", "")

        text = f"Agent 正在 Skill `{skill or 'unknown'}` 中决定下一步工具调用{_cost_text()}。\n"

        if response:
            text += f"\nSkill `{skill}` 第 {step} 轮模型输出：\n```json\n{_short_text(response)}\n```\n"

        return text

    if name == "before_skill_tool_call":
        skill = args.get("skill", "")
        tool = args.get("tool", "")
        tool_args = args.get("arguments", {})

        try:
            tool_args_text = json.dumps(tool_args, ensure_ascii=False, indent=2)
        except Exception:
            tool_args_text = str(tool_args)

        return (
            f"Agent 准备在 Skill `{skill or 'unknown'}` 中调用工具 `{tool or 'unknown'}`。\n"
            f"\n工具参数：\n```json\n{_short_text(tool_args_text)}\n```\n"
        )

    if name == "search_my_dateset":
        query = args.get("query", "")
        return f"Agent 正在检索知识库：{query}\n"

    if name == "write_file":
        filename = args.get("filename", "")
        return f"Agent 正在写入文件：{filename}\n"

    if name == "skill_tool_call":
        tool = args.get("tool", "")
        skill = args.get("skill", "")
        tool_args = args.get("arguments", {})

        text = f"Agent 在 Skill `{skill}` 中完成工具 `{tool}` 调用{_cost_text()}。\n"

        try:
            tool_args_text = json.dumps(tool_args, ensure_ascii=False, indent=2)
        except Exception:
            tool_args_text = str(tool_args)

        text += f"\n工具参数：\n```json\n{_short_text(tool_args_text)}\n```\n"

        if isinstance(result, dict):
            if tool == "write_file":
                text += "\n工具结果：\n"
                text += f"- ok: {result.get('ok')}\n"
                text += f"- filename: {result.get('filename')}\n"
                text += f"- path: {result.get('path')}\n"
                text += f"- bytes: {result.get('bytes')}\n"

            elif tool == "search_my_dateset":
                text += "\n工具结果：\n"
                text += f"- ok: {result.get('ok')}\n"
                text += f"- total: {result.get('total')}\n"
                if result.get("message"):
                    text += f"- message: {result.get('message')}\n"

            else:
                try:
                    result_text = json.dumps(result, ensure_ascii=False, indent=2)
                except Exception:
                    result_text = str(result)

                text += f"\n工具结果：\n```json\n{_short_text(result_text)}\n```\n"
        else:
            text += f"\n工具结果：\n{_short_text(result)}\n"

        return text

    if name == "skill_reflection":
        skill = ""
        reflection = ""

        try:
            if isinstance(result, dict):
                skill = result.get("skill") or ""
                reflection = result.get("reflection") or ""
        except Exception:
            pass

        text = f"Agent 正在根据工具结果进行反思和整理{_cost_text()}。\n"

        if skill:
            text += f"当前 Skill：`{skill}`\n"

        if reflection:
            text += f"\n模型反思输出：\n{_short_text(reflection)}\n"

        return text

    if name == "skill_summary":
        skill = ""
        summary = ""

        try:
            if isinstance(result, dict):
                skill = result.get("skill") or ""
                summary = result.get("summary") or ""
        except Exception:
            pass

        text = f"Agent 已总结 Skill `{skill or 'unknown'}` 的执行结果{_cost_text()}。\n"

        if summary:
            text += f"\nSkill 总结：\n{_short_text(summary)}\n"

        return text

    if name == "skill_no_tool_answer":
        skill = ""
        answer = ""

        try:
            if isinstance(result, dict):
                skill = result.get("skill") or ""
                answer = result.get("answer") or ""
        except Exception:
            pass

        text = f"Agent 使用无工具 Skill `{skill or 'unknown'}` 生成结果{_cost_text()}。\n"

        if answer:
            text += f"\n模型输出：\n{_short_text(answer)}\n"

        return text

    return f"Agent 执行步骤：{name}\n"

async def async_chat_agent_mode(
    dialog,
    messages,
    questions,
    attachments,
    attachments_text,
    kbs,
    embd_mdl,
    rerank_mdl,
    chat_mdl,
    retriever,
    prompt_config,
    stream=True,
    **kwargs
):
    # 1. 准备 skills
    prepare_agent_skills()

    user_prompt = questions[-1] if questions else messages[-1]["content"]

    conversation_id = kwargs.get("conversation_id") or str(uuid.uuid4())
    message_id = kwargs.get("message_id") or messages[-1].get("id") or str(uuid.uuid4())

    def build_canvas_history(messages):
        history = []

        for m in messages:
            role = m.get("role")
            content = m.get("content", "")

            if role not in ["user", "assistant"]:
                continue

            if not content:
                continue

            # Canvas.get_history() 里面是：for role, obj in self.history
            # 所以这里必须是二元列表
            history.append([
                role,
                {
                    "content": content
                }
            ])

        return history
    # 2. 创建 Canvas
    dsl = {
        "components": {},
        "history": [],
        "path": [],
        "retrieval": [
            {
                "chunks": {},
                "doc_aggs": {}
            }
        ],
        "globals": {
            "sys.query": user_prompt,
            "sys.user_id": dialog.tenant_id,
            "sys.conversation_turns": len(messages),
            "sys.files": []
        }
    }

    canvas = Canvas(
        dsl=json.dumps(dsl, ensure_ascii=False),
        tenant_id=dialog.tenant_id
    )

    canvas.task_id = conversation_id
    canvas.message_id = message_id

    # 3. Agent 参数
    param = AgentParam()

    default_agent_prompt = """
你是一个企业知识库 Agent。

你可以使用以下 Skill：

1. knowledge_search
   当用户问题需要知识库、数据集、文档、企业内部资料、报告、制度、手册等内容时，使用该 Skill。
   该 Skill 可以调用 search_my_dateset 工具。

2. file_writer
   当用户要求保存、导出、生成 markdown、报告、方案、文档或指定文件名时，使用该 Skill。
   该 Skill 可以调用 write_file 工具。

规则：
- 如果用户问题需要知识库依据，必须先使用 knowledge_search。
- 回答必须基于 search_my_dateset 返回的知识库内容，不要编造。
- 如果知识库结果不足、为空或无关，必须回答：知识库中未找到您要的答案！
- 如果用户要求保存文件，需要先生成内容，再使用 file_writer 保存。
- 最终回答需要简洁说明完成情况。
"""

    param.sys_prompt = prompt_config.get("agent_system") or default_agent_prompt
    param.llm_id = dialog.llm_id
    param.tenant_id = dialog.tenant_id
    param.max_retries = 1
    param.delay_after_error = 1
    param.max_rounds = 8

    param.tools = []
    param.mcp = []
    param.prompts = [
        {
            "role": "user",
            "content": "{{sys.query}}"
        }
    ]

    # 4. 创建 Agent
    agent = Agent(
        canvas=canvas,
        id="agent_0",
        param=param
    )

    # 5. 注入知识库检索工具
    search_tool = AgentKnowledgeSearchTool(
        retriever=retriever,
        embd_mdl=embd_mdl,
        rerank_mdl=rerank_mdl,
        chat_mdl=chat_mdl,
        kbs=kbs,
        kb_ids=dialog.kb_ids,
        top_n=dialog.top_n,
        top_k=dialog.top_k,
        similarity_threshold=dialog.similarity_threshold,
        vector_similarity_weight=dialog.vector_similarity_weight,
        doc_ids=attachments,
        prompt_config=prompt_config,
    )

    # 6. 注入写文件工具
    output_dir = Path("./agent_outputs") / str(dialog.tenant_id) / str(conversation_id)
    output_dir.mkdir(parents=True, exist_ok=True)

    write_file_tool = SimpleWriteFileTool(base_dir=str(output_dir))

    agent.tools["search_my_dateset"] = search_tool
    agent.tools["write_file"] = write_file_tool

    agent.tool_meta = [
        search_tool.get_meta(),
        write_file_tool.get_meta()
    ]

    # # 7. 绑定工具调用日志
    # agent.callback = partial(agent._canvas.tool_use_callback, agent._id)
    #
    # agent.toolcall_session = LLMToolPluginCallSession(
    #     agent.tools,
    #     agent.callback
    # )
    tool_event_queue = asyncio.Queue()

    def stream_tool_callback(func_name, params, result, elapsed_time=None):
        """
        工具/Agent内部事件回调：
        1. 保留原来的 canvas Redis 日志
        2. 同时放入队列，给前端流式展示
        """
        try:
            agent._canvas.tool_use_callback(
                agent._id,
                func_name,
                params,
                result,
                elapsed_time
            )
        except Exception as e:
            logging.exception(e)

        try:
            tool_event_queue.put_nowait({
                "type": "agent_step",
                "name": func_name,
                "arguments": params,
                "result": result,
                "elapsed_time": elapsed_time
            })
        except Exception as e:
            logging.exception(e)

    agent.callback = stream_tool_callback

    agent.toolcall_session = LLMToolPluginCallSession(
        agent.tools,
        agent.callback
    )

    # 8. 构造上下文
    context = ""

    if attachments_text:
        context += "\n\n用户上传文件内容：\n" + attachments_text

    context += f"""

当前用户问题：
{user_prompt}

请根据任务需要选择合适的 Skill：
- 如果需要查询知识库，使用 knowledge_search。
- 如果需要保存文件，使用 file_writer。
"""

    # # 9. 执行 Agent
    # result = await agent._invoke_async(
    #     user_prompt=user_prompt,
    #     reasoning="",
    #     context=context
    # )
    #
    # answer = result or agent.output("content") or ""

    # 9. 流式执行 Agent
    answer = ""

    async def run_agent_stream():
        """
        后台运行 Agent 流式生成，把 answer delta 也写入同一个队列。
        """
        nonlocal answer

        try:
            async for delta in agent._invoke_stream_async(
                    user_prompt=user_prompt,
                    reasoning="",
                    context=context
            ):
                if not delta:
                    continue

                answer += delta

                await tool_event_queue.put({
                    "type": "answer_delta",
                    "delta": delta,
                    "answer": answer
                })

            await tool_event_queue.put({
                "type": "agent_done",
                "answer": answer or agent.output("content") or ""
            })

        except Exception as e:
            logging.exception(e)
            await tool_event_queue.put({
                "type": "agent_error",
                "error": str(e)
            })

    if stream:
        # think 用来累计 Skill / 工具调用过程日志
        # answer 用来累计正式回答
        think = ""

        def build_think_answer():
            """
            返回给前端的累计 answer：
            <think>
            Agent 过程日志
            </think>

            正式回答
            """
            if think.strip():
                return f"<think>\n{think.strip()}\n</think>\n\n{answer}"
            return answer

        start_text = "Agent 已启动，正在分析任务...\n"
        think += start_text

        yield {
            "answer": build_think_answer(),
            "reference": {},
            "audio_binary": None,
            "suggestions": [],
            "agent_event": {
                "type": "agent_start",
                "display": start_text
            }
        }

        agent_task = asyncio.create_task(run_agent_stream())

        while True:
            event = await tool_event_queue.get()

            event_type = event.get("type")

            if event_type == "answer_delta":
                # 正式回答流，只更新 answer
                answer = event.get("answer", "")

                yield {
                    "answer": build_think_answer(),
                    "reference": {},
                    "audio_binary": None,
                    "suggestions": [],
                    "agent_event": {
                        "type": "answer_delta",
                        "delta": event.get("delta", "")
                    }
                }

            elif event_type == "agent_step":
                step_name = event.get("name")

                # Skill / 工具调用过程日志写入 think
                display_text = build_agent_step_display(event)

                if display_text:
                    think += display_text
                    if not think.endswith("\n"):
                        think += "\n"

                yield {
                    "answer": build_think_answer(),
                    "reference": {},
                    "audio_binary": None,
                    "suggestions": [],
                    "agent_event": {
                        "type": "agent_step",
                        "name": step_name,
                        "arguments": event.get("arguments"),
                        "elapsed_time": event.get("elapsed_time"),
                        "display": display_text
                    }
                }

            elif event_type == "agent_error":
                err_msg = event.get("error", "")
                err_text = "**ERROR**: " + err_msg

                think += "\n" + err_text + "\n"

                yield {
                    "answer": build_think_answer(),
                    "reference": {},
                    "audio_binary": None,
                    "suggestions": [],
                    "agent_event": {
                        "type": "agent_error",
                        "error": err_msg,
                        "display": err_text
                    }
                }

                break

            elif event_type == "agent_done":
                answer = event.get("answer", "") or agent.output("content") or ""
                break

        await agent_task

    else:
        result = await agent._invoke_async(
            user_prompt=user_prompt,
            reasoning="",
            context=context
        )

        answer = result or agent.output("content") or ""

    # 10. 引用信息
    refs = search_tool.output("reference") or {
        "total": 0,
        "chunks": [],
        "doc_aggs": []
    }

    safe_refs = {
        "total": refs.get("total", 0),
        "chunks": [],
        "doc_aggs": refs.get("doc_aggs", [])
    }

    for ck in refs.get("chunks", []):
        ck2 = dict(ck)
        ck2.pop("vector", None)
        safe_refs["chunks"].append(ck2)

    if stream and think.strip():
        final_answer = f"<think>\n{think.strip()}\n</think>\n\n{answer}"
    else:
        final_answer = answer

    if stream and think.strip():
        final_answer = f"<think>\n{think.strip()}\n</think>\n\n{answer}"
    else:
        final_answer = answer

    final = {
        "answer": final_answer,
        "reference": safe_refs,
        "prompt": "",
        "created_at": time.time(),
        "suggestions": [],
        "use_tools": agent.output("use_tools"),
        "output_dir": str(output_dir.resolve()),
        "file": write_file_tool.output("json")
    }

    yield final

if __name__ == '__main__':
    prepare_agent_skills()