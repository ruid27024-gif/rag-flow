import os
import re
import json
import time
from typing import Any, Dict, List, Set

import httpx
import pandas as pd


# ============================================================
# 1. 基础配置
# ============================================================

INPUT_EXCEL = "/home/zyb/文件名称.xlsx"

# 文档分类结果
OUTPUT_EXCEL = "/home/zyb/paper_files_classified_gpt.xlsx"

# 本次运行动态发现的新分类
DYNAMIC_CATEGORY_OUTPUT_EXCEL = (
    "/home/zyb/dynamic_category_candidates.xlsx"
)

# 最终完整分类体系
FINAL_CATEGORY_OUTPUT_EXCEL = (
    "/home/zyb/final_category_definitions.xlsx"
)

# 每批处理文件数
BATCH_SIZE = 20

# 一个文件最多允许输出几个分类
MAX_CATEGORIES_PER_FILE = 3

# 固定分类自动写入建议的最低置信度
CONFIDENCE_AUTO_THRESHOLD = 0.80

# 动态新增分类的最低置信度
DYNAMIC_CATEGORY_MIN_CONFIDENCE = 0.90

# 整次运行最多允许新增多少个动态分类
MAX_DYNAMIC_CATEGORIES = 30

# 是否启用动态分类
ENABLE_DYNAMIC_CATEGORIES = True

# 模型请求失败最大重试次数
MODEL_MAX_RETRIES = 3

# 每批请求完成后的暂停时间
BATCH_SLEEP_SECONDS = 0.5


# ============================================================
# 2. 模型配置
# ============================================================

# 示例：
#
MODEL_BASE_URL="https://api.ciyuan.fast/v1"
MODEL_API_KEY="sk-12063bea7d2756b05f27eb166eeb51108c693198041573de62def4b5eb0e3d89"
MODEL_NAME="gpt-5.5"

# MODEL_BASE_URL = os.environ.get(
#     "MODEL_BASE_URL",
#     "https://dashscope.aliyuncs.com/compatible-mode/v1",
# )

# MODEL_API_KEY = os.environ.get(
#     "MODEL_API_KEY",
#     "",
# )

# MODEL_NAME = os.environ.get(
#     "MODEL_NAME",
#     "qwen-plus",
# )


# ============================================================
# 3. 分类统一配置
# ============================================================

CATEGORY_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "pulping": {
        "name": "打浆",
        "description": (
            "制浆、碎浆、打浆、磨浆、浆料、纸浆、浆板、"
            "纤维处理、蒸煮、洗浆、筛选、漂白、废纸制浆、"
            "脱墨、木质素处理及制浆原料研究等"
        ),
        "dynamic": False,
        "auto_writable": True,
    },

    "modulation": {
        "name": "调制",
        "description": (
            "配浆、调浆、浆料配方、造纸助剂、施胶、填料、"
            "湿部化学、添加剂、分散、助留、助滤、增强剂、"
            "消泡剂及杀菌剂等"
        ),
        "dynamic": False,
        "auto_writable": True,
    },

    "papermaking": {
        "name": "抄造",
        "description": (
            "纸机抄造、造纸生产、流浆箱、网部、成形、压榨、"
            "干燥、烘干、纸页、纸幅、成纸、卷取、断纸、"
            "原纸生产及抄造工艺优化等"
        ),
        "dynamic": False,
        "auto_writable": True,
    },

    "processing": {
        "name": "加工",
        "description": (
            "纸张后加工、分切、复卷、包装、裁切、涂布、复合、"
            "压纹、印刷、覆膜、模切及纸制品加工等"
        ),
        "dynamic": False,
        "auto_writable": True,
    },

    "general_mgmt": {
        "name": "通用管理",
        "description": (
            "企业管理制度、会议活动、行业交流、培训、项目管理、"
            "通知、课程、年会、论坛、工作总结及产业管理等；"
            "如果文件有明确技术主题，应优先按照技术主题分类"
        ),
        "dynamic": False,
        "auto_writable": True,
    },

    "water_management": {
        "name": "用水与水处理/环保",
        "description": (
            "造纸用水、白水循环、水系统封闭、废水处理、污水处理、"
            "中水回用、节水、水质控制、污泥、废气、固废及环保治理等"
        ),
        "dynamic": False,
        "auto_writable": True,
    },

    "equipment_maintenance": {
        "name": "设备与维护",
        "description": (
            "制浆造纸设备、纸机设计、设备运行、故障诊断、"
            "维修维护、润滑、设备改造、辊筒、磨盘、真空系统、"
            "传动系统及自动控制系统等"
        ),
        "dynamic": False,
        "auto_writable": True,
    },

    "quality_control": {
        "name": "质量检测与控制",
        "description": (
            "纸浆和纸张性能检测、质量评价、缺陷分析、检测方法、"
            "质量标准、纤维分析、强度、定量、水分、白度、"
            "平滑度及过程质量控制等"
        ),
        "dynamic": False,
        "auto_writable": True,
    },

    "energy_carbon": {
        "name": "节能与碳排/绿色低碳",
        "description": (
            "节能降耗、能源管理、能耗分析、余热利用、碳足迹、"
            "碳排放、绿色制造、低碳评价、清洁生产及生命周期评价等"
        ),
        "dynamic": False,
        "auto_writable": True,
    },

    # 兜底分类
    "other": {
        "name": "其他",
        "description": (
            "文件明显属于造纸行业相关知识，"
            "但无法归入已有正式分类"
        ),
        "dynamic": False,
        "auto_writable": False,
    },

    "uncategorized": {
        "name": "未分类",
        "description": (
            "文件名信息不足，无法判断具体分类"
        ),
        "dynamic": False,
        "auto_writable": False,
    },
}


# ============================================================
# 4. 根据统一配置生成其他变量
# ============================================================

# 所有允许返回的分类 code
ALLOWED_CATEGORY_CODES: Dict[str, str] = {
    code: config["name"]
    for code, config in CATEGORY_DEFINITIONS.items()
}

# 可以自动写入 StagedFileTag 的固定分类
AUTO_WRITABLE_CATEGORY_CODES: Set[str] = {
    code
    for code, config in CATEGORY_DEFINITIONS.items()
    if config.get("auto_writable", False)
}

# 本次运行期间动态新增的分类 code
DYNAMIC_CATEGORY_CODES: Set[str] = set()

# 动态分类详细信息
DYNAMIC_CATEGORY_RECORDS: Dict[str, Dict[str, Any]] = {}


# ============================================================
# 5. 通用辅助函数
# ============================================================

def ensure_output_parent(path: str):
    """
    确保输出文件的父目录存在。
    """

    parent = os.path.dirname(
        os.path.abspath(path)
    )

    if parent:
        os.makedirs(
            parent,
            exist_ok=True,
        )


def clean_excel_value(value: Any) -> str:
    """
    清理 Excel 单元格，防止空值变成字符串 nan。
    """

    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass

    return str(value).strip()


def clamp_confidence(value: Any) -> float:
    """
    将置信度转换为 0～1 的小数。
    """

    try:
        confidence = float(value or 0)
    except Exception:
        confidence = 0.0

    if confidence < 0:
        confidence = 0.0

    if confidence > 1:
        confidence = 1.0

    return round(
        confidence,
        4,
    )


def chunk_list(
    items: List[Dict[str, str]],
    batch_size: int,
):
    """
    将列表按固定大小分批。
    """

    for index in range(
        0,
        len(items),
        batch_size,
    ):
        yield items[
            index:index + batch_size
        ]


def normalize_dynamic_category_code(
    value: Any,
) -> str:
    """
    标准化动态分类 code。

    规则：
    - 小写英文字母开头；
    - 只能包含小写字母、数字、下划线；
    - 最大长度 64。
    """

    code = str(
        value or ""
    ).strip().lower()

    # 空格和横线转换为下划线
    code = re.sub(
        r"[\s\-]+",
        "_",
        code,
    )

    # 删除非法字符
    code = re.sub(
        r"[^a-z0-9_]",
        "",
        code,
    )

    # 合并连续下划线
    code = re.sub(
        r"_+",
        "_",
        code,
    ).strip("_")

    if not code:
        return ""

    if len(code) > 64:
        return ""

    if not re.fullmatch(
        r"[a-z][a-z0-9_]*",
        code,
    ):
        return ""

    if code in {
        "other",
        "uncategorized",
    }:
        return ""

    return code


# ============================================================
# 6. 动态构建分类说明
# ============================================================

def build_category_description() -> str:
    """
    根据当前 CATEGORY_DEFINITIONS 生成分类说明。

    上一个批次动态新增的分类，
    会自动出现在下一个批次的 Prompt 中。
    """

    lines = []
    sequence = 1

    # 正式分类
    for code, config in CATEGORY_DEFINITIONS.items():
        if code in {
            "other",
            "uncategorized",
        }:
            continue

        dynamic_note = ""

        if config.get("dynamic", False):
            dynamic_note = (
                "（前面批次动态发现的新分类）"
            )

        lines.append(
            f"{sequence}. {code}："
            f"{config['name']}{dynamic_note}\n"
            f"   包括：{config['description']}。"
        )

        sequence += 1

    # other
    lines.append(
        f"{sequence}. other：其他\n"
        "   文件明显属于造纸行业相关知识，"
        "但无法归入以上已有正式分类。\n"
        "   如果选择 other，必须提供一个可复用的 "
        "suggested_new_category。"
    )

    sequence += 1

    # uncategorized
    lines.append(
        f"{sequence}. uncategorized：未分类\n"
        "   文件名信息不足，无法判断具体分类。\n"
        "   例如：附件1.pdf、新建文档.docx、"
        "资料汇编.pdf、2023版.pdf。"
    )

    return "\n\n".join(lines)


# ============================================================
# 7. 构建 Prompt
# ============================================================

def build_prompt(
    items: List[Dict[str, str]],
) -> str:
    """
    构建当前批次提示词。
    """

    file_list_text = json.dumps(
        items,
        ensure_ascii=False,
        indent=2,
    )

    category_description = (
        build_category_description()
    )

    prompt = f"""
你是造纸行业知识库文件分类助手。
请根据文件名判断文件所属的一个或多个知识分类。

知识分类是多选标签：

- 文件名只明确涉及一个分类时，只输出一个分类。
- 文件名明确涉及多个不同技术主题时，可以输出多个分类。
- 不要因为弱关联而过度多选。
- 每个文件最多输出 {MAX_CATEGORIES_PER_FILE} 个分类。
- 同一个 category_code 不得重复。

当前允许选择的分类如下：

{category_description}

分类判断要求：

1. categories 必须是 JSON 数组。

2. 文件只明确属于一个分类时，只输出一个分类。

3. 文件明确涉及多个不同技术主题时，可以多选，
   但最多输出 {MAX_CATEGORIES_PER_FILE} 个分类。

4. 每个分类必须单独提供 confidence，
   confidence 是 0 到 1 的小数。

5. 同一个 category_code 不得重复。

6. other 和 uncategorized 是互斥兜底分类：
   - other 不能和其他分类同时出现；
   - uncategorized 不能和其他分类同时出现；
   - other 和 uncategorized 不能同时出现。

7. 如果能够归入已有正式分类，
   不要选择 other 或 uncategorized。

8. “项目、鉴定、验收、论文、报告、标准、会议”
   可能只是文件形式。
   应优先根据文件标题中的实际技术主题分类。

9. 如果标题只是会议召开、活动通知或行业交流信息，
   且没有明确具体技术主题，可以归为 general_mgmt。

10. 如果标题涉及设备设计、设备故障、维修、润滑、
    机械改造或自动控制，应考虑 equipment_maintenance，
    不要因为出现“纸机”就只归为 papermaking。

11. 如果标题涉及性能检测、质量评价、缺陷分析、
    检测方法或质量控制，应考虑 quality_control。
    但不能仅因为普通出现“性能”就添加该分类。

12. 助剂、填料、施胶、助留、助滤、杀菌剂、
    湿部化学等内容优先考虑 modulation。

13. 节能、能耗、碳排、碳足迹、绿色制造、
    清洁生产等内容优先考虑 energy_carbon。

14. 白水循环、水系统封闭、废水、污水、
    水处理或环保治理等内容优先考虑 water_management。

15. 如果已有正式分类确实无法覆盖，
    但文件技术主题明确：
    - categories 中选择 other；
    - suggested_new_category 必须建议一个可复用的新分类；
    - code 使用小写英文和下划线；
    - name 使用中文；
    - description 描述该分类的适用范围；
    - 不要为只适用于一篇文件的狭窄主题创建分类；
    - 新分类应当能够覆盖一批相似文件。

16. 如果文件名信息不足，选择 uncategorized，
    不要建议新分类。

17. 必须原样返回输入中的 item_id、doc_id 和 filename。

18. reason 简要说明分类依据，控制在 50 个汉字以内。

19. 只能输出合法 JSON 数组。
    不要输出 Markdown。
    不要输出代码块。
    不要输出 JSON 之外的解释文本。

输入文件列表如下：

{file_list_text}

请严格按照以下 JSON 数组格式输出：

[
  {{
    "item_id": "原样返回输入的item_id",
    "doc_id": "原样返回输入的doc_id",
    "filename": "原始文件名",
    "categories": [
      {{
        "category_code": "pulping",
        "category_name": "打浆",
        "confidence": 0.95
      }},
      {{
        "category_code": "papermaking",
        "category_name": "抄造",
        "confidence": 0.85
      }}
    ],
    "reason": "简要分类依据",
    "suggested_new_category": {{
      "code": "",
      "name": "",
      "description": ""
    }}
  }}
]
"""

    return prompt.strip()


# ============================================================
# 8. 调用模型
# ============================================================

def call_model(prompt: str) -> str:
    """
    调用 OpenAI 兼容模型接口。

    增强功能：
    1. 打印非 JSON 响应；
    2. 检查空响应；
    3. 检查 HTTP 状态码；
    4. 检查接口 error 字段；
    5. 请求失败自动重试；
    6. 禁止流式响应。
    """

    if not MODEL_BASE_URL:
        raise ValueError("MODEL_BASE_URL 未配置")

    if not MODEL_NAME:
        raise ValueError("MODEL_NAME 未配置")

    if not MODEL_API_KEY:
        raise ValueError("MODEL_API_KEY 未配置")

    url = (
        f"{MODEL_BASE_URL.rstrip('/')}"
        "/chat/completions"
    )

    headers = {
        "Authorization": f"Bearer {MODEL_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是严谨的造纸行业文件分类助手。"
                    "你必须只输出合法 JSON 数组，"
                    "不能输出 Markdown 和解释文本。"
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "temperature": 0.1,
        "top_p": 0.8,

        # 明确关闭流式输出
        "stream": False,
    }

    last_error = None

    for retry_index in range(
        1,
        MODEL_MAX_RETRIES + 1,
    ):
        try:
            print(
                f"正在请求模型：{MODEL_NAME}，"
                f"接口地址：{url}"
            )

            with httpx.Client(
                timeout=httpx.Timeout(
                    connect=30.0,
                    read=180.0,
                    write=60.0,
                    pool=30.0,
                ),
                follow_redirects=True,
            ) as client:
                response = client.post(
                    url,
                    headers=headers,
                    json=payload,
                )

            status_code = response.status_code

            content_type = response.headers.get(
                "content-type",
                "",
            )

            request_id = (
                response.headers.get("x-request-id")
                or response.headers.get(
                    "x-dashscope-request-id"
                )
                or response.headers.get(
                    "request-id"
                )
                or ""
            )

            response_text = (
                response.text or ""
            ).strip()

            print(
                f"模型 HTTP 状态码：{status_code}，"
                f"Content-Type：{content_type}，"
                f"Request-ID：{request_id or '无'}，"
                f"响应长度：{len(response_text)}"
            )

            # 先检查状态码，不直接调用 response.json()
            if status_code < 200 or status_code >= 300:
                raise RuntimeError(
                    f"模型接口 HTTP 错误："
                    f"status={status_code}，"
                    f"content_type={content_type}，"
                    f"request_id={request_id}，"
                    f"response={response_text[:2000]}"
                )

            # HTTP 200 但响应为空
            if not response_text:
                raise RuntimeError(
                    "模型接口返回空响应："
                    f"status={status_code}，"
                    f"content_type={content_type}，"
                    f"request_id={request_id}"
                )

            # 如果意外返回流式数据，给出明确错误
            if response_text.startswith("data:"):
                raise RuntimeError(
                    "模型接口返回了 SSE 流式内容，"
                    "但当前程序要求非流式 JSON。"
                    f"响应内容：{response_text[:1000]}"
                )

            # 手动解析 JSON，解析失败时保留原始响应
            try:
                data = json.loads(response_text)
            except json.JSONDecodeError as e:
                raise RuntimeError(
                    "模型接口返回的不是合法 JSON："
                    f"{e}；"
                    f"status={status_code}；"
                    f"content_type={content_type}；"
                    f"request_id={request_id}；"
                    f"response={response_text[:2000]}"
                ) from e

            if not isinstance(data, dict):
                raise RuntimeError(
                    "模型接口返回的最外层不是 JSON 对象："
                    f"{str(data)[:1000]}"
                )

            # 检查 OpenAI 兼容接口错误格式
            if data.get("error"):
                error_data = data.get("error")

                raise RuntimeError(
                    "模型接口返回 error："
                    f"{json.dumps(error_data, ensure_ascii=False)}"
                )

            choices = data.get("choices") or []

            if not choices:
                raise RuntimeError(
                    "模型接口没有返回 choices："
                    f"{json.dumps(data, ensure_ascii=False)[:2000]}"
                )

            first_choice = choices[0]

            if not isinstance(first_choice, dict):
                raise RuntimeError(
                    "模型接口 choices[0] 格式错误："
                    f"{str(first_choice)[:1000]}"
                )

            message = (
                first_choice.get("message")
                or {}
            )

            if not isinstance(message, dict):
                raise RuntimeError(
                    "模型接口 message 格式错误："
                    f"{str(message)[:1000]}"
                )

            content = message.get("content")

            if content is None:
                raise RuntimeError(
                    "模型接口没有返回 message.content："
                    f"{json.dumps(data, ensure_ascii=False)[:2000]}"
                )

            content = str(content).strip()

            if not content:
                raise RuntimeError(
                    "模型接口返回的 message.content 为空："
                    f"{json.dumps(data, ensure_ascii=False)[:2000]}"
                )

            # 可选：打印 Token 用量
            usage = data.get("usage") or {}

            if usage:
                print(
                    "本次 Token 用量："
                    f"输入={usage.get('prompt_tokens', 0)}，"
                    f"输出={usage.get('completion_tokens', 0)}，"
                    f"总计={usage.get('total_tokens', 0)}"
                )

            return content

        except Exception as e:
            last_error = e

            print(
                f"模型请求第 {retry_index}/"
                f"{MODEL_MAX_RETRIES} 次失败：{e}"
            )

            if retry_index < MODEL_MAX_RETRIES:
                wait_seconds = retry_index * 2

                print(
                    f"{wait_seconds} 秒后重试..."
                )

                time.sleep(wait_seconds)

    raise RuntimeError(
        "模型请求重试后仍然失败："
        f"{last_error}"
    )


# ============================================================
# 9. 提取 JSON 数组
# ============================================================

def extract_json_array(
    text: str,
) -> List[Dict[str, Any]]:
    """
    从模型返回内容中提取 JSON 数组。
    """

    text = str(
        text or ""
    ).strip()

    if not text:
        raise ValueError(
            "模型返回内容为空"
        )

    # 去除 Markdown 包裹
    if text.startswith("```"):
        text = re.sub(
            r"^```json\s*",
            "",
            text,
            flags=re.IGNORECASE,
        )

        text = re.sub(
            r"^```\s*",
            "",
            text,
        )

        text = re.sub(
            r"\s*```$",
            "",
            text,
        )

        text = text.strip()

    # 首先直接解析
    try:
        data = json.loads(text)

        if not isinstance(data, list):
            raise ValueError(
                "模型返回 JSON 不是数组"
            )

        return data

    except json.JSONDecodeError:
        pass

    # 兜底截取第一个 [ 到最后一个 ]
    start = text.find("[")
    end = text.rfind("]")

    if start < 0 or end <= start:
        raise ValueError(
            "模型返回不是合法 JSON 数组："
            f"{text[:500]}"
        )

    json_text = text[
        start:end + 1
    ]

    try:
        data = json.loads(
            json_text
        )
    except json.JSONDecodeError as e:
        raise ValueError(
            "模型返回的 JSON 数组无法解析："
            f"{e}；原始内容：{text[:500]}"
        ) from e

    if not isinstance(data, list):
        raise ValueError(
            "模型返回 JSON 不是数组"
        )

    return data


# ============================================================
# 10. 动态分类注册
# ============================================================

def register_dynamic_categories(
    raw_results: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    从当前批次结果中提取：

        category_code = other
        suggested_new_category != 空

    注册后：
    1. 当前文件的 other 立即替换成新分类；
    2. 下一批 Prompt 自动包含新分类；
    3. 动态分类暂时不自动写数据库。
    """

    if not ENABLE_DYNAMIC_CATEGORIES:
        return []

    newly_registered = []

    for result in raw_results:
        if not isinstance(result, dict):
            continue

        categories = (
            result.get("categories")
            or []
        )

        if not isinstance(categories, list):
            continue

        other_category = None

        for category in categories:
            if not isinstance(category, dict):
                continue

            category_code = str(
                category.get(
                    "category_code",
                    "",
                ) or ""
            ).strip()

            if category_code == "other":
                other_category = category
                break

        # 没有选择 other，不处理
        if other_category is None:
            continue

        confidence = clamp_confidence(
            other_category.get(
                "confidence",
                0,
            )
        )

        # 置信度不足，不注册
        if (
            confidence
            < DYNAMIC_CATEGORY_MIN_CONFIDENCE
        ):
            continue

        suggested = (
            result.get(
                "suggested_new_category"
            )
            or {}
        )

        if not isinstance(suggested, dict):
            continue

        suggested_code = (
            normalize_dynamic_category_code(
                suggested.get("code")
            )
        )

        suggested_name = str(
            suggested.get(
                "name",
                "",
            ) or ""
        ).strip()

        suggested_description = str(
            suggested.get(
                "description",
                "",
            ) or ""
        ).strip()

        if not suggested_code:
            continue

        if not suggested_name:
            continue

        if not suggested_description:
            suggested_description = (
                f"与“{suggested_name}”相关的"
                "造纸行业知识"
            )

        # 分类不存在时新增
        if (
            suggested_code
            not in CATEGORY_DEFINITIONS
        ):
            if (
                len(DYNAMIC_CATEGORY_CODES)
                >= MAX_DYNAMIC_CATEGORIES
            ):
                print(
                    "动态分类数量达到上限，忽略："
                    f"{suggested_name}"
                    f"（{suggested_code}）"
                )
                continue

            CATEGORY_DEFINITIONS[
                suggested_code
            ] = {
                "name": suggested_name,
                "description": (
                    suggested_description
                ),
                "dynamic": True,

                # 动态分类尚未进入数据库
                "auto_writable": False,
            }

            ALLOWED_CATEGORY_CODES[
                suggested_code
            ] = suggested_name

            DYNAMIC_CATEGORY_CODES.add(
                suggested_code
            )

            DYNAMIC_CATEGORY_RECORDS[
                suggested_code
            ] = {
                "category_code": (
                    suggested_code
                ),
                "category_name": (
                    suggested_name
                ),
                "description": (
                    suggested_description
                ),
                "first_source_filename": str(
                    result.get(
                        "filename",
                        "",
                    ) or ""
                ),
                "first_confidence": confidence,
                "suggestion_count": 1,
                "database_created": False,
            }

            newly_registered.append({
                "code": suggested_code,
                "name": suggested_name,
                "description": (
                    suggested_description
                ),
                "confidence": confidence,
            })

            print(
                "动态新增分类："
                f"{suggested_name}"
                f"（{suggested_code}），"
                f"置信度：{confidence}"
            )

        else:
            # 如果这个分类是以前动态创建的，
            # 增加建议出现次数
            if (
                suggested_code
                in DYNAMIC_CATEGORY_RECORDS
            ):
                DYNAMIC_CATEGORY_RECORDS[
                    suggested_code
                ]["suggestion_count"] += 1

        # 获取标准中文名
        registered_name = (
            CATEGORY_DEFINITIONS[
                suggested_code
            ]["name"]
        )

        # 当前文件立即从 other 替换成新分类
        result["categories"] = [
            {
                "category_code": (
                    suggested_code
                ),
                "category_name": (
                    registered_name
                ),
                "confidence": confidence,
            }
        ]

        if not result.get("reason"):
            result["reason"] = (
                f"动态识别为{registered_name}"
            )

    return newly_registered


# ============================================================
# 11. 标准化分类结果
# ============================================================

def normalize_categories(
    result: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    标准化 categories：

    - 删除非法分类；
    - 相同分类去重；
    - 重复分类保留最高置信度；
    - other / uncategorized 不与正式分类共存；
    - 最多保留指定数量；
    - 不排序，保持模型返回顺序。
    """

    raw_categories = result.get(
        "categories"
    )

    # 兼容旧版单分类格式
    if not isinstance(raw_categories, list):
        old_code = str(
            result.get(
                "category_code",
                "",
            ) or ""
        ).strip()

        if old_code:
            raw_categories = [
                {
                    "category_code": old_code,
                    "category_name": result.get(
                        "category_name",
                        "",
                    ),
                    "confidence": result.get(
                        "confidence",
                        0,
                    ),
                }
            ]
        else:
            raw_categories = []

    category_map: Dict[
        str,
        Dict[str, Any],
    ] = {}

    for category in raw_categories:
        if not isinstance(category, dict):
            continue

        category_code = str(
            category.get(
                "category_code",
                "",
            ) or ""
        ).strip()

        if (
            category_code
            not in ALLOWED_CATEGORY_CODES
        ):
            continue

        confidence = clamp_confidence(
            category.get(
                "confidence",
                0,
            )
        )

        normalized_category = {
            "category_code": category_code,
            "category_name": (
                ALLOWED_CATEGORY_CODES[
                    category_code
                ]
            ),
            "confidence": confidence,
        }

        existing = category_map.get(
            category_code
        )

        if (
            existing is None
            or confidence
            > existing["confidence"]
        ):
            category_map[
                category_code
            ] = normalized_category

    # 除兜底分类外，全部属于正式分类
    official_categories = [
        category
        for code, category
        in category_map.items()
        if code not in {
            "other",
            "uncategorized",
        }
    ]

    # 有正式分类时丢弃兜底分类
    if official_categories:
        return official_categories[
            :MAX_CATEGORIES_PER_FILE
        ]

    # 没有正式分类时，other 优先
    if "other" in category_map:
        return [
            category_map["other"]
        ]

    # 然后使用未分类
    if "uncategorized" in category_map:
        return [
            category_map["uncategorized"]
        ]

    # 没有有效结果时兜底
    return [
        {
            "category_code": (
                "uncategorized"
            ),
            "category_name": "未分类",
            "confidence": 0.0,
        }
    ]


def normalize_result(
    result: Dict[str, Any],
    fallback_item: Dict[str, str],
) -> Dict[str, Any]:
    """
    标准化一个文件的最终输出。
    """

    categories = normalize_categories(
        result
    )

    # 优先使用原始 Excel 中的数据
    item_id = str(
        fallback_item.get("item_id")
        or result.get("item_id")
        or ""
    ).strip()

    doc_id = str(
        fallback_item.get("doc_id")
        or result.get("doc_id")
        or ""
    ).strip()

    filename = str(
        fallback_item.get("filename")
        or result.get("filename")
        or ""
    ).strip()

    reason = str(
        result.get(
            "reason",
            "",
        ) or ""
    ).strip()

    category_codes = [
        category["category_code"]
        for category in categories
    ]

    category_names = [
        category["category_name"]
        for category in categories
    ]

    category_confidences = [
        category["confidence"]
        for category in categories
    ]

    suggested = (
        result.get(
            "suggested_new_category"
        )
        or {}
    )

    if not isinstance(suggested, dict):
        suggested = {}

    # 只有最终仍然是 other，才保留建议分类
    if category_codes == ["other"]:
        suggested_code = (
            normalize_dynamic_category_code(
                suggested.get("code")
            )
        )

        suggested_name = str(
            suggested.get(
                "name",
                "",
            ) or ""
        ).strip()

        suggested_description = str(
            suggested.get(
                "description",
                "",
            ) or ""
        ).strip()
    else:
        suggested_code = ""
        suggested_name = ""
        suggested_description = ""

    # 自动写入建议
    auto_write_category_codes = []

    for category in categories:
        category_code = (
            category["category_code"]
        )

        confidence = (
            category["confidence"]
        )

        if (
            category_code
            in AUTO_WRITABLE_CATEGORY_CODES
            and confidence
            >= CONFIDENCE_AUTO_THRESHOLD
        ):
            auto_write_category_codes.append(
                category_code
            )

    contains_dynamic_category = any(
        code in DYNAMIC_CATEGORY_CODES
        for code in category_codes
    )

    needs_review = False

    # 兜底分类需要复核
    if (
        "other" in category_codes
        or "uncategorized" in category_codes
    ):
        needs_review = True

    # 动态分类还没有进入数据库
    if contains_dynamic_category:
        needs_review = True

    # 低置信度需要复核
    for category in categories:
        if (
            category["confidence"]
            < CONFIDENCE_AUTO_THRESHOLD
        ):
            needs_review = True
            break

    auto_write_suggested = (
        not needs_review
        and len(categories) > 0
        and len(auto_write_category_codes)
        == len(categories)
    )

    return {
        "item_id": item_id,
        "doc_id": doc_id,
        "filename": filename,

        "category_codes": ",".join(
            category_codes
        ),

        "category_names": ",".join(
            category_names
        ),

        "category_confidences": ",".join(
            str(confidence)
            for confidence
            in category_confidences
        ),

        "categories_json": json.dumps(
            categories,
            ensure_ascii=False,
        ),

        "reason": reason,

        "suggested_new_category_code": (
            suggested_code
        ),

        "suggested_new_category_name": (
            suggested_name
        ),

        "suggested_new_category_description": (
            suggested_description
        ),

        "contains_dynamic_category": (
            contains_dynamic_category
        ),

        "auto_write_category_codes": ",".join(
            auto_write_category_codes
        ),

        "auto_write_suggested": (
            auto_write_suggested
        ),

        "needs_review": needs_review,
    }


def build_failure_result(
    item: Dict[str, str],
    error_message: str,
) -> Dict[str, Any]:
    """
    文件或批次处理失败时生成未分类结果。
    """

    categories = [
        {
            "category_code": (
                "uncategorized"
            ),
            "category_name": "未分类",
            "confidence": 0.0,
        }
    ]

    return {
        "item_id": item.get(
            "item_id",
            "",
        ),
        "doc_id": item.get(
            "doc_id",
            "",
        ),
        "filename": item.get(
            "filename",
            "",
        ),
        "category_codes": "uncategorized",
        "category_names": "未分类",
        "category_confidences": "0.0",
        "categories_json": json.dumps(
            categories,
            ensure_ascii=False,
        ),
        "reason": (
            "模型调用或结果处理失败："
            f"{error_message}"
        ),
        "suggested_new_category_code": "",
        "suggested_new_category_name": "",
        "suggested_new_category_description": "",
        "contains_dynamic_category": False,
        "auto_write_category_codes": "",
        "auto_write_suggested": False,
        "needs_review": True,
    }


# ============================================================
# 12. 将结果匹配回原始文件
# ============================================================

def match_batch_results(
    batch: List[Dict[str, str]],
    raw_results: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    将模型返回结果匹配回原始文件。

    返回顺序严格按照 batch 原始顺序。
    """

    result_by_item_id = {}
    result_by_doc_id = {}
    result_by_filename = {}

    valid_results = []

    for raw_result in raw_results:
        if not isinstance(raw_result, dict):
            continue

        valid_results.append(
            raw_result
        )

        item_id = str(
            raw_result.get(
                "item_id",
                "",
            ) or ""
        ).strip()

        doc_id = str(
            raw_result.get(
                "doc_id",
                "",
            ) or ""
        ).strip()

        filename = str(
            raw_result.get(
                "filename",
                "",
            ) or ""
        ).strip()

        if item_id:
            result_by_item_id[
                item_id
            ] = raw_result

        if doc_id:
            result_by_doc_id[
                doc_id
            ] = raw_result

        if filename:
            result_by_filename[
                filename
            ] = raw_result

    normalized_results = []

    # 严格按照原始批次顺序循环
    for index, item in enumerate(batch):
        item_id = item.get(
            "item_id",
            "",
        )

        doc_id = item.get(
            "doc_id",
            "",
        )

        filename = item.get(
            "filename",
            "",
        )

        raw_result = None

        # 1. item_id 精确匹配
        if item_id:
            raw_result = (
                result_by_item_id.get(
                    item_id
                )
            )

        # 2. doc_id 精确匹配
        if (
            raw_result is None
            and doc_id
        ):
            raw_result = (
                result_by_doc_id.get(
                    doc_id
                )
            )

        # 3. filename 精确匹配
        if (
            raw_result is None
            and filename
        ):
            raw_result = (
                result_by_filename.get(
                    filename
                )
            )

        # 4. 按位置兜底
        if (
            raw_result is None
            and index < len(valid_results)
        ):
            raw_result = (
                valid_results[index]
            )

        if raw_result is None:
            normalized_results.append(
                build_failure_result(
                    item,
                    "模型没有返回该文件结果",
                )
            )
            continue

        normalized_results.append(
            normalize_result(
                raw_result,
                fallback_item=item,
            )
        )

    return normalized_results


# ============================================================
# 13. 分类使用量统计
# ============================================================

def count_category_usage(
    results: List[Dict[str, Any]],
) -> Dict[str, int]:
    """
    统计每个分类对应多少篇文件。

    同一篇文件的同一个分类只计算一次。
    """

    category_usage = {
        code: 0
        for code in CATEGORY_DEFINITIONS
    }

    for result in results:
        categories_text = result.get(
            "categories_json",
            "[]",
        )

        try:
            categories = json.loads(
                categories_text
            )
        except Exception:
            categories = []

        used_codes = set()

        for category in categories:
            if not isinstance(category, dict):
                continue

            category_code = str(
                category.get(
                    "category_code",
                    "",
                ) or ""
            ).strip()

            if category_code:
                used_codes.add(
                    category_code
                )

        for category_code in used_codes:
            if (
                category_code
                not in category_usage
            ):
                category_usage[
                    category_code
                ] = 0

            category_usage[
                category_code
            ] += 1

    return category_usage


def print_category_statistics(
    results: List[Dict[str, Any]],
):
    """
    打印每个分类的文件数量。
    """

    category_usage = (
        count_category_usage(
            results
        )
    )

    print("\n分类使用统计：")

    for code, config in (
        CATEGORY_DEFINITIONS.items()
    ):
        print(
            f"{config['name']}（{code}）："
            f"{category_usage.get(code, 0)}"
        )

    review_count = sum(
        1
        for result in results
        if result.get("needs_review")
    )

    auto_write_count = sum(
        1
        for result in results
        if result.get(
            "auto_write_suggested"
        )
    )

    dynamic_file_count = sum(
        1
        for result in results
        if result.get(
            "contains_dynamic_category"
        )
    )

    print(
        f"\n需要人工复核：{review_count}"
    )

    print(
        f"建议自动写入：{auto_write_count}"
    )

    print(
        "使用动态分类的文件："
        f"{dynamic_file_count}"
    )


# ============================================================
# 14. 最终分类体系统计
# ============================================================

def print_final_category_summary():
    """
    打印最终分类数量和分类列表。
    """

    fallback_codes = {
        "other",
        "uncategorized",
    }

    fixed_codes = [
        code
        for code, config
        in CATEGORY_DEFINITIONS.items()
        if (
            code not in fallback_codes
            and not config.get(
                "dynamic",
                False,
            )
        )
    ]

    dynamic_codes = [
        code
        for code, config
        in CATEGORY_DEFINITIONS.items()
        if (
            code not in fallback_codes
            and config.get(
                "dynamic",
                False,
            )
        )
    ]

    formal_codes = [
        code
        for code in CATEGORY_DEFINITIONS
        if code not in fallback_codes
    ]

    print("\n" + "=" * 60)
    print("最终分类体系统计")
    print("=" * 60)

    print(
        "固定正式分类数量："
        f"{len(fixed_codes)}"
    )

    print(
        "动态新增分类数量："
        f"{len(dynamic_codes)}"
    )

    print(
        "最终正式分类数量："
        f"{len(formal_codes)}"
    )

    print(
        "包含兜底分类的总数量："
        f"{len(CATEGORY_DEFINITIONS)}"
    )

    print("\n最终正式分类列表：")

    for index, code in enumerate(
        formal_codes,
        start=1,
    ):
        config = (
            CATEGORY_DEFINITIONS[code]
        )

        source = (
            "动态新增"
            if config.get("dynamic", False)
            else "固定分类"
        )

        print(
            f"{index}. "
            f"{config['name']}（{code}）"
            f"[{source}]"
        )

    print("\n兜底分类：")

    print("- 其他（other）")
    print("- 未分类（uncategorized）")


# ============================================================
# 15. 导出动态分类
# ============================================================

def export_dynamic_categories():
    """
    导出本次运行中新发现的动态分类。
    """

    if not DYNAMIC_CATEGORY_RECORDS:
        print(
            "\n本次运行没有发现新的动态分类"
        )
        return

    rows = []

    # 按动态分类发现顺序输出，不排序
    for code, record in (
        DYNAMIC_CATEGORY_RECORDS.items()
    ):
        rows.append({
            "category_code": code,
            "category_name": record.get(
                "category_name",
                "",
            ),
            "description": record.get(
                "description",
                "",
            ),
            "first_source_filename": (
                record.get(
                    "first_source_filename",
                    "",
                )
            ),
            "first_confidence": (
                record.get(
                    "first_confidence",
                    0,
                )
            ),
            "suggestion_count": (
                record.get(
                    "suggestion_count",
                    0,
                )
            ),
            "database_created": False,
        })

    ensure_output_parent(
        DYNAMIC_CATEGORY_OUTPUT_EXCEL
    )

    pd.DataFrame(rows).to_excel(
        DYNAMIC_CATEGORY_OUTPUT_EXCEL,
        index=False,
    )

    print(
        "\n动态分类清单已写入："
        f"{DYNAMIC_CATEGORY_OUTPUT_EXCEL}"
    )


# ============================================================
# 16. 导出最终完整分类
# ============================================================

def export_final_categories(
    results: List[Dict[str, Any]],
):
    """
    导出最终全部分类。

    包含：
    - 固定分类；
    - 动态分类；
    - 兜底分类；
    - 每个分类对应的文件数量。
    """

    category_usage = (
        count_category_usage(
            results
        )
    )

    rows = []

    for sequence, (
        code,
        config,
    ) in enumerate(
        CATEGORY_DEFINITIONS.items(),
        start=1,
    ):
        is_fallback = code in {
            "other",
            "uncategorized",
        }

        is_dynamic = bool(
            config.get(
                "dynamic",
                False,
            )
        )

        if is_fallback:
            category_type = "兜底分类"
        elif is_dynamic:
            category_type = "动态新增分类"
        else:
            category_type = "固定分类"

        dynamic_record = (
            DYNAMIC_CATEGORY_RECORDS.get(
                code,
                {},
            )
        )

        rows.append({
            "sequence": sequence,
            "category_code": code,
            "category_name": config.get(
                "name",
                "",
            ),
            "description": config.get(
                "description",
                "",
            ),
            "category_type": category_type,
            "file_count": (
                category_usage.get(
                    code,
                    0,
                )
            ),
            "is_dynamic": is_dynamic,
            "is_fallback": is_fallback,
            "auto_writable": bool(
                config.get(
                    "auto_writable",
                    False,
                )
            ),
            "first_source_filename": (
                dynamic_record.get(
                    "first_source_filename",
                    "",
                )
            ),
            "first_confidence": (
                dynamic_record.get(
                    "first_confidence",
                    "",
                )
            ),
            "suggestion_count": (
                dynamic_record.get(
                    "suggestion_count",
                    0,
                )
            ),
            "database_created": (
                not is_dynamic
            ),
        })

    ensure_output_parent(
        FINAL_CATEGORY_OUTPUT_EXCEL
    )

    pd.DataFrame(rows).to_excel(
        FINAL_CATEGORY_OUTPUT_EXCEL,
        index=False,
    )

    print(
        "最终完整分类清单已写入："
        f"{FINAL_CATEGORY_OUTPUT_EXCEL}"
    )


# ============================================================
# 17. 主函数
# ============================================================

def classify_excel():
    """
    主流程：

    1. 按 Excel 原始顺序读取；
    2. 每批重新生成 Prompt；
    3. 当前批发现新分类后立即注册；
    4. 当前文件立即使用新分类；
    5. 下一批 Prompt 自动带上新分类；
    6. 结果按 Excel 原始顺序输出，不排序。
    """

    if not os.path.exists(INPUT_EXCEL):
        raise FileNotFoundError(
            "输入 Excel 不存在："
            f"{INPUT_EXCEL}"
        )

    df = pd.read_excel(
        INPUT_EXCEL
    )

    if "PDF名字" not in df.columns:
        raise ValueError(
            'Excel 必须包含“PDF名字”列'
        )

    has_doc_id = (
        "doc_id" in df.columns
    )

    items: List[Dict[str, str]] = []

    # iterrows 按 Excel 原始顺序遍历
    for row_index, row in df.iterrows():
        filename = clean_excel_value(
            row.get("PDF名字")
        )

        # 空文件名跳过
        if not filename:
            continue

        doc_id = ""

        if has_doc_id:
            doc_id = clean_excel_value(
                row.get("doc_id")
            )

        item_id = (
            f"item_{row_index + 1}"
        )

        items.append({
            "item_id": item_id,
            "doc_id": doc_id,
            "filename": filename,
        })

    print(
        f"读取到 {len(items)} 个有效文件"
    )

    if not items:
        raise ValueError(
            "Excel 中没有有效文件名"
        )

    all_results: List[
        Dict[str, Any]
    ] = []

    total_batches = (
        len(items) + BATCH_SIZE - 1
    ) // BATCH_SIZE

    for batch_index, batch in enumerate(
        chunk_list(
            items,
            BATCH_SIZE,
        ),
        start=1,
    ):
        print(
            f"\n正在处理第 "
            f"{batch_index}/{total_batches} 批，"
            f"本批 {len(batch)} 个文件"
        )

        formal_category_count = len([
            code
            for code in CATEGORY_DEFINITIONS
            if code not in {
                "other",
                "uncategorized",
            }
        ])

        print(
            "当前正式分类数量："
            f"{formal_category_count}，"
            "其中动态分类数量："
            f"{len(DYNAMIC_CATEGORY_CODES)}"
        )

        # 每一批重新构建 Prompt
        prompt = build_prompt(
            batch
        )

        try:
            content = call_model(
                prompt
            )

            raw_results = (
                extract_json_array(
                    content
                )
            )

            # 关键顺序：
            # 先注册动态分类，再标准化结果
            newly_registered = (
                register_dynamic_categories(
                    raw_results
                )
            )

            if newly_registered:
                print(
                    f"第 {batch_index} 批动态新增 "
                    f"{len(newly_registered)} 个分类"
                )

                print(
                    "新增分类将在下一批 Prompt "
                    "中自动生效"
                )

            batch_results = (
                match_batch_results(
                    batch,
                    raw_results,
                )
            )

            # 按原始批次顺序追加
            all_results.extend(
                batch_results
            )

            print(
                f"第 {batch_index} 批完成："
                f"模型返回 {len(raw_results)} 条，"
                f"最终生成 {len(batch_results)} 条"
            )

        except Exception as e:
            print(
                f"第 {batch_index} 批处理失败："
                f"{e}"
            )

            # 失败批次按原顺序生成未分类
            for item in batch:
                all_results.append(
                    build_failure_result(
                        item,
                        str(e),
                    )
                )

        # 不能写 break，否则只会处理第一批
        time.sleep(
            BATCH_SLEEP_SECONDS
        )

    if not all_results:
        raise ValueError(
            "没有生成任何分类结果"
        )

    # ========================================================
    # 不进行任何排序
    # all_results 就是原始 Excel 顺序
    # ========================================================

    result_df = pd.DataFrame(
        all_results
    )

    output_columns = [
        "item_id",
        "doc_id",
        "filename",
        "category_codes",
        "category_names",
        "category_confidences",
        "categories_json",
        "reason",
        "suggested_new_category_code",
        "suggested_new_category_name",
        "suggested_new_category_description",
        "contains_dynamic_category",
        "auto_write_category_codes",
        "auto_write_suggested",
        "needs_review",
    ]

    existing_columns = [
        column
        for column in output_columns
        if column in result_df.columns
    ]

    result_df = result_df[
        existing_columns
    ]

    ensure_output_parent(
        OUTPUT_EXCEL
    )

    # 不排序，直接输出
    result_df.to_excel(
        OUTPUT_EXCEL,
        index=False,
    )

    print(
        "\n分类完成，结果已写入："
        f"{OUTPUT_EXCEL}"
    )

    # 打印分类使用情况
    print_category_statistics(
        all_results
    )

    # 导出动态分类
    export_dynamic_categories()

    # 导出最终完整分类体系
    export_final_categories(
        all_results
    )

    # 打印最终分类数量
    print_final_category_summary()


# ============================================================
# 18. 程序入口
# ============================================================

if __name__ == "__main__":
    classify_excel()