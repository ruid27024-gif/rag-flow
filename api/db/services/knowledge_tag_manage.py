from api.db.db_models import DB,KnowledgeTagType,KnowledgeTagOption
from api.db.services.knowledge_tag_type import KnowledgeTagTypeService
from api.db.services.knowledge_tag_option import KnowledgeTagOptionService
from common.misc_utils import get_uuid
from common.time_utils import current_timestamp


class KnowledgeTagManageService:

    @classmethod
    @DB.connection_context()
    def create_type_with_options(cls, data):
        """
        新增标签类型，并同时新增选项
        注意：
        这个方法自己管理事务，里面不要调用其他带 @DB.connection_context() 的 Service 方法。
        """

        type_code = data.get("type_code")
        type_name = data.get("type_name")

        if not type_code:
            raise ValueError("type_code 不能为空")

        if not type_name:
            raise ValueError("type_name 不能为空")

        type_code = type_code.strip()
        type_name = type_name.strip()

        multi_select = 1 if data.get("multi_select", False) else 0
        required = 1 if data.get("required", False) else 0
        sort_order = data.get("sort_order", 0)
        enabled = 1 if data.get("enabled", True) else 0
        options = data.get("options", [])

        with DB.atomic():
            # 1. 校验类型是否已存在
            exists = KnowledgeTagType.select().where(
                KnowledgeTagType.type_code == type_code
            ).first()

            if exists:
                raise ValueError(f"标签类型已存在: {type_code}")

            now = current_timestamp()

            # 2. 新增标签类型
            tag_type = KnowledgeTagType(
                id=get_uuid(),
                type_code=type_code,
                type_name=type_name,
                multi_select=multi_select,
                required=required,
                sort_order=sort_order,
                enabled=enabled,
                create_time=now,
                update_time=now,
            )
            tag_type.save(force_insert=True)

            # 3. 新增标签选项
            rows = []

            option_code_set = set()

            for item in options:
                option_code = item.get("option_code")
                option_name = item.get("option_name")

                if not option_code:
                    raise ValueError("option_code 不能为空")

                if not option_name:
                    raise ValueError("option_name 不能为空")

                option_code = option_code.strip()
                option_name = option_name.strip()

                if option_code in option_code_set:
                    raise ValueError(f"选项编码重复: {option_code}")

                option_code_set.add(option_code)

                rows.append({
                    "id": get_uuid(),
                    "type_code": type_code,
                    "option_code": option_code,
                    "option_name": option_name,
                    "sort_order": item.get("sort_order", 0),
                    "enabled": 1 if item.get("enabled", True) else 0,
                    "create_time": now,
                    "update_time": now,
                })

            if rows:
                KnowledgeTagOption.insert_many(rows).execute()

            return tag_type

    @classmethod
    @DB.connection_context()
    def list_tag_config(cls):
        """
        返回标签类型 + 选项配置
        """

        types = KnowledgeTagType.select().where(
            KnowledgeTagType.enabled == 1
        ).order_by(
            KnowledgeTagType.sort_order.asc()
        )

        result = []

        for tag_type in types:
            options = KnowledgeTagOption.select().where(
                (KnowledgeTagOption.type_code == tag_type.type_code) &
                (KnowledgeTagOption.enabled == 1)
            ).order_by(
                KnowledgeTagOption.sort_order.asc()
            )

            result.append({
                "type_code": tag_type.type_code,
                "type_name": tag_type.type_name,
                "multi_select": bool(tag_type.multi_select),
                "required": bool(tag_type.required),
                "sort_order": tag_type.sort_order,
                "options": [
                    {
                        "option_code": option.option_code,
                        "option_name": option.option_name,
                        "sort_order": option.sort_order,
                    }
                    for option in options
                ]
            })

        return result

    @classmethod
    @DB.connection_context()
    def list_tag_config_all(cls):
        """
        管理页面用：返回全部类型和全部选项，包括禁用的
        """
        types = (
            KnowledgeTagType
            .select()
            .order_by(KnowledgeTagType.sort_order.asc(), KnowledgeTagType.create_time.asc())
        )

        result = []

        for tag_type in types:
            options = (
                KnowledgeTagOption
                .select()
                .where(KnowledgeTagOption.type_code == tag_type.type_code)
                .order_by(KnowledgeTagOption.sort_order.asc(), KnowledgeTagOption.create_time.asc())
            )

            result.append({
                "id": tag_type.id,
                "type_code": tag_type.type_code,
                "type_name": tag_type.type_name,
                "multi_select": bool(tag_type.multi_select),
                "required": bool(tag_type.required),
                "sort_order": tag_type.sort_order,
                "enabled": bool(tag_type.enabled),
                "options": [
                    {
                        "id": option.id,
                        "option_code": option.option_code,
                        "option_name": option.option_name,
                        "sort_order": option.sort_order,
                        "enabled": bool(option.enabled),
                    }
                    for option in options
                ]
            })

        return result