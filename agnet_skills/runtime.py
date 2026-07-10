面给你一套完整的 Runtime 方案代码：不用真实 Canvas，而是用 AgentRuntimeContext 作为 Agent 的运行上下文。这样 Chat 页面可以直接初始化和调用 Agent。

这个方案特点：

Chat 页面 / API
  ↓
create_agent_runtime(...)
  ↓
AgentRuntimeContext 替代 Canvas
  ↓
Agent(canvas_like_runtime, agent_id, param)
  ↓
Agent 内部照旧使用 self._canvas.get_tenant_id()
  ↓
但 self._canvas 实际是 runtime，不是真 Canvas
1. 新增文件：agent/runtime/context.py
import asyncio
import base64
import json
import logging
import time
from typing import Any, Optional

try:
    from api.db.services.file_service import FileService
except Exception:
    FileService = None


class AgentRuntimeContext:
    """
    Agent Runtime 上下文。

    用途：
    - 在 Chat 页面或 API 场景替代 Canvas。
    - 保持和 Canvas 类似的方法签名，使现有 Agent/Tool 不用大改。
    - 管理 tenant_id、user_id、files、reference、tool traces 等运行态数据。

    这个类不是图执行器，不负责 downstream/upstream/path 工作流。
    它只提供 Agent 和工具运行所需要的上下文能力。
    """

    def __init__(
        self,
        tenant_id: str,
        user_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        task_id: Optional[str] = None,
        files: Optional[list[dict]] = None,
        reference: Optional[dict] = None,
        variables: Optional[dict] = None,
        globals_: Optional[dict] = None,
    ):
        self._tenant_id = tenant_id
        self.user_id = user_id or tenant_id
        self.conversation_id = conversation_id or ""
        self.task_id = task_id or f"chat-task-{int(time.time() * 1000)}"

        self.files = files or []

        self.reference = reference or {
            "chunks": {},
            "doc_aggs": {}
        }

        self.variables = variables or {}

        self.globals = globals_ or {
            "sys.query": "",
            "sys.user_id": self.user_id,
            "sys.conversation_turns": 0,
            "sys.files": self.files
        }

        # 兼容 Canvas.path
        self.path = []

        # 工具调用轨迹
        self.tool_traces = []

        # 普通运行日志
        self.events = []

        # 组件对象表。Runtime 场景一般不用，但为了兼容 get_component/get_component_obj。
        self.components = {}

        # 是否取消
        self._canceled = False

    # ------------------------------------------------------------------
    # Canvas compatible methods
    # ------------------------------------------------------------------

    def get_tenant_id(self):
        """
        Agent 初始化 LLMBundle 时会调用。
        """
        return self._tenant_id

    def get_component(self, component_id):
        """
        Agent 在 _invoke_async 里会用它判断 downstream 是否有 Message 组件。
        Chat Runtime 不走 Canvas workflow，因此默认返回无 downstream。
        """
        return self.components.get(component_id, {
            "downstream": []
        })

    def get_component_obj(self, component_id):
        """
        Chat Runtime 默认没有画布组件。
        """
        cpn = self.components.get(component_id)
        if not cpn:
            return None
        return cpn.get("obj")

    def register_component(self, component_id: str, obj: Any, downstream=None, upstream=None):
        """
        如果你以后想在 Runtime 中注册一些伪组件，可以使用这个方法。
        """
        self.components[component_id] = {
            "obj": obj,
            "downstream": downstream or [],
            "upstream": upstream or []
        }

    def tool_use_callback(
        self,
        agent_id: str,
        func_name: str,
        params: dict,
        result: Any = None,
        elapsed_time: Any = None
    ):
        """
        Agent 工具调用 callback。

        原 Canvas 会把工具调用日志写 Redis。
        Runtime 场景直接写到 self.tool_traces，Chat API 可返回或落库。
        """
        trace = {
            "agent_id": agent_id,
            "tool_name": func_name,
            "arguments": params,
            "result": result,
            "elapsed_time": elapsed_time,
            "created_at": int(time.time())
        }

        self.tool_traces.append(trace)

        logging.info(f"[AgentRuntime Tool] {func_name} args={params} elapsed={elapsed_time}")

    def get_reference(self):
        """
        Agent citation 逻辑会调用。
        """
        return self.reference or {
            "chunks": {},
            "doc_aggs": {}
        }

    def set_reference(self, reference: dict):
        self.reference = reference or {
            "chunks": {},
            "doc_aggs": {}
        }

    def add_reference(self, chunks: list[object], doc_infos: list[object]):
        """
        兼容 Retrieval 工具可能调用 add_reference 的情况。
        这里尽量保持和 Canvas.add_reference 类似，但做一个简化版。

        如果你的项目里 chunks_format/hash_str2int 可用，也可以替换成原 Canvas 的实现。
        """
        if not self.reference:
            self.reference = {
                "chunks": {},
                "doc_aggs": {}
            }

        if "chunks" not in self.reference:
            self.reference["chunks"] = {}
        if "doc_aggs" not in self.reference:
            self.reference["doc_aggs"] = {}

        for idx, ck in enumerate(chunks or []):
            try:
                if isinstance(ck, dict):
                    cid = ck.get("id") or f"chunk-{len(self.reference['chunks']) + idx}"
                    self.reference["chunks"][cid] = ck
                else:
                    cid = f"chunk-{len(self.reference['chunks']) + idx}"
                    self.reference["chunks"][cid] = {
                        "id": cid,
                        "content": str(ck)
                    }
            except Exception:
                logging.exception("Failed to add reference chunk.")

        for idx, doc in enumerate(doc_infos or []):
            try:
                if isinstance(doc, dict):
                    name = doc.get("doc_name") or doc.get("name") or f"doc-{idx}"
                    self.reference["doc_aggs"][name] = doc
                else:
                    name = f"doc-{idx}"
                    self.reference["doc_aggs"][name] = {
                        "doc_name": name,
                        "content": str(doc)
                    }
            except Exception:
                logging.exception("Failed to add reference doc.")

    def set_global_param(self, **kwargs):
        self.globals.update(kwargs)

    def get_variable_value(self, exp: str) -> Any:
        """
        简化版变量解析。
        支持：
        - sys.query
        - sys.files
        - env.xxx
        """
        exp = exp.strip("{").strip("}").strip()

        if exp in self.globals:
            return self.globals.get(exp)

        if exp.startswith("env."):
            key = exp[4:]
            if key in self.variables:
                val = self.variables[key]
                if isinstance(val, dict) and "value" in val:
                    return val["value"]
                return val
            return ""

        return None

    def get_value_with_variable(self, value: str) -> Any:
        """
        简化版变量替换。
        如果工具组件 Param 里用了 {sys.query} 这类变量，可以处理。
        """
        if not isinstance(value, str):
            return value

        out = value

        for key, val in self.globals.items():
            out = out.replace("{{" + key + "}}", str(val))
            out = out.replace("{" + key + "}", str(val))

        for key, val in self.variables.items():
            raw = val.get("value") if isinstance(val, dict) else val
            out = out.replace("{{env." + key + "}}", str(raw))
            out = out.replace("{env." + key + "}", str(raw))

        return out

    # ------------------------------------------------------------------
    # File compatible methods
    # ------------------------------------------------------------------

    async def get_files_async(self, files: Optional[list[dict]]) -> list[str]:
        """
        兼容 Canvas.get_files_async。

        如果工具需要处理上传文件，可以调用这个。
        这里复用 FileService。
        """
        if not files:
            return []

        if FileService is None:
            logging.warning("FileService is not available. Returning empty file contents.")
            return []

        def image_to_base64(file):
            blob = FileService.get_blob(file["created_by"], file["id"])
            return "data:{};base64,{}".format(
                file["mime_type"],
                base64.b64encode(blob).decode("utf-8")
            )

        loop = asyncio.get_running_loop()
        tasks = []

        for file in files:
            try:
                mime_type = file.get("mime_type", "")
                if "image" in mime_type:
                    tasks.append(loop.run_in_executor(None, image_to_base64, file))
                else:
                    tasks.append(
                        loop.run_in_executor(
                            None,
                            FileService.parse,
                            file["name"],
                            FileService.get_blob(file["created_by"], file["id"]),
                            True,
                            file["created_by"]
                        )
                    )
            except Exception:
                logging.exception(f"Failed to schedule file parsing: {file}")

        if not tasks:
            return []

        return await asyncio.gather(*tasks)

    def get_files(self, files: Optional[list[dict]]) -> list[str]:
        """
        同步 wrapper。
        """
        try:
            loop = asyncio.get_running_loop()
            if loop and loop.is_running():
                return asyncio.run_coroutine_threadsafe(
                    self.get_files_async(files),
                    loop
                ).result()
        except RuntimeError:
            pass

        return asyncio.run(self.get_files_async(files))

    # ------------------------------------------------------------------
    # Cancellation
    # ------------------------------------------------------------------

    def cancel_task(self):
        self._canceled = True
        return True

    def is_canceled(self):
        return self._canceled

    # ------------------------------------------------------------------
    # Logs
    # ------------------------------------------------------------------

    def add_event(self, event: str, data: Any = None):
        self.events.append({
            "event": event,
            "data": data,
            "created_at": int(time.time())
        })

    def get_tool_traces(self):
        return self.tool_traces

    def get_events(self):
        return self.events
2. 新增文件：agent/runtime/factory.py
这个文件负责创建 Agent，不让业务代码到处手动拼 AgentParam。

import os
from typing import Any, Optional

from agent.component.agent import Agent, AgentParam
from agent.runtime.context import AgentRuntimeContext


def build_agent_param(config: dict[str, Any]) -> AgentParam:
    """
    根据后端配置构造 AgentParam。

    config 示例：
    {
        "llm_id": "...",
        "system_prompt": "...",
        "max_rounds": 5,
        "tools": [...],
        "mcp": [],
        "cite": false
    }
    """
    param = AgentParam()

    # -------------------------
    # LLM config
    # -------------------------
    param.llm_id = config["llm_id"]
    param.max_rounds = config.get("max_rounds", 5)
    param.max_retries = config.get("max_retries", 2)
    param.delay_after_error = config.get("delay_after_error", 1)

    # -------------------------
    # Output / citation
    # -------------------------
    param.cite = config.get("cite", False)

    # 如果你的 AgentParam/LLMParam 有 temperature/top_p 等字段，也可以在这里补
    for k in [
        "temperature",
        "top_p",
        "presence_penalty",
        "frequency_penalty",
        "outputs"
    ]:
        if k in config:
            setattr(param, k, config[k])

    # -------------------------
    # Prompt
    # -------------------------
    if "prompts" in config and config["prompts"]:
        param.prompts = config["prompts"]
    else:
        param.prompts = [
            {
                "role": "system",
                "content": config.get(
                    "system_prompt",
                    "You are a helpful assistant."
                )
            }
        ]

    # -------------------------
    # Tools
    # -------------------------
    param.tools = config.get("tools", [])

    # -------------------------
    # MCP
    # -------------------------
    param.mcp = config.get("mcp", [])

    return param


def create_agent_runtime(
    *,
    tenant_id: str,
    llm_id: str,
    agent_id: str = "chat_agent",
    system_prompt: str = "You are a helpful assistant.",
    tools: Optional[list[dict]] = None,
    mcp: Optional[list[dict]] = None,
    skill_root: str = "skills",
    user_id: Optional[str] = None,
    conversation_id: Optional[str] = None,
    task_id: Optional[str] = None,
    files: Optional[list[dict]] = None,
    reference: Optional[dict] = None,
    max_rounds: int = 5,
    max_retries: int = 2,
    delay_after_error: int = 1,
    cite: bool = False,
    extra_config: Optional[dict[str, Any]] = None,
):
    """
    创建一个可以直接在 Chat/API 场景使用的 Agent 和 Runtime。

    返回：
        agent, runtime

    注意：
        API key 不在这里传。
        Agent 通过 tenant_id + llm_id 到 TenantLLMService/LLMBundle 查询模型配置。
    """
    os.environ["AGENT_SKILL_ROOT"] = skill_root

    runtime = AgentRuntimeContext(
        tenant_id=tenant_id,
        user_id=user_id,
        conversation_id=conversation_id,
        task_id=task_id,
        files=files,
        reference=reference
    )

    config = {
        "llm_id": llm_id,
        "system_prompt": system_prompt,
        "max_rounds": max_rounds,
        "max_retries": max_retries,
        "delay_after_error": delay_after_error,
        "cite": cite,
        "tools": tools or [],
        "mcp": mcp or [],
    }

    if extra_config:
        config.update(extra_config)

    param = build_agent_param(config)

    agent = Agent(
        runtime,
        agent_id,
        param
    )

    return agent, runtime
