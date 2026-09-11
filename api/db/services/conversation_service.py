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
import time
from uuid import uuid4
from common.constants import StatusEnum
from api.db.db_models import Conversation, DB
from api.db.services.api_service import API4ConversationService
from api.db.services.common_service import CommonService
from api.db.services.dialog_service import DialogService, async_chat
from common.misc_utils import get_uuid
import json

from rag.prompts.generator import chunks_format
import uuid

class ConversationService(CommonService):
    model = Conversation

    @classmethod
    @DB.connection_context()
    def get_list(cls, dialog_id, page_number, items_per_page, orderby, desc, id, name, user_id=None):
        sessions = cls.model.select().where(cls.model.dialog_id == dialog_id)
        if id:
            sessions = sessions.where(cls.model.id == id)
        if name:
            sessions = sessions.where(cls.model.name == name)
        if user_id:
            sessions = sessions.where(cls.model.user_id == user_id)
        if desc:
            sessions = sessions.order_by(cls.model.getter_by(orderby).desc())
        else:
            sessions = sessions.order_by(cls.model.getter_by(orderby).asc())

        sessions = sessions.paginate(page_number, items_per_page)

        return list(sessions.dicts())

    @classmethod
    @DB.connection_context()
    def get_all_conversation_by_dialog_ids(cls, dialog_ids):
        sessions = cls.model.select().where(cls.model.dialog_id.in_(dialog_ids))
        sessions.order_by(cls.model.create_time.asc())
        offset, limit = 0, 100
        res = []
        while True:
            s_batch = sessions.offset(offset).limit(limit)
            _temp = list(s_batch.dicts())
            if not _temp:
                break
            res.extend(_temp)
            offset += limit
        return res
    
    @classmethod
    @DB.connection_context()
    def generate_branch_name(cls, dialog_id, base_name, user_id=None):
        base_name = base_name or "新会话"

        suffix = " - 分支"
        max_base_len = 255 - len(suffix) - 8
        safe_base_name = base_name[:max_base_len]

        prefix = f"{safe_base_name}{suffix}"

        query = cls.model.select().where(
            cls.model.dialog_id == dialog_id,
            cls.model.name.startswith(prefix),
        )

        if user_id:
            query = query.where(cls.model.user_id == user_id)

        existing_names = [item.name for item in query]

        if prefix not in existing_names:
            return prefix

        index = 2
        while True:
            name = f"{prefix} {index}"

            if len(name) > 255:
                extra_len = len(name) - 255
                name = f"{prefix[:-extra_len]} {index}"

            if name not in existing_names:
                return name

            index += 1

    @classmethod
    @DB.connection_context()
    def create_branch_conversation(
        cls,
        dialog_id,
        name,
        message,
        reference,
        user_id=None,
    ):
        """
        创建分支 conversation
        """
        conversation_id = uuid.uuid4().hex

        conv = cls.model.create(
            id=conversation_id,
            dialog_id=dialog_id,
            name=name,
            message=message,
            reference=reference,
            user_id=user_id,
        )

        return conv.to_dict()

# def structure_answer(conv, ans, message_id, session_id):
#     reference = ans["reference"]
#     if not isinstance(reference, dict):
#         reference = {}
#         ans["reference"] = {}
#
#     chunk_list = chunks_format(reference)
#
#     reference["chunks"] = chunk_list
#     ans["id"] = message_id
#     ans["session_id"] = session_id
#
#
#     if not conv:
#         return ans
#
#     if not conv.message:
#         conv.message = []
#     if not conv.message or conv.message[-1].get("role", "") != "assistant":
#         conv.message.append({"role": "assistant", "content": ans["answer"], "created_at": time.time(), "id": message_id, "suggestions":ans.get("suggestions", [])})
#     else:
#         conv.message[-1] = {"role": "assistant", "content": ans["answer"], "created_at": time.time(), "id": message_id, "suggestions":ans.get("suggestions", [])}
#     if conv.reference:
#         conv.reference[-1] = reference
#
#     print(".......................................................................................")
#     print(reference)
#     print(".......................................................................................")
#     print(ans)
#     return ans
def agent_event_key(event):
    """
    用于 agent event 去重。
    """
    if not isinstance(event, dict):
        return ""

    return "|".join([
        str(event.get("type", "")),
        str(event.get("name", "")),
        str(event.get("title", "")),
        str(event.get("summary", "")),
        str(event.get("status", "")),
        str(event.get("display", "")),
    ])


def merge_agent_events(old_events=None, incoming_events=None):
    """
    合并旧 agent_events 和新事件。

    - old_events: 已经保存在 conv.message[-1] 里的事件列表
    - incoming_events: 当前 ans 里的 agent_event / agent_events
    """
    old_events = old_events or []
    incoming_events = incoming_events or []

    result = []
    seen = set()

    for event in list(old_events) + list(incoming_events):
        if not isinstance(event, dict):
            continue

        # answer_delta 是正文流式增量，不展示在工具调用面板里，也不保存
        if event.get("type") == "answer_delta":
            continue

        key = agent_event_key(event)

        if key in seen:
            continue

        seen.add(key)
        result.append(event)

    return result


def extract_agent_events(ans):
    """
    从当前 ans 中提取 Agent 事件。

    兼容：
    - agent_events: []
    - agentEvents: []
    - agent_event: {}
    - agentEvent: {}
    """
    events = []

    if isinstance(ans.get("agent_events"), list):
        events.extend(ans.get("agent_events") or [])

    if isinstance(ans.get("agentEvents"), list):
        events.extend(ans.get("agentEvents") or [])

    if isinstance(ans.get("agent_event"), dict):
        events.append(ans.get("agent_event"))

    if isinstance(ans.get("agentEvent"), dict):
        events.append(ans.get("agentEvent"))

    return events


# def structure_answer(conv, ans, message_id, session_id):
#     """
#     统一整理每个流式 ans：

#     1. 格式化 reference
#     2. 保存工具信息
#     3. 累积保存 agent_events 到 conv.message
#     4. 防止 answer="" 覆盖已有正文
#     5. 返回给 SSE 前端
#     """
#     if ans is None:
#         ans = {}

#     # -----------------------------
#     # 1. reference 处理
#     # -----------------------------
#     reference = ans.get("reference", {})

#     if not isinstance(reference, dict):
#         reference = {}
#         ans["reference"] = {}

#     chunk_list = chunks_format(reference)
#     reference["chunks"] = chunk_list

#     # -----------------------------
#     # 2. 兼容 Agent 工具信息
#     # -----------------------------
#     use_tools = ans.get("use_tools") or []
#     output_dir = ans.get("output_dir")
#     tool_logs = ans.get("tool_logs")

#     if use_tools:
#         reference["use_tools"] = use_tools

#     if output_dir:
#         reference["output_dir"] = output_dir

#     if tool_logs:
#         reference["tool_logs"] = tool_logs

#     # -----------------------------
#     # 3. 基础字段回写给前端
#     # -----------------------------
#     ans["id"] = message_id
#     ans["session_id"] = session_id
#     ans["reference"] = reference

#     if use_tools:
#         ans["use_tools"] = use_tools

#     if output_dir:
#         ans["output_dir"] = output_dir

#     if tool_logs:
#         ans["tool_logs"] = tool_logs

#     # -----------------------------
#     # 4. 提取当前 Agent 事件
#     # -----------------------------
#     incoming_agent_events = extract_agent_events(ans)

#     # 如果没有 conv，只返回 ans，不做持久化
#     if not conv:
#         return ans

#     if not conv.message:
#         conv.message = []

#     # -----------------------------
#     # 5. 获取上一条 assistant message
#     # -----------------------------
#     prev_assistant_msg = None

#     if conv.message and conv.message[-1].get("role", "") == "assistant":
#         prev_assistant_msg = conv.message[-1]

#     # -----------------------------
#     # 6. 读取旧 agent_events 并合并
#     # -----------------------------
#     old_agent_events = []

#     if prev_assistant_msg:
#         old_agent_events = (
#             prev_assistant_msg.get("agent_events")
#             or prev_assistant_msg.get("agentEvents")
#             or []
#         )

#     merged_agent_events = merge_agent_events(
#         old_agent_events,
#         incoming_agent_events
#     )

#     # -----------------------------
#     # 7. 防止 answer="" 覆盖已有正文
#     # -----------------------------
#     answer_text = ans.get("answer")

#     # Agent 过程事件可能是 {"answer": "", "agent_event": {...}}
#     # 这种情况下保留旧正文
#     if (answer_text is None or answer_text == "") and prev_assistant_msg:
#         answer_text = prev_assistant_msg.get("content", "")

#     if answer_text is None:
#         answer_text = ""

#     # 如果 ans 没有 answer，也补一个，避免前端读取报错
#     ans["answer"] = answer_text

#     # -----------------------------
#     # 8. 构造 assistant message
#     # -----------------------------
#     assistant_msg = {
#         "role": "assistant",
#         "content": answer_text,
#         "created_at": (
#             prev_assistant_msg.get("created_at")
#             if prev_assistant_msg and prev_assistant_msg.get("created_at")
#             else time.time()
#         ),
#         "id": message_id,
#         "suggestions": ans.get(
#             "suggestions",
#             prev_assistant_msg.get("suggestions", []) if prev_assistant_msg else []
#         )
#     }

#     # -----------------------------
#     # 9. 保存工具信息到 assistant message
#     # -----------------------------
#     if use_tools:
#         assistant_msg["use_tools"] = use_tools
#     elif prev_assistant_msg and prev_assistant_msg.get("use_tools"):
#         assistant_msg["use_tools"] = prev_assistant_msg.get("use_tools")

#     if output_dir:
#         assistant_msg["output_dir"] = output_dir
#     elif prev_assistant_msg and prev_assistant_msg.get("output_dir"):
#         assistant_msg["output_dir"] = prev_assistant_msg.get("output_dir")

#     if tool_logs:
#         assistant_msg["tool_logs"] = tool_logs
#     elif prev_assistant_msg and prev_assistant_msg.get("tool_logs"):
#         assistant_msg["tool_logs"] = prev_assistant_msg.get("tool_logs")

#     # -----------------------------
#     # 10. 保存 Agent 事件到 assistant message
#     # -----------------------------
#     if merged_agent_events:
#         # 数据库中保存下划线字段
#         assistant_msg["agent_events"] = merged_agent_events

#         # 同时保存驼峰字段，方便前端兼容
#         assistant_msg["agentEvents"] = merged_agent_events

#         # 当前 SSE 返回也带累计后的 agent_events
#         ans["agent_events"] = merged_agent_events
#         ans["agentEvents"] = merged_agent_events

#     # 保留最后一个单事件，方便前端调试或兜底展示
#     if ans.get("agent_event"):
#         assistant_msg["agent_event"] = ans.get("agent_event")

#     if ans.get("agentEvent"):
#         assistant_msg["agentEvent"] = ans.get("agentEvent")

#     # -----------------------------
#     # 11. 写回 conv.message
#     # -----------------------------
#     if not conv.message or conv.message[-1].get("role", "") != "assistant":
#         conv.message.append(assistant_msg)
#     else:
#         conv.message[-1] = assistant_msg

#     # -----------------------------
#     # 12. 写回 conv.reference
#     # -----------------------------
#     if conv.reference:
#         conv.reference[-1] = reference

#     print(".......................................................................................")
#     print(reference)
#     print(".......................................................................................")
#     print(ans)

#     return ans
from copy import deepcopy
def structure_answer(
    conv,
    ans,
    message_id,
    session_id,
    reference_index=None,
):
    """
    统一整理每个流式 ans：

    1. 格式化并累计 reference
    2. 保存工具信息
    3. 累积保存 agent_events 到 conv.message
    4. 防止 answer="" 覆盖已有正文
    5. 按 reference_index 更新本次回答对应的溯源
    6. 返回给 SSE 前端

    Args:
        conv:
            当前 Conversation 对象。

        ans:
            async_chat 返回的单次流式数据。

        message_id:
            本次回答关联的消息 ID。

        session_id:
            当前会话 ID。

        reference_index:
            completion() 中为本次回答创建的 reference 占位位置。
            重新生成时，通过该位置覆盖对应 reference，
            防止无条件 append 导致消息和溯源错位。
    """
    if ans is None:
        ans = {}

    # 防止 async_chat 返回的不是字典
    if not isinstance(ans, dict):
        ans = {
            "answer": str(ans),
        }

    # 如果没有 conv，只能整理返回数据，不进行持久化
    if not conv:
        reference = ans.get("reference")

        if not isinstance(reference, dict):
            reference = {}

        chunk_list = chunks_format(reference)
        reference["chunks"] = chunk_list
        reference["message_id"] = message_id

        ans["id"] = message_id
        ans["session_id"] = session_id
        ans["reference"] = reference
        ans["answer"] = ans.get("answer") or ""

        return ans

    if not conv.message:
        conv.message = []

    if not conv.reference:
        conv.reference = []

    # --------------------------------------------------
    # 1. 获取本次回答当前已经保存的 reference
    # --------------------------------------------------
    stored_reference = {}

    if (
        reference_index is not None
        and 0 <= reference_index < len(conv.reference)
        and isinstance(conv.reference[reference_index], dict)
    ):
        stored_reference = deepcopy(conv.reference[reference_index])

    elif conv.reference and isinstance(conv.reference[-1], dict):
        # 兼容未传 reference_index 的旧调用方式
        stored_reference = deepcopy(conv.reference[-1])

    # --------------------------------------------------
    # 2. 处理本次流式数据携带的 reference
    # --------------------------------------------------
    incoming_reference = ans.get("reference")

    if isinstance(incoming_reference, dict) and incoming_reference:
        # 使用新的 reference，但保留旧 reference 中本次没有返回的字段
        reference = deepcopy(stored_reference)
        reference.update(deepcopy(incoming_reference))
    else:
        # Agent 过程事件可能不携带 reference，
        # 此时保留上一轮流式事件已经保存的 reference
        reference = deepcopy(stored_reference)

    if not isinstance(reference, dict):
        reference = {}

    # reference 必须关联当前消息
    reference["message_id"] = message_id

    # 格式化 chunks
    chunk_list = chunks_format(reference)
    reference["chunks"] = chunk_list

    # doc_aggs 不存在时补充为空数组
    if "doc_aggs" not in reference:
        reference["doc_aggs"] = []

    # --------------------------------------------------
    # 3. 兼容 Agent 工具信息
    # --------------------------------------------------
    use_tools = ans.get("use_tools") or []
    output_dir = ans.get("output_dir")
    tool_logs = ans.get("tool_logs")

    # 当前流式事件没有工具信息时，尝试使用之前保存的信息
    if not use_tools:
        use_tools = reference.get("use_tools") or []

    if not output_dir:
        output_dir = reference.get("output_dir")

    if not tool_logs:
        tool_logs = reference.get("tool_logs")

    if use_tools:
        reference["use_tools"] = use_tools

    if output_dir:
        reference["output_dir"] = output_dir

    if tool_logs:
        reference["tool_logs"] = tool_logs

    # --------------------------------------------------
    # 4. 基础字段回写给前端
    # --------------------------------------------------
    ans["id"] = message_id
    ans["session_id"] = session_id
    ans["reference"] = reference

    if use_tools:
        ans["use_tools"] = use_tools

    if output_dir:
        ans["output_dir"] = output_dir

    if tool_logs:
        ans["tool_logs"] = tool_logs

    # --------------------------------------------------
    # 5. 提取当前 Agent 事件
    # --------------------------------------------------
    incoming_agent_events = extract_agent_events(ans)

    # --------------------------------------------------
    # 6. 获取当前正在生成的 assistant message
    # --------------------------------------------------
    prev_assistant_msg = None

    if (
        conv.message
        and isinstance(conv.message[-1], dict)
        and conv.message[-1].get("role", "") == "assistant"
    ):
        prev_assistant_msg = conv.message[-1]

    # --------------------------------------------------
    # 7. 读取旧 agent_events 并合并
    # --------------------------------------------------
    old_agent_events = []

    if prev_assistant_msg:
        old_agent_events = (
            prev_assistant_msg.get("agent_events")
            or prev_assistant_msg.get("agentEvents")
            or []
        )

    merged_agent_events = merge_agent_events(
        old_agent_events,
        incoming_agent_events,
    )

    # --------------------------------------------------
    # 8. 防止 answer="" 覆盖已有正文
    # --------------------------------------------------
    answer_text = ans.get("answer")

    # Agent 过程事件可能是：
    #
    # {
    #     "answer": "",
    #     "agent_event": {...}
    # }
    #
    # 这种情况下应该保留当前已生成的正文
    if (answer_text is None or answer_text == "") and prev_assistant_msg:
        answer_text = prev_assistant_msg.get("content", "")

    if answer_text is None:
        answer_text = ""

    # 确保前端始终可以读取 answer
    ans["answer"] = answer_text

    # --------------------------------------------------
    # 9. 构造 assistant message
    # --------------------------------------------------
    assistant_msg = {
        "role": "assistant",
        "content": answer_text,
        "created_at": (
            prev_assistant_msg.get("created_at")
            if (
                prev_assistant_msg
                and prev_assistant_msg.get("created_at")
            )
            else time.time()
        ),
        "id": message_id,
        "suggestions": ans.get(
            "suggestions",
            (
                prev_assistant_msg.get("suggestions", [])
                if prev_assistant_msg
                else []
            ),
        ),
    }

    # --------------------------------------------------
    # 10. 保存工具信息到 assistant message
    # --------------------------------------------------
    if use_tools:
        assistant_msg["use_tools"] = use_tools
    elif prev_assistant_msg and prev_assistant_msg.get("use_tools"):
        assistant_msg["use_tools"] = prev_assistant_msg.get("use_tools")

    if output_dir:
        assistant_msg["output_dir"] = output_dir
    elif prev_assistant_msg and prev_assistant_msg.get("output_dir"):
        assistant_msg["output_dir"] = prev_assistant_msg.get("output_dir")

    if tool_logs:
        assistant_msg["tool_logs"] = tool_logs
    elif prev_assistant_msg and prev_assistant_msg.get("tool_logs"):
        assistant_msg["tool_logs"] = prev_assistant_msg.get("tool_logs")

    # --------------------------------------------------
    # 11. 保存 Agent 事件到 assistant message
    # --------------------------------------------------
    if merged_agent_events:
        # 数据库保存下划线字段
        assistant_msg["agent_events"] = merged_agent_events

        # 同时保存驼峰字段，兼容前端
        assistant_msg["agentEvents"] = merged_agent_events

        # SSE 返回累计后的事件
        ans["agent_events"] = merged_agent_events
        ans["agentEvents"] = merged_agent_events

    # 保留当前最后一个单事件，方便前端调试或兜底展示
    if ans.get("agent_event"):
        assistant_msg["agent_event"] = ans.get("agent_event")

    if ans.get("agentEvent"):
        assistant_msg["agentEvent"] = ans.get("agentEvent")

    # --------------------------------------------------
    # 12. 写回 conv.message
    # --------------------------------------------------
    if (
        not conv.message
        or not isinstance(conv.message[-1], dict)
        or conv.message[-1].get("role", "") != "assistant"
    ):
        # 第一个流式事件：
        # 请求最后一条通常是 user，因此追加 assistant
        conv.message.append(assistant_msg)
    else:
        # 后续流式事件：
        # 替换当前正在生成的 assistant
        conv.message[-1] = assistant_msg

    # --------------------------------------------------
    # 13. 写回本次回答对应的 conv.reference
    # --------------------------------------------------
    if (
        reference_index is not None
        and 0 <= reference_index < len(conv.reference)
    ):
        # 推荐方式：
        # 精确更新 completion() 中创建的 reference 占位
        conv.reference[reference_index] = reference
    elif conv.reference:
        # 兼容旧调用方式
        conv.reference[-1] = reference
    else:
        # 理论上 completion() 已经创建过占位，
        # 这里作为兜底
        conv.reference.append(reference)

    print(
        "......................................................................................."
    )
    print("reference_index:", reference_index)
    print("reference:", reference)
    print(
        "......................................................................................."
    )
    print("ans:", ans)

    return ans

async def async_completion(tenant_id, chat_id, question, name="New session", session_id=None, stream=True, **kwargs):
    assert name, "`name` can not be empty."
    dia = DialogService.query(id=chat_id, tenant_id=tenant_id, status=StatusEnum.VALID.value)
    assert dia, "You do not own the chat."

    if not session_id:
        session_id = get_uuid()
        conv = {
            "id": session_id,
            "dialog_id": chat_id,
            "name": name,
            "message": [{"role": "assistant", "content": dia[0].prompt_config.get("prologue"), "created_at": time.time()}],
            "user_id": kwargs.get("user_id", "")
        }
        ConversationService.save(**conv)
        if stream:
            yield "data:" + json.dumps({"code": 0, "message": "",
                                        "data": {
                                            "answer": conv["message"][0]["content"],
                                            "reference": {},
                                            "audio_binary": None,
                                            "id": None,
                                        "session_id": session_id
                                        }},
                                    ensure_ascii=False) + "\n\n"
            yield "data:" + json.dumps({"code": 0, "message": "", "data": True}, ensure_ascii=False) + "\n\n"
            return

    conv = ConversationService.query(id=session_id, dialog_id=chat_id)
    if not conv:
        raise LookupError("Session does not exist")

    conv = conv[0]
    msg = []
    question = {
        "content": question,
        "role": "user",
        "id": str(uuid4())
    }
    conv.message.append(question)
    for m in conv.message:
        if m["role"] == "system":
            continue
        if m["role"] == "assistant" and not msg:
            continue
        msg.append(m)
    message_id = msg[-1].get("id")
    e, dia = DialogService.get_by_id(conv.dialog_id)

    kb_ids = kwargs.get("kb_ids",[])
    dia.kb_ids = list(set(dia.kb_ids + kb_ids))
    if not conv.reference:
        conv.reference = []
    conv.message.append({"role": "assistant", "content": "", "id": message_id})
    conv.reference.append({"chunks": [], "doc_aggs": []})

    if stream:
        try:
            async for ans in async_chat(dia, msg, True, **kwargs):
                ans = structure_answer(conv, ans, message_id, session_id)
                yield "data:" + json.dumps({"code": 0, "data": ans}, ensure_ascii=False) + "\n\n"
            ConversationService.update_by_id(conv.id, conv.to_dict())
        except Exception as e:
            yield "data:" + json.dumps({"code": 500, "message": str(e),
                                        "data": {"answer": "**ERROR**: " + str(e), "reference": []}},
                                       ensure_ascii=False) + "\n\n"
        yield "data:" + json.dumps({"code": 0, "data": True}, ensure_ascii=False) + "\n\n"

    else:
        answer = None
        async for ans in async_chat(dia, msg, False, **kwargs):
            answer = structure_answer(conv, ans, message_id, session_id)
            ConversationService.update_by_id(conv.id, conv.to_dict())
            break
        yield answer

async def async_iframe_completion(dialog_id, question, session_id=None, stream=True, **kwargs):
    e, dia = DialogService.get_by_id(dialog_id)
    assert e, "Dialog not found"
    if not session_id:
        session_id = get_uuid()
        conv = {
            "id": session_id,
            "dialog_id": dialog_id,
            "user_id": kwargs.get("user_id", ""),
            "message": [{"role": "assistant", "content": dia.prompt_config["prologue"], "created_at": time.time()}]
        }
        API4ConversationService.save(**conv)
        yield "data:" + json.dumps({"code": 0, "message": "",
                                    "data": {
                                        "answer": conv["message"][0]["content"],
                                        "reference": {},
                                        "audio_binary": None,
                                        "id": None,
                                        "session_id": session_id
                                    }},
                                   ensure_ascii=False) + "\n\n"
        yield "data:" + json.dumps({"code": 0, "message": "", "data": True}, ensure_ascii=False) + "\n\n"
        return
    else:
        session_id = session_id
        e, conv = API4ConversationService.get_by_id(session_id)
        assert e, "Session not found!"

    if not conv.message:
        conv.message = []
    messages = conv.message
    question = {
        "role": "user",
        "content": question,
        "id": str(uuid4())
    }
    messages.append(question)

    msg = []
    for m in messages:
        if m["role"] == "system":
            continue
        if m["role"] == "assistant" and not msg:
            continue
        msg.append(m)
    if not msg[-1].get("id"):
        msg[-1]["id"] = get_uuid()
    message_id = msg[-1]["id"]

    if not conv.reference:
        conv.reference = []
    conv.reference.append({"chunks": [], "doc_aggs": []})

    if stream:
        try:
            async for ans in async_chat(dia, msg, True, **kwargs):
                ans = structure_answer(conv, ans, message_id, session_id)
                yield "data:" + json.dumps({"code": 0, "message": "", "data": ans},
                                           ensure_ascii=False) + "\n\n"
            API4ConversationService.append_message(conv.id, conv.to_dict())
        except Exception as e:
            yield "data:" + json.dumps({"code": 500, "message": str(e),
                                        "data": {"answer": "**ERROR**: " + str(e), "reference": []}},
                                       ensure_ascii=False) + "\n\n"
        yield "data:" + json.dumps({"code": 0, "message": "", "data": True}, ensure_ascii=False) + "\n\n"

    else:
        answer = None
        async for ans in async_chat(dia, msg, False, **kwargs):
            answer = structure_answer(conv, ans, message_id, session_id)
            API4ConversationService.append_message(conv.id, conv.to_dict())
            break
        yield answer

    
