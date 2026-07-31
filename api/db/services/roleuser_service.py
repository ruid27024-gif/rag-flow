import logging

from api.db.db_models import DB, RoleUser, User
from api.db.services.common_service import CommonService
from common.time_utils import current_timestamp
import time

class RoleUserService(CommonService):
    model = RoleUser

    @classmethod
    def bind_persons(cls, role_id, phones, created_by=None):
        """
        一个用户只能绑定一个角色。
        一个角色可以绑定多个用户。
        """

        if not isinstance(phones, list):
            raise ValueError("phones 必须是数组")

        normalized_phones = list({
            str(phone).strip()
            for phone in phones
            if phone is not None and str(phone).strip()
        })

        if not normalized_phones:
            raise ValueError("phones 不能为空")

        role_id = int(role_id)

        # 根据 phone 对应 User.email 查询用户
        users = list(
            User
            .select(User.id, User.email)
            .where(User.email.in_(normalized_phones))
        )

        if not users:
            raise ValueError("未找到对应系统用户")

        user_ids = [
            str(user.id).strip()
            for user in users
            if user.id is not None
        ]

        if not user_ids:
            raise ValueError("未找到有效用户")

        now = int(time.time() * 1000)

        database = cls.model._meta.database

        with database.atomic():
            # 删除这些用户旧的角色关系
            cls.model.delete().where(
                cls.model.user_id.in_(user_ids)
            ).execute()

            # 给这些用户绑定新的角色
            rows = [
                {
                    "role_id": role_id,
                    "user_id": user_id,
                    "created_by": (
                        str(created_by)
                        if created_by is not None
                        else None
                    ),
                    "created_time": now,
                }
                for user_id in user_ids
            ]

            if rows:
                cls.model.insert_many(rows).execute()

        return True

    @classmethod
    @DB.connection_context()
    def get_bound_phones_by_role_id(cls, role_id):
        """
        查询某个角色已绑定的人员，
        返回的是 User.email，也就是前端树节点的 phone。
        """
        rows = cls.model.select(cls.model.user_id).where(
            cls.model.role_id == role_id
        )

        user_ids = [row.user_id for row in rows]

        if not user_ids:
            return []

        users = User.select(User.id, User.email).where(
            User.id.in_(user_ids)
        )

        phones = [
            user.email
            for user in users
            if user.email
        ]

        return phones
