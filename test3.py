# -*- coding: utf-8 -*-

"""
历史文档标签补录脚本。

表格必须包含两列：

    filename
    category_codes

示例：

    filename                              category_codes
    测试文件.pdf                           pulping
    测试文件2.pdf                          raw_materials, papermaking

匹配方式：

    Document.name == filename

即文件名完全一致匹配，不去空格、不忽略大小写、不做模糊匹配。

写入的固定标签：

    knowledge_level / public
    knowledge_type / operation_sop
    applicable_lines / line_1
    applicable_lines / line_2
    applicable_lines / public_engineering
    applicable_lines / qc_center

知识分类从表格 category_codes 读取：

    knowledge_category / pulping
    knowledge_category / papermaking
    ...

注意：
    创建 StagedFile 时不会传 version，使用模型默认值。
"""

import csv
import re
import sys
import uuid
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import pandas as pd


# ============================================================
# 一、修改为你项目中的真实导入路径
# ============================================================

# 如果这些模型都在 api.db.db_models 中，可以直接使用。
# 如果实际路径不同，只修改这里即可。
from api.db.db_models import (
    DB,
    Document,
    StagedFile,
    StagedFileTag,
)


# ============================================================
# 二、运行配置：请修改这里
# ============================================================

# Excel 或 CSV 文件地址。
INPUT_FILE = "/home/zyb/paper_files_classified_gpt.xlsx"

# StagedFile.tenant_id 是必填字段，但 Document 中没有 tenant_id。
# 请填写当前系统对应的租户 ID。
TENANT_ID = ""

# Document.created_by 为空时使用的用户 ID。
DEFAULT_USER_ID = "manual_backfill"

# 执行结果报告。
REPORT_FILE = "./backfill_document_tags_report.csv"

# 是否只处理有效的 Document。
# True：只处理 Document.status == "1"
# False：不限制 Document.status
ONLY_VALID_DOCUMENT = True

# 如果只需要处理一个知识库，可以填写对应 kb_id。
# 不限制知识库请设置为 None。
TARGET_KB_ID = None

# 是否仅预览。
# True：只查询，不写数据库。
# False：正式写数据库。
DRY_RUN = False


# ============================================================
# 三、标签配置
# ============================================================

# 后补批次标记。
# StagedFile.batch_id 最大长度为32。
BATCH_ID = f"tag_backfill_{datetime.now():%Y%m%d%H%M%S}"

# 用于识别历史补录数据。
BACKFILL_BATCH_PREFIX = "tag_backfill_"

# 固定适用产线。
DEFAULT_APPLICABLE_LINES = [
    "line_1",
    "line_2",
    "public_engineering",
    "qc_center",
]

# 本脚本管理的标签类型。
MANAGED_TYPE_CODES = [
    "knowledge_level",
    "knowledge_category",
    "knowledge_type",
    "applicable_lines",
]

# 合法知识分类。
VALID_CATEGORY_CODES = {
    "pulping",
    "modulation",
    "papermaking",
    "processing",
    "general_mgmt",
    "water_management",
    "equipment_maintenance",
    "quality_control",
    "energy_carbon",
    "raw_materials",
    "paper_conservation",
    "paper_industry_history",
    "papermaking_process_simulation",
    "other",
    "uncategorized",
}


# ============================================================
# 四、读取表格
# ============================================================

def read_input_file(file_path):
    """
    读取 Excel 或 CSV。

    必须包含：
        filename
        category_codes
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"输入文件不存在：{path.resolve()}")

    suffix = path.suffix.lower()

    if suffix in {".xlsx", ".xls"}:
        dataframe = pd.read_excel(
            path,
            dtype=object,
            keep_default_na=False,
        )

    elif suffix == ".csv":
        try:
            dataframe = pd.read_csv(
                path,
                dtype=object,
                keep_default_na=False,
                encoding="utf-8-sig",
            )
        except UnicodeDecodeError:
            dataframe = pd.read_csv(
                path,
                dtype=object,
                keep_default_na=False,
                encoding="gb18030",
            )

    else:
        raise ValueError(
            f"不支持的文件格式：{suffix}，"
            "只支持 .xlsx、.xls、.csv"
        )

    required_columns = {
        "filename",
        "category_codes",
    }

    missing_columns = required_columns - set(dataframe.columns)

    if missing_columns:
        raise ValueError(
            f"表格缺少必要列：{sorted(missing_columns)}；"
            f"当前表格列为：{list(dataframe.columns)}"
        )

    return dataframe


def parse_category_codes(value):
    """
    解析 category_codes 多选值。

    支持：
        raw_materials, papermaking
        raw_materials，papermaking
        raw_materials;papermaking
        raw_materials；papermaking
        换行分隔
    """
    if value is None:
        return []

    value = str(value)

    if not value.strip():
        return []

    parts = re.split(r"[,，;；\r\n]+", value)

    result = []
    seen = set()

    for part in parts:
        code = part.strip()

        if not code:
            continue

        if code not in seen:
            result.append(code)
            seen.add(code)

    return result


def load_assignments(file_path):
    """
    加载表格数据。

    filename 不执行 strip，不转小写，不做任何标准化。

    如果相同 filename 在表格中出现多次，则合并 category_codes。
    """
    dataframe = read_input_file(file_path)

    assignments = {}

    for index, row in dataframe.iterrows():
        excel_row = index + 2

        raw_filename = row["filename"]

        if raw_filename is None:
            print(f"[跳过] 表格第 {excel_row} 行 filename 为空")
            continue

        # 故意不调用 strip()。
        # 必须保持原始文件名，后续完全一致匹配 Document.name。
        filename = str(raw_filename)

        if filename == "":
            print(f"[跳过] 表格第 {excel_row} 行 filename 为空字符串")
            continue

        category_codes = parse_category_codes(
            row["category_codes"]
        )

        invalid_codes = [
            code
            for code in category_codes
            if code not in VALID_CATEGORY_CODES
        ]

        if invalid_codes:
            raise ValueError(
                f"表格第 {excel_row} 行包含非法分类："
                f"{invalid_codes}；filename={filename!r}"
            )

        if filename not in assignments:
            assignments[filename] = {
                "filename": filename,
                "category_codes": set(),
                "excel_rows": [],
            }

        assignments[filename]["category_codes"].update(
            category_codes
        )
        assignments[filename]["excel_rows"].append(excel_row)

    return assignments


# ============================================================
# 五、构造标签
# ============================================================

def build_tags(category_codes):
    """
    构造一个 Document 对应的全部标签。
    """
    tags = {
        # 知识等级：公开。
        ("knowledge_level", "public"),

        # 知识类型：操作规程。
        ("knowledge_type", "operation_sop"),
    }

    # 知识分类。
    for category_code in category_codes:
        tags.add(
            ("knowledge_category", category_code)
        )

    # 适用产线。
    for line_code in DEFAULT_APPLICABLE_LINES:
        tags.add(
            ("applicable_lines", line_code)
        )

    return sorted(tags)


# ============================================================
# 六、查询 Document
# ============================================================

def find_documents_by_exact_name(filename):
    """
    根据完全一致的原始文件名查询 Document。

    对应条件：

        Document.name == filename

    同名 Document 全部返回。
    """
    query = Document.select().where(
        Document.name == filename
    )

    if ONLY_VALID_DOCUMENT:
        query = query.where(
            Document.status == "1"
        )

    if TARGET_KB_ID:
        query = query.where(
            Document.kb_id == TARGET_KB_ID
        )

    return list(query)


# ============================================================
# 七、创建或查找 StagedFile
# ============================================================

def find_existing_backfill_stage(document_id):
    """
    查询该 Document 是否已有本脚本创建的补录 StagedFile。

    使用条件：
        doc_id 相同
        batch_id 以 tag_backfill_ 开头

    这样重复运行脚本时，不会不断创建新的 StagedFile。
    """
    return (
        StagedFile
        .select()
        .where(
            (StagedFile.doc_id == document_id)
            & (
                StagedFile.batch_id.startswith(
                    BACKFILL_BATCH_PREFIX
                )
            )
        )
        .order_by(StagedFile.created_at.asc())
        .first()
    )


def create_backfill_stage(document):
    """
    创建历史补录 StagedFile。

    注意：
        这里没有传入 version。
        version 使用 StagedFile 模型定义的默认值。
    """
    now = datetime.now()

    stage = StagedFile.create(
        id=uuid.uuid4().hex,

        # 标记为脚本后补数据。
        batch_id=BATCH_ID,

        # 从 Document 获取。
        kb_id=document.kb_id,
        doc_id=document.id,

        # Document 中没有 tenant_id，使用配置值。
        tenant_id=TENANT_ID,

        # 优先使用 Document.created_by。
        user_id=document.created_by or DEFAULT_USER_ID,

        filename=document.name,

        # path 不能为空。
        path=document.location or document.name,

        size=document.size or 0,

        # 重要：不传 version。
        # version 使用模型默认值。

        # 原 Document 已经存在，因此设置为 committed。
        status="committed",

        approval_level_1=None,
        approval_level_2=None,

        minio_bucket=None,
        minio_object_name=None,
        url=None,

        created_at=now,
        approved_at=None,

        # 标记为脚本补录。
        approved_by="manual_tag_backfill",

        committed_at=now,
        error_msg=None,
    )

    return stage


def get_or_create_backfill_stage(document):
    """
    获取或创建补录 StagedFile。

    返回：
        stage, created
    """
    stage = find_existing_backfill_stage(document.id)

    if stage:
        return stage, False

    stage = create_backfill_stage(document)

    return stage, True


# ============================================================
# 八、写入 StagedFileTag
# ============================================================

def replace_managed_tags(stage_id, tags):
    """
    同步补录标签。

    先删除当前 stage 下本脚本管理的四类标签，然后重新写入。

    这样重复执行脚本时：
        1. 不会重复插入；
        2. Excel 中修改的标签可以同步；
        3. 不会影响其他未知 type_code 的标签。
    """
    delete_count = (
        StagedFileTag
        .delete()
        .where(
            (StagedFileTag.stage_id == stage_id)
            & (
                StagedFileTag.type_code.in_(
                    MANAGED_TYPE_CODES
                )
            )
        )
        .execute()
    )

    if not tags:
        return delete_count, 0

    now = datetime.now()

    rows = [
        {
            "stage_id": stage_id,
            "type_code": type_code,
            "option_code": option_code,
            "create_time": now,
        }
        for type_code, option_code in tags
    ]

    StagedFileTag.insert_many(rows).execute()

    return delete_count, len(rows)


# ============================================================
# 九、执行报告
# ============================================================

def write_report(report_rows):
    """
    将执行结果写入 CSV。
    """
    report_path = Path(REPORT_FILE)

    if report_path.parent:
        report_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

    fieldnames = [
        "filename",
        "excel_rows",
        "category_codes",
        "result",
        "doc_id",
        "kb_id",
        "stage_id",
        "stage_created",
        "deleted_tag_count",
        "inserted_tag_count",
        "message",
    ]

    with report_path.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(report_rows)


# ============================================================
# 十、配置检查
# ============================================================

def check_config():
    if not INPUT_FILE:
        raise ValueError("请配置 INPUT_FILE")

    # if not TENANT_ID:
    #     raise ValueError("请配置 TENANT_ID")

    # if TENANT_ID == "请修改为实际tenant_id":
    #     raise ValueError(
    #         "请先修改脚本顶部的 TENANT_ID"
    #     )

    if len(BATCH_ID) > 32:
        raise ValueError(
            f"BATCH_ID 超过32个字符：{BATCH_ID}"
        )


# ============================================================
# 十一、主程序
# ============================================================

def main():
    check_config()

    print("=" * 100)
    print("开始补录历史文档标签")
    print("=" * 100)
    print(f"输入文件：{Path(INPUT_FILE).resolve()}")
    print(f"tenant_id：{TENANT_ID}")
    print(f"目标 kb_id：{TARGET_KB_ID or '全部知识库'}")
    print(f"仅有效文档：{ONLY_VALID_DOCUMENT}")
    print(f"dry-run：{DRY_RUN}")
    print(f"补录 batch_id：{BATCH_ID}")
    print("version：创建 StagedFile 时不传，使用模型默认值")
    print("文件名匹配方式：Document.name == filename")
    print("=" * 100)

    assignments = load_assignments(INPUT_FILE)

    print(
        f"表格中共读取到 {len(assignments)} 个不同文件名"
    )

    statistics = defaultdict(int)
    statistics["input_filename_count"] = len(assignments)

    report_rows = []

    with DB.connection_context():
        for filename, assignment in assignments.items():
            category_codes = sorted(
                assignment["category_codes"]
            )
            excel_rows = assignment["excel_rows"]

            tags = build_tags(category_codes)

            print()
            print("-" * 100)
            print(f"文件名：{filename!r}")
            print(f"Excel 行：{excel_rows}")
            print(f"知识分类：{category_codes}")

            documents = find_documents_by_exact_name(
                filename
            )

            if not documents:
                statistics["not_found_filename_count"] += 1

                print(
                    "[未找到] Document 表中不存在完全同名的有效文档"
                )

                report_rows.append({
                    "filename": filename,
                    "excel_rows": ",".join(
                        str(row) for row in excel_rows
                    ),
                    "category_codes": ",".join(
                        category_codes
                    ),
                    "result": "not_found",
                    "doc_id": "",
                    "kb_id": "",
                    "stage_id": "",
                    "stage_created": "",
                    "deleted_tag_count": 0,
                    "inserted_tag_count": 0,
                    "message": (
                        "Document.name 完全一致匹配失败"
                    ),
                })

                continue

            statistics["matched_filename_count"] += 1

            print(
                f"[找到] 匹配到 {len(documents)} 条 Document，"
                "全部补录相同标签"
            )

            for document in documents:
                statistics["matched_document_count"] += 1

                print()
                print(
                    f"  Document："
                    f"id={document.id}，"
                    f"kb_id={document.kb_id}，"
                    f"name={document.name!r}"
                )

                print("  待写入标签：")

                for type_code, option_code in tags:
                    print(
                        f"    {type_code} / {option_code}"
                    )

                if DRY_RUN:
                    print("  [预览] DRY_RUN=True，未写数据库")

                    report_rows.append({
                        "filename": filename,
                        "excel_rows": ",".join(
                            str(row) for row in excel_rows
                        ),
                        "category_codes": ",".join(
                            category_codes
                        ),
                        "result": "dry_run",
                        "doc_id": document.id,
                        "kb_id": document.kb_id,
                        "stage_id": "",
                        "stage_created": "",
                        "deleted_tag_count": 0,
                        "inserted_tag_count": len(tags),
                        "message": "预览成功，未写数据库",
                    })

                    continue

                try:
                    # 每个 Document 单独使用事务。
                    # 单条失败不会影响其他 Document。
                    with DB.atomic():
                        stage, created = (
                            get_or_create_backfill_stage(
                                document
                            )
                        )

                        deleted_count, inserted_count = (
                            replace_managed_tags(
                                stage_id=stage.id,
                                tags=tags,
                            )
                        )

                    if created:
                        statistics["created_stage_count"] += 1
                        stage_action = "新建"
                    else:
                        statistics["reused_stage_count"] += 1
                        stage_action = "复用"

                    statistics["deleted_tag_count"] += (
                        deleted_count
                    )
                    statistics["inserted_tag_count"] += (
                        inserted_count
                    )

                    print(
                        f"  [成功] {stage_action} StagedFile；"
                        f"stage_id={stage.id}；"
                        f"删除旧标签={deleted_count}；"
                        f"写入标签={inserted_count}"
                    )

                    report_rows.append({
                        "filename": filename,
                        "excel_rows": ",".join(
                            str(row) for row in excel_rows
                        ),
                        "category_codes": ",".join(
                            category_codes
                        ),
                        "result": "success",
                        "doc_id": document.id,
                        "kb_id": document.kb_id,
                        "stage_id": stage.id,
                        "stage_created": (
                            "yes" if created else "no"
                        ),
                        "deleted_tag_count": deleted_count,
                        "inserted_tag_count": inserted_count,
                        "message": (
                            f"{stage_action}历史补录StagedFile"
                        ),
                    })

                except Exception as exception:
                    statistics["failed_document_count"] += 1

                    error_message = (
                        f"{type(exception).__name__}: "
                        f"{exception}"
                    )

                    print(
                        f"  [失败] {error_message}"
                    )

                    report_rows.append({
                        "filename": filename,
                        "excel_rows": ",".join(
                            str(row) for row in excel_rows
                        ),
                        "category_codes": ",".join(
                            category_codes
                        ),
                        "result": "failed",
                        "doc_id": document.id,
                        "kb_id": document.kb_id,
                        "stage_id": "",
                        "stage_created": "",
                        "deleted_tag_count": 0,
                        "inserted_tag_count": 0,
                        "message": error_message,
                    })

    write_report(report_rows)

    print()
    print("=" * 100)
    print("补录执行完成")
    print("=" * 100)
    print(
        f"表格文件名数量："
        f"{statistics['input_filename_count']}"
    )
    print(
        f"匹配成功文件名数量："
        f"{statistics['matched_filename_count']}"
    )
    print(
        f"未匹配文件名数量："
        f"{statistics['not_found_filename_count']}"
    )
    print(
        f"匹配到的 Document 数量："
        f"{statistics['matched_document_count']}"
    )

    if DRY_RUN:
        print("当前为 DRY_RUN，没有写入数据库")
    else:
        print(
            f"新建 StagedFile 数量："
            f"{statistics['created_stage_count']}"
        )
        print(
            f"复用 StagedFile 数量："
            f"{statistics['reused_stage_count']}"
        )
        print(
            f"删除旧标签数量："
            f"{statistics['deleted_tag_count']}"
        )
        print(
            f"写入 StagedFileTag 数量："
            f"{statistics['inserted_tag_count']}"
        )
        print(
            f"失败 Document 数量："
            f"{statistics['failed_document_count']}"
        )

    print(f"执行报告：{Path(REPORT_FILE).resolve()}")
    print("=" * 100)

    if statistics["failed_document_count"] > 0:
        sys.exit(2)


if __name__ == "__main__":
    main()