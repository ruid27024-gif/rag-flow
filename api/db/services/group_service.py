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
            
        obj = cls.model(**kwargs).save(force_insert=True)
        return obj
