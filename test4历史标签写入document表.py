import logging

from api.db.db_models import (
    KnowledgeTagOption,
    StagedFile,
    StagedFileTag,
)
from api.db.services.document_service import DocumentService


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

logger = logging.getLogger(__name__)


def build_tag_option_name_map():
    """
    构建标签选项映射：

    {
        (type_code, option_code): option_name
    }
    """

    option_name_map = {}

    query = KnowledgeTagOption.select(
        KnowledgeTagOption.type_code,
        KnowledgeTagOption.option_code,
        KnowledgeTagOption.option_name,
    )

    for row in query:
        type_code = row.type_code
        option_code = row.option_code
        option_name = row.option_name

        if not type_code or not option_code:
            continue

        option_name_map[
            (str(type_code), str(option_code))
        ] = option_name or option_code

    return option_name_map


def get_staged_file_tags_map(stage_id, option_name_map):
    """
    查询暂存文件标签，并将 option_code 转成 option_name。

    返回：

    {
        "标签类型编码": ["标签中文名称1", "标签中文名称2"]
    }
    """

    tag_rows = StagedFileTag.select(
        StagedFileTag.type_code,
        StagedFileTag.option_code,
    ).where(
        StagedFileTag.stage_id == stage_id
    )

    tags_map = {}

    for row in tag_rows:
        type_code = row.type_code
        option_code = row.option_code

        if not type_code or not option_code:
            continue

        type_code = str(type_code)
        option_code = str(option_code)

        # 查询中文名称。
        # 如果数据库找不到对应配置，则保留原 option_code，避免丢数据。
        option_name = option_name_map.get(
            (type_code, option_code),
            option_code,
        )

        tags_map.setdefault(type_code, [])

        if option_name not in tags_map[type_code]:
            tags_map[type_code].append(option_name)

    return tags_map


def get_staged_file_name(staged):
    """
    获取暂存文件名称。
    根据实际模型字段兼容多个名称。
    """

    return (
        getattr(staged, "name", None)
        or getattr(staged, "file_name", None)
        or getattr(staged, "filename", None)
        or "未知文件名"
    )


def backfill_staged_tags_to_documents(dry_run=False):
    """
    将暂存文件标签重新写入正式文档的 meta_fields。

    dry_run=True：
        只打印，不更新数据库。

    dry_run=False：
        真正更新数据库。
    """

    print("开始执行历史标签中文名称回填...", flush=True)

    # 只查询一次标签配置，避免每个文件重复查询
    option_name_map = build_tag_option_name_map()

    print(
        f"已加载标签选项数量：{len(option_name_map)}",
        flush=True,
    )

    staged_query = StagedFile.select()
    total_count = staged_query.count()

    print(
        f"StagedFile 总记录数：{total_count}",
        flush=True,
    )

    total = 0
    updated = 0
    unchanged = 0
    skipped = 0
    failed = 0

    failed_items = []

    for staged in staged_query.iterator():
        total += 1

        stage_id = staged.id
        doc_id = getattr(staged, "doc_id", None)
        file_name = get_staged_file_name(staged)

        print(
            f"[{total}/{total_count}] "
            f"文件名={file_name}, "
            f"stage_id={stage_id}, "
            f"doc_id={doc_id}",
            flush=True,
        )

        # 没有关联正式文档
        if not doc_id:
            skipped += 1

            reason = "StagedFile 没有 doc_id"

            failed_items.append({
                "file_name": file_name,
                "stage_id": stage_id,
                "doc_id": "",
                "reason": reason,
            })

            print(f"跳过：{reason}", flush=True)
            continue

        try:
            # 读取标签，并把编码转换成中文名称
            tags_map = get_staged_file_tags_map(
                stage_id=stage_id,
                option_name_map=option_name_map,
            )

            if not tags_map:
                skipped += 1

                reason = "没有有效标签"

                failed_items.append({
                    "file_name": file_name,
                    "stage_id": stage_id,
                    "doc_id": doc_id,
                    "reason": reason,
                })

                print(f"跳过：{reason}", flush=True)
                continue

            # 查询正式文档
            success, doc_obj = DocumentService.get_by_id(doc_id)

            if not success or not doc_obj:
                skipped += 1

                reason = "对应的 Document 不存在"

                failed_items.append({
                    "file_name": file_name,
                    "stage_id": stage_id,
                    "doc_id": doc_id,
                    "reason": reason,
                })

                print(f"跳过：{reason}", flush=True)
                continue

            # 保留原来的其他元数据
            old_meta_fields = dict(doc_obj.meta_fields or {})
            new_meta_fields = dict(old_meta_fields)

            # 用中文标签覆盖原来的同名标签字段
            new_meta_fields.update(tags_map)

            # 如果已经是中文且内容相同，则不更新
            if new_meta_fields == old_meta_fields:
                unchanged += 1

                print(
                    f"无需更新：meta_fields 已经是最新值，doc_id={doc_id}",
                    flush=True,
                )
                continue

            print(
                "发现需要更新的标签：\n"
                f"  文件名：{file_name}\n"
                f"  doc_id：{doc_id}\n"
                f"  标签：{tags_map}\n"
                f"  原数据：{old_meta_fields}\n"
                f"  新数据：{new_meta_fields}",
                flush=True,
            )

            if dry_run:
                updated += 1
                print(
                    f"[DRY-RUN] 未写入数据库，doc_id={doc_id}",
                    flush=True,
                )
                continue

            # 真正写回正式文档
            result = DocumentService.update_by_id(
                doc_id,
                {
                    "meta_fields": new_meta_fields,
                },
            )

            if result is False:
                failed += 1

                reason = (
                    "DocumentService.update_by_id 返回 False"
                )

                failed_items.append({
                    "file_name": file_name,
                    "stage_id": stage_id,
                    "doc_id": doc_id,
                    "reason": reason,
                })

                print(
                    f"更新失败：{reason}",
                    flush=True,
                )
                continue

            updated += 1

            print(
                f"更新成功：文件名={file_name}, "
                f"stage_id={stage_id}, "
                f"doc_id={doc_id}",
                flush=True,
            )

        except Exception as exc:
            failed += 1

            reason = f"处理发生异常：{exc}"

            failed_items.append({
                "file_name": file_name,
                "stage_id": stage_id,
                "doc_id": doc_id,
                "reason": reason,
            })

            logger.exception(
                "处理失败：文件名=%s, stage_id=%s, doc_id=%s",
                file_name,
                stage_id,
                doc_id,
            )

    print("\n" + "=" * 80, flush=True)
    print("处理完成", flush=True)
    print(f"总记录数：{total}", flush=True)

    if dry_run:
        print(f"预计更新数量：{updated}", flush=True)
    else:
        print(f"实际更新成功：{updated}", flush=True)

    print(f"已经是最新值：{unchanged}", flush=True)
    print(f"跳过数量：{skipped}", flush=True)
    print(f"失败数量：{failed}", flush=True)
    print("=" * 80, flush=True)

    if failed_items:
        print("\n以下记录没有成功处理：", flush=True)

        for index, item in enumerate(failed_items, start=1):
            print(
                f"{index}. 文件名：{item['file_name']}\n"
                f"   stage_id：{item['stage_id']}\n"
                f"   doc_id：{item['doc_id'] or '-'}\n"
                f"   原因：{item['reason']}",
                flush=True,
            )
    else:
        print("\n所有需要处理的记录均已处理成功。", flush=True)


if __name__ == "__main__":
    # 第一次建议先使用 True 查看转换结果
    # backfill_staged_tags_to_documents(dry_run=True)

    # 确认输出正确后，执行真正的数据库更新
    backfill_staged_tags_to_documents(dry_run=False)