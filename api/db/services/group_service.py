from api.db.db_models import DB, Group
from api.db.services.common_service import CommonService
from common.misc_utils import get_uuid
from common.time_utils import current_timestamp

class GroupService(CommonService):
    model = Group

    @classmethod
    @DB.connection_context()
    def save(cls, **kwargs):
        if "group_id" not in kwargs:
            kwargs["group_id"] = get_uuid()
        if "created_time" not in kwargs:
            kwargs["created_time"] = current_timestamp()
            
        obj = cls.model(**kwargs)
        obj.save(force_insert=True)
        return obj

    @classmethod
    @DB.connection_context()
    def get_name_by_id(cls, group_id):
        """
        通过组 ID 获取组名称
        Args:
            group_id: 组的唯一标识符 (UUID)
        Returns:
            str: 组名称，如果未找到则返回 None
        """
        try:
            # 从数据库查询指定 ID 的组记录
            group = cls.model.select().where(cls.model.group_id == group_id).first()

            # 如果找到了记录，返回名称；否则返回 None
            if group:
                return group.group_name
            return None
        except Exception as e:
            # 生产环境中建议记录日志，这里为了保持简洁直接返回 None
            print(f"Error fetching group name for {group_id}: {e}")
            return None


    # 通过库的创建者来获取
    @classmethod
    @DB.connection_context()
    def get_ids_by_created_by(cls, created_by_value):
        """
        通过创建者 (created_by) 获取所有相关记录的 ID 列表
        Args:
            created_by_value: 创建者的唯一标识
        Returns:
            list: 包含 ID 的列表 (例如: ['uuid-1', 'uuid-2']), 如果未找到则返回空列表 []
        """
        try:
            query = cls.model.select().where(cls.model.created_by == created_by_value)

            result_ids = [item.group_id for item in query]

            return result_ids

        except Exception as e:
            print(f"Error fetching ID list for created_by '{created_by_value}': {e}")
            return []  # 出错时返回空列表，保证程序不崩溃