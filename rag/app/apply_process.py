# apply_process.py
#
# 一个完整流程生成一个 chunk。
# 流程提取使用文本模型，不使用 IMAGE2TEXT/VLM。

import asyncio
import concurrent.futures
import json
import logging
import re
from typing import Any, Dict, List, Optional

from common.constants import LLMType
from api.db.services.llm_service import LLMBundle

# RAGFlow 标准分词 / chunk 出口。
# tokenize_chunks 会统一补齐 content_ltks / content_sm_ltks /
# doc_id / kb_id / docnm_kwd / title_tks / title_sm_tks /
# create_timestamp_flt / create_time 等字段，
# 保证和 ES mapping 完全一致。
from rag.nlp import rag_tokenizer, tokenize_chunks


logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# 导入原有的 naive 解析器
# -----------------------------------------------------------------------------
# 注意：rag/app/naive.py 里提供的是 chunk 函数，naive 是模块而不是函数/类。
# 所以这里导入模块本身，调用时使用 naive_module.chunk(...)。
try:
    from rag.app import naive as naive_module
except ImportError:
    try:
        from . import naive as naive_module
    except ImportError:
        try:
            import naive as naive_module
        except ImportError:
            naive_module = None


# -----------------------------------------------------------------------------
# 基础工具
# -----------------------------------------------------------------------------

def _safe_callback(callback, progress: float, message: str):
    """兼容 callback(progress, message) 和 callback(msg=...) 两种写法。"""
    if not callback:
        return

    try:
        callback(progress, message)
    except TypeError:
        try:
            callback(prog=progress, msg=message)
        except TypeError:
            try:
                callback(msg=message)
            except Exception:
                pass
    except Exception:
        logger.exception("Parser callback failed")


def _section_to_text(section: Any) -> str:
    """从不同解析器返回的 section/chunk 中提取文本。"""
    if section is None:
        return ""

    if isinstance(section, str):
        return section.strip()

    if isinstance(section, dict):
        for key in (
            "content_with_weight",
            "content",
            "text",
            "content_ltks",
            "chunk_content",
        ):
            value = section.get(key)
            if value:
                return str(value).strip()
        return ""

    if isinstance(section, (tuple, list)):
        if not section:
            return ""
        return _section_to_text(section[0])

    return str(section).strip()


def _result_to_text(result: Any) -> str:
    """将 naive 解析器返回的结果统一转换为一段文本。"""
    if result is None:
        return ""

    if isinstance(result, str):
        return result.strip()

    if isinstance(result, dict):
        return _section_to_text(result)

    if isinstance(result, (tuple, list)):
        lines = []
        for item in result:
            text = _section_to_text(item)
            if text:
                lines.append(text)
        return "\n\n".join(lines)

    return str(result).strip()


def _split_text(text: str, max_chars: int) -> List[str]:
    """按段落切分长文本，避免一次调用超过模型上下文。"""
    if not text:
        return []

    max_chars = max(2000, int(max_chars or 12000))
    paragraphs = text.splitlines()
    parts = []
    current = []
    current_length = 0

    for paragraph in paragraphs:
        paragraph = paragraph.rstrip()
        paragraph_length = len(paragraph) + 1

        if current and current_length + paragraph_length > max_chars:
            parts.append("\n".join(current).strip())
            current = []
            current_length = 0

        if len(paragraph) > max_chars:
            if current:
                parts.append("\n".join(current).strip())
                current = []
                current_length = 0

            for start in range(0, len(paragraph), max_chars):
                parts.append(paragraph[start:start + max_chars].strip())
            continue

        current.append(paragraph)
        current_length += paragraph_length

    if current:
        parts.append("\n".join(current).strip())

    return [part for part in parts if part]


def _parse_json(answer: Any) -> Any:
    """兼容模型返回 JSON、```json``` 以及前后带解释文字的情况。"""
    if answer is None:
        return None

    if isinstance(answer, (list, dict)):
        return answer

    text = str(answer).strip()
    if not text:
        return None

    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char not in "[{":
            continue
        try:
            value, _ = decoder.raw_decode(text[index:])
            return value
        except json.JSONDecodeError:
            continue

    logger.warning("模型返回的内容不是合法 JSON：%s", text[:1000])
    return None


def _extract_answer(response: Any) -> str:
    """将不同模型封装返回值转换成字符串。"""
    if response is None:
        return ""

    if isinstance(response, str):
        return response

    if isinstance(response, bytes):
        return response.decode("utf-8", errors="replace")

    if isinstance(response, dict):
        for key in ("content", "text", "answer", "response", "output"):
            value = response.get(key)
            if value is not None:
                return str(value)

        choices = response.get("choices")
        if isinstance(choices, list) and choices:
            choice = choices[0]
            if isinstance(choice, dict):
                message = choice.get("message")
                if isinstance(message, dict) and message.get("content") is not None:
                    return str(message["content"])
                if choice.get("text") is not None:
                    return str(choice["text"])

    content = getattr(response, "content", None)
    if content is not None:
        return str(content)

    return str(response)


def _consume_stream(response: Any) -> str:
    """消费 chat_streamly 返回的生成器（当前路径未用到，保留备用）。"""
    if response is None:
        return ""

    if isinstance(response, (str, bytes, dict)):
        return _extract_answer(response)

    try:
        iterator = iter(response)
    except TypeError:
        return _extract_answer(response)

    parts = []
    for item in iterator:
        text = _extract_answer(item)
        if text:
            parts.append(text)

    return "".join(parts)


def _run_async(coro):
    """在同步上下文中安全地运行协程。"""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()

    return asyncio.run(coro)


def _call_text_model(
    tenant_id: str,
    prompt: str,
    llm_id: Optional[str] = None,
    lang: str = "Chinese",
) -> str:
    """调用 RAGFlow 的文本模型（Chat）。

    对齐 RAGFlow 内部用法：
        await chat_mdl.async_chat(system_prompt, history)
    """
    if not tenant_id:
        raise ValueError("tenant_id is required for process extraction")

    llm = LLMBundle(tenant_id, LLMType.CHAT, llm_name=llm_id, lang=lang)

    async_chat = getattr(llm, "async_chat", None)
    if callable(async_chat):
        return _extract_answer(
            _run_async(async_chat(prompt, []))
        )

    model = getattr(llm, "mdl", None)
    if model is not None:
        mdl_async_chat = getattr(model, "async_chat", None)
        if callable(mdl_async_chat):
            return _extract_answer(
                _run_async(mdl_async_chat(prompt, []))
            )

        chat = getattr(model, "chat", None)
        if callable(chat):
            try:
                return _extract_answer(chat(prompt))
            except TypeError:
                return _extract_answer(
                    chat([{"role": "user", "content": prompt}])
                )

    raise RuntimeError(
        f"当前 LLMBundle 没有可用的文本生成接口；"
        f"可调用方法：{[m for m in dir(llm) if not m.startswith('_')]}"
    )


# -----------------------------------------------------------------------------
# 流程提取
# -----------------------------------------------------------------------------

_PROCESS_PROMPT = """
你是一个文档流程提取器。

请从下面的文章内容中提取所有明确存在的、相对完整的流程。

【什么是流程】
包括但不限于：办理流程、申请流程、审批流程、操作流程、业务流程、工作流程、实验流程、报名流程、审核流程、入学流程、报销流程、注册流程、配置流程、使用流程等。

【严格要求】
1. 一篇文章可能有多个流程，必须全部提取。
2. 一个完整流程只能返回一个对象，不能按步骤拆成多个对象。
3. content 必须包含这个流程的完整内容，包括流程标题、前置条件、材料、操作步骤、审核要求、注意事项、结果等原文信息。
4. 不要把背景介绍、概念解释、单独的注意事项、普通制度说明当成流程。
5. 不要补充原文中不存在的信息。
6. 如果当前文章内容没有明确流程，返回空数组 []。
7. 只返回合法 JSON，不要返回 Markdown，不要输出解释。

【返回格式】
[
  {
    "process_name": "流程名称",
    "content": "该完整流程的原文内容"
  }
]

【文章内容】
{text}
"""


_MERGE_PROMPT = """
请合并下面从同一篇文章中提取出的流程候选项。

要求：
1. 相同流程或同一流程的不同片段必须合并为一个流程。
2. 不同流程不能合并。
3. 保留每个流程的完整内容。
4. 删除明显重复的流程。
5. 只保留文章中确实存在的流程。
6. 只返回合法 JSON 数组，不要输出解释。

返回格式：
[
  {
    "process_name": "流程名称",
    "content": "完整流程内容"
  }
]

流程候选项：
{candidates}
"""


def _normalize_processes(value: Any) -> List[Dict[str, str]]:
    if isinstance(value, dict):
        value = [value]

    if not isinstance(value, list):
        return []

    result = []
    for item in value:
        if not isinstance(item, dict):
            continue

        name = str(
            item.get("process_name")
            or item.get("name")
            or item.get("title")
            or "未命名流程"
        ).strip()
        content = str(
            item.get("content")
            or item.get("process_content")
            or item.get("text")
            or ""
        ).strip()

        if content:
            result.append({
                "process_name": name,
                "content": content,
            })

    return result


def _deduplicate_processes(processes: List[Dict[str, str]]) -> List[Dict[str, str]]:
    result = []
    seen = set()

    for process in processes:
        name = process["process_name"]
        content = process["content"]
        key = re.sub(r"\s+", "", name + content).lower()

        if not key or key in seen:
            continue

        seen.add(key)
        result.append(process)

    return result


def _to_process_chunks(
    processes: List[Dict[str, str]],
    filename: str,
    doc_id: str = "",
    kb_id: str = "",
    is_english: bool = False,
) -> List[Dict[str, Any]]:
    """将每个完整流程转换为符合 RAGFlow 标准的 chunk。"""
    if not processes:
        return []

    texts: List[str] = []
    metas: List[Dict[str, str]] = []

    for index, process in enumerate(processes, start=1):
        process_name = process["process_name"].strip()
        process_content = process["content"].strip()
        if not process_content:
            continue

        texts.append(f"流程名称：{process_name}\n{process_content}")
        metas.append({
            "process_id": f"process_{index:03d}",
            "process_name": process_name,
        })

    if not texts:
        return []

    title_source = re.sub(r"\.[a-zA-Z0-9]+$", "", filename or "unknown_doc")
    title_tks = rag_tokenizer.tokenize(title_source)

    # 与 rag/app/naive.py 保持一致。
    doc: Dict[str, Any] = {
        "docnm_kwd": filename,
        "title_tks": title_tks,
        "title_sm_tks": rag_tokenizer.fine_grained_tokenize(title_tks),
    }

    # tokenize_chunks 不会自行生成这些归属字段。
    if doc_id:
        doc["doc_id"] = doc_id
    if kb_id:
        doc["kb_id"] = kb_id

    try:
        # 参数形式与 naive.py 一致；pdf_parser 对流程纯文本没有意义，传 None。
        chunks = tokenize_chunks(texts, doc, is_english, None)
    except Exception as exc:
        # 不建议吞掉该错误并返回不完整的伪标准 chunk，
        # 否则任务看似成功，但后续索引一定有问题。
        logger.exception("Failed to tokenize process chunks: %s", exc)
        raise RuntimeError(f"Failed to tokenize process chunks: {exc}") from exc

    final_chunks: List[Dict[str, Any]] = []

    for index, chunk in enumerate(chunks):
        if not isinstance(chunk, dict):
            logger.warning(
                "Unexpected tokenize_chunks result type: %s",
                type(chunk).__name__,
            )
            continue

        # RAGFlow 标准正文是 content_with_weight。
        content = str(
            chunk.get("content_with_weight")
            or chunk.get("content")
            or ""
        ).strip()

        if not content:
            logger.warning("Skipped empty process chunk at index %s", index)
            continue

        chunk["content_with_weight"] = content
        chunk.setdefault("content_ltks", rag_tokenizer.tokenize(content))
        chunk.setdefault(
            "content_sm_ltks",
            rag_tokenizer.fine_grained_tokenize(chunk["content_ltks"]),
        )

        if index < len(metas):
            chunk["process_id"] = metas[index]["process_id"]
            chunk["process_name"] = metas[index]["process_name"]

        # 可作为自定义筛选字段使用；不要以它替代标准正文类型字段。
        chunk["chunk_type"] = "process"

        final_chunks.append(chunk)

    logger.info(
        "Built %s process chunks from %s extracted processes for %s",
        len(final_chunks),
        len(processes),
        filename,
    )
    return final_chunks
# -----------------------------------------------------------------------------
# 对外解析器入口
# -----------------------------------------------------------------------------

def chunk(
    filename,
    binary=None,
    from_page=0,
    to_page=100000,
    lang="Chinese",
    callback=None,
    **kwargs,
):
    """
    流程解析器入口。

    参数：
        tenant_id: 必填，用于调用文本模型
        llm_id: 可选，指定聊天模型，不传则用租户默认
        process_max_chars: 单次模型调用的最大字符数，默认 12000
        doc_id / kb_id: 从上游透传，用于溯源
    """
    tenant_id = kwargs.get("tenant_id")
    if not tenant_id:
        raise ValueError("apply_process requires tenant_id")

    llm_id = kwargs.get("llm_id")
    doc_id = kwargs.get("doc_id") or ""
    kb_id = kwargs.get("kb_id") or ""
    is_english = lang.lower() == "english"

    _safe_callback(callback, 0.05, "Start to parse document.")

    source_text = kwargs.get("source_text")
    sections = kwargs.get("sections")

    if source_text:
        text = str(source_text)
    elif sections is not None:
        text = _result_to_text(sections)
    else:
        if naive_module is None:
            raise ImportError(
                "无法导入 naive 模块，请检查 rag/app/naive.py 是否存在"
            )

        naive_kwargs = dict(kwargs)
        naive_kwargs.pop("extract_process", None)
        naive_kwargs.pop("source_text", None)
        naive_kwargs.pop("sections", None)
        naive_kwargs.pop("process_max_chars", None)

        parsed = naive_module.chunk(
            filename,
            binary=binary,
            from_page=from_page,
            to_page=to_page,
            lang=lang,
            callback=callback,
            **naive_kwargs,
        )
        text = _result_to_text(parsed)

    if not text.strip():
        _safe_callback(callback, 1.0, "No text found in document.")
        return []

    max_chars = int(kwargs.get("process_max_chars", 12000) or 12000)
    text_parts = _split_text(text, max_chars)
    candidates = []

    for index, part in enumerate(text_parts, start=1):
        _safe_callback(
            callback,
            0.10 + 0.55 * index / max(len(text_parts), 1),
            f"Extracting processes {index}/{len(text_parts)}...",
        )

        # 提示词里含 JSON 示例的 {}，不能用 .format()，这里用 replace。
        prompt = _PROCESS_PROMPT.replace("{text}", part)
        print(prompt)
        try:
            answer = _call_text_model(
                tenant_id,
                prompt,
                llm_id=llm_id,
                lang=lang,
            )
            print(answer)
            candidates.extend(_normalize_processes(_parse_json(answer)))
        except Exception as exc:
            logger.exception("Failed to extract process from %s: %s", filename, exc)

    candidates = _deduplicate_processes(candidates)

    if len(text_parts) > 1 and candidates:
        try:
            merge_input = json.dumps(candidates, ensure_ascii=False)
            merge_answer = _call_text_model(
                tenant_id,
                _MERGE_PROMPT.replace("{candidates}", merge_input),
                llm_id=llm_id,
                lang=lang,
            )
            merged = _normalize_processes(_parse_json(merge_answer))
            if merged:
                candidates = _deduplicate_processes(merged)
        except Exception as exc:
            logger.exception("Failed to merge process candidates: %s", exc)

    process_chunks = _to_process_chunks(
        candidates,
        filename,
        doc_id=doc_id,
        kb_id=kb_id,
        is_english=is_english,
    )
    _safe_callback(
        callback,
        0.95,
        f"Extracted {len(process_chunks)} process chunks.",
    )
    _safe_callback(callback, 1.0, "Process parsing finished.")

    return process_chunks