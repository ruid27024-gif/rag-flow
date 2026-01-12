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
