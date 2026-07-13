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
import json
import os
import re
import logging
from copy import deepcopy
import tempfile
from quart import Response, request
from api.apps import current_user, login_required
from api.db.db_models import APIToken
from api.db.services.conversation_service import ConversationService, structure_answer
from api.db.services.conversation_share_service import ConversationShareService
from api.db.services.dialog_service import DialogService, async_ask, async_chat, gen_mindmap
from api.db.services.llm_service import LLMBundle
from api.db.services.search_service import SearchService
from api.db.services.tenant_llm_service import TenantLLMService
from api.db.services.user_service import TenantService, UserTenantService
from api.utils.api_utils import get_data_error_result, get_json_result, get_request_json, server_error_response, validate_request
from rag.prompts.template import load_prompt
from rag.prompts.generator import chunks_format
from common.constants import RetCode, LLMType


@manager.route("/set", methods=["POST"])  # noqa: F821
@login_required
async def set_conversation():
    req = await get_request_json()
    conv_id = req.get("conversation_id")
    is_new = req.get("is_new")
    name = req.get("name", "New conversation")
    req["user_id"] = current_user.id

    if len(name) > 255:
        name = name[0:255]

    del req["is_new"]
    if not is_new:
        del req["conversation_id"]
        try:
            if not ConversationService.update_by_id(conv_id, req):
                return get_data_error_result(message="Conversation not found!")
            e, conv = ConversationService.get_by_id(conv_id)
            if not e:
                return get_data_error_result(message="Fail to update a conversation!")
            conv = conv.to_dict()
            return get_json_result(data=conv)
        except Exception as e:
            return server_error_response(e)

    try:
        e, dia = DialogService.get_by_id(req["dialog_id"])
        if not e:
            return get_data_error_result(message="Dialog not found")
        conv = {
            "id": conv_id,
            "dialog_id": req["dialog_id"],
            "name": name,
            "message": [{"role": "assistant", "content": dia.prompt_config["prologue"]}],
            "user_id": current_user.id,
            "reference": [],
        }
        ConversationService.save(**conv)
        return get_json_result(data=conv)
    except Exception as e:
        return server_error_response(e)


@manager.route("/get", methods=["GET"])  # noqa: F821
@login_required
async def get():
    conv_id = request.args["conversation_id"]
    try:
        e, conv = ConversationService.get_by_id(conv_id)
        if not e:
            return get_data_error_result(message="Conversation not found!")
        tenants = UserTenantService.query(user_id=current_user.id)
        for tenant in tenants:
            dialog = DialogService.query(tenant_id=tenant.tenant_id, id=conv.dialog_id)
            if dialog and len(dialog) > 0:
                avatar = dialog[0].icon
                break
        else:
            return get_json_result(data=False, message="Only owner of conversation authorized for this operation.", code=RetCode.OPERATING_ERROR)

        for ref in conv.reference:
            if isinstance(ref, list):
                continue
            ref["chunks"] = chunks_format(ref)

        conv = conv.to_dict()
        conv["avatar"] = avatar
        return get_json_result(data=conv)
    except Exception as e:
        return server_error_response(e)


@manager.route("/getsse/<dialog_id>", methods=["GET"])  # type: ignore # noqa: F821
def getsse(dialog_id):
    token = request.headers.get("Authorization").split()
    if len(token) != 2:
        return get_data_error_result(message='Authorization is not valid!"')
    token = token[1]
    objs = APIToken.query(beta=token)
    if not objs:
        return get_data_error_result(message='Authentication error: API key is invalid!"')
    try:
        e, conv = DialogService.get_by_id(dialog_id)
        if not e:
            return get_data_error_result(message="Dialog not found!")
        conv = conv.to_dict()
        conv["avatar"] = conv["icon"]
        del conv["icon"]
        return get_json_result(data=conv)
    except Exception as e:
        return server_error_response(e)


@manager.route("/rm", methods=["POST"])  # noqa: F821
@login_required
async def rm():
    req = await get_request_json()
    conv_ids = req["conversation_ids"]
    try:
        for cid in conv_ids:
            exist, conv = ConversationService.get_by_id(cid)
            if not exist:
                return get_data_error_result(message="Conversation not found!")
            tenants = UserTenantService.query(user_id=current_user.id)
            for tenant in tenants:
                if DialogService.query(tenant_id=tenant.tenant_id, id=conv.dialog_id):
                    break
            else:
                return get_json_result(data=False, message="Only owner of conversation authorized for this operation.", code=RetCode.OPERATING_ERROR)
            ConversationService.delete_by_id(cid)
        return get_json_result(data=True)
    except Exception as e:
        return server_error_response(e)


@manager.route("/list", methods=["GET"])  # noqa: F821
@login_required
async def list_conversation():
    dialog_id = request.args["dialog_id"]
    try:
        if not DialogService.query(tenant_id=current_user.id, id=dialog_id):
            return get_json_result(data=False, message="Only owner of dialog authorized for this operation.", code=RetCode.OPERATING_ERROR)
        convs = ConversationService.query(dialog_id=dialog_id, order_by=ConversationService.model.create_time, reverse=True)

        convs = [d.to_dict() for d in convs]
        return get_json_result(data=convs)
    except Exception as e:
        return server_error_response(e)


@manager.route("/completion", methods=["POST"])  # noqa: F821
@login_required
@validate_request("conversation_id", "messages")
async def completion():
    req = await get_request_json()
    print("收到的信息为-------------------------------------------------------")
    print(req)
    msg = []
    for m in req["messages"]:
        if m["role"] == "system":
            continue
        if m["role"] == "assistant" and not msg:
            continue
        msg.append(m)
    message_id = msg[-1].get("id")
    chat_model_id = req.get("llm_id", "")
    req.pop("llm_id", None)

    chat_model_config = {}
    for model_config in [
        "temperature",
        "top_p",
        "frequency_penalty",
        "presence_penalty",
        "max_tokens",
    ]:
        config = req.get(model_config)
        if config:
            chat_model_config[model_config] = config

    try:
        e, conv = ConversationService.get_by_id(req["conversation_id"])
        if not e:
            return get_data_error_result(message="Conversation not found!")
        conv.message = deepcopy(req["messages"])
        e, dia = DialogService.get_by_id(conv.dialog_id)
        if not e:
            return get_data_error_result(message="Dialog not found!")
        # del req["conversation_id"]
        # del req["messages"]
        conversation_id = req["conversation_id"]

        del req["conversation_id"]
        del req["messages"]

        req["conversation_id"] = conversation_id
        req["message_id"] = message_id

        if not conv.reference:
            conv.reference = []
        conv.reference = [r for r in conv.reference if r]
        conv.reference.append({"chunks": [], "doc_aggs": []})

        if chat_model_id:
            if not TenantLLMService.get_api_key(tenant_id=dia.tenant_id, model_name=chat_model_id):
                req.pop("chat_model_id", None)
                req.pop("chat_model_config", None)
                return get_data_error_result(message=f"Cannot use specified model {chat_model_id}.")
            dia.llm_id = chat_model_id
            dia.llm_setting = chat_model_config

        is_embedded = bool(chat_model_id)
        async def stream():
            nonlocal dia, msg, req, conv
            try:
                async for ans in async_chat(dia, msg, True, **req):
                    ans = structure_answer(conv, ans, message_id, conv.id)
                    yield "data:" + json.dumps({"code": 0, "message": "", "data": ans}, ensure_ascii=False) + "\n\n"
                if not is_embedded:
                    ConversationService.update_by_id(conv.id, conv.to_dict())
            except Exception as e:
                logging.exception(e)
                yield "data:" + json.dumps({"code": 500, "message": str(e), "data": {"answer": "**ERROR**: " + str(e), "reference": []}}, ensure_ascii=False) + "\n\n"

            yield "data:" + json.dumps({"code": 0, "message": "", "data": True}, ensure_ascii=False) + "\n\n"

        if req.get("stream", True):
            resp = Response(stream(), mimetype="text/event-stream")
            resp.headers.add_header("Cache-control", "no-cache")
            resp.headers.add_header("Connection", "keep-alive")
            resp.headers.add_header("X-Accel-Buffering", "no")
            resp.headers.add_header("Content-Type", "text/event-stream; charset=utf-8")
            return resp

        else:
            answer = None
            async for ans in async_chat(dia, msg, **req):
                answer = structure_answer(conv, ans, message_id, conv.id)
                if not is_embedded:
                    ConversationService.update_by_id(conv.id, conv.to_dict())
                break
            return get_json_result(data=answer)
    except Exception as e:
        return server_error_response(e)

@manager.route("/sequence2txt", methods=["POST"])  # noqa: F821
@login_required
async def sequence2txt():
    req = await request.form
    stream_mode = req.get("stream", "false").lower() == "true"
    files = await request.files
    if "file" not in files:
        return get_data_error_result(message="Missing 'file' in multipart form-data")

    uploaded = files["file"]

    ALLOWED_EXTS = {
        ".wav", ".mp3", ".m4a", ".aac",
        ".flac", ".ogg", ".webm",
        ".opus", ".wma"
    }

    filename = uploaded.filename or ""
    suffix = os.path.splitext(filename)[-1].lower()
    if suffix not in ALLOWED_EXTS:
        return get_data_error_result(message=
            f"Unsupported audio format: {suffix}. "
            f"Allowed: {', '.join(sorted(ALLOWED_EXTS))}"
        )
    fd, temp_audio_path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    await uploaded.save(temp_audio_path)

    tenants = TenantService.get_info_by(current_user.id)
    if not tenants:
        return get_data_error_result(message="Tenant not found!")

    asr_id = tenants[0]["asr_id"]
    if not asr_id:
        return get_data_error_result(message="No default ASR model is set")

    asr_mdl=LLMBundle(tenants[0]["tenant_id"], LLMType.SPEECH2TEXT, asr_id)
    if not stream_mode:
        text = asr_mdl.transcription(temp_audio_path)
        try:
            os.remove(temp_audio_path)
        except Exception as e:
            logging.error(f"Failed to remove temp audio file: {str(e)}")
        return get_json_result(data={"text": text})
    async def event_stream():
        try:
            for evt in asr_mdl.stream_transcription(temp_audio_path):
                yield f"data: {json.dumps(evt, ensure_ascii=False)}\n\n"
        except Exception as e:
            err = {"event": "error", "text": str(e)}
            yield f"data: {json.dumps(err, ensure_ascii=False)}\n\n"
        finally:
            try:
                os.remove(temp_audio_path)
            except Exception as e:
                logging.error(f"Failed to remove temp audio file: {str(e)}")

    return Response(event_stream(), content_type="text/event-stream")

@manager.route("/tts", methods=["POST"])  # noqa: F821
@login_required
async def tts():
    req = await get_request_json()
    text = req["text"]

    tenants = TenantService.get_info_by(current_user.id)
    if not tenants:
        return get_data_error_result(message="Tenant not found!")

    tts_id = tenants[0]["tts_id"]
    if not tts_id:
        return get_data_error_result(message="No default TTS model is set")

    tts_mdl = LLMBundle(tenants[0]["tenant_id"], LLMType.TTS, tts_id)

    def stream_audio():
        try:
            for txt in re.split(r"[，。/《》？；：！\n\r:;]+", text):
                for chunk in tts_mdl.tts(txt):
                    yield chunk
        except Exception as e:
            yield ("data:" + json.dumps({"code": 500, "message": str(e), "data": {"answer": "**ERROR**: " + str(e)}}, ensure_ascii=False)).encode("utf-8")

    resp = Response(stream_audio(), mimetype="audio/mpeg")
    resp.headers.add_header("Cache-Control", "no-cache")
    resp.headers.add_header("Connection", "keep-alive")
    resp.headers.add_header("X-Accel-Buffering", "no")

    return resp


@manager.route("/delete_msg", methods=["POST"])  # noqa: F821
@login_required
@validate_request("conversation_id", "message_id")
async def delete_msg():
    req = await get_request_json()
    e, conv = ConversationService.get_by_id(req["conversation_id"])
    if not e:
        return get_data_error_result(message="Conversation not found!")

    conv = conv.to_dict()
    for i, msg in enumerate(conv["message"]):
        if req["message_id"] != msg.get("id", ""):
            continue
        assert conv["message"][i + 1]["id"] == req["message_id"]
        conv["message"].pop(i)
        conv["message"].pop(i)
        conv["reference"].pop(max(0, i // 2 - 1))
        break

    ConversationService.update_by_id(conv["id"], conv)
    return get_json_result(data=conv)


@manager.route("/thumbup", methods=["POST"])  # noqa: F821
@login_required
@validate_request("conversation_id", "message_id")
async def thumbup():
    req = await get_request_json()
    e, conv = ConversationService.get_by_id(req["conversation_id"])
    if not e:
        return get_data_error_result(message="Conversation not found!")
    up_down = req.get("thumbup")
    feedback = req.get("feedback", "")
    conv = conv.to_dict()
    for i, msg in enumerate(conv["message"]):
        if req["message_id"] == msg.get("id", "") and msg.get("role", "") == "assistant":
            if up_down:
                msg["thumbup"] = True
                if "feedback" in msg:
                    del msg["feedback"]
            else:
                msg["thumbup"] = False
                if feedback:
                    msg["feedback"] = feedback
            break

    ConversationService.update_by_id(conv["id"], conv)
    return get_json_result(data=conv)


@manager.route("/ask", methods=["POST"])  # noqa: F821
@login_required
@validate_request("question", "kb_ids")
async def ask_about():
    req = await get_request_json()
    uid = current_user.id

    search_id = req.get("search_id", "")
    search_app = None
    search_config = {}
    if search_id:
        search_app = SearchService.get_detail(search_id)
    if search_app:
        search_config = search_app.get("search_config", {})

    async def stream():
        nonlocal req, uid
        try:
            async for ans in async_ask(req["question"], req["kb_ids"], uid, search_config=search_config):
                yield "data:" + json.dumps({"code": 0, "message": "", "data": ans}, ensure_ascii=False) + "\n\n"
        except Exception as e:
            yield "data:" + json.dumps({"code": 500, "message": str(e), "data": {"answer": "**ERROR**: " + str(e), "reference": []}}, ensure_ascii=False) + "\n\n"
        yield "data:" + json.dumps({"code": 0, "message": "", "data": True}, ensure_ascii=False) + "\n\n"

    resp = Response(stream(), mimetype="text/event-stream")
    resp.headers.add_header("Cache-control", "no-cache")
    resp.headers.add_header("Connection", "keep-alive")
    resp.headers.add_header("X-Accel-Buffering", "no")
    resp.headers.add_header("Content-Type", "text/event-stream; charset=utf-8")
    return resp


@manager.route("/mindmap", methods=["POST"])  # noqa: F821
@login_required
@validate_request("question", "kb_ids")
async def mindmap():
    req = await get_request_json()
    search_id = req.get("search_id", "")
    search_app = SearchService.get_detail(search_id) if search_id else {}
    search_config = search_app.get("search_config", {}) if search_app else {}
    kb_ids = search_config.get("kb_ids", [])
    kb_ids.extend(req["kb_ids"])
    kb_ids = list(set(kb_ids))

    mind_map = await gen_mindmap(req["question"], kb_ids, search_app.get("tenant_id", current_user.id), search_config)
    if "error" in mind_map:
        return server_error_response(Exception(mind_map["error"]))
    return get_json_result(data=mind_map)


@manager.route("/related_questions", methods=["POST"])  # noqa: F821
@login_required
@validate_request("question")
async def related_questions():
    req = await get_request_json()

    search_id = req.get("search_id", "")
    search_config = {}
    if search_id:
        if search_app := SearchService.get_detail(search_id):
            search_config = search_app.get("search_config", {})

    question = req["question"]

    chat_id = search_config.get("chat_id", "")
    chat_mdl = LLMBundle(current_user.id, LLMType.CHAT, chat_id)

    gen_conf = search_config.get("llm_setting", {"temperature": 0.9})
    if "parameter" in gen_conf:
        del gen_conf["parameter"]
    prompt = load_prompt("related_question")
    ans = await chat_mdl.async_chat(
        prompt,
        [
            {
                "role": "user",
                "content": f"""
Keywords: {question}
Related search terms:
    """,
            }
        ],
        gen_conf,
    )
    return get_json_result(data=[re.sub(r"^[0-9]\. ", "", a) for a in ans.split("\n") if re.match(r"^[0-9]\. ", a)])


import copy

def normalize_role(role):
    return str(role or "").lower()


def is_assistant_msg(msg):
    return normalize_role(msg.get("role")) == "assistant"


def is_user_msg(msg):
    return normalize_role(msg.get("role")) == "user"


def is_opening_assistant_message(index, msg):
    """
    第 0 条 assistant 是开场白，不消耗 reference
    """
    return index == 0 and is_assistant_msg(msg)


def build_share_messages_for_assistant_reference(
    messages,
    references,
    target_message_id,
):
    """
    reference 只对应真正的 assistant 回复，不包含第 0 条 assistant 开场白。

    后端兼容逻辑：
    如果 user 和 assistant 共用同一个 id，
    优先选择 assistant 那条作为分享截止消息。
    """

    if not isinstance(messages, list):
        messages = []

    if not isinstance(references, list):
        references = []

    # 1. 找到点击分享的消息位置
    #    如果同一个 id 同时出现在 user 和 assistant 上，优先选 assistant
    target_index = -1
    fallback_index = -1

    for idx, msg in enumerate(messages):
        if not isinstance(msg, dict):
            continue

        if msg.get("id") != target_message_id:
            continue

        # 先记录第一个匹配的，作为兜底
        if fallback_index < 0:
            fallback_index = idx

        # 如果匹配到 assistant，优先使用 assistant
        if is_assistant_msg(msg):
            target_index = idx
            break

    # 如果没有找到 assistant，但找到同 id 的其他消息，就用兜底
    if target_index < 0:
        target_index = fallback_index

    if target_index < 0:
        return None

    # 2. 截取当前消息以及上面的所有消息
    selected_messages = messages[: target_index + 1]

    result = []

    # 3. 给真正的 assistant 回复依次挂 reference
    #    第 0 条 assistant 开场白不消耗 reference
    assistant_ref_index = 0

    for idx, msg in enumerate(selected_messages):
        if not isinstance(msg, dict):
            continue

        role = msg.get("role")
        ref = None

        is_opening = is_opening_assistant_message(idx, msg)

        if is_assistant_msg(msg) and not is_opening:
            if assistant_ref_index < len(references):
                # 用 deepcopy，避免 chunks_format 改到 conv.reference 原数据
                ref = copy.deepcopy(references[assistant_ref_index])

            assistant_ref_index += 1

        if ref and isinstance(ref, dict):
            try:
                ref["chunks"] = chunks_format(ref)
            except Exception:
                pass

        item = {
            "id": msg.get("id"),
            "role": role,
            "content": msg.get("content"),
            "reference": ref if is_assistant_msg(msg) and not is_opening else None,
        }

        if msg.get("prompt"):
            item["prompt"] = msg.get("prompt")

        if msg.get("created_at"):
            item["created_at"] = msg.get("created_at")

        if msg.get("create_time"):
            item["create_time"] = msg.get("create_time")

        result.append(item)

    return result


@manager.route("/share", methods=["POST"])
@login_required
async def create_share():
    """
    创建分享快照

    前端传:
    {
        "conversation_id": "xxx",
        "message_id": "xxx"
    }
    """
    try:
        req = await get_request_json()


        conversation_id = req.get("conversation_id")
        message_id = req.get("message_id")

        if not conversation_id:
            return get_json_result(
                data=False,
                message="conversation_id is required",
                code=RetCode.ARGUMENT_ERROR,
            )

        if not message_id:
            return get_json_result(
                data=False,
                message="message_id is required",
                code=RetCode.ARGUMENT_ERROR,
            )

        e, conv = ConversationService.get_by_id(conversation_id)
        if not e:
            return get_data_error_result(message="Conversation not found!")

        # 权限校验，模仿你原来的 get 接口
        tenants = UserTenantService.query(user_id=current_user.id)

        for tenant in tenants:
            dialog = DialogService.query(
                tenant_id=tenant.tenant_id,
                id=conv.dialog_id,
            )
            if dialog and len(dialog) > 0:
                break
        else:
            return get_json_result(
                data=False,
                message="Only owner of conversation authorized for this operation.",
                code=RetCode.OPERATING_ERROR,
            )

        messages = conv.message or []
        references = conv.reference or []

        share_messages = build_share_messages_for_assistant_reference(
            messages=messages,
            references=references,
            target_message_id=message_id,
        )

        if share_messages is None:
            return get_json_result(
                data=False,
                message="Message not found in conversation.",
                code=RetCode.DATA_ERROR,
            )

        # 过滤空内容
        share_messages = [
            item for item in share_messages
            if item.get("content")
        ]

        snapshot = {
            "conversation_id": conv.id,
            "dialog_id": conv.dialog_id,
            "name": conv.name,
            "messages": share_messages,
        }

        share = ConversationShareService.create_share(
            conversation_id=conv.id,
            dialog_id=conv.dialog_id,
            name=conv.name,
            user_id=current_user.id,
            snapshot=snapshot,
        )

        web_url = os.environ.get("WEB_URL", "").rstrip("/")
        if not web_url:
            web_url = request.host_url.rstrip("/")
        web_url = "http://localhost:9222"
        share_url = f"{web_url}/share/chat/{share.id}"

        return get_json_result(
            data={
                "share_id": share.id,
                "url": share_url,
            }
        )

    except Exception as e:
        return server_error_response(e)

# 获取分享快照接口
@manager.route("/share/<share_id>", methods=["GET"])
async def get_share(share_id):
    try:
        share = ConversationShareService.get_share_by_id(share_id)

        if not share:
            return get_json_result(
                data=False,
                message="Share not found.",
                code=RetCode.DATA_ERROR,
            )

        return get_json_result(
            data={
                "id": share.get("id"),
                "conversation_id": share.get("conversation_id"),
                "dialog_id": share.get("dialog_id"),
                "name": share.get("name"),
                "snapshot": share.get("snapshot"),
            }
        )

    except Exception as e:
        return server_error_response(e)
    
def normalize_role(role):
    return str(role or "").lower()


def is_assistant_msg(msg):
    role = normalize_role(msg.get("role"))
    return role == "assistant"


def is_user_msg(msg):
    role = normalize_role(msg.get("role"))
    return role == "user"


def is_opening_assistant_message(index, msg):
    """
    第 0 条 assistant 是开场白，不消耗 reference
    """
    return index == 0 and is_assistant_msg(msg)


def build_rebase_messages_and_references(
    messages,
    references,
    target_message_id,
):
    """
    用于变基 / 分支会话。

    返回:
    - new_messages: 截取后的 message
    - new_references: 截取后的 reference

    注意:
    你的 reference 只对应真正的 assistant 回复，
    不包含第 0 条 assistant 开场白。

    如果 user 和 assistant 共用同一个 id，
    优先选择 assistant 那条作为截止消息。
    """

    if not isinstance(messages, list):
        messages = []

    if not isinstance(references, list):
        references = []

    # 1. 找到点击消息位置
    # 如果同一个 id 同时出现在 user 和 assistant 上，优先选 assistant
    target_index = -1
    fallback_index = -1

    for idx, msg in enumerate(messages):
        if not isinstance(msg, dict):
            continue

        if msg.get("id") != target_message_id:
            continue

        # 先记录第一个匹配的，兜底用
        if fallback_index < 0:
            fallback_index = idx

        # 优先使用 assistant
        if is_assistant_msg(msg):
            target_index = idx
            break

    if target_index < 0:
        target_index = fallback_index

    if target_index < 0:
        return None, None

    # 2. 截取当前消息以及上面的所有消息
    new_messages = copy.deepcopy(messages[: target_index + 1])

    # 3. 截取对应 reference
    new_references = []

    assistant_ref_index = 0

    for idx, msg in enumerate(new_messages):
        if not isinstance(msg, dict):
            continue

        # 第 0 条 assistant 开场白不消耗 reference
        is_opening = is_opening_assistant_message(idx, msg)

        if is_assistant_msg(msg) and not is_opening:
            if assistant_ref_index < len(references):
                new_references.append(copy.deepcopy(references[assistant_ref_index]))
            else:
                # 保持 reference 数量和 assistant 回复数量一致
                new_references.append({"chunks": []})

            assistant_ref_index += 1

    return new_messages, new_references

@manager.route("/rebase", methods=["POST"])
@login_required
async def rebase_conversation():
    """
    从某条消息处分支新会话。

    前端传:
    {
        "conversation_id": "xxx",
        "message_id": "xxx"
    }

    返回:
    {
        "conversation_id": "新的 conversation id"
    }
    """
    try:
        req = await get_request_json()

        conversation_id = req.get("conversation_id")
        message_id = req.get("message_id")

        if not conversation_id:
            return get_json_result(
                data=False,
                message="conversation_id is required",
                code=RetCode.ARGUMENT_ERROR,
            )

        if not message_id:
            return get_json_result(
                data=False,
                message="message_id is required",
                code=RetCode.ARGUMENT_ERROR,
            )

        e, conv = ConversationService.get_by_id(conversation_id)
        if not e:
            return get_data_error_result(message="Conversation not found!")

        # 权限校验，和 share/get 保持一致
        tenants = UserTenantService.query(user_id=current_user.id)

        for tenant in tenants:
            dialog = DialogService.query(
                tenant_id=tenant.tenant_id,
                id=conv.dialog_id,
            )
            if dialog and len(dialog) > 0:
                break
        else:
            return get_json_result(
                data=False,
                message="Only owner of conversation authorized for this operation.",
                code=RetCode.OPERATING_ERROR,
            )

        messages = conv.message or []
        references = conv.reference or []

        new_messages, new_references = build_rebase_messages_and_references(
            messages=messages,
            references=references,
            target_message_id=message_id,
        )

        if new_messages is None:
            return get_json_result(
                data=False,
                message="Message not found in conversation.",
                code=RetCode.DATA_ERROR,
            )

        # 不建议这里过滤空内容，否则可能导致 message/reference 对不上
        # 如果你确实要过滤，需要同步重新计算 reference
        # 所以这里保持原样最安全

        old_name = conv.name or "新会话"
        new_name = ConversationService.generate_branch_name(
            dialog_id=conv.dialog_id,
            base_name=conv.name or "新会话",
            user_id=current_user.id,
        )

        # 防止 name 超长
        if len(new_name) > 255:
            new_name = new_name[:255]

        new_conv = ConversationService.create_branch_conversation(
            dialog_id=conv.dialog_id,
            name=new_name,
            message=new_messages,
            reference=new_references,
            user_id=current_user.id,
        )

        return get_json_result(
            data={
                "conversation_id": new_conv["id"],
                "id": new_conv["id"],
                "name": new_conv.get("name"),
                "dialog_id": new_conv.get("dialog_id"),
            }
        )

    except Exception as e:
        return server_error_response(e)