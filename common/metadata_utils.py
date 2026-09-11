#
#  Copyright 2025 The InfiniFlow Authors. All Rights Reserved.
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
import logging
from typing import Any, Callable, Dict

import json_repair

from rag.prompts.generator import gen_meta_filter, gen_special_meta_filter,gen_ab_group_logic


def convert_conditions(metadata_condition):
    if metadata_condition is None:
        metadata_condition = {}
    op_mapping = {
        "is": "=",
        "not is": "≠"
    }
    return [
        {
            "op": op_mapping.get(cond["comparison_operator"], cond["comparison_operator"]),
            "key": cond["name"],
            "value": cond["value"]
        }
        for cond in metadata_condition.get("conditions", [])
    ]

import ast
import re


def parse_meta_value_to_list(raw_value):
    """
    原始 metadata 的值解析为 list[str]
    """
    if raw_value is None:
        return []

    if isinstance(raw_value, list):
        return [str(x).strip() for x in raw_value if str(x).strip()]

    if isinstance(raw_value, tuple):
        return [str(x).strip() for x in raw_value if str(x).strip()]

    s = str(raw_value).strip()
    if not s:
        return []

    try:
        parsed = ast.literal_eval(s)
        if isinstance(parsed, list):
            return [str(x).strip() for x in parsed if str(x).strip()]
        if isinstance(parsed, tuple):
            return [str(x).strip() for x in parsed if str(x).strip()]
    except Exception:
        pass

    return [s]


def parse_filter_value_to_list(value):
    """
    模型输出的 value 解析为 list[str]
    """
    if value is None:
        return []

    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]

    if isinstance(value, tuple):
        return [str(x).strip() for x in value if str(x).strip()]

    s = str(value).strip()
    if not s:
        return []

    try:
        parsed = ast.literal_eval(s)
        if isinstance(parsed, list):
            return [str(x).strip() for x in parsed if str(x).strip()]
        if isinstance(parsed, tuple):
            return [str(x).strip() for x in parsed if str(x).strip()]
    except Exception:
        pass

    return [x.strip() for x in re.split(r"[,，]", s) if x.strip()]


def meta_filter(metas: dict, filters: list[dict], logic: str = "and"):
    """
    支持多标签、多值条件的 metadata 过滤器。

    metas:
    {
        "knowledge_category": {
            "['打浆', '质量检测与控制']": ["doc1"],
            "['打浆', '调制']": ["doc2"]
        }
    }

    filters:
    [
        {"key": "knowledge_category", "value": "打浆, 质量检测与控制", "op": "in"}
    ]
    """
    if not filters:
        return []

    def match_one(raw_input, operator, value):
        input_list = parse_meta_value_to_list(raw_input)
        value_list = parse_filter_value_to_list(value)

        input_lower = [x.lower() for x in input_list]
        value_lower = [x.lower() for x in value_list]

        input_set = set(input_lower)
        value_set = set(value_lower)

        # 空值判断
        if operator == "empty":
            return len(input_list) == 0

        if operator == "not empty":
            return len(input_list) > 0

        # contains / not contains
        # 定义：
        # contains: 查询中的任一值，是文档任一值的子串
        # not contains: 查询中的所有值，都不是文档任一值的子串
        if operator == "contains":
            if not value_list:
                return False
            return any(
                target in x
                for target in value_lower
                for x in input_lower
            )

        if operator == "not contains":
            if not value_list:
                return False
            return all(
                target not in x
                for target in value_lower
                for x in input_lower
            )

        # in / not in
        # in: 查询集合是文档集合的子集
        # not in: 两者没有交集
        if operator == "in":
            if not value_set:
                return False
            return value_set.issubset(input_set)

        if operator == "not in":
            if not value_set:
                return False
            return input_set.isdisjoint(value_set)

        # start with / end with
        if operator == "start with":
            if not value_list:
                return False
            return any(
                x.startswith(target)
                for target in value_lower
                for x in input_lower
            )

        if operator == "end with":
            if not value_list:
                return False
            return any(
                x.endswith(target)
                for target in value_lower
                for x in input_lower
            )

        # 数值 / 日期 / 精确比较
        # 约定：只取 value_list[0] 作为比较目标
        if operator in ["=", "≠", ">", "<", "≥", "≤"]:
            if not value_list:
                return False

            target = value_list[0]

            for x in input_list:
                left = x
                right = target

                try:
                    left = float(left)
                    right = float(right)
                except Exception:
                    left = str(left)
                    right = str(right)

                try:
                    if operator == "=" and left == right:
                        return True
                    if operator == "≠" and left != right:
                        return True
                    if operator == ">" and left > right:
                        return True
                    if operator == "<" and left < right:
                        return True
                    if operator == "≥" and left >= right:
                        return True
                    if operator == "≤" and left <= right:
                        return True
                except Exception:
                    pass

            return False

        return False

    # 每个 filter 先独立得到一个集合
    result_sets = []

    for f in filters:
        key = f.get("key")
        operator = f.get("op")
        value = f.get("value")

        if not key or key not in metas:
            continue

        v2docs = metas[key]
        matched_ids = set()

        for raw_input, docids in v2docs.items():
            try:
                if match_one(raw_input, operator, value):
                    matched_ids.update(docids)
            except Exception:
                pass

        result_sets.append(matched_ids)

    if not result_sets:
        return []

    # 多条件合并
    if logic == "or":
        final_ids = set()
        for s in result_sets:
            final_ids |= s
        return list(final_ids)

    # 默认 and
    final_ids = result_sets[0]
    for s in result_sets[1:]:
        final_ids &= s
        if not final_ids:
            return []

    return list(final_ids)

# def meta_filter(metas: dict, filters: list[dict], logic: str = "and"):
#     doc_ids = set([])

#     def filter_out(v2docs, operator, value):
#         ids = []
#         for input, docids in v2docs.items():
#             if operator in ["=", "≠", ">", "<", "≥", "≤"]:
#                 try:
#                     input = float(input)
#                     value = float(value)
#                 except Exception:
#                     input = str(input)
#                     value = str(value)

#             for conds in [
#                 (operator == "contains", str(value).lower() in str(input).lower()),
#                 (operator == "not contains", str(value).lower() not in str(input).lower()),
#                 (operator == "in", str(input).lower() in str(value).lower()),
#                 (operator == "not in", str(input).lower() not in str(value).lower()),
#                 (operator == "start with", str(input).lower().startswith(str(value).lower())),
#                 (operator == "end with", str(input).lower().endswith(str(value).lower())),
#                 (operator == "empty", not input),
#                 (operator == "not empty", input),
#                 (operator == "=", input == value),
#                 (operator == "≠", input != value),
#                 (operator == ">", input > value),
#                 (operator == "<", input < value),
#                 (operator == "≥", input >= value),
#                 (operator == "≤", input <= value),
#             ]:
#                 try:
#                     if all(conds):
#                         ids.extend(docids)
#                         break
#                 except Exception:
#                     pass
#         return ids

#     for k, v2docs in metas.items():
#         for f in filters:
#             if k != f["key"]:
#                 continue
#             ids = filter_out(v2docs, f["op"], f["value"])
#             if not doc_ids:
#                 doc_ids = set(ids)
#             else:
#                 if logic == "and":
#                     doc_ids = doc_ids & set(ids)
#                 else:
#                     doc_ids = doc_ids | set(ids)
#             if not doc_ids:
#                 return []
#     return list(doc_ids)


async def apply_meta_data_filter(
    meta_data_filter: dict | None,
    metas: dict,
    question: str,
    chat_mdl: Any = None,
    base_doc_ids: list[str] | None = None,
    manual_value_resolver: Callable[[dict], dict] | None = None,
) -> list[str] | None:
    """
    Apply metadata filtering rules and return the filtered doc_ids.

    meta_data_filter supports three modes:
    - auto: generate filter conditions via LLM (gen_meta_filter)
    - semi_auto: generate conditions using selected metadata keys only
    - manual: directly filter based on provided conditions

    Returns:
        list of doc_ids, ["-999"] when manual filters yield no result, or None
        when auto/semi_auto filters return empty.
    """
    doc_ids = list(base_doc_ids) if base_doc_ids else []

    if not meta_data_filter:
        return doc_ids

    method = meta_data_filter.get("method")

    # if method == "auto":
    #     # filters: dict = await gen_meta_filter(chat_mdl, metas, question)
    #     # doc_ids.extend(meta_filter(metas, filters["conditions"], filters.get("logic", "and")))
    #     filters: dict = await gen_meta_filter(chat_mdl, metas, question)
    #     special_filters: dict = await gen_special_meta_filter(chat_mdl, question)

    #     doc_id_set = set()

    #     if filters.get("conditions"):
    #         normal_ids = meta_filter(
    #             metas,
    #             filters["conditions"],
    #             filters.get("logic", "and")
    #         )
    #         doc_id_set.update(normal_ids)

    #     if special_filters.get("conditions"):
    #         special_ids = meta_filter(
    #             metas,
    #             special_filters["conditions"],
    #             special_filters.get("logic", "and")
    #         )
    #         doc_id_set.update(special_ids)

    #     doc_ids = list(doc_id_set)

    #     if not doc_ids:
    #         return None
    if method == "auto":
        a_filters: dict = await gen_special_meta_filter(chat_mdl, question)
        b_filters: dict = await gen_meta_filter(chat_mdl, metas, question)

        a_ids = None
        b_ids = None

        if a_filters.get("conditions"):
            a_ids = set(meta_filter(
                metas,
                a_filters["conditions"],
                a_filters.get("logic", "and")
            ))
            print("学校过滤")
            print(a_ids)

        if b_filters.get("conditions"):
            b_ids = set(meta_filter(
                metas,
                b_filters["conditions"],
                b_filters.get("logic", "and")
            ))
            print("类型过滤")
            print(b_ids)
        logic = await gen_ab_group_logic(
            chat_mdl,
            question,
            a_filters,
            b_filters
        )

        if a_ids is None and b_ids is None:
            return doc_ids

        elif a_ids is None:
            doc_ids = list(b_ids)
            

        elif b_ids is None:
            doc_ids = list(a_ids)

        else:
            if logic == "or":
                doc_ids = list(a_ids | b_ids)   # 并集
            else:
                doc_ids = list(a_ids & b_ids)   # 交集
        print("所有条件的")
        print(doc_ids)
        if not doc_ids:
            return None
        
    elif method == "semi_auto":
        selected_keys = meta_data_filter.get("semi_auto", [])
        if selected_keys:
            filtered_metas = {key: metas[key] for key in selected_keys if key in metas}
            if filtered_metas:
                filters: dict = await gen_meta_filter(chat_mdl, filtered_metas, question)
                doc_ids.extend(meta_filter(metas, filters["conditions"], filters.get("logic", "and")))
                if not doc_ids:
                    return None
    elif method == "manual":
        filters = meta_data_filter.get("manual", [])
        if manual_value_resolver:
            filters = [manual_value_resolver(flt) for flt in filters]
        doc_ids.extend(meta_filter(metas, filters, meta_data_filter.get("logic", "and")))
        if filters and not doc_ids:
            doc_ids = ["-999"]

    return doc_ids


def update_metadata_to(metadata, meta):
    if not meta:
        return metadata
    if isinstance(meta, str):
        try:
            meta = json_repair.loads(meta)
        except Exception:
            logging.error("Meta data format error.")
            return metadata
    if not isinstance(meta, dict):
        return metadata
    for k, v in meta.items():
        if isinstance(v, list):
            v = [vv for vv in v if isinstance(vv, str)]
            if not v:
                continue
        if not isinstance(v, list) and not isinstance(v, str):
            continue
        if k not in metadata:
            metadata[k] = v
            continue
        if isinstance(metadata[k], list):
            if isinstance(v, list):
                metadata[k].extend(v)
            else:
                metadata[k].append(v)
        else:
            metadata[k] = v

    return metadata


def metadata_schema(metadata: list|None) -> Dict[str, Any]:
    if not metadata:
        return {}
    properties = {}

    for item in metadata:
        key = item.get("key")
        if not key:
            continue

        prop_schema = {
            "description": item.get("description", "")
        }
        if "enum" in item and item["enum"]:
            prop_schema["enum"] = item["enum"]
            prop_schema["type"] = "string"

        properties[key] = prop_schema

    json_schema = {
        "type": "object",
        "properties": properties,
    }

    json_schema["additionalProperties"] = False
    return json_schema