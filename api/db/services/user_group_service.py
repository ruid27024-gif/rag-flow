from api.db.db_models import DB, UserGroup, UserTenant
from api.db.services.common_service import CommonService
from common.time_utils import current_timestamp


class UserGroupService(CommonService):
    model = UserGroup

    @classmethod
    @DB.connection_context()
    def save(cls, **kwargs):
        kwargs["created_time"] = current_timestamp()
        inst = cls.model(**kwargs)
        inst.save(force_insert=True)
        return inst

    @classmethod
    @DB.connection_context()
    def delete_by_user_group(cls, user_id: str, group_id: str):
        return cls.model.delete().where(
            (cls.model.user_id == user_id) & (cls.model.group_id == group_id)
        ).execute()

    # 同组队友拥有的租户
    @classmethod
    @DB.connection_context()
    def get_team_tenant_ids(cls, user_id: str):
        # 1. Get groups of the current user
        my_group_ids = cls.model.select(cls.model.group_id).where(cls.model.user_id == user_id)
        
        # 2. Get users in these groups (teammates)
        teammate_ids = cls.model.select(cls.model.user_id).where(cls.model.group_id.in_(my_group_ids))
        
        # 3. Get tenants owned by these teammates
        team_tenant_ids = UserTenant.select(UserTenant.tenant_id).where(
            UserTenant.user_id.in_(teammate_ids), 
            UserTenant.role == 'owner'
        )
        return [t.tenant_id for t in team_tenant_ids]

    @classmethod
    @DB.connection_context()
    def get_group_id_by_id(cls, id):
        """
        通过主键 ID 获取 group_id
        Args:
            id: 数据库记录的主键 ID
        Returns:
            str: group_id，如果未找到则返回 None
        """
        try:
            # 查询指定 ID 的记录
            # 只选择 group_id 字段，提高查询效率
            record = cls.model.select(cls.model.group_id).where(cls.model.user_id == id).first()

            # 如果找到记录，返回 group_id；否则返回 None
            if record:
                return record.group_id
            return None
        except Exception as e:
            # 记录错误日志（可选）
            print(f"Error fetching group_id by id {id}: {e}")
            return None

    @classmethod
    @DB.connection_context()
    def get_member_ids_by_group_id(cls, group_id):
        """
        修正版：确保只返回纯净的 user_id 字符串列表
        """
        try:
            # 1. 显式使用 cls.model.user_id 查询
            # 注意：确保 cls.model 指向的是截图中的这张表
            query = cls.model.select(cls.model.user_id).where(cls.model.group_id == group_id)

            # 2. 清洗数据：
            # x[0] 取出元组中的值
            # str() 确保转换为字符串 (防止是整数ID)
            ids = [str(x[0]) for x in query.tuples()]

            # 调试打印（上线后可删除）
            # print(f"Raw IDs from DB: {ids}")

            return ids

        except Exception as e:
            print(f"Error fetching member ids by group_id {group_id}: {e}")
            return []

    # # 通过user_id获取组
    # @classmethod
    # @DB.connection_context()
    # def get_group_ids_by_user_id(cls, user_id):
    #     """
    #     通过 User ID 获取该用户所属的所有组 ID 列表
    #     Args:
    #         user_id: 用户 ID
    #     Returns:
    #         list: 组 ID 组成的列表 (例如: ['group_uuid_1', 'group_uuid_2']), 如果未找到则返回空列表
    #     """
    #     try:
    #         # 1. 构建查询：筛选 user_id 匹配的记录，只选择 group_id 字段
    #         query = cls.model.select(cls.model.group_id).where(cls.model.id == user_id)
    #
    #         # 2. 提取结果
    #         # 使用 .tuples() 可以直接获取 (group_id,) 这样的元组列表，效率更高
    #         # 如果你的 group_id 是元组形式，直接返回 group_ids 即可
    #         # 如果想要纯字符串列表，可以使用列表推导式: [item[0] for item in query.tuples()]
    #         group_ids = [item[0] for item in query.tuples()]
    #
    #         return group_ids
    #
    #     except Exception as e:
    #         print(f"Error fetching group ids by user_id {user_id}: {e}")
    #         return []