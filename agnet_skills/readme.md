Base Phase:
  system prompt = 原始系统提示词 + skills/index.md
  tools = [read_skill]
  ↓
模型调用 read_skill("xxx")
  ↓
Python 拦截 read_skill，不走真实工具系统
  ↓
读取 skill.md / manifest.json
  ↓
进入 Skill Phase

Skill Phase:
  system prompt = 原始系统提示词 + skill.md
  tools = 当前 skill 声明的真实工具
  ↓
模型调用 excel_processor / web_search / ...
  ↓
真实工具通过 self.toolcall_session.tool_call_async 执行
  ↓
工具结果进入 skill_hist
  ↓
模型 complete_task
  ↓
总结当前 skill 结果
  ↓
把结果写入 base_hist
  ↓
丢弃 skill prompt 和 skill_hist
  ↓
回到 Base Phase