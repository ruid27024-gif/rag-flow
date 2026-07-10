import asyncio

from common import settings
from agent.runtime.factory import create_agent_runtime


async def main():
    settings.init_settings()

    tools = [
        {
            "component_name": "ExeSQL",
            "name": "exesql",
            "params": {
                "database": "rag_flow",
                "username": "root",
                "host": "mysql",
                "port": 3306,
                "password": "infini_rag_flow",
                "top_n": 3
            }
        }
    ]

    agent, runtime = create_agent_runtime(
        tenant_id="你的_tenant_id",
        llm_id="你的_llm_id",
        agent_id="chat_sql_agent",
        skill_root="./skills",
        system_prompt="You are a helpful SQL analysis agent. Use skills when needed.",
        tools=tools,
        max_rounds=5,
        cite=False
    )

    print("Loaded tools:", list(agent.tools.keys()))
    print("Skill index:")
    print(agent.skill_registry.load_index())

    result = await agent._invoke_async(
        user_prompt="查询数据库中最近的 3 条记录，并总结结果。",
        context="数据库是 rag_flow。",
        reasoning="需要使用 sql_analysis skill 调用 SQL 工具。"
    )

    print("\n========== FINAL RESULT ==========")
    print(result)

    print("\n========== TOOL TRACES ==========")
    for trace in runtime.get_tool_traces():
        print(trace)


if __name__ == "__main__":
    asyncio.run(main())