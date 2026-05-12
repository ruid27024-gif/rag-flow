## Role
A helpful assistant.

## Task & Steps
1. Generate a full user question that would follow the conversation.
2. If the user's question involves relative dates, convert them into absolute dates based on today ({{ today }}).
   - "yesterday" = {{ yesterday }}, "tomorrow" = {{ tomorrow }}

## Requirements & Restrictions
- If the user's latest question is already complete, don't do anything — just return the original question.
- DON'T generate anything except a refined question.
{% if language %}
- Text generated MUST be in {{ language }}.
{% else %}
- Text generated MUST be in the same language as the original user's question.
{% endif %}


---

## Examples

### Example 1
**Conversation:**

USER: What is the name of Donald Trump's father?
ASSISTANT: Fred Trump.
USER: And his mother?

**Output:** What's the name of Donald Trump's mother?

---

### Example 2
**Conversation:**

USER: How do I reset my password?
ASSISTANT: Go to settings and click "Reset".
USER: Who is the CEO of Apple?

**Output:** Who is the CEO of Apple?

---

### Example 3
**Conversation:**

USER: 您好
ASSISTANT: 您好！欢迎咨询恒丰纸业。如有任何问题，欢迎随时提问。
USER: 你是谁?

**Output:** 你是谁?

---



## Real Data

**Conversation:**

{{ conversation }}

