from api.db.db_models import DB, KnowledgeTagType,KnowledgeTagOption
from api.db.services.common_service import CommonService
from common.misc_utils import get_uuid
from common.time_utils import current_timestamp


class KnowledgeTagTypeService(CommonService):
    model = KnowledgeTagType

    @classmethod
    @DB.connection_context()
    def save(cls, **kwargs):
        """
        新增标签类型
        示例：
        {
            "type_code": "knowledge_level",
            "type_name": "知识等级",
            "multi_select": 0,
            "required": 1,
            "sort_order": 1,
            "enabled": 1
        }
        """

        if "id" not in kwargs:
            kwargs["id"] = get_uuid()

        if "create_time" not in kwargs:
            kwargs["create_time"] = current_timestamp()

        if "update_time" not in kwargs:
            kwargs["update_time"] = current_timestamp()

        if "enabled" not in kwargs:
            kwargs["enabled"] = 1

        if "multi_select" not in kwargs:
            kwargs["multi_select"] = 0

        if "required" not in kwargs:
            kwargs["required"] = 0

        if "sort_order" not in kwargs:
            kwargs["sort_order"] = 0

        # 校验 type_code
        type_code = kwargs.get("type_code")
        if not type_code:
            raise ValueError("type_code 不能为空")

        # 校验 type_name
        type_name = kwargs.get("type_name")
        if not type_name:
            raise ValueError("type_name 不能为空")

        # 校验是否重复
        exists = cls.model.select().where(
            cls.model.type_code == type_code
        ).first()

        if exists:
            raise ValueError(f"标签类型已存在: {type_code}")

        obj = cls.model(**kwargs)
        obj.save(force_insert=True)
        return obj

    @classmethod
    @DB.connection_context()
    def get_by_type_code(cls, type_code):
        """
        根据 type_code 获取标签类型
        """
        try:
            return cls.model.select().where(
                cls.model.type_code == type_code
            ).first()
        except Exception as e:
            print(f"Error fetching tag type by type_code={type_code}: {e}")
            return None

    @classmethod
    @DB.connection_context()
    def list_enabled(cls):
        """
        获取所有启用的标签类型
        """
        try:
            return list(
                cls.model.select()
                .where(cls.model.enabled == 1)
                .order_by(cls.model.sort_order.asc())
            )
        except Exception as e:
            print(f"Error listing enabled tag types: {e}")
            return []

    @classmethod
    @DB.connection_context()
    def update_by_type_code(cls, type_code, **kwargs):
        """
        根据 type_code 更新标签类型
        """
        if "updated_time" not in kwargs:
            kwargs["update_time"] = current_timestamp()

        return cls.model.update(**kwargs).where(
            cls.model.type_code == type_code
        ).execute()

    @classmethod
    @DB.connection_context()
    def disable_by_type_code(cls, type_code):
        """
        禁用标签类型
        """
        return cls.model.update(
            enabled=0,
            update_time=current_timestamp()
        ).where(
            cls.model.type_code == type_code
        ).execute()

    @classmethod
    @DB.connection_context()
    def enable_by_type_code(cls, type_code):
        """
        启用标签类型
        """
        return cls.model.update(
            enabled=1,
            update_time=current_timestamp()
        ).where(
            cls.model.type_code == type_code
        ).execute()

    @classmethod
    @DB.connection_context()
    def delete_by_type_code(cls, type_code):
        """
        删除标签类型，并删除该类型下的所有选项。
        当前还没有 DocumentTagRelation，所以直接物理删除。
        """
        if not type_code:
            raise ValueError("type_code 不能为空")

        with DB.atomic():
            # 删除该类型下的所有选项
            KnowledgeTagOption.delete().where(
                KnowledgeTagOption.type_code == type_code
            ).execute()

            # 删除类型本身
            deleted_count = cls.model.delete().where(
                cls.model.type_code == type_code
            ).execute()

        return deleted_count