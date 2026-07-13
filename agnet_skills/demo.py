import asyncio
import json
import os
from pathlib import Path
from functools import partial

# 你的真实 import
from agent.canvas import Canvas
from agent1 import Agent, AgentParam
from agent.tools.base import LLMToolPluginCallSession



TENANT_ID = "b6d704fd2f7811f1bf57a06663d8aa69"
LLM_ID = "qwen3-32b"


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


def prepare_file_writer_skill():
    """
    准备 skills 目录。

    目录结构：

    skills/
      index.md
      file_writer/
        skill.md
        manifest.json
    """

    skill_root = Path("./skills")
    skill_root.mkdir(parents=True, exist_ok=True)

    # 让 Agent 使用这个 skills 目录
    os.environ["AGENT_SKILL_ROOT"] = str(skill_root)

    # Base Phase 能看到的 Skill 索引
    (skill_root / "index.md").write_text(
        """# Available Skills

## file_writer

Use this skill when the user asks to create, write, save, or export a text file, markdown file, report, document, note, or plan.
""",
        encoding="utf-8"
    )

    skill_dir = skill_root / "file_writer"
    skill_dir.mkdir(parents=True, exist_ok=True)

    # manifest 里声明这个 skill 允许使用 write_file 工具
    manifest = {
        "name": "file_writer",
        "description": "Create and write text files.",
        "tools": [
            "write_file"
        ]
    }

    (skill_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    # skill prompt
    (skill_dir / "skill.md").write_text(
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


async def main():
    # 1. 准备 Skill
    prepare_file_writer_skill()

    # 2. 创建最小 Canvas
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
            "sys.query": "",
            "sys.user_id": TENANT_ID,
            "sys.conversation_turns": 0,
            "sys.files": []
        }
    }

    canvas = Canvas(
        dsl=json.dumps(dsl, ensure_ascii=False),
        tenant_id=TENANT_ID
    )

    # TODO 不通过 canvas.run() 启动时，需要手动补 message_id
    canvas.message_id = "1"

    # 3. 创建 AgentParam
    param = AgentParam()
    param.sys_prompt = "You are a helpful agent. Follow the user's instructions carefully."
    # 必须是真实可用的 LLM ID
    param.llm_id = LLM_ID
    param.tenant_id = TENANT_ID

    param.max_retries = 1
    param.delay_after_error = 1
    param.max_rounds = 5

    # 这里先不通过 param.tools 加载工具
    # 因为 write_file 是我们手动 mock 注入的工具
    param.tools = []
    param.mcp = []

    param.prompts = [
        {
            "role": "user",
            "content": "{{sys.query}}"
        }
    ]
    print("TENANT_ID =", TENANT_ID)
    print("LLM_ID =", LLM_ID)
    print("canvas tenant =", canvas.get_tenant_id())
    from common.constants import LLMType
    from api.db.services.tenant_llm_service import TenantLLMService
    TenantLLMService.llm_id2llm_type = staticmethod(lambda llm_id: LLMType.CHAT)
    # 4. 实例化 Agent
    agent = Agent(
        canvas=canvas,
        id="agent_0",
        param=param
    )

    # 5. 手动注入 write_file 工具
    write_file_tool = SimpleWriteFileTool(base_dir="./agent_outputs")

    agent.tools["write_file"] = write_file_tool
    agent.tool_meta = [
        write_file_tool.get_meta()
    ]

    # 记录日志的
    agent.callback = partial(agent._canvas.tool_use_callback, agent._id)
    # 工具调用 + 记录日志的
    agent.toolcall_session = LLMToolPluginCallSession(
        agent.tools,
        agent.callback
    )

    print("Loaded tools:", list(agent.tools.keys()))
    print("Tool metas:", json.dumps(agent.tool_meta, ensure_ascii=False, indent=2))

    # 6. 调用 Agent
    result = await agent._invoke_async(
        user_prompt="请帮我写一份 AI Agent 技术方案，并保存成 agent_plan.md 文件。",
        reasoning="",
        context="面向企业内部研发团队，要求中文输出，结构清晰，包含背景、目标、架构、核心模块、实施计划和风险。"
    )

    # 7. 输出结果
    print("\n========== FINAL RESULT ==========\n")
    print(result or agent.output("content"))

    print("\n========== USE TOOLS ==========\n")
    print(json.dumps(agent.output("use_tools"), ensure_ascii=False, indent=2))

    print("\n========== OUTPUT DIR ==========\n")
    print(Path("./agent_outputs").resolve())


if __name__ == "__main__":
    asyncio.run(main())