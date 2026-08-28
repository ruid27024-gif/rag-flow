from api.db.db_models import DB, KnowledgeTagOption, KnowledgeTagType
from api.db.services.common_service import CommonService
from common.misc_utils import get_uuid
from common.time_utils import current_timestamp



class KnowledgeTagOptionService(CommonService):
    model = KnowledgeTagOption

    @classmethod
    @DB.connection_context()
    def save(cls, **kwargs):
        """
        新增标签选项。

        id 完全由 MySQL AUTO_INCREMENT 生成。
        无论调用方是否传入 id，都不会将 id 写入数据库。
        """

        # 无论调用方有没有传入 id，都强制删除。
        kwargs.pop("id", None)

        type_code = kwargs.get("type_code")
        option_code = kwargs.get("option_code")
        option_name = kwargs.get("option_name")

        if not type_code:
            raise ValueError("type_code 不能为空")

        if not option_code:
            raise ValueError("option_code 不能为空")

        if not option_name:
            raise ValueError("option_name 不能为空")

        sort_order = kwargs.get("sort_order", 0)
        enabled = 1 if kwargs.get("enabled", 1) else 0

        create_time = kwargs.get(
            "create_time",
            current_timestamp(),
        )
        update_time = kwargs.get(
            "update_time",
            current_timestamp(),
        )

        # 校验标签类型是否存在且已启用。
        tag_type = (
            KnowledgeTagType
            .select()
            .where(
                (KnowledgeTagType.type_code == type_code)
                & (KnowledgeTagType.enabled == 1)
            )
            .first()
        )

        if not tag_type:
            raise ValueError(
                f"标签类型不存在或未启用: {type_code}"
            )

        # 校验同一个 type_code 下 option_code 是否重复。
        exists = (
            cls.model
            .select()
            .where(
                (cls.model.type_code == type_code)
                & (cls.model.option_code == option_code)
            )
            .first()
        )

        if exists:
            raise ValueError(
                "标签选项已存在: "
                f"type_code={type_code}, "
                f"option_code={option_code}"
            )

        # 明确指定插入字段，不包含 id。
        insert_query = cls.model.insert(
            type_code=type_code,
            option_code=option_code,
            option_name=option_name,
            sort_order=sort_order,
            enabled=enabled,
            create_time=create_time,
            update_time=update_time,
        )

        # 临时保留这两行，检查生成的 SQL。
        sql, params = insert_query.sql()
        print("[KnowledgeTagOption INSERT SQL]", sql)
        print("[KnowledgeTagOption INSERT PARAMS]", params)

        # MySQL + BigAutoField 下，execute() 返回数据库生成的自增 ID。
        new_id = insert_query.execute()

        print("[KnowledgeTagOption generated id]", new_id)

        return cls.model.get_by_id(new_id)


    @classmethod
    @DB.connection_context()
    def batch_save(cls, type_code, options):
        """
        批量新增标签选项

        options 示例：
        [
            {
                "option_code": "internal",
                "option_name": "内部",
                "sort_order": 1
            },
            {
                "option_code": "public",
                "option_name": "公开",
                "sort_order": 2
            }
        ]
        """

        if not type_code:
            raise ValueError("type_code 不能为空")

        tag_type = KnowledgeTagType.select().where(
            KnowledgeTagType.type_code == type_code,
            KnowledgeTagType.enabled == 1
        ).first()

        if not tag_type:
            raise ValueError(f"标签类型不存在或未启用: {type_code}")

        rows = []

        for item in options:
            option_code = item.get("option_code")
            option_name = item.get("option_name")

            if not option_code:
                raise ValueError("option_code 不能为空")

            if not option_name:
                raise ValueError("option_name 不能为空")

            exists = cls.model.select().where(
                (cls.model.type_code == type_code) &
                (cls.model.option_code == option_code)
            ).first()

            if exists:
                raise ValueError(
                    f"标签选项已存在: type_code={type_code}, option_code={option_code}"
                )

            rows.append({
                "id": get_uuid(),
                "type_code": type_code,
                "option_code": option_code,
                "option_name": option_name,
                "sort_order": item.get("sort_order", 0),
                "enabled": item.get("enabled", 1),
                "create_time": current_timestamp(),
                "update_time": current_timestamp(),
            })

        if rows:
            cls.model.insert_many(rows).execute()

        return True

    @classmethod
    @DB.connection_context()
    def list_by_type_code(cls, type_code):
        """
        根据 type_code 获取选项列表
        """
        try:
            return list(
                cls.model.select()
                .where(
                    (cls.model.type_code == type_code) &
                    (cls.model.enabled == 1)
                )
                .order_by(cls.model.sort_order.asc())
            )
        except Exception as e:
            print(f"Error listing tag options by type_code={type_code}: {e}")
            return []

    @classmethod
    @DB.connection_context()
    def get_option_name(cls, type_code, option_code):
        """
        根据 type_code + option_code 获取 option_name
        """
        try:
            option = cls.model.select().where(
                (cls.model.type_code == type_code) &
                (cls.model.option_code == option_code)
            ).first()

            if option:
                return option.option_name

            return None
        except Exception as e:
            print(
                f"Error fetching option_name for type_code={type_code}, "
                f"option_code={option_code}: {e}"
            )
            return None

    @classmethod
    @DB.connection_context()
    def update_option(cls, type_code, option_code, **kwargs):
        """
        更新标签选项
        """
        if "update_time" not in kwargs:
            kwargs["update_time"] = current_timestamp()

        return cls.model.update(**kwargs).where(
            (cls.model.type_code == type_code) &
            (cls.model.option_code == option_code)
        ).execute()

    @classmethod
    @DB.connection_context()
    def disable_option(cls, type_code, option_code):
        """
        禁用标签选项
        """
        return cls.model.update(
            enabled=0,
            update_time=current_timestamp()
        ).where(
            (cls.model.type_code == type_code) &
            (cls.model.option_code == option_code)
        ).execute()

    @classmethod
    @DB.connection_context()
    def enable_option(cls, type_code, option_code):
        """
        启用标签选项
        """
        return cls.model.update(
            enabled=1,
            update_time=current_timestamp()
        ).where(
            (cls.model.type_code == type_code) &
            (cls.model.option_code == option_code)
        ).execute()

    @classmethod
    @DB.connection_context()
    def delete_option(cls, type_code, option_code):
        """
        删除标签选项。
        当前还没有 DocumentTagRelation，所以直接物理删除。
        """
        if not type_code:
            raise ValueError("type_code 不能为空")

        if not option_code:
            raise ValueError("option_code 不能为空")

        deleted_count = cls.model.delete().where(
            (cls.model.type_code == type_code) &
            (cls.model.option_code == option_code)
        ).execute()

        return deleted_count