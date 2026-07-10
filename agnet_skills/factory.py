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