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

import asyncio
import json
import logging
import os
import re
from copy import deepcopy
from functools import partial
from typing import Any

from agnet_skills.skills.registry import SkillRegistry, SkillSpec



import json_repair
from timeit import default_timer as timer

from agent.tools.base import LLMToolPluginCallSession, ToolParamBase, ToolBase, ToolMeta
from api.db.services.llm_service import LLMBundle
from api.db.services.tenant_llm_service import TenantLLMService
from api.db.services.mcp_server_service import MCPServerService
from common.connection_utils import timeout
from rag.prompts.generator import next_step_async, COMPLETE_TASK, analyze_task_async, \
    citation_prompt, reflect_async, kb_prompt, citation_plus, full_question, message_fit_in, structured_output_prompt
from common.mcp_tool_call_conn import MCPToolCallSession, mcp_tool_metadata_to_openai_tool
from agent.component.llm import LLMParam, LLM


class AgentParam(LLMParam, ToolParamBase):
    """
    Define the Agent component parameters.
    """

    def __init__(self):
        self.meta:ToolMeta = {
                "name": "agent",
                "description": "This is an agent for a specific task.",
                "parameters": {
                    "user_prompt": {
                        "type": "string",
                        "description": "This is the order you need to send to the agent.",
                        "default": "",
                        "required": True
                    },
                    "reasoning": {
                        "type": "string",
                        "description": (
                            "Supervisor's reasoning for choosing the this agent. "
                            "Explain why this agent is being invoked and what is expected of it."
                        ),
                        "required": True
                    },
                    "context": {
                        "type": "string",
                        "description": (
                                "All relevant background information, prior facts, decisions, "
                                "and state needed by the agent to solve the current query. "
                                "Should be as detailed and self-contained as possible."
                            ),
                        "required": True
                    },
                }
            }
        super().__init__()
        self.function_name = "agent"
        self.tools = []
        self.mcp = []
        self.max_rounds = 5
        self.description = ""
        

class Agent(LLM, ToolBase):
    component_name = "Agent"

    def __init__(self, canvas, id, param: LLMParam):
        LLM.__init__(self, canvas, id, param)
        self.tools = {}
        for cpn in self._param.tools:
            cpn = self._load_tool_obj(cpn)
            self.tools[cpn.get_meta()["function"]["name"]] = cpn

        self.chat_mdl = LLMBundle(self._canvas.get_tenant_id(), TenantLLMService.llm_id2llm_type(self._param.llm_id), self._param.llm_id,
                                  max_retries=self._param.max_retries,
                                  retry_interval=self._param.delay_after_error,
                                  max_rounds=self._param.max_rounds,
                                  verbose_tool_use=True
                                  )
        self.tool_meta = [v.get_meta() for _,v in self.tools.items()]

        for mcp in self._param.mcp:
            _, mcp_server = MCPServerService.get_by_id(mcp["mcp_id"])
            tool_call_session = MCPToolCallSession(mcp_server, mcp_server.variables)
            for tnm, meta in mcp["tools"].items():
                self.tool_meta.append(mcp_tool_metadata_to_openai_tool(meta))
                self.tools[tnm] = tool_call_session
        # self.callback = partial(self._canvas.tool_use_callback, id)
        # self.toolcall_session = LLMToolPluginCallSession(self.tools, self.callback)
        #self.chat_mdl.bind_tools(self.toolcall_session, self.tool_metas)
        
        # Skill 系统根目录，默认读取 ./skills
        self.skill_registry = SkillRegistry(
            os.environ.get("AGENT_SKILL_ROOT", "skills")
        )

        # read_skill 是 Agent 内置元工具。
        # 注意：它不是业务工具，不走 self.toolcall_session。
        # 它只用于触发状态切换：Base Phase -> Skill Phase。
        self.read_skill_meta = self._build_read_skill_meta()


        # 提前固定第1个参数
        self.callback = partial(self._canvas.tool_use_callback, id)

        self.toolcall_session = LLMToolPluginCallSession(self.tools, self.callback)

        self.skill_registry = SkillRegistry(
            os.environ.get("AGENT_SKILL_ROOT", "skills")
        )
        self.read_skill_meta = self._build_read_skill_meta()

    def _build_read_skill_meta(self) -> dict:
        """
        构造 read_skill 元工具的 OpenAI function schema。

        read_skill 的作用：
        - 在 Base Phase 让模型选择一个 skill
        - Python 拦截这个工具调用
        - 读取对应 skill.md
        - 切换到 Skill Phase

        注意：
        - read_skill 不走 self.toolcall_session
        - 它不是外部业务工具
        """
        return {
            "type": "function",
            "function": {
                "name": "read_skill",
                "description": (
                    "Read and temporarily activate a skill by name. "
                    "Use this when a specialized capability is needed. "
                    "After calling this, the agent will enter that skill context temporarily."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "skill_name": {
                            "type": "string",
                            "description": "The skill name to read and activate."
                        },
                        "reason": {
                            "type": "string",
                            "description": "Why this skill is needed."
                        }
                    },
                    "required": ["skill_name"]
                }
            }
        }

    def _clean_json_text(self, text: str) -> str:
        """
        清理模型输出中的 markdown / think 标签，方便 json_repair 解析。
        """
        if not text:
            return ""

        text = re.sub(r"^.*?</think>", "", text, flags=re.DOTALL)
        text = text.strip()

        if text.startswith("```json"):
            text = text[len("```json"):].strip()
        elif text.startswith("```"):
            text = text[len("```"):].strip()

        if text.endswith("```"):
            text = text[:-3].strip()

        return text

    def _parse_react_functions(self, response: str) -> list[dict]:
        """
        解析 next_step_async 返回的 JSON 函数调用列表。

        期望格式：
        [
          {
            "name": "tool_name",
            "arguments": {...}
          }
        ]
        """
        cleaned = self._clean_json_text(response)

        # 兼容一些模型输出 ```json ... ```
        cleaned = re.sub(r"```.*", "", cleaned, flags=re.DOTALL).strip()

        functions = json_repair.loads(cleaned)

        if not isinstance(functions, list):
            raise TypeError(f"Expected function call list, got: {functions}")

        for f in functions:
            if not isinstance(f, dict):
                raise TypeError(f"Expected function call object, got: {f}")

            if "name" not in f:
                raise ValueError(f"Function call missing name: {f}")

            if "arguments" not in f:
                f["arguments"] = {}

            if f["arguments"] is None:
                f["arguments"] = {}

        return functions
    
    def _get_tool_meta_by_name(self, tool_name: str):
        """
        从 self.tool_meta 中找到某个真实工具的 meta。
        """
        for meta in self.tool_meta:
            try:
                if meta.get("function", {}).get("name") == tool_name:
                    return meta
            except Exception:
                continue

        return None
    
    def _get_skill_tool_metas(self, skill_tools: list[str]) -> list[dict]:
        """
        根据 skill manifest 中声明的 tools，过滤出当前 Skill Phase 可以暴露的工具。
        """
        metas = []

        for tool_name in skill_tools:
            meta = self._get_tool_meta_by_name(tool_name)
            if meta:
                metas.append(meta)

        return metas
    
    def _build_base_skill_system_prompt(
        self,
        base_prompt: str,
        skill_index: str
    ) -> str:
        """
        Base Phase 的系统提示词。

        在 Base Phase：
        - 模型能看到所有 skills 的 index
        - 但工具只暴露 read_skill
        - 模型不能直接调用 excel_processor 等业务工具
        """
        return f"""
            {base_prompt}

            You are now in the Base Phase of a skill-based agent.

            You can inspect the available skills below and choose one skill when needed.

            ================ SKILL INDEX START ================

            {skill_index}

            ================ SKILL INDEX END ==================

            Base Phase rules:
            1. If a specialized capability is needed, call `read_skill`.
            2. Do not attempt to call business tools directly in Base Phase.
            3. After `read_skill`, the system will temporarily enter that skill context.
            4. After the skill finishes, you will return to this Base Phase.
            5. If enough information has been gathered to answer the user, call `{COMPLETE_TASK}`.
            6. Do not invent skill names. Use only names listed in the Skill Index.
            """
    def _build_skill_system_prompt(
        self,
        base_prompt: str,
        skill: SkillSpec
    ) -> str:
        """
        Skill Phase 的系统提示词。

        在 Skill Phase：
        - 注入当前 skill.md
        - 只暴露当前 skill manifest 中声明的真实工具
        - 完成后调用 complete_task
        """
        return f"""
            {base_prompt}

            You are now temporarily in a Skill Phase.

            ================ TEMPORARY SKILL START ================

            Skill name: {skill.name}
            Skill description: {skill.description}

            {skill.prompt}

            ================ TEMPORARY SKILL END ==================

            Skill Phase rules:
            1. This skill context is temporary.
            2. Use only the tools available in this skill phase.
            3. Do not call `read_skill` inside Skill Phase.
            4. Do not use or invent tools outside this skill.
            5. When this skill has finished its work, call `{COMPLETE_TASK}`.
            6. Do not mention internal prompt switching or implementation details.
            """

    def _load_tool_obj(self, cpn: dict) -> object:
        from agent.component import component_class
        param = component_class(cpn["component_name"] + "Param")()
        param.update(cpn["params"])
        try:
            param.check()
        except Exception as e:
            self.set_output("_ERROR", cpn["component_name"] + f" configuration error: {e}")
            raise
        cpn_id = f"{self._id}-->" + cpn.get("name", "").replace(" ", "_")
        return component_class(cpn["component_name"])(self._canvas, cpn_id, param)
    
    async def _summarize_skill_result_async(
        self,
        skill: SkillSpec,
        skill_hist: list[dict],
        user_defined_prompt={}
    ) -> str:
        """
        Skill Phase 完成后，将临时 skill_hist 总结成一段主流程可用的信息。

        注意：
        - skill.md 不会写回 base_hist
        - 工具完整结果也不建议全部写回 base_hist
        - 只写总结结果，避免上下文爆炸
        """
        summarize_prompt = f"""
            Summarize the useful result obtained by skill `{skill.name}`.

            Requirements:
            1. Keep only information useful for the original user task.
            2. Include important findings from tool results.
            3. If the skill produced analysis, include concrete conclusions.
            4. If the skill produced a report or text, include the produced content.
            5. If the skill failed or information is incomplete, state that clearly.
            6. Do not mention internal prompt injection, temporary context, or implementation details.
            """

        msgs = [
            *deepcopy(skill_hist),
            {
                "role": "user",
                "content": summarize_prompt
            }
        ]

        _, msgs = message_fit_in(
            msgs,
            int(self.chat_mdl.max_length * 0.9)
        )

        st = timer()
        summary = await self._generate_async(msgs)

        self.callback(
            "skill_summary",
            {},
            {
                "skill": skill.name,
                "summary": summary
            },
            elapsed_time=timer() - st
        )

        return summary
    
    async def _generate_final_from_base_history_async(
        self,
        base_prompt: str,
        base_hist: list[dict],
        schema_prompt: str = ""
    ):
        """
        恢复 Base Prompt，基于所有 Skill Result 生成最终答案。
        """
        final_system_prompt = base_prompt

        if schema_prompt:
            final_system_prompt += "\n\n" + schema_prompt

        final_instruction = """
            Now provide the final answer to the user's original request based on all gathered skill results.
            
            Rules:
            1. Do not mention internal skill switching unless the user explicitly asks.
            2. Do not mention temporary prompts or implementation details.
            3. If a report was requested, provide the report directly.
            4. If information is incomplete, state what is known and what could not be determined.
            5. Use the same language as the user's original request.
        """

        final_hist = [
            {
                "role": "system",
                "content": final_system_prompt
            },
            *deepcopy(base_hist),
            {
                "role": "user",
                "content": final_instruction
            }
        ]

        _, final_hist = message_fit_in(
            final_hist,
            int(self.chat_mdl.max_length * 0.97)
        )

        async for delta in self._generate_streamly(final_hist):
            yield delta

    async def _react_with_skill_state_machine_async(
        self,
        prompt,
        history: list[dict],
        use_tools,
        user_defined_prompt={},
        schema_prompt: str = ""
    ):
        """
        基于状态机的 Skill Agent。

        两个阶段：

        1. Base Phase
           - system prompt = base_prompt + skills/index.md
           - tools = [read_skill]
           - 模型只能选择 skill 或 complete_task

        2. Skill Phase
           - system prompt = base_prompt + selected_skill.skill.md
           - tools = selected_skill.manifest.tools
           - 模型调用真实业务工具
           - complete_task 后总结 skill 结果，回到 Base Phase
        """

        token_count = 0

        # 原始系统提示词，不被 skill 污染
        base_prompt = prompt

        # 主历史，只保存：
        # - 用户请求
        # - skill 选择记录
        # - skill 总结结果
        #
        # 不保存 skill.md
        base_hist = deepcopy(history)

        # 读取 skills/index.md
        skill_index = self.skill_registry.load_index()

        # 如果没有 skill index，退回你原来的 ReAct
        if not skill_index.strip():
            logging.warning("No skills/index.md found. Fallback to normal tool ReAct.")

            hist = [
                {"role": "system", "content": prompt},
                *deepcopy(history)
            ]

            _, hist = message_fit_in(
                hist,
                int(self.chat_mdl.max_length * 0.97)
            )

            async for delta_ans, tk in self._react_with_tools_streamly_async(
                prompt,
                hist,
                use_tools,
                user_defined_prompt,
                schema_prompt=schema_prompt
            ):
                yield delta_ans, tk

            return

        # 状态机变量
        phase = "base"          # "base" or "skill"
        current_skill = None    # SkillSpec
        skill_hist = None       # 当前 skill 的临时历史

        # 防止无限循环
        max_total_steps = max(3, self._param.max_rounds * 3 + 3)
        used_skills = []

        for step_idx in range(max_total_steps):
            if self.check_if_canceled("Agent skill state machine"):
                return

            # ============================================================
            # Base Phase
            # ============================================================
            if phase == "base":
                base_system_prompt = self._build_base_skill_system_prompt(
                    base_prompt=base_prompt,
                    skill_index=skill_index
                )

                base_loop_hist = [
                    {
                        "role": "system",
                        "content": base_system_prompt
                    },
                    *deepcopy(base_hist)
                ]

                _, base_loop_hist = message_fit_in(
                    base_loop_hist,
                    int(self.chat_mdl.max_length * 0.9)
                )

                # Base Phase 只暴露 read_skill
                base_tool_metas = [
                    self.read_skill_meta
                ]

                task_desc = f"""
                You are in Base Phase.

                Available skills:

                {skill_index}

                Choose the next action:
                - Call `read_skill` if a listed skill is needed.
                - Call `{COMPLETE_TASK}` if enough information has been gathered.

                Rules:
                1. Do not call business tools directly in Base Phase.
                2. Do not invent skill names.
                3. Do not translate skill names.
                4. The `skill_name` argument must be copied exactly from the Available skills list.
                5. For file writing, saving markdown, saving reports, or creating documents, use skill_name exactly `file_writer`.
                """

                st = timer()
                response, tk = await next_step_async(
                    self.chat_mdl,
                    base_loop_hist,
                    base_tool_metas,
                    task_desc,
                    user_defined_prompt
                )

                token_count += tk or 0

                self.callback(
                    "base_next_step",
                    {},
                    {
                        "step": step_idx,
                        "response": response
                    },
                    elapsed_time=timer() - st
                )

                try:
                    functions = self._parse_react_functions(response)
                except Exception as e:
                    logging.exception(f"Base Phase parse error: {e}")

                    base_hist.append({
                        "role": "user",
                        "content": f"""
                            The previous Base Phase response had invalid JSON/tool-call format.
                            
                            Error:
                            {e}
                            
                            Please choose either `read_skill` or `{COMPLETE_TASK}` with valid JSON format.
                            """
                    })
                    continue

                # 处理 Base Phase 的工具调用
                switched_to_skill = False

                for func in functions:
                    name = func.get("name")
                    args = func.get("arguments", {}) or {}

                    # 任务完成：退出状态机，生成最终答案
                    if name == COMPLETE_TASK:
                        async for delta in self._generate_final_from_base_history_async(
                            base_prompt=base_prompt,
                            base_hist=base_hist,
                            schema_prompt=schema_prompt
                        ):
                            yield delta, 0
                        return

                    # read_skill 是元工具，不走 toolcall_session
                    if name == "read_skill":
                        skill_name = args.get("skill_name")
                        reason = args.get("reason", "")

                        if not skill_name:
                            base_hist.append({
                                "role": "user",
                                "content": "read_skill requires argument `skill_name`."
                            })
                            continue

                        # 兼容模型误传列表
                        if isinstance(skill_name, list):
                            if len(skill_name) == 0:
                                base_hist.append({
                                    "role": "user",
                                    "content": "read_skill argument `skill_name` cannot be an empty list."
                                })
                                continue

                            base_hist.append({
                                "role": "user",
                                "content": f"""
                        read_skill only accepts one skill_name at a time.

                        You provided multiple skill names:
                        {skill_name}

                        Please select the single most necessary skill now and call read_skill again.
                        """
                            })
                            continue

                        if not isinstance(skill_name, str):
                            base_hist.append({
                                "role": "user",
                                "content": f"read_skill argument `skill_name` must be a string, got {type(skill_name).__name__}."
                            })
                            continue

                        # 防止同一个 skill 被无限重复调用
                        if used_skills.count(skill_name) >= 2:
                            base_hist.append({
                                "role": "assistant",
                                "content": f"""
                                    [Skill Skipped: {skill_name}]
                                    
                                    The skill `{skill_name}` was selected repeatedly and has already been used {used_skills.count(skill_name)} times.
                                    Skipping it to avoid an infinite loop.
                                    """
                            })
                            continue

                        self.callback(
                            "before_read_skill",
                            {
                                "skill_name": skill_name,
                                "reason": reason
                            },
                            {
                                "message": f"About to read skill `{skill_name}`.",
                                "skill_name": skill_name,
                                "reason": reason
                            }
                        )

                        try:
                            skill = self.skill_registry.load_skill(skill_name)
                        except Exception as e:
                            logging.exception(f"Failed to read skill: {skill_name}")

                            self.callback(
                                "read_skill_error",
                                {
                                    "skill_name": skill_name,
                                    "reason": reason
                                },
                                {
                                    "skill_name": skill_name,
                                    "error": str(e)
                                }
                            )

                            base_hist.append({
                                "role": "assistant",
                                "content": f"""
                        [Skill Read Error: {skill_name}]

                        Failed to read skill `{skill_name}`.

                        Error:
                        {e}
                        """
                            })
                            continue

                        # 记录 skill 选择到 base history
                        base_hist.append({
                            "role": "assistant",
                            "content": f"""
[Skill Selection]

Selected skill: {skill.name}
Reason: {reason}
"""
                        })

                        self.callback(
                            "read_skill",
                            {
                                "skill_name": skill_name,
                                "reason": reason
                            },
                            {
                                "skill": skill.name,
                                "description": skill.description,
                                "tools": skill.tools,
                                "reason": reason
                            }
                        )

                        # 切换到 Skill Phase
                        current_skill = skill
                        skill_hist = deepcopy(base_hist)
                        phase = "skill"
                        switched_to_skill = True
                        break

                    # Base Phase 不允许调用其他业务工具
                    base_hist.append({
                        "role": "user",
                        "content": f"""
Tool `{name}` is not allowed in Base Phase.

Allowed tool:
- read_skill

If you need a business tool, first call read_skill for the appropriate skill.
"""
                    })

                if switched_to_skill:
                    continue

                # 如果 Base Phase 没有有效动作，继续下一轮
                continue

            # ============================================================
            # Skill Phase
            # ============================================================
            if phase == "skill":
                if current_skill is None or skill_hist is None:
                    # 理论上不会发生，防御性处理
                    phase = "base"
                    current_skill = None
                    skill_hist = None
                    continue

                skill = current_skill

                # 当前 skill 可以使用的真实工具
                skill_tool_metas = self._get_skill_tool_metas(skill.tools)

                missing_tools = [
                    tool_name for tool_name in skill.tools
                    if not self._get_tool_meta_by_name(tool_name)
                ]

                self.callback(
                    "enter_skill_phase",
                    {},
                    {
                        "skill": skill.name,
                        "tools": skill.tools,
                        "missing_tools": missing_tools
                    }
                )

                # --------------------------------------------------------
                # 如果 skill 没有工具，例如 report_writer
                # 直接用 skill prompt 生成一次结果，然后总结并回到 Base Phase
                # --------------------------------------------------------
                if not skill_tool_metas:
                    skill_system_prompt = self._build_skill_system_prompt(
                        base_prompt=base_prompt,
                        skill=skill
                    )

                    no_tool_hist = [
                        {
                            "role": "system",
                            "content": skill_system_prompt
                        },
                        *deepcopy(skill_hist),
                        {
                            "role": "user",
                            "content": f"""
Use skill `{skill.name}` to make progress on the original user request.

This skill has no external tools. Produce the best result directly.
"""
                        }
                    ]

                    _, no_tool_hist = message_fit_in(
                        no_tool_hist,
                        int(self.chat_mdl.max_length * 0.9)
                    )

                    st = timer()
                    skill_answer = await self._generate_async(no_tool_hist)

                    self.callback(
                        "skill_no_tool_answer",
                        {},
                        {
                            "skill": skill.name,
                            "answer": skill_answer
                        },
                        elapsed_time=timer() - st
                    )

                    # 写入临时 skill_hist
                    skill_hist.append({
                        "role": "assistant",
                        "content": skill_answer
                    })

                    # 总结 skill 结果
                    summary = await self._summarize_skill_result_async(
                        skill=skill,
                        skill_hist=skill_hist,
                        user_defined_prompt=user_defined_prompt
                    )

                    # 将总结写回 base_hist
                    base_hist.append({
                        "role": "assistant",
                        "content": f"""
[Skill Result: {skill.name}]

{summary}
"""
                    })

                    used_skills.append(skill.name)

                    # 丢弃 skill prompt / skill_hist，回到 Base Phase
                    current_skill = None
                    skill_hist = None
                    phase = "base"
                    continue

                # --------------------------------------------------------
                # 有工具的 Skill Phase
                # --------------------------------------------------------
                skill_system_prompt = self._build_skill_system_prompt(
                    base_prompt=base_prompt,
                    skill=skill
                )

                skill_loop_hist = [
                    {
                        "role": "system",
                        "content": skill_system_prompt
                    },
                    *deepcopy(skill_hist)
                ]

                _, skill_loop_hist = message_fit_in(
                    skill_loop_hist,
                    int(self.chat_mdl.max_length * 0.9)
                )

                task_desc = f"""
You are in Skill Phase for skill `{skill.name}`.

Available tools for this skill:
{skill.tools}

Missing tools:
{missing_tools}

Rules:
- Use only available tools for this skill.
- Do not call `read_skill` in Skill Phase.
- When the skill has finished its work, call `{COMPLETE_TASK}`.
"""

                st = timer()
                response, tk = await next_step_async(
                    self.chat_mdl,
                    skill_loop_hist,
                    skill_tool_metas,
                    task_desc,
                    user_defined_prompt
                )

                token_count += tk or 0

                self.callback(
                    "skill_next_step",
                    {},
                    {
                        "step": step_idx,
                        "skill": skill.name,
                        "response": response
                    },
                    elapsed_time=timer() - st
                )

                # 将 assistant 的工具调用意图写入 skill_hist
                skill_hist.append({
                    "role": "assistant",
                    "content": response
                })

                try:
                    functions = self._parse_react_functions(response)
                except Exception as e:
                    logging.exception(f"Skill Phase parse error: {e}")

                    skill_hist.append({
                        "role": "user",
                        "content": f"""
The previous Skill Phase response had invalid JSON/tool-call format.

Error:
{e}

Please call an available skill tool or call `{COMPLETE_TASK}`.
"""
                    })
                    continue

                has_complete = False
                results_for_reflect = []

                for func in functions:
                    name = func.get("name")
                    args = func.get("arguments", {}) or {}

                    # Skill 完成，稍后总结并回 Base Phase
                    if name == COMPLETE_TASK:
                        has_complete = True
                        continue

                    # Skill Phase 不允许 read_skill
                    if name == "read_skill":
                        result = {
                            "ok": False,
                            "error": "read_skill is not allowed in Skill Phase. Complete current skill first."
                        }

                        results_for_reflect.append((name, result))

                        skill_hist.append({
                            "role": "user",
                            "content": str(result)
                        })

                        continue

                    # 权限校验：只能调用当前 skill manifest 声明的工具
                    if name not in skill.tools:
                        result = {
                            "ok": False,
                            "error": f"Tool `{name}` is not allowed in skill `{skill.name}`.",
                            "allowed_tools": skill.tools
                        }

                        results_for_reflect.append((name, result))

                        skill_hist.append({
                            "role": "user",
                            "content": str(result)
                        })

                        continue

                    # 工具是否真实存在
                    if name not in self.tools:
                        result = {
                            "ok": False,
                            "error": f"Tool `{name}` does not exist in Agent tools."
                        }

                        results_for_reflect.append((name, result))

                        skill_hist.append({
                            "role": "user",
                            "content": str(result)
                        })

                        continue

                    # ====================================================
                    # 真实业务工具执行位置
                    # ====================================================
                    self.callback(
                        "before_skill_tool_call",
                        {
                            "skill": skill.name,
                            "tool": name,
                            "arguments": args
                        },
                        {
                            "message": f"About to call tool `{name}` in skill `{skill.name}`."
                        }
                    )

                    st = timer()

                    tool_response = await self.toolcall_session.tool_call_async(
                        name,
                        args
                    )

                    elapsed = timer() - st

                    self.callback(
                        "skill_tool_call",
                        {
                            "skill": skill.name,
                            "tool": name,
                            "arguments": args
                        },
                        tool_response,
                        elapsed_time=elapsed
                    )

                    tool_item = {
                        "name": name,
                        "arguments": args,
                        "results": tool_response,
                        "skill": skill.name
                    }

                    # 记录到 use_tools，供 Agent 输出使用
                    use_tools.append(tool_item)

                    # 给 reflect_async 用
                    results_for_reflect.append((name, tool_response))

                # 工具执行后反思，将工具结果转成自然语言上下文放入 skill_hist
                if results_for_reflect:
                    st = timer()

                    reflection = await reflect_async(
                        self.chat_mdl,
                        skill_hist,
                        results_for_reflect,
                        user_defined_prompt
                    )

                    skill_hist.append({
                        "role": "user",
                        "content": reflection
                    })

                    self.callback(
                        "skill_reflection",
                        {},
                        {
                            "skill": skill.name,
                            "reflection": reflection
                        },
                        elapsed_time=timer() - st
                    )

                # 如果模型调用了 complete_task，则总结 skill 结果并回到 Base Phase
                if has_complete:
                    summary = await self._summarize_skill_result_async(
                        skill=skill,
                        skill_hist=skill_hist,
                        user_defined_prompt=user_defined_prompt
                    )

                    base_hist.append({
                        "role": "assistant",
                        "content": f"""
[Skill Result: {skill.name}]

{summary}
"""
                    })

                    used_skills.append(skill.name)

                    # 丢弃临时 skill 状态，恢复 Base Phase
                    current_skill = None
                    skill_hist = None
                    phase = "base"
                    continue

                # 如果没有 complete，就继续 Skill Phase 下一轮
                continue

        # ================================================================
        # 超过最大步数，直接基于已有结果生成最终答案
        # ================================================================
        logging.warning(f"Skill state machine reached max steps: {max_total_steps}")

        base_hist.append({
            "role": "user",
            "content": """
The agent has reached the maximum skill loop steps.
Based on all gathered skill results so far, provide the best possible final answer.
"""
        })

        async for delta in self._generate_final_from_base_history_async(
            base_prompt=base_prompt,
            base_hist=base_hist,
            schema_prompt=schema_prompt
        ):
            yield delta, 0


    def get_meta(self) -> dict[str, Any]:
        self._param.function_name= self._id.split("-->")[-1]
        m = super().get_meta()
        if hasattr(self._param, "user_prompt") and self._param.user_prompt:
            m["function"]["parameters"]["properties"]["user_prompt"] = self._param.user_prompt
        return m

    def get_input_form(self) -> dict[str, dict]:
        res = {}
        for k, v in self.get_input_elements().items():
            res[k] = {
                "type": "line",
                "name": v["name"]
            }
        for cpn in self._param.tools:
            if not isinstance(cpn, LLM):
                continue
            res.update(cpn.get_input_form())
        return res

    def _get_output_schema(self):
        try:
            cand = self._param.outputs.get("structured")
        except Exception:
            return None

        if isinstance(cand, dict):
            if isinstance(cand.get("properties"), dict) and len(cand["properties"]) > 0:
                return cand
            for k in ("schema", "structured"):
                if isinstance(cand.get(k), dict) and isinstance(cand[k].get("properties"), dict) and len(cand[k]["properties"]) > 0:
                    return cand[k]

        return None

    async def _force_format_to_schema_async(self, text: str, schema_prompt: str) -> str:
        fmt_msgs = [
            {"role": "system", "content": schema_prompt + "\nIMPORTANT: Output ONLY valid JSON. No markdown, no extra text."},
            {"role": "user", "content": text},
        ]
        _, fmt_msgs = message_fit_in(fmt_msgs, int(self.chat_mdl.max_length * 0.97))
        return await self._generate_async(fmt_msgs)

    def _invoke(self, **kwargs):
        return asyncio.run(self._invoke_async(**kwargs))

    @timeout(int(os.environ.get("COMPONENT_EXEC_TIMEOUT", 20*60)))
    async def _invoke_async(self, **kwargs):
        if self.check_if_canceled("Agent processing"):
            return

        if kwargs.get("user_prompt"):
            usr_pmt = ""
            if kwargs.get("reasoning"):
                usr_pmt += "\nREASONING:\n{}\n".format(kwargs["reasoning"])
            if kwargs.get("context"):
                usr_pmt += "\nCONTEXT:\n{}\n".format(kwargs["context"])
            if usr_pmt:
                usr_pmt += "\nQUERY:\n{}\n".format(str(kwargs["user_prompt"]))
            else:
                usr_pmt = str(kwargs["user_prompt"])
            self._param.prompts = [{"role": "user", "content": usr_pmt}]

        if not self.tools:
            if self.check_if_canceled("Agent processing"):
                return
            return await LLM._invoke_async(self, **kwargs)

        prompt, msg, user_defined_prompt = self._prepare_prompt_variables()
        output_schema = self._get_output_schema()
        schema_prompt = ""
        if output_schema:
            schema = json.dumps(output_schema, ensure_ascii=False, indent=2)
            schema_prompt = structured_output_prompt(schema)

        downstreams = self._canvas.get_component(self._id)["downstream"] if self._canvas.get_component(self._id) else []
        ex = self.exception_handler()
        if any([self._canvas.get_component_obj(cid).component_name.lower()=="message" for cid in downstreams]) and not (ex and ex["goto"]) and not output_schema:
            self.set_output("content", partial(self.stream_output_with_tools_async, prompt, deepcopy(msg), user_defined_prompt))
            return

        # _, msg = message_fit_in([{"role": "system", "content": prompt}, *msg], int(self.chat_mdl.max_length * 0.97))
        # use_tools = []
        # ans = ""
        # async for delta_ans, _tk in self._react_with_tools_streamly_async(prompt, msg, use_tools, user_defined_prompt,schema_prompt=schema_prompt):
        #     if self.check_if_canceled("Agent processing"):
        #         return
        #     ans += delta_ans

        # 调用循环获取答案
        """
        think
        action    ↑
        observise ↑
        finalanswer
        """

        _, msg = message_fit_in(
            msg,
            int(self.chat_mdl.max_length * 0.9)
        )

        use_tools = []
        ans = ""

        async for delta_ans, _tk in self._react_with_skill_state_machine_async(
            prompt,
            msg,
            use_tools,
            user_defined_prompt,
            schema_prompt=schema_prompt
        ):
            if self.check_if_canceled("Agent processing"):
                return
            ans += delta_ans

        if ans.find("**ERROR**") >= 0:
            logging.error(f"Agent._chat got error. response: {ans}")
            if self.get_exception_default_value():
                self.set_output("content", self.get_exception_default_value())
            else:
                self.set_output("_ERROR", ans)
            return

        if output_schema:
            error = ""
            for _ in range(self._param.max_retries + 1):
                try:
                    def clean_formated_answer(ans: str) -> str:
                        ans = re.sub(r"^.*</think>", "", ans, flags=re.DOTALL)
                        ans = re.sub(r"^.*```json", "", ans, flags=re.DOTALL)
                        return re.sub(r"```\n*$", "", ans, flags=re.DOTALL)
                    obj = json_repair.loads(clean_formated_answer(ans))
                    self.set_output("structured", obj)
                    if use_tools:
                        self.set_output("use_tools", use_tools)
                    return obj
                except Exception:
                    error = "The answer cannot be parsed as JSON"
                    ans = await self._force_format_to_schema_async(ans, schema_prompt)
                    if ans.find("**ERROR**") >= 0:
                        continue

            self.set_output("_ERROR", error)
            return

        self.set_output("content", ans)
        if use_tools:
            self.set_output("use_tools", use_tools)
        return ans

    @timeout(int(os.environ.get("COMPONENT_EXEC_TIMEOUT", 20 * 60)))
    async def _invoke_stream_async(self, **kwargs):
        """
        Agent 流式执行入口。

        和 _invoke_async 类似，但会把最终回答的 delta 流式 yield 出去。
        工具调用过程通过 callback 对外暴露。
        """
        if self.check_if_canceled("Agent streaming processing"):
            return

        if kwargs.get("user_prompt"):
            usr_pmt = ""

            if kwargs.get("reasoning"):
                usr_pmt += "\nREASONING:\n{}\n".format(kwargs["reasoning"])

            if kwargs.get("context"):
                usr_pmt += "\nCONTEXT:\n{}\n".format(kwargs["context"])

            if usr_pmt:
                usr_pmt += "\nQUERY:\n{}\n".format(str(kwargs["user_prompt"]))
            else:
                usr_pmt = str(kwargs["user_prompt"])

            self._param.prompts = [
                {
                    "role": "user",
                    "content": usr_pmt
                }
            ]

        # 如果没有工具，退回普通 LLM 流式
        if not self.tools:
            prompt, msg, user_defined_prompt = self._prepare_prompt_variables()

            hist = [
                {
                    "role": "system",
                    "content": prompt
                },
                *msg
            ]

            _, hist = message_fit_in(
                hist,
                int(self.chat_mdl.max_length * 0.97)
            )

            ans = ""

            async for delta in self._generate_streamly(hist):
                ans += delta
                yield delta

            self.set_output("content", ans)
            return

        prompt, msg, user_defined_prompt = self._prepare_prompt_variables()

        output_schema = self._get_output_schema()
        schema_prompt = ""

        if output_schema:
            schema = json.dumps(output_schema, ensure_ascii=False, indent=2)
            schema_prompt = structured_output_prompt(schema)

        _, msg = message_fit_in(
            msg,
            int(self.chat_mdl.max_length * 0.9)
        )

        use_tools = []
        ans = ""

        async for delta_ans, _tk in self._react_with_skill_state_machine_async(
                prompt,
                msg,
                use_tools,
                user_defined_prompt,
                schema_prompt=schema_prompt
        ):
            if self.check_if_canceled("Agent streaming processing"):
                return

            if delta_ans.find("**ERROR**") >= 0:
                logging.error(f"Agent._invoke_stream_async got error. response: {delta_ans}")

                if self.get_exception_default_value():
                    self.set_output("content", self.get_exception_default_value())
                    yield self.get_exception_default_value()
                else:
                    self.set_output("_ERROR", delta_ans)

                return

            ans += delta_ans

            # 边生成边设置，方便外部随时读取
            self.set_output("content", ans)

            yield delta_ans

        # 结构化输出场景，流式一般不建议开启；这里先保持文本输出
        self.set_output("content", ans)

        if use_tools:
            self.set_output("use_tools", use_tools)

    async def stream_output_with_tools_async(self, prompt, msg, user_defined_prompt={}):
        """
        流式输出入口。

        现在默认走 Skill State Machine：

        Base Phase:
            system prompt = base_prompt + skills/index.md
            tools = [read_skill]

        Skill Phase:
            system prompt = base_prompt + selected_skill/skill.md
            tools = selected_skill.manifest.tools

        注意：
        这里不要提前把 {"role": "system", "content": prompt} 塞进 msg。
        因为 _react_with_skill_state_machine_async 内部会根据 phase 自己构造 system prompt。
        """

        # 只裁剪用户消息历史，不注入 system prompt
        _, runtime_msg = message_fit_in(
            deepcopy(msg),
            int(self.chat_mdl.max_length * 0.9)
        )

        answer_without_toolcall = ""
        use_tools = []

        async for delta_ans, _ in self._react_with_skill_state_machine_async(
            prompt,
            runtime_msg,
            use_tools,
            user_defined_prompt,
            schema_prompt=""
        ):
            if self.check_if_canceled("Agent streaming"):
                return

            if delta_ans.find("**ERROR**") >= 0:
                if self.get_exception_default_value():
                    self.set_output("content", self.get_exception_default_value())
                    yield self.get_exception_default_value()
                else:
                    self.set_output("_ERROR", delta_ans)
                    return

            answer_without_toolcall += delta_ans
            yield delta_ans

        self.set_output("content", answer_without_toolcall)

        if use_tools:
            self.set_output("use_tools", use_tools)

    async def _react_with_tools_streamly_async(self, prompt, history: list[dict], use_tools, user_defined_prompt={}, schema_prompt: str = ""):
        token_count = 0
        tool_metas = self.tool_meta
        hist = deepcopy(history)
        last_calling = ""
        if len(hist) > 3:
            st = timer()
            user_request = await full_question(messages=history, chat_mdl=self.chat_mdl)
            self.callback("Multi-turn conversation optimization", {}, user_request, elapsed_time=timer()-st)
        else:
            user_request = history[-1]["content"]

        async def use_tool_async(name, args):
            nonlocal hist, use_tools, last_calling
            logging.info(f"{last_calling=} == {name=}")
            last_calling = name
            tool_response = await self.toolcall_session.tool_call_async(name, args)
            use_tools.append({
                "name": name,
                "arguments": args,
                "results": tool_response
            })
            # self.callback("add_memory", {}, "...")
            #self.add_memory(hist[-2]["content"], hist[-1]["content"], name, args, str(tool_response), user_defined_prompt)

            return name, tool_response

        async def complete():
            nonlocal hist
            need2cite = self._param.cite and self._canvas.get_reference()["chunks"] and self._id.find("-->") < 0
            if schema_prompt:
                need2cite = False
            cited = False
            if hist and hist[0]["role"] == "system":
                if schema_prompt:
                    hist[0]["content"] += "\n" + schema_prompt
                if need2cite and len(hist) < 7:
                    hist[0]["content"] += citation_prompt()
                    cited = True
            yield "", token_count

            _hist = hist
            if len(hist) > 12:
                _hist = [hist[0], hist[1], *hist[-10:]]
            entire_txt = ""
            async for delta_ans in self._generate_streamly(_hist):
                if not need2cite or cited:
                    yield delta_ans, 0
                entire_txt += delta_ans
            if not need2cite or cited:
                return

            st = timer()
            txt = ""
            async for delta_ans in self._gen_citations_async(entire_txt):
                if self.check_if_canceled("Agent streaming"):
                    return
                yield delta_ans, 0
                txt += delta_ans

            self.callback("gen_citations", {}, txt, elapsed_time=timer()-st)

        def append_user_content(hist, content):
            if hist[-1]["role"] == "user":
                hist[-1]["content"] += content
            else:
                hist.append({"role": "user", "content": content})

        st = timer()
        task_desc = await analyze_task_async(self.chat_mdl, prompt, user_request, tool_metas, user_defined_prompt)
        self.callback("analyze_task", {}, task_desc, elapsed_time=timer()-st)
        for _ in range(self._param.max_rounds + 1):
            if self.check_if_canceled("Agent streaming"):
                return
            response, tk = await next_step_async(self.chat_mdl, hist, tool_metas, task_desc, user_defined_prompt)
            # self.callback("next_step", {}, str(response)[:256]+"...")
            token_count += tk or 0
            hist.append({"role": "assistant", "content": response})
            try:
                functions = json_repair.loads(re.sub(r"```.*", "", response))
                if not isinstance(functions, list):
                    raise TypeError(f"List should be returned, but `{functions}`")
                for f in functions:
                    if not isinstance(f, dict):
                        raise TypeError(f"An object type should be returned, but `{f}`")

                tool_tasks = []
                for func in functions:
                    name = func["name"]
                    args = func["arguments"]
                    if name == COMPLETE_TASK:
                        append_user_content(hist, f"Respond with a formal answer. FORGET(DO NOT mention) about `{COMPLETE_TASK}`. The language for the response MUST be as the same as the first user request.\n")
                        async for txt, tkcnt in complete():
                            yield txt, tkcnt
                        return

                    tool_tasks.append(asyncio.create_task(use_tool_async(name, args)))

                results = await asyncio.gather(*tool_tasks) if tool_tasks else []
                st = timer()
                reflection = await reflect_async(self.chat_mdl, hist, results, user_defined_prompt)
                append_user_content(hist, reflection)
                self.callback("reflection", {}, str(reflection), elapsed_time=timer()-st)

            except Exception as e:
                logging.exception(msg=f"Wrong JSON argument format in LLM ReAct response: {e}")
                e = f"\nTool call error, please correct the input parameter of response format and call it again.\n *** Exception ***\n{e}"
                append_user_content(hist, str(e))

        logging.warning( f"Exceed max rounds: {self._param.max_rounds}")
        final_instruction = f"""
{user_request}
IMPORTANT: You have reached the conversation limit. Based on ALL the information and research you have gathered so far, please provide a DIRECT and COMPREHENSIVE final answer to the original request.
Instructions:
1. SYNTHESIZE all information collected during this conversation
2. Provide a COMPLETE response using existing data - do not suggest additional research
3. Structure your response as a FINAL DELIVERABLE, not a plan
4. If information is incomplete, state what you found and provide the best analysis possible with available data
5. DO NOT mention conversation limits or suggest further steps
6. Focus on delivering VALUE with the information already gathered
Respond immediately with your final comprehensive answer.
        """
        if self.check_if_canceled("Agent final instruction"):
            return
        append_user_content(hist, final_instruction)

        async for txt, tkcnt in complete():
            yield txt, tkcnt

    async def _gen_citations_async(self, text):
        retrievals = self._canvas.get_reference()
        retrievals = {"chunks": list(retrievals["chunks"].values()), "doc_aggs": list(retrievals["doc_aggs"].values())}
        formated_refer = kb_prompt(retrievals, self.chat_mdl.max_length, True)
        async for delta_ans in self._generate_streamly([{"role": "system", "content": citation_plus("\n\n".join(formated_refer))},
                                                  {"role": "user", "content": text}
                                                  ]):
            yield delta_ans

    def reset(self, only_output=False):
        """
        Reset all tools if they have a reset method. This avoids errors for tools like MCPToolCallSession.
        """
        for k in self._param.outputs.keys():
            self._param.outputs[k]["value"] = None

        for k, cpn in self.tools.items():
            if hasattr(cpn, "reset") and callable(cpn.reset):
                cpn.reset()
        if only_output:
            return
        for k in self._param.inputs.keys():
            self._param.inputs[k]["value"] = None
        self._param.debug_inputs = {}
